"""Classical post-processing for BB84: error correction, verification, privacy amplification.

Everything Alice and Bob say to each other here goes over a public (authenticated)
channel, so every bit they reveal is counted as "leaked" and subtracted from the
final key length.

Error correction is written as a *dialogue*. Bob owns the corrupted key and drives
Cascade as a generator: it yields a request ("tell me Alice's parity of these index
sets") and receives Alice's answers. In one process `drive_locally` plays Alice; over
the network the generator lives on Bob's node and Alice's node answers the requests
in HTTP messages. It is the same algorithm either way.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Generator

import numpy as np

from .bb84 import h2

QBER_ABORT_THRESHOLD = 0.11  # Shor-Preskill: no secure key above ~11% error
MIN_KEY_BITS = 256  # we need an AES-256 key
PA_SECURITY_BITS = 30  # eps_pa = 2^-30 -> subtract 2*30 bits
VERIFY_BITS = 40  # residual errors slip past verification with probability 2^-40


def _parity(bits: np.ndarray, idx: np.ndarray) -> int:
    return int(bits[idx].sum() & 1)


# --------------------------------------------------------------------------- #
# Verification helpers (seeded, so both sides derive the same random masks)
# --------------------------------------------------------------------------- #
def verify_matrix(n: int, bits: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, 2, size=(bits, n), dtype=np.uint8)


def verify_tag(key: np.ndarray, h: np.ndarray) -> np.ndarray:
    return ((h.astype(np.int64) @ key.astype(np.int64)) & 1).astype(np.uint8)


# --------------------------------------------------------------------------- #
# Cascade error correction, as a dialogue
# --------------------------------------------------------------------------- #
# A request is ("parities", [index arrays]) or ("verify", seed, bits).
# The answer to "parities" is a list of 0/1 ints, one per index array.
# The answer to "verify" is a list of `bits` 0/1 ints.
Request = tuple
Dialogue = Generator[Request, list, tuple]


def cascade_corrector(
    bob: np.ndarray,
    qber: float,
    passes: int = 4,
    rng: np.random.Generator | None = None,
    shuffle_first: bool = False,
) -> Dialogue:
    """Cascade (Brassard & Salvail, 1993), Bob's side. Corrects `bob` in place.

    Each pass shuffles the key, splits it into blocks, and Alice reveals each block's
    parity. A block whose parity disagrees hides an odd number of errors; a binary
    search (one more revealed parity per step) pins one down and Bob flips it. A bit
    fixed in a later pass also re-opens earlier blocks that contained it ("cascading
    back"). Those re-checks are local: Alice's parities were already public.

    Returns (leaked_bits, errors_fixed).
    """
    rng = rng or np.random.default_rng()
    n = len(bob)
    leaked = 0
    fixed = 0
    k1 = max(4, int(math.ceil(0.73 / max(qber, 0.005))))
    blocks: list[list[np.ndarray]] = []
    block_of: list[np.ndarray] = []
    alice_par: list[list[int]] = []

    def locate(batch: list[np.ndarray]) -> Generator[Request, list, list[int]]:
        """Binary-search one error in each block (all disagree). Blocks run in parallel."""
        nonlocal leaked
        lo = [0] * len(batch)
        hi = [len(b) for b in batch]
        active = [i for i in range(len(batch)) if hi[i] - lo[i] > 1]
        while active:
            queries = [batch[i][lo[i] : (lo[i] + hi[i]) // 2] for i in active]
            answers = yield ("parities", queries)
            leaked += len(queries)
            still = []
            for i, q, a in zip(active, queries, answers):
                mid = (lo[i] + hi[i]) // 2
                if _parity(bob, q) != int(a):
                    hi[i] = mid  # the error is in the left half
                else:
                    lo[i] = mid  # the error is in the right half
                if hi[i] - lo[i] > 1:
                    still.append(i)
            active = still
        return [int(batch[i][lo[i]]) for i in range(len(batch))]

    for p in range(passes):
        k = k1 * (2**p)
        # Pass 0 uses the natural order; a retry round reshuffles it so that residual
        # errors that shared a block last time are split apart.
        perm = np.arange(n) if (p == 0 and not shuffle_first) else rng.permutation(n)
        pass_blocks = [perm[i : i + k] for i in range(0, n, k)]
        owner = np.empty(n, dtype=np.int32)
        for b, idx in enumerate(pass_blocks):
            owner[idx] = b
        blocks.append(pass_blocks)
        block_of.append(owner)

        answers = yield ("parities", pass_blocks)
        leaked += len(pass_blocks)
        alice_par.append([int(a) for a in answers])

        pending = {(p, b) for b, idx in enumerate(pass_blocks) if _parity(bob, idx) != alice_par[p][b]}
        while pending:
            # Smallest blocks first: cheapest searches, and fixing them often clears the rest.
            qp = min(q for q, _ in pending)
            group = sorted(b for q, b in pending if q == qp)
            positions = yield from locate([blocks[qp][b] for b in group])
            for pos in positions:  # blocks of one pass are disjoint, so positions are distinct
                bob[pos] ^= 1
            fixed += len(positions)
            if fixed > 2 * n:
                raise ValueError("Cascade did not converge: the parity answers are inconsistent")
            pending = {(q, b) for q, b in pending if q != qp}
            for pos in positions:
                for q in range(p + 1):
                    if q != qp:
                        pending.add((q, int(block_of[q][pos])))
            pending = {(q, b) for q, b in pending if _parity(bob, blocks[q][b]) != alice_par[q][b]}
    return leaked, fixed


def reconcile_corrector(
    bob: np.ndarray,
    qber: float,
    rng: np.random.Generator | None = None,
    max_rounds: int = 3,
    verify_bits: int = VERIFY_BITS,
) -> Dialogue:
    """Cascade plus verification, retried if verification fails. Bob's side.

    One Cascade round leaves residual errors in roughly 1 run in 200 (two errors that
    land in the same block on every pass cancel out in the parity). Verification
    catches that. Instead of throwing the whole session away, run another round on
    the partly corrected key with a fresh shuffle. Retries cost extra revealed bits,
    which are subtracted from the final key like any others.

    Returns (leaked_bits, errors_fixed, rounds, verified).
    """
    rng = rng or np.random.default_rng()
    leaked = fixed = 0
    for rnd in range(1, max_rounds + 1):
        l, f = yield from cascade_corrector(bob, qber, rng=rng, shuffle_first=rnd > 1)
        leaked += l
        fixed += f
        seed = int(rng.integers(0, 2**62))
        tags = yield ("verify", seed, verify_bits)
        leaked += verify_bits
        mine = verify_tag(bob, verify_matrix(len(bob), verify_bits, seed))
        if np.array_equal(mine, np.asarray(tags, dtype=np.uint8)):
            return leaked, fixed, rnd, True
    return leaked, fixed, max_rounds, False


def answer_request(alice: np.ndarray, request: Request) -> list[int]:
    """Alice's side: answer one request from Bob's dialogue using her own key."""
    if request[0] == "parities":
        return [_parity(alice, np.asarray(idx)) for idx in request[1]]
    if request[0] == "verify":
        _, seed, bits = request
        return verify_tag(alice, verify_matrix(len(alice), bits, seed)).tolist()
    raise ValueError(f"unknown request {request[0]!r}")


def drive_locally(dialogue: Dialogue, alice: np.ndarray):
    """Run a Bob-side dialogue in one process, with Alice answering from her key."""
    try:
        request = next(dialogue)
        while True:
            request = dialogue.send(answer_request(alice, request))
    except StopIteration as stop:
        return stop.value


@dataclass
class CascadeResult:
    corrected: np.ndarray  # Bob's key after correction
    leaked_bits: int  # parity bits revealed on the public channel
    errors_fixed: int
    passes: int


def cascade(
    alice: np.ndarray,
    bob: np.ndarray,
    qber: float,
    passes: int = 4,
    rng: np.random.Generator | None = None,
    shuffle_first: bool = False,
) -> CascadeResult:
    """One-process Cascade: Bob corrects towards Alice's key. See `cascade_corrector`."""
    alice = alice.astype(np.uint8)
    bob = bob.copy().astype(np.uint8)
    leaked, fixed = drive_locally(cascade_corrector(bob, qber, passes, rng, shuffle_first), alice)
    return CascadeResult(bob, leaked, fixed, passes)


def verify(
    alice: np.ndarray, bob: np.ndarray, bits: int = 40, rng: np.random.Generator | None = None
) -> tuple[bool, int]:
    """Compare `bits` random parity checks. Residual errors slip through with prob 2^-bits."""
    rng = rng or np.random.default_rng()
    h = rng.integers(0, 2, size=(bits, len(alice)), dtype=np.uint8)
    pa = (h @ alice.astype(np.int64)) & 1
    pb = (h @ bob.astype(np.int64)) & 1
    return bool(np.array_equal(pa, pb)), bits


@dataclass
class ReconcileResult:
    corrected: np.ndarray
    leaked_bits: int  # every parity and verification bit revealed, across all rounds
    errors_fixed: int
    rounds: int
    verified: bool


def reconcile(
    alice: np.ndarray,
    bob: np.ndarray,
    qber: float,
    rng: np.random.Generator | None = None,
    max_rounds: int = 3,
) -> ReconcileResult:
    """One-process Cascade + verification with retries. See `reconcile_corrector`."""
    alice = alice.astype(np.uint8)
    bob = bob.copy().astype(np.uint8)
    leaked, fixed, rounds, ok = drive_locally(reconcile_corrector(bob, qber, rng, max_rounds), alice)
    return ReconcileResult(bob, leaked, fixed, rounds, ok)


# --------------------------------------------------------------------------- #
# Privacy amplification
# --------------------------------------------------------------------------- #
def secret_key_length(n: int, qber_upper: float, leaked_bits: int) -> int:
    """How many truly secret bits survive.

    l = n * (1 - h2(q_upper)) - leaked - 2*log2(1/eps)

    The first term removes what Eve could know from the disturbance she caused,
    the second removes what the public error-correction chatter revealed.
    """
    l = n * (1.0 - h2(qber_upper)) - leaked_bits - 2 * PA_SECURITY_BITS
    return max(0, int(math.floor(l)))


def privacy_amplify(key: np.ndarray, out_bits: int, seed: np.ndarray) -> np.ndarray:
    """Toeplitz universal hashing: out = T @ key (mod 2).

    `seed` holds len(key) + out_bits - 1 random bits. It is announced publicly --
    security comes from the hash being universal, not from hiding it.
    """
    n = len(key)
    k = key.astype(np.int32)
    j = np.arange(n)[None, :]
    out = np.empty(out_bits, dtype=np.uint8)
    step = 256  # build the matrix a slab of rows at a time to keep memory small
    for r0 in range(0, out_bits, step):
        r1 = min(out_bits, r0 + step)
        i = np.arange(r0, r1)[:, None]
        slab = seed[i - j + (n - 1)].astype(np.int32)
        out[r0:r1] = ((slab @ k) & 1).astype(np.uint8)
    return out


def bits_to_bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits).tobytes()

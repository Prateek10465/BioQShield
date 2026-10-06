"""Classical post-processing for BB84: error correction, verification, privacy amplification.

Everything Alice and Bob say to each other here goes over a public (authenticated)
channel, so every bit they reveal is counted as "leaked" and subtracted from the
final key length.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .bb84 import h2

QBER_ABORT_THRESHOLD = 0.11  # Shor-Preskill: no secure key above ~11% error
MIN_KEY_BITS = 256  # we need an AES-256 key
PA_SECURITY_BITS = 30  # eps_pa = 2^-30 -> subtract 2*30 bits


# --------------------------------------------------------------------------- #
# Cascade error correction
# --------------------------------------------------------------------------- #
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
    """Cascade (Brassard & Salvail, 1993).

    Each pass shuffles the key, splits it into blocks, and compares block parities.
    A mismatching block hides an odd number of errors; a binary search (one
    revealed parity per step) locates and flips one. Fixing a bit in a later pass
    also re-checks earlier blocks that contained it ("cascading back").
    """
    rng = rng or np.random.default_rng()
    n = len(alice)
    bob = bob.copy().astype(np.uint8)
    alice = alice.astype(np.uint8)
    leaked = 0
    fixed = 0

    k1 = max(4, int(math.ceil(0.73 / max(qber, 0.005))))
    blocks: list[list[np.ndarray]] = []  # blocks[pass][block] -> index array
    block_of: list[np.ndarray] = []  # block_of[pass][position] -> block id
    alice_par: list[np.ndarray] = []  # Alice's published parity per block

    def parity(bits: np.ndarray, idx: np.ndarray) -> int:
        return int(bits[idx].sum() & 1)

    def binary_search(idx: np.ndarray) -> int:
        """Locate one error in a block whose parities disagree."""
        nonlocal leaked
        lo, hi = 0, len(idx)
        while hi - lo > 1:
            mid = (lo + hi) // 2
            left = idx[lo:mid]
            leaked += 1  # Alice reveals the parity of the left half
            if parity(alice, left) != parity(bob, left):
                hi = mid
            else:
                lo = mid
        return int(idx[lo])

    def resolve(start_pass: int, start_block: int, upto: int) -> None:
        nonlocal fixed
        stack = [(start_pass, start_block)]
        while stack:
            p, b = stack.pop()
            idx = blocks[p][b]
            if parity(bob, idx) == alice_par[p][b]:
                continue
            pos = binary_search(idx)
            bob[pos] ^= 1
            fixed += 1
            for q in range(upto + 1):
                if q != p:
                    stack.append((q, int(block_of[q][pos])))

    for p in range(passes):
        k = k1 * (2**p)
        # Pass 0 uses the natural order; a retry round reshuffles it so that residual
        # errors that shared a block last time are split apart.
        perm = np.arange(n) if (p == 0 and not shuffle_first) else rng.permutation(n)
        pass_blocks = [perm[i : i + k] for i in range(0, n, k)]
        bo = np.empty(n, dtype=np.int32)
        for b, idx in enumerate(pass_blocks):
            bo[idx] = b
        blocks.append(pass_blocks)
        block_of.append(bo)
        alice_par.append(np.array([parity(alice, idx) for idx in pass_blocks], dtype=np.uint8))
        leaked += len(pass_blocks)  # one parity per block is announced
        for b in range(len(pass_blocks)):
            resolve(p, b, p)

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
    """Cascade + verification, retried if verification fails.

    One Cascade round leaves residual errors in roughly 1 run in 200 (two errors that
    land in the same block on every pass cancel out in the parity). Verification
    catches that. Instead of throwing the whole session away, run another round on
    the partly corrected key with a fresh shuffle. Retries cost extra revealed bits,
    which are subtracted from the final key like any others.
    """
    rng = rng or np.random.default_rng()
    current = bob
    leaked = fixed = 0
    for rnd in range(1, max_rounds + 1):
        cas = cascade(alice, current, qber, rng=rng, shuffle_first=rnd > 1)
        current = cas.corrected
        ok, verify_bits = verify(alice, current, rng=rng)
        leaked += cas.leaked_bits + verify_bits
        fixed += cas.errors_fixed
        if ok:
            return ReconcileResult(current, leaked, fixed, rnd, True)
    return ReconcileResult(current, leaked, fixed, max_rounds, False)


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

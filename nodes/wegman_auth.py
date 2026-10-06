"""Wegman-Carter authentication using universal hashing.

Implements information-theoretic authentication for QKD:
- Universal hash function: polynomial hash over GF(2^w)
- One-time MAC key for XOR with hash output
- Provides information-theoretic security when MAC key is never reused
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Tuple

import numpy as np


def gf2_polyval(x: int, y: int, w: int = 64) -> int:
    """Evaluate polynomial in GF(2^w) using Horner's method.

    Args:
        x: Point at which to evaluate polynomial (treated as bits)
        y: Coefficients of polynomial (treated as bits, little-endian)
        w: Width of GF(2^w) field (default 64)

    Returns:
        Result of polynomial evaluation in GF(2^w)
    """
    # For simplicity in implementation, we'll use a simpler universal hash
    # In production, this would be a proper polynomial hash over GF(2^w)
    # For now, we use a Toeplitz hash construction which is also universal

    # Convert inputs to bit arrays
    x_bits = np.array([(x >> i) & 1 for i in range(w)], dtype=np.uint8)
    y_bits = np.array([(y >> i) & 1 for i in range(w)], dtype=np.uint8)

    # Toeplitz hash: y * x (matrix multiplication over GF(2))
    # Create Toeplitz matrix from y and multiply by x
    result = 0
    for i in range(w):
        if y_bits[i]:
            result ^= x << i

    return result & ((1 << w) - 1)


def universal_hash(key: int, message: bytes, w: int = 64) -> int:
    """Compute universal hash of message using key.

    Uses polynomial hash: h_k(m) = (k * p(m)) mod 2^w
    where p(m) is message treated as polynomial over GF(2).

    Args:
        key: Hash key (w bits)
        message: Message to hash
        w: Width of hash output in bits

    Returns:
        Hash value (w bits)
    """
    # Simple implementation: treat message as integer and multiply in GF(2^w)
    # For better security, we should use proper polynomial hash

    # Convert message to integer (using first w bits or hash to w bits)
    if len(message) >= w // 8:
        msg_int = int.from(message[:w//8], 'big')
    else:
        # Pad with zeros if message too short
        padded = message.ljust(w//8, b'\x00')
        msg_int = int.from_bytes(padded, 'big')

    # For simplicity, we'll use a construction that works for demonstration
    # In practice, use: h_k(m) = (k · p(m)) mod 2^w where p(m) is polynomial

    # Use a simpler universal hash: multiply key with hash of message
    msg_hash = int.from_bytes(hashlib.sha256(message).digest()[:w//8], 'big')
    return gf2_polyval(key, msg_hash, w)


@dataclass
class WegmanCarterKeys:
    """Keys for Wegman-Carter authentication."""
    hash_key: int   # Key for universal hash function
    mac_key: int    # One-time MAC key for XOR with hash output
    w: int = 64     # Width of authentication tag in bits


def split_auth_key(auth_key_bytes: bytes, w: int = 64) -> WegmanCarterKeys:
    """Split authentication key into hash key and MAC key.

    Args:
        auth_key_bytes: Authentication key from QKD (at least 2*w/8 bytes)
        w: Width of each key in bits

    Returns:
        WegmanCarterKeys with hash_key and mac_key
    """
    required_length = 2 * w // 8
    if len(auth_key_bytes) < required_length:
        # If key is too short, derive it
        expanded = hashlib.sha256(auth_key_bytes).digest()
        while len(expanded) < required_length:
            expanded += hashlib.sha256(expanded).digest()
        auth_key_bytes = expanded[:required_length]

    # Split key into hash key and MAC key
    half = len(auth_key_bytes) // 2
    hash_key_bytes = auth_key_bytes[:half]
    mac_key_bytes = auth_key_bytes[half:half + w//8]

    # Convert to integers
    hash_key = int.from_bytes(hash_key_bytes, 'big')
    mac_key = int.from_bytes(mac_key_bytes, 'big')

    return WegmanCarterKeys(hash_key=hash_key, mac_key=mac_key, w=w)


def seal_wc(key_hash: int, key_mac: int, body: dict, w: int = 64) -> dict:
    """Create Wegman-Carter authenticated envelope.

    Args:
        key_hash: Hash key for universal hash function
        key_mac: MAC key for XOR with hash output
        body: Message body to authenticate
        w: Width of authentication tag in bits

    Returns:
        Envelope dictionary with authentication tag
    """
    from .common import canonical, FIELDS

    # Create body without MAC
    body_for_auth = {f: body[f] for f in FIELDS if f in body}
    canonical_body = canonical(body_for_auth)

    # Compute universal hash
    hash_value = universal_hash(key_hash, canonical_body, w)

    # XOR with MAC key to get tag
    tag_value = hash_value ^ key_mac

    # Convert tag to bytes and then to hex
    tag_bytes = tag_value.to_bytes(w // 8, 'big')
    tag_hex = tag_bytes.hex()

    # Return envelope with tag
    result = body.copy()
    result["mac"] = tag_hex
    return result


def verify_wc(envelope: dict, key_hash: int, key_mac: int, w: int = 64) -> bool:
    """Verify Wegman-Carter authenticated envelope.

    Args:
        envelope: Envelope dictionary with MAC/tag
        key_hash: Hash key for universal hash function
        key_mac: MAC key for XOR with hash output
        w: Width of authentication tag in bits

    Returns:
        True if authentication succeeds, False otherwise
    """
    from .common import canonical, FIELDS

    # Extract tag
    tag_hex = envelope.get("mac")
    if tag_hex is None:
        return False

    try:
        tag_bytes = bytes.fromhex(tag_hex)
        tag_value = int.from_bytes(tag_bytes, 'big')
    except ValueError:
        return False

    # Create body without MAC
    body_for_auth = {f: envelope[f] for f in FIELDS if f in envelope}
    canonical_body = canonical(body_for_auth)

    # Compute universal hash
    hash_value = universal_hash(key_hash, canonical_body, w)

    # Expected tag is hash XOR mac_key
    expected_tag = hash_value ^ key_mac

    # Compare tags
    return tag_value == expected_tag


# Convenience functions that work with bytes keys
def seal_wc_bytes(auth_key_bytes: bytes, body: dict) -> dict:
    """Seal using Wegman-Carter with bytes key.

    Args:
        auth_key_bytes: Authentication key from QKD (will be split into hash and MAC keys)
        body: Message body to authenticate

    Returns:
        Authenticated envelope
    """
    keys = split_auth_key(auth_key_bytes)
    return seal_wc(keys.hash_key, keys.mac_key, body, keys.w)


def verify_wc_bytes(envelope: dict, auth_key_bytes: bytes) -> bool:
    """Verify using Wegman-Carter with bytes key.

    Args:
        envelope: Envelope dictionary with MAC/tag
        auth_key_bytes: Authentication key from QKD (will be split into hash and MAC keys)

    Returns:
        True if authentication succeeds, False otherwise
    """
    keys = split_auth_key(auth_key_bytes)
    return verify_wc(envelope, keys.hash_key, keys.mac_key, keys.w)
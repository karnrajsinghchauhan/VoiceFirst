"""Identifiers and hashes. Phone numbers are stored hashed wherever a raw number is not needed."""

from __future__ import annotations

import hashlib
import secrets
import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def new_trace_id() -> str:
    return secrets.token_hex(16)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def phone_hash(phone_e164: str, pepper: str) -> str:
    # Peppered so the hash cannot be reversed by enumerating the +91 number space.
    return sha256_hex(pepper + phone_e164)


def mask_booking_id(booking_id: str) -> str:
    """At most the last 4 characters are ever shown or spoken (10.4)."""
    tail = booking_id[-4:]
    return "*" * max(1, len(booking_id) - 4) + tail

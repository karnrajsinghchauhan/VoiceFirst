"""Written money formatting for messages (Indian digit grouping). Spoken read-back lives in voice/normalise.py."""

from __future__ import annotations

from decimal import Decimal

_SYMBOL = {"INR": "₹"}


def group_indian(integer_part: str) -> str:
    """1234567 -> 12,34,567: last three digits, then pairs."""
    if len(integer_part) <= 3:
        return integer_part
    head, tail = integer_part[:-3], integer_part[-3:]
    pairs: list[str] = []
    while len(head) > 2:
        pairs.insert(0, head[-2:])
        head = head[:-2]
    if head:
        pairs.insert(0, head)
    return ",".join(pairs) + "," + tail


def format_inr(value: str, currency: str) -> str:
    amount = Decimal(value)
    integer, _, fraction = f"{amount:.2f}".partition(".")
    text = group_indian(integer)
    if fraction != "00":
        text += "." + fraction
    symbol = _SYMBOL.get(currency)
    return f"{symbol}{text}" if symbol else f"{currency} {text}"

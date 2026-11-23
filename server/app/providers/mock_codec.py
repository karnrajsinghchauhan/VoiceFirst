"""Round-trippable text <-> 8 kHz audio codec behind the mock TTS and STT.

Each UTF-8 byte becomes two 10 ms 16-FSK symbols (one per nibble), so one
20 ms RTP packet carries exactly one byte. Line impairments (mu-law, loss,
noise, clipping) therefore corrupt characters in proportion to their
severity, which makes WER/CER through the line simulator meaningful without
any real speech model.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

SAMPLE_RATE = 8000
SYMBOL_SAMPLES = 80  # 10 ms
TONES_HZ = np.array([600 + 200 * k for k in range(16)], dtype=np.float64)
AMPLITUDE = 0.3
# Symbol energy below this fraction of a clean symbol's energy is an erasure (lost packet).
_ERASURE_FRACTION = 0.15
_ERASED = 0x3F  # "?"

_t = np.arange(SYMBOL_SAMPLES) / SAMPLE_RATE
_SYMBOLS = AMPLITUDE * np.sin(2 * np.pi * TONES_HZ[:, None] * _t[None, :])
_BASIS = np.exp(-2j * np.pi * TONES_HZ[:, None] * _t[None, :])
_CLEAN_ENERGY = float(np.abs(_SYMBOLS[0] @ _BASIS[0]) ** 2)

Float = npt.NDArray[np.float64]


def encode(text: str) -> Float:
    data = np.frombuffer(text.encode("utf-8"), dtype=np.uint8)
    nibbles = np.empty(data.size * 2, dtype=np.int64)
    nibbles[0::2] = data >> 4
    nibbles[1::2] = data & 0x0F
    if nibbles.size == 0:
        return np.zeros(0, dtype=np.float64)
    return np.asarray(_SYMBOLS[nibbles].reshape(-1), dtype=np.float64)


def decode(signal: Float) -> tuple[str, float]:
    """Returns (text, erasure_ratio). Undecodable bytes become U+FFFD or '?'."""
    n_symbols = signal.size // SYMBOL_SAMPLES
    if n_symbols < 2:
        return "", 0.0
    frames = signal[: n_symbols * SYMBOL_SAMPLES].reshape(n_symbols, SYMBOL_SAMPLES)
    energy = np.abs(frames @ _BASIS.T) ** 2
    best = energy.argmax(axis=1)
    erased = energy.max(axis=1) < _ERASURE_FRACTION * _CLEAN_ENERGY
    out = bytearray()
    erasures = 0
    for i in range(0, n_symbols - 1, 2):
        if erased[i] or erased[i + 1]:
            out.append(_ERASED)
            erasures += 1
            continue
        out.append(int(best[i]) << 4 | int(best[i + 1]))
    return out.decode("utf-8", errors="replace"), erasures / max(1, len(out))


def to_pcm16(signal: Float) -> bytes:
    return (np.clip(signal, -1.0, 1.0) * 32767).astype("<i2").tobytes()


def from_pcm16(pcm: bytes) -> Float:
    return np.asarray(np.frombuffer(pcm, dtype="<i2").astype(np.float64) / 32767, dtype=np.float64)

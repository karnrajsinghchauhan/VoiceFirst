"""Telephone line simulator (11.7).

8 kHz G.711 mu-law encode/decode; packet loss 0/1/3/5% with Gilbert-Elliott
bursts; jitter 20-80 ms against a fixed jitter buffer (late packets are lost);
noise at SNR 20/10/5 dB from generated sources (white, street, babble: all
synthesised here, so CC0 by construction, no downloads); clipping and AGC;
one-way delay 150-400 ms reported for the latency budget.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from app.providers.mock_codec import SAMPLE_RATE, Float

Bools = npt.NDArray[np.bool_]
Codes = npt.NDArray[np.uint8]

PACKET_SAMPLES = 160  # 20 ms
JITTER_BUFFER_MS = 60.0
_MU = 255.0


def mulaw_encode(signal: Float) -> Codes:
    x = np.clip(signal, -1.0, 1.0)
    y = np.sign(x) * np.log1p(_MU * np.abs(x)) / np.log1p(_MU)
    return np.asarray(np.round((y + 1) / 2 * 255), dtype=np.uint8)


def mulaw_decode(codes: Codes) -> Float:
    y = codes.astype(np.float64) / 255 * 2 - 1
    return np.asarray(np.sign(y) * np.expm1(np.abs(y) * np.log1p(_MU)) / _MU, dtype=np.float64)


@dataclass(frozen=True)
class LineProfile:
    name: str
    loss_pct: float
    jitter_ms: tuple[float, float]
    snr_db: float | None
    noise: str
    clip: bool
    delay_ms: float


PROFILES: dict[str, LineProfile] = {
    "clean": LineProfile("clean", 0.0, (20, 20), None, "white", False, 150),
    "loss_1": LineProfile("loss_1", 1.0, (20, 40), 20, "white", False, 200),
    "mobile_3g": LineProfile("mobile_3g", 3.0, (20, 80), 20, "white", False, 250),
    "loss_5": LineProfile("loss_5", 5.0, (40, 80), 10, "white", False, 300),
    "noisy_street": LineProfile("noisy_street", 1.0, (20, 60), 10, "street", True, 200),
    "tv_background": LineProfile("tv_background", 0.0, (20, 40), 10, "babble", False, 180),
    "worst": LineProfile("worst", 5.0, (60, 80), 5, "babble", True, 400),
}


@dataclass(frozen=True)
class LineStats:
    packets: int
    lost: int
    late: int
    delay_ms: float


def _gilbert_elliott(n: int, loss_pct: float, rng: np.random.Generator) -> Bools:
    """Bursty loss: mean burst length 1/p_bg packets, bad-state loss 80%."""
    if loss_pct == 0:
        return np.zeros(n, dtype=bool)
    loss_bad, p_bg = 0.8, 0.3
    p_bad = min(0.99, loss_pct / 100 / loss_bad)
    p_gb = p_bad * p_bg / (1 - p_bad)
    lost = np.zeros(n, dtype=bool)
    bad = False
    for i in range(n):
        bad = rng.random() < (1 - p_bg if bad else p_gb)
        lost[i] = bad and rng.random() < loss_bad
    return lost


def _noise(kind: str, n: int, rng: np.random.Generator) -> Float:
    white = rng.standard_normal(n)
    if kind == "white":
        return white
    if kind == "street":
        # Brownian rumble plus occasional horn tones.
        rumble = np.cumsum(white)
        rumble -= np.convolve(rumble, np.ones(400) / 400, mode="same")
        t = np.arange(n) / SAMPLE_RATE
        horn = np.sin(2 * np.pi * 440 * t) * (rng.random(n // 800 + 1).repeat(800)[:n] > 0.9)
        return np.asarray(rumble / (np.std(rumble) + 1e-9) + 2 * horn, dtype=np.float64)
    # Babble: several amplitude-modulated formant bands, like speech in a background TV.
    t = np.arange(n) / SAMPLE_RATE
    out = np.zeros(n)
    for f in rng.uniform(300, 3000, 6):
        envelope = 0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(2, 6) * t + rng.uniform(0, 6))
        out += envelope * np.sin(2 * np.pi * f * t + rng.uniform(0, 6))
    return np.asarray(out + 0.3 * white, dtype=np.float64)


def _agc_clip(signal: Float) -> Float:
    # A hot microphone gain clips peaks; the far-end AGC then pulls the level back down.
    hot = np.clip(signal * 2.5, -0.6, 0.6)
    peak = np.max(np.abs(hot)) or 1.0
    return np.asarray(hot * (0.5 / peak), dtype=np.float64)


class Line:
    def __init__(self, profile: LineProfile, seed: int) -> None:
        self.profile = profile
        self.rng = np.random.default_rng(seed)

    def transmit(self, signal: Float) -> tuple[Float, LineStats]:
        p = self.profile
        x = signal.copy()
        if p.clip:
            x = _agc_clip(x)
        if p.snr_db is not None and x.size:
            noise = _noise(p.noise, x.size, self.rng)
            sig_power = float(np.mean(x**2)) or 1e-12
            noise *= np.sqrt(sig_power / (10 ** (p.snr_db / 10)) / (np.mean(noise**2) + 1e-12))
            x = np.asarray(x + noise, dtype=np.float64)
        x = mulaw_decode(mulaw_encode(x))
        n_packets = -(-x.size // PACKET_SAMPLES)
        lost = _gilbert_elliott(n_packets, p.loss_pct, self.rng)
        jitter = self.rng.uniform(p.jitter_ms[0], p.jitter_ms[1], n_packets)
        late = jitter - p.jitter_ms[0] > JITTER_BUFFER_MS
        dropped = lost | late
        for i in np.flatnonzero(dropped):
            # No packet-loss concealment: a dropped packet is silence, which the codec reads as erasure.
            x[i * PACKET_SAMPLES : (i + 1) * PACKET_SAMPLES] = 0.0
        delay = p.delay_ms + float(np.mean(jitter)) if n_packets else p.delay_ms
        return x, LineStats(n_packets, int(lost.sum()), int((late & ~lost).sum()), delay)


def char_error_rate(reference: str, hypothesis: str) -> float:
    return _edit_distance(list(reference), list(hypothesis)) / max(1, len(reference))


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref = reference.split()
    return _edit_distance(ref, hypothesis.split()) / max(1, len(ref))


def _edit_distance(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from app.providers import mock_codec
from app.simulator.line import (
    PROFILES,
    Line,
    _gilbert_elliott,
    mulaw_decode,
    mulaw_encode,
    word_error_rate,
)


@settings(max_examples=50)
@given(st.text(max_size=60))
def test_codec_round_trips_clean(text: str) -> None:
    decoded, erasures = mock_codec.decode(mock_codec.encode(text))
    assert decoded == text and erasures == 0


def test_mulaw_round_trip_error_is_small() -> None:
    x = np.sin(np.linspace(0, 20, 8000)) * 0.5
    assert np.max(np.abs(mulaw_decode(mulaw_encode(x)) - x)) < 0.02


def test_gilbert_elliott_mean_loss_and_bursts() -> None:
    rng = np.random.default_rng(0)
    lost = _gilbert_elliott(200_000, 3.0, rng)
    assert 0.02 < lost.mean() < 0.04
    runs = np.diff(np.flatnonzero(np.diff(lost.astype(int)) != 0))
    assert runs.size and lost.sum() / max(1, (np.diff(lost.astype(int)) == 1).sum()) > 1.2  # bursty


def test_impairment_degrades_wer_monotonically_on_average() -> None:
    text = "haan ji, bhej dijiye. main shaam ko saat baje ke baad free hoon " * 3
    signal = mock_codec.encode(text)

    def mean_wer(profile: str) -> float:
        out = [
            mock_codec.decode(Line(PROFILES[profile], s).transmit(signal)[0])[0] for s in range(10)
        ]
        return float(np.mean([word_error_rate(text, h) for h in out]))

    assert mean_wer("clean") == 0.0
    assert mean_wer("clean") <= mean_wer("loss_1") <= mean_wer("worst")
    assert mean_wer("worst") > 0.05


def test_profiles_cover_brief_ranges() -> None:
    losses = {p.loss_pct for p in PROFILES.values()}
    snrs = {p.snr_db for p in PROFILES.values()}
    assert {0.0, 1.0, 3.0, 5.0} <= losses and {20, 10, 5} <= snrs
    assert all(150 <= p.delay_ms <= 400 for p in PROFILES.values())
    assert all(p.jitter_ms[0] >= 20 and p.jitter_ms[1] <= 80 for p in PROFILES.values())

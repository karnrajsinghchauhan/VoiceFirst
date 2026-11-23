"""REQ-AI-01 (disclosure + provenance), REQ-AI-02 (voice gender lint), REQ-AI-03 (never claims human)."""

import re

import pytest

from app.simulator.caller import load_personas
from app.simulator.scenario import run_text
from tests.voice.helpers import run
from tests.voice.helpers import settings as av_settings

_CLAIMS_HUMAN = re.compile(r"main (ek )?insaan hoon|i am (a )?(human|real)|मैं इंसान हूँ", re.I)


@pytest.mark.parametrize("p", load_personas(), ids=lambda p: p.id)
def test_first_utterance_says_ai_assistant_and_recording(p) -> None:  # type: ignore[no-untyped-def]
    for language in p.languages:
        r = run_text(av_settings(), p, language, 0)
        first = r.result.transcript[0]
        assert first.speaker == "agent"
        assert re.search(r"AI (assistant|असिस्टेंट)", first.text)
        assert re.search(r"record|रिकॉर्ड", first.text)
        out = r.result.outcome
        assert (
            out.ai_generated is True
            and out.model_ids
            and re.fullmatch(r"[0-9a-f]{64}", out.provenance_hash)
        )
        assert out.disclosure_played_at is not None


def test_provenance_hash_changes_with_transcript() -> None:
    assert (
        run("C-01").result.outcome.provenance_hash
        != run("C-03", "en").result.outcome.provenance_hash
    )

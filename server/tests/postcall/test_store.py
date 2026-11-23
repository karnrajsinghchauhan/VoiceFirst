import pytest
from cryptography.fernet import Fernet

from app.core.errors import (
    ConfigError,
    NotFoundError,
    ProductionConfigError,
    StateConflictError,
)
from app.postcall.crypto import DataCipher
from app.postcall.models import TranscriptRow
from app.postcall.settings import (
    DEV_DATA_KEY,
    PostcallSettings,
    validate_postcall_for_production,
)
from app.postcall.store import (
    TranscriptTurn,
    get_outcome,
    list_outcomes,
    read_transcript,
    record_outcome,
    store_transcript,
)
from tests.outcome_factory import make_outcome


def test_outcome_round_trip_and_publish(session, bus, clock):
    outcome = make_outcome(clock.now())
    record_outcome(session, bus, outcome, "ph")
    assert get_outcome(session, outcome.call_id) == outcome
    assert list_outcomes(session, 10) == [outcome]
    key, payload = bus.messages["av.call-outcomes.v1"][0]
    assert key == outcome.booking_id
    assert payload["call_id"] == outcome.call_id


def test_outcome_is_recorded_once(session, bus, clock):
    outcome = make_outcome(clock.now())
    record_outcome(session, bus, outcome, "ph")
    with pytest.raises(StateConflictError):
        record_outcome(session, bus, outcome, "ph")


def test_missing_outcome_raises(session):
    with pytest.raises(NotFoundError):
        get_outcome(session, "call_nope")


def test_transcript_redacted_before_encryption(session, clock):
    cipher = DataCipher(DEV_DATA_KEY)
    turns = [
        TranscriptTurn("agent", "Namaste ji"),
        TranscriptTurn("customer", "mera card 4111 1111 1111 1111 hai aur OTP 4 5 8 2 9 1"),
    ]
    store_transcript(session, cipher, call_id="c1", phone_hash="ph", at=clock.now(), turns=turns)
    row = session.get(TranscriptRow, "c1")
    assert b"4111" not in row.ciphertext and b"Namaste" not in row.ciphertext
    back = read_transcript(session, cipher, "c1")
    assert back[0].text == "Namaste ji"
    assert "4111" not in back[1].text and "[REDACTED_PAN]" in back[1].text
    assert "[REDACTED_OTP]" in back[1].text


def test_wrong_key_cannot_read(session, clock):
    store_transcript(
        session,
        DataCipher(DEV_DATA_KEY),
        call_id="c1",
        phone_hash="ph",
        at=clock.now(),
        turns=[TranscriptTurn("agent", "hi")],
    )
    other = DataCipher(Fernet.generate_key().decode())
    with pytest.raises(StateConflictError):
        read_transcript(session, other, "c1")


def test_invalid_key_fails_at_construction():
    with pytest.raises(ConfigError):
        DataCipher("not-a-key")


def test_production_rejects_dev_key():
    with pytest.raises(ProductionConfigError):
        validate_postcall_for_production(PostcallSettings())
    validate_postcall_for_production(PostcallSettings(data_key=Fernet.generate_key().decode()))

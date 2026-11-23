"""11.4 compliance proof: dial is invoked iff all gates pass.

Bookings, consent, DND, CLI states, clocks, complaints and the kill switch vary
freely. The oracle below re-derives the rules from the brief in plain Python,
independently of app/compliance/gates.py, and every dial attempt must agree
with it. Example count: AV_PROOF_EXAMPLES (10,000 in CI, 100,000 nightly).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from hypothesis import HealthCheck
from hypothesis import event as hypothesis_event
from hypothesis import settings as hsettings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, rule

from app.compliance.complaints import ingest_complaint, lift_campaign_pause
from app.compliance.consent import mark_dnc, record_consent
from app.compliance.evaluate import evaluate
from app.compliance.holdout import is_held_out
from app.compliance.killswitch import engage, release
from app.compliance.models import CliRow
from app.contracts.generated.complaint import Complaint
from app.core.bus import MemoryBus
from app.core.clock import FrozenClock
from app.core.db import Base, create_all, make_engine, make_session_factory
from app.core.errors import GateError
from app.core.ids import new_id, new_trace_id, sha256_hex
from app.providers.telephony.mock import MockTelephony
from app.telephony.dial import dial
from tests.factories import (
    booking_id_with_holdout,
    make_event,
    make_settings,
    seed_cli,
    seed_consent,
    seed_preference,
)

IST = ZoneInfo("Asia/Kolkata")
START = datetime(2026, 11, 23, 4, 30, tzinfo=UTC)  # 10:00 IST: inside the window

PHONES = ("+919812345678", "+917012345678", "+14155550100")
CLIS = {
    # cli: (series, purpose, declared)
    "+911600000001": ("1600", "transactional", True),
    "+911601000002": ("1601", "service", True),
    "+91140000003": ("140", "promotional", True),
    "+911600000004": ("1600", "transactional", False),
}
PURPOSES = ("J1", "J2", "J7")
# The pilot contract allows consent only for J1/J2; J7 attempts must always be refused.
CONSENT_PURPOSES = ("J1", "J2")
CATEGORY = {"J1": "transactional", "J2": "service", "J7": "promotional"}
EXAMPLES = int(os.environ.get("AV_PROOF_EXAMPLES", "10000"))

# One engine for the whole run; each example starts from empty tables. Creating the
# schema per example dominated runtime.
_ENGINE = make_engine("sqlite://")
create_all(_ENGINE)
_FACTORY = make_session_factory(_ENGINE)


def _wipe() -> None:
    with _ENGINE.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@dataclass
class Consent:
    basis: str
    purpose: str
    booking_id: str | None
    obtained_at: datetime
    expires_at: datetime | None
    revoked: bool = False


@dataclass
class Oracle:
    signoff: bool
    held_out: dict[str, bool]
    phone_of: dict[str, str]
    kill: bool = False
    paused_all: bool = False
    cli_status: dict[str, str] = field(default_factory=lambda: dict.fromkeys(CLIS, "active"))
    complaints: list[tuple[str, datetime]] = field(default_factory=list)
    consents: dict[str, list[Consent]] = field(default_factory=dict)
    dnd: dict[str, str] = field(default_factory=dict)
    opted_out_at: dict[str, datetime] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=dict)
    last_dial: dict[str, datetime] = field(default_factory=dict)

    def live(self, phone: str, purpose: str, booking: str, now: datetime) -> list[Consent]:
        out = []
        for c in self.consents.get(phone, []):
            if c.revoked or c.purpose != purpose:
                continue
            if c.basis == "transaction":
                if c.booking_id == booking:
                    out.append(c)
            elif c.expires_at is not None and now < c.expires_at:
                out.append(c)
        return out

    def allows(self, booking: str, cli: str, purpose: str, now: datetime) -> bool:
        phone = self.phone_of[booking]
        if self.held_out[booking]:
            return False
        if not (phone.startswith("+91") and len(phone) == 13 and phone[3] in "6789"):
            return False
        if self.kill or self.paused_all:
            return False
        if not [c for c in self.consents.get(phone, []) if c.purpose == purpose]:
            return False
        live = self.live(phone, purpose, booking, now)
        if not live:
            return False
        if self.dnd.get(phone, "none") != "none":
            j1_ok = purpose == "J1" and self.signoff and any(c.basis == "transaction" for c in live)
            if not j1_ok:
                return False
        if phone in self.opted_out_at and not any(
            c.basis == "explicit" and c.obtained_at > self.opted_out_at[phone] for c in live
        ):
            return False
        series, cli_purpose, declared = CLIS[cli]
        if not declared:
            return False
        promo = CATEGORY[purpose] == "promotional"
        if promo != (series == "140") or promo != (cli_purpose == "promotional"):
            return False
        if self.cli_status[cli] != "active":
            return False
        local = now.astimezone(IST)
        if not (9 <= local.hour < 21):
            return False
        if self.attempts.get(booking, 0) >= 2:
            return False
        last = self.last_dial.get(phone)
        return last is None or now - last >= timedelta(hours=24)


class DialProof(RuleBasedStateMachine):
    @initialize(signoff=st.booleans())
    def setup(self, signoff: bool) -> None:
        overrides = (
            {"compliance": {"dnd_j1_transaction_signoff_ref": "COUNSEL-1"}} if signoff else {}
        )
        self.settings = make_settings(**overrides)
        _wipe()
        self.session = _FACTORY()
        self.clock = FrozenClock(START)
        self.bus = MemoryBus()
        self.tel = MockTelephony()
        s = self.settings
        ids = {
            "b0": (booking_id_with_holdout(s, False, 0), PHONES[0]),
            "b1": (booking_id_with_holdout(s, False, 500), PHONES[1]),
            "b2": (booking_id_with_holdout(s, True, 0), PHONES[0]),
            "b3": (booking_id_with_holdout(s, False, 900), PHONES[2]),
        }
        self.events = {
            key: make_event(s, booking_id=bid, customer={"phone_e164": phone})
            for key, (bid, phone) in ids.items()
        }
        for cli, (series, purpose, declared) in CLIS.items():
            seed_cli(
                self.session,
                s,
                cli_e164=cli,
                series=series,
                purpose=purpose,
                a2p_declared=declared,
                declaration_ref="D-1" if declared else None,
            )
        self.oracle = Oracle(
            signoff=signoff,
            held_out={
                k: is_held_out(s.holdout.experiment_salt, e.booking_id, s.holdout.percent)
                for k, e in self.events.items()
            },
            phone_of={k: e.customer.phone_e164 for k, e in self.events.items()},
        )
        self.oracle.phone_of = {e.booking_id: e.customer.phone_e164 for e in self.events.values()}
        # A dialable baseline (J1 transaction consent for every booking) so that both
        # outcomes are exercised; the rules then take it apart.
        for key in self.events:
            self.transaction_consent(key, "J1")
        self.oracle.held_out = {
            e.booking_id: is_held_out(s.holdout.experiment_salt, e.booking_id, s.holdout.percent)
            for e in self.events.values()
        }

    @rule(minutes=st.integers(min_value=1, max_value=60 * 50))
    def advance(self, minutes: int) -> None:
        self.clock.advance(timedelta(minutes=minutes))

    @rule(on=st.booleans())
    def kill_switch(self, on: bool) -> None:
        fn = engage if on else release
        fn(
            self.session,
            self.bus,
            self.clock,
            tenant_id=self.settings.tenant_id,
            actor="t",
            role="admin",
            reason="proof",
        )
        self.oracle.kill = on

    @rule(
        cli=st.sampled_from(sorted(CLIS)), status=st.sampled_from(["active", "paused", "retired"])
    )
    def set_cli_status(self, cli: str, status: str) -> None:
        row = self.session.get(CliRow, cli)
        assert row is not None
        row.status = status  # type: ignore[assignment]
        self.session.flush()
        self.oracle.cli_status[cli] = status

    @rule(cli=st.sampled_from(sorted(CLIS)), who=st.sampled_from(["a", "b", "c"]))
    def complaint(self, cli: str, who: str) -> None:
        now = self.clock.now()
        ingest_complaint(
            self.session,
            self.bus,
            self.settings,
            Complaint(
                schema_version="1.0.0",
                tenant_id=self.settings.tenant_id,
                trace_id=new_trace_id(),
                complaint_id=new_id("cmp"),
                cli_e164=cli,
                complainant_hash=sha256_hex(who),
                received_at=now,
                source="dlt_forwarded",
                ai_flagged=True,
                dlt_ref=None,
            ),
        )
        self.oracle.cli_status[cli] = "paused"
        self.oracle.complaints.append((who, now))
        window = {w for w, at in self.oracle.complaints if at >= now - timedelta(days=10)}
        if len(window) >= 2:
            self.oracle.paused_all = True

    @rule()
    def lift_pause(self) -> None:
        lift_campaign_pause(self.session, self.settings.tenant_id, self.clock.now(), "ops")
        self.oracle.paused_all = False

    @rule(
        booking=st.sampled_from(["b0", "b1", "b2", "b3"]), purpose=st.sampled_from(CONSENT_PURPOSES)
    )
    def transaction_consent(self, booking: str, purpose: str) -> None:
        event = self.events[booking]
        now = self.clock.now()
        seed_consent(self.session, self.settings, event, purpose=purpose, obtained_at=now)
        self.oracle.consents.setdefault(event.customer.phone_e164, []).append(
            Consent("transaction", purpose, event.booking_id, now, None)
        )

    @rule(phone=st.sampled_from(PHONES), purpose=st.sampled_from(CONSENT_PURPOSES))
    def explicit_consent(self, phone: str, purpose: str) -> None:
        now = self.clock.now()
        rec = record_consent(
            self.session,
            self.settings,
            phone_e164=phone,
            basis="explicit",
            purpose=purpose,
            channel="whatsapp",
            obtained_at=now,
            booking_id=None,
            source_ref="proof",
            trace_id=new_trace_id(),
        )
        self.oracle.consents.setdefault(phone, []).append(
            Consent("explicit", purpose, None, now, rec.expires_at)
        )

    @rule(phone=st.sampled_from(PHONES))
    def opt_out(self, phone: str) -> None:
        now = self.clock.now()
        mark_dnc(
            self.session, self.settings, phone_e164=phone, at=now, channel="voice", call_id=None
        )
        for c in self.oracle.consents.get(phone, []):
            c.revoked = True
        self.oracle.opted_out_at[phone] = now

    @rule(
        phone=st.sampled_from(PHONES),
        state=st.sampled_from(["none", "block_promo", "partial", "fully_blocked"]),
    )
    def dnd(self, phone: str, state: str) -> None:
        seed_preference(self.session, self.settings, phone, state)
        self.oracle.dnd[phone] = state

    @rule(
        booking=st.sampled_from(["b0", "b1", "b2", "b3"]),
        cli=st.sampled_from(sorted(CLIS)),
        purpose=st.sampled_from(PURPOSES),
    )
    def attempt(self, booking: str, cli: str, purpose: str) -> None:
        event = self.events[booking]
        now = self.clock.now()
        expected = self.oracle.allows(event.booking_id, cli, purpose, now)
        before = len(self.tel.placed)
        try:
            clearance = evaluate(
                self.session, self.bus, self.settings, self.clock, event, purpose, cli
            )  # type: ignore[arg-type]
            dial(
                self.session,
                clearance,
                self.tel,
                self.clock,
                self.settings.tenant_id,
                self.settings.phone_pepper,
            )
        except GateError:
            pass
        dialled = len(self.tel.placed) == before + 1
        assert dialled == expected, (booking, cli, purpose, now, self.oracle)
        hypothesis_event("dialled" if dialled else "refused")
        if dialled:
            self.oracle.attempts[event.booking_id] = (
                self.oracle.attempts.get(event.booking_id, 0) + 1
            )
            self.oracle.last_dial[event.customer.phone_e164] = now

    def teardown(self) -> None:
        if hasattr(self, "session"):
            self.session.rollback()
            self.session.close()


# Four shards so `pytest -n 4` spreads the examples over cores; the total is EXAMPLES.
SHARDS = 4
_SETTINGS = hsettings(
    max_examples=EXAMPLES // SHARDS,
    stateful_step_count=20,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)


class DialProofShard1(DialProof):
    pass


class DialProofShard2(DialProof):
    pass


class DialProofShard3(DialProof):
    pass


class DialProofShard4(DialProof):
    pass


TestDialProofShard1 = DialProofShard1.TestCase
TestDialProofShard2 = DialProofShard2.TestCase
TestDialProofShard3 = DialProofShard3.TestCase
TestDialProofShard4 = DialProofShard4.TestCase
for _case in (TestDialProofShard1, TestDialProofShard2, TestDialProofShard3, TestDialProofShard4):
    _case.settings = _SETTINGS

"""REQ-TRAI-06: any complaint pauses its CLI; 2 unique complainants in 10 days pause everything."""

from datetime import timedelta

import pytest

from app.compliance.complaints import ingest_complaint, lift_campaign_pause
from app.compliance.evaluate import evaluate
from app.compliance.models import CliRow
from app.compliance.repository import campaigns_paused
from app.contracts.generated.complaint import Complaint
from app.core.errors import CliPausedError, KillSwitchEngagedError
from app.core.ids import new_id, new_trace_id, sha256_hex
from app.incidents.service import list_open
from tests.factories import SERVICE_CLI, make_event, seed_cli, seed_consent

OTHER_CLI = "+911601999888"


def complaint(settings, at, who: str, cli: str = SERVICE_CLI, ai_flagged: bool = True):
    return Complaint(
        schema_version="1.0.0",
        tenant_id=settings.tenant_id,
        trace_id=new_trace_id(),
        complaint_id=new_id("cmp"),
        cli_e164=cli,
        complainant_hash=sha256_hex(who),
        received_at=at,
        source="dlt_forwarded",
        ai_flagged=ai_flagged,
        dlt_ref="DLT-CMP-1",
    )


def test_single_complaint_pauses_that_cli_only(session, settings, clock, bus):
    seed_cli(session, settings)
    seed_cli(session, settings, cli_e164=OTHER_CLI, series="1601")
    out = ingest_complaint(session, bus, settings, complaint(settings, clock.now(), "a"))
    assert out.cli_paused and not out.campaigns_paused
    assert session.get(CliRow, SERVICE_CLI).status == "paused"
    assert session.get(CliRow, OTHER_CLI).status == "active"
    event = make_event(settings)
    seed_consent(session, settings, event)
    with pytest.raises(CliPausedError):
        evaluate(session, bus, settings, clock, event, "J1", SERVICE_CLI)
    evaluate(session, bus, settings, clock, event, "J1", OTHER_CLI)


def test_two_unique_in_ten_days_pause_all_and_page(session, settings, clock, bus):
    seed_cli(session, settings)
    seed_cli(session, settings, cli_e164=OTHER_CLI, series="1601")
    ingest_complaint(session, bus, settings, complaint(settings, clock.now(), "a"))
    out = ingest_complaint(
        session, bus, settings, complaint(settings, clock.now() + timedelta(days=9), "b", OTHER_CLI)
    )
    assert out.campaigns_paused
    assert campaigns_paused(session, settings.tenant_id)
    assert any("complaint guardrail" in i.summary for i in list_open(session, settings.tenant_id))
    event = make_event(settings)
    seed_consent(session, settings, event)
    with pytest.raises(KillSwitchEngagedError):
        evaluate(session, bus, settings, clock, event, "J1", OTHER_CLI)


def test_same_complainant_twice_is_one_unique(session, settings, clock, bus):
    seed_cli(session, settings)
    ingest_complaint(session, bus, settings, complaint(settings, clock.now(), "a"))
    out = ingest_complaint(
        session, bus, settings, complaint(settings, clock.now() + timedelta(days=1), "a")
    )
    assert not out.campaigns_paused


def test_complaints_outside_window_do_not_combine(session, settings, clock, bus):
    seed_cli(session, settings)
    ingest_complaint(session, bus, settings, complaint(settings, clock.now(), "a"))
    out = ingest_complaint(
        session,
        bus,
        settings,
        complaint(settings, clock.now() + timedelta(days=10, seconds=1), "b"),
    )
    assert not out.campaigns_paused


@pytest.mark.parametrize(("ai_flagged", "limit"), [(True, 3), (False, 5)])
def test_trai_threshold_tracking(session, settings, clock, bus, ai_flagged, limit):
    seed_cli(session, settings)
    outs = [
        ingest_complaint(
            session, bus, settings, complaint(settings, clock.now(), str(i), ai_flagged=ai_flagged)
        )
        for i in range(limit)
    ]
    assert [o.trai_threshold_reached for o in outs] == [False] * (limit - 1) + [True]


def test_pause_lifts_only_by_explicit_action(session, settings, clock, bus):
    seed_cli(session, settings)
    for who in ("a", "b"):
        ingest_complaint(session, bus, settings, complaint(settings, clock.now(), who))
    lift_campaign_pause(session, settings.tenant_id, clock.now(), "ops@prosperops")
    assert not campaigns_paused(session, settings.tenant_id)

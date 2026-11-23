"""The real port implementations the API is wired with."""

from datetime import timedelta

import pytest

from app.campaigns.models import QueueItemRow
from app.campaigns.service import CampaignPort
from app.core.errors import NotFoundError
from app.incidents.api_port import IncidentPort


def test_incident_kinds_map_to_regulatory_clocks(session_factory, settings, clock):
    port = IncidentPort(session_factory, settings.tenant_id)
    t = clock.now()
    sec = port.open_incident("security", "login anomaly", t, "ops")
    assert sec.cert_in_due_at == t + timedelta(hours=6) and sec.board_report_due_at is None
    breach = port.open_incident("data_breach", "bucket exposed", t, "ops")
    assert breach.board_report_due_at == t + timedelta(hours=72)
    assert breach.cert_in_due_at == t + timedelta(hours=6)
    other = port.open_incident("telecom_complaint", "spike", t, "ops")
    assert other.cert_in_due_at is None and other.board_report_due_at is None
    kinds = sorted(v.kind for v in port.list_incidents())
    # A data breach also opens its CERT-In record, listed as a security incident.
    assert kinds == ["data_breach", "other", "security", "security"]


def test_campaign_pause_stops_the_dispatcher_taking_items(session_factory, settings, clock):
    port = CampaignPort(session_factory, settings.tenant_id, clock)
    assert [c.status for c in port.list_campaigns()] == ["active", "active"]
    paused = port.pause("cmp_j1", "ops", "drill")
    assert paused.status == "paused"
    assert port.resume("cmp_j1", "ops", "done").status == "active"
    with pytest.raises(NotFoundError):
        port.pause("cmp_j9", "ops", "x")


def test_paused_purpose_is_skipped_by_dispatcher_query(session_factory, settings, clock):
    from app.campaigns.dispatcher import Dispatcher
    from app.campaigns.journeys import JourneyRules
    from app.core.bus import MemoryBus
    from app.providers.telephony.mock import MockTelephony

    with session_factory() as s:
        s.add(QueueItemRow(item_id="q1", tenant_id=settings.tenant_id, booking_event_id="e",
                           booking_id="b", purpose="J1", cli_e164="+911600123456",
                           due_at=clock.now(), state="queued", attempts=0, last_reason=None,
                           last_call_id=None, last_outcome=None, last_dialled_at=None,
                           updated_at=clock.now()))
        s.commit()
    CampaignPort(session_factory, settings.tenant_id, clock).pause("cmp_j1", "ops", "drill")
    dispatcher = Dispatcher(session_factory=session_factory, bus=MemoryBus(), settings=settings,
                            clock=clock, telephony=MockTelephony(), runner=None,  # type: ignore[arg-type]
                            fallback=None,  # type: ignore[arg-type]
                            cli_by_purpose={"J1": "+911600123456", "J2": "+911601123456"},
                            rules=JourneyRules())
    assert dispatcher._take_next_due() is None

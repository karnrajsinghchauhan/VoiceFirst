"""REQ-DPDP-10: SDF readiness: DPIA inputs, audit logs, model-risk notes exist."""

from pathlib import Path

DOC = (Path(__file__).parents[3] / "docs/dpia-inputs.md").read_text()


def test_dpia_inputs_cover_required_sections() -> None:
    for needle in ("Processing record", "Retention", "Audit logs", "Model-risk", "subprocessors"):
        assert needle in DOC


def test_audit_rows_are_written_for_privileged_actions(session, settings, clock, bus) -> None:
    from app.compliance.killswitch import engage
    from app.core.audit import AuditRow

    engage(
        session,
        bus,
        clock,
        tenant_id=settings.tenant_id,
        actor="karn",
        role="admin",
        reason="drill",
    )
    row = session.query(AuditRow).one()
    assert (row.actor, row.action, row.reason) == ("karn", "kill_switch.engage", "drill")
    assert bus.messages["av.audit.v1"][0][1]["actor"] == "karn"

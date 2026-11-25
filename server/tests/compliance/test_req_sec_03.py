"""REQ-SEC-03: ICT logs 180 days rolling, producible within India, clocks synced to NIC/NPL NTP."""

import pytest
from pydantic import ValidationError

from tests.factories import make_settings


def test_defaults() -> None:
    s = make_settings()
    assert s.retention.ict_log_days >= 180
    assert all(server.endswith(".nic.in") or "npl" in server for server in s.ntp_servers)


def test_shorter_retention_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(retention={"ict_log_days": 179})


def test_kafka_topic_retention_documented() -> None:
    from pathlib import Path

    doc = (Path(__file__).parents[3] / "contracts/kafka-topics.md").read_text()
    assert "av.audit.v1" in doc and "180 days" in doc


def test_helm_values_pin_ntp_and_retention() -> None:
    from pathlib import Path

    values = (Path(__file__).parents[3] / "deploy/helm/agoda-voice/values.yaml").read_text()
    assert "samay1.nic.in" in values and "ictLogDays: 180" in values

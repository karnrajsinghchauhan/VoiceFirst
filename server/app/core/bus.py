"""Event bus. One interface; `kafka` (Kafka API: Redpanda locally, Agoda Kafka in prod) or `memory` (D-003).

Every message is validated against its contract model before publish; topics are
keyed by booking_id where the record has one (contracts/kafka-topics.md).
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Literal, Protocol

from pydantic import BaseModel

from app.core.errors import ConfigError, ProviderError

Topic = Literal[
    "av.booking-events.v1",
    "av.gate-decisions.v1",
    "av.call-outcomes.v1",
    "av.handoffs.v1",
    "av.complaints.v1",
    "av.audit.v1",
]


class EventBus(Protocol):
    def publish(self, topic: Topic, key: str, record: BaseModel) -> None: ...


class MemoryBus:
    """Deterministic test double. Keeps every message in publish order."""

    def __init__(self) -> None:
        self.messages: dict[str, list[tuple[str, dict[str, object]]]] = defaultdict(list)

    def publish(self, topic: Topic, key: str, record: BaseModel) -> None:
        self.messages[topic].append((key, json.loads(record.model_dump_json())))


class KafkaBus:
    """A publish returns only after the broker acknowledges it (acks=all), or raises."""

    def __init__(self, bootstrap: str) -> None:
        from confluent_kafka import Producer

        self._producer = Producer(
            {"bootstrap.servers": bootstrap, "acks": "all", "enable.idempotence": True}
        )

    def publish(self, topic: Topic, key: str, record: BaseModel) -> None:
        errors: list[str] = []

        def _on_delivery(err: object, _msg: object) -> None:
            if err is not None:
                errors.append(str(err))

        self._producer.produce(
            topic,
            key=key.encode(),
            value=record.model_dump_json().encode(),
            on_delivery=_on_delivery,
        )
        remaining = self._producer.flush(10.0)
        if remaining or errors:
            raise ProviderError(f"kafka publish to {topic} failed: {errors or 'timeout'}")


def make_bus(name: str, bootstrap: str) -> EventBus:
    if name == "memory":
        return MemoryBus()
    if name == "kafka":
        return KafkaBus(bootstrap)
    raise ConfigError(f"unknown bus {name!r}")

"""Deterministic CRM test double."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.providers.base import CrmTicket


@dataclass
class MockCrm:
    name: str = "mock"
    tickets: dict[str, dict[str, object]] = field(default_factory=dict)

    def create_ticket(
        self, subject: str, body: str, requester_ref: str, tags: list[str], priority: str
    ) -> CrmTicket:
        ticket_id = f"T{len(self.tickets) + 1:05d}"
        self.tickets[ticket_id] = {
            "subject": subject,
            "body": body,
            "requester": requester_ref,
            "tags": list(tags),
            "priority": priority,
            "notes": [],
        }
        return CrmTicket(ticket_id=ticket_id, url=f"mock://crm/{ticket_id}")

    def add_note(self, ticket_id: str, body: str) -> None:
        notes = self.tickets[ticket_id]["notes"]
        assert isinstance(notes, list)
        notes.append(body)

"""REQ-WA-02: utility templates only in pilot; cost model assumes every template is paid."""

import pytest

from app.core.errors import WhatsAppTemplateNotAllowedError
from app.messaging import whatsapp
from app.messaging.templates import TEMPLATES, Template
from app.providers.whatsapp.mock import MockWhatsApp
from tests.factories import make_event


def test_every_pilot_template_is_utility() -> None:
    assert {t.category for t in TEMPLATES.values()} == {"utility"}


def test_marketing_template_is_refused(session, settings, clock, monkeypatch) -> None:
    promo = Template(name="promo", category="marketing", params=(), bodies={"en": "x"})
    monkeypatch.setitem(TEMPLATES, "av_payment_link_v1", promo)
    with pytest.raises(WhatsAppTemplateNotAllowedError):
        whatsapp.send_payment_link(session, settings, clock, MockWhatsApp(), make_event(settings))


def test_cost_is_utility_rate_plus_gst_rounded_up(settings) -> None:
    # Rs 0.1150 = 11.50 paise; +18% GST = 13.57 paise -> 14 paise per template.
    assert whatsapp.template_cost_paise(settings) == 14


def test_every_send_carries_a_cost(session, settings, clock) -> None:
    from app.compliance.models import WhatsAppSendRow

    event = make_event(settings)
    wa = MockWhatsApp()
    whatsapp.send_payment_link(session, settings, clock, wa, event)
    whatsapp.send_privacy_notice(session, settings, clock, wa, event)
    assert [r.cost_paise for r in session.query(WhatsAppSendRow)] == [14, 14]


@pytest.mark.parametrize("name", sorted(TEMPLATES))
def test_every_template_has_all_three_languages(name: str) -> None:
    assert set(TEMPLATES[name].bodies) == {"hi", "hinglish", "en"}

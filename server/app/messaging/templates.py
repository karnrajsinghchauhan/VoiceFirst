"""WhatsApp templates. The pilot uses utility templates only (REQ-WA-02); marketing is disabled.

Template bodies are what Meta approves; `{{n}}` placeholders are filled by params in order.
Every body is run through the dark-pattern suite in tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.types import Language

Category = Literal["utility", "marketing"]


@dataclass(frozen=True)
class Template:
    name: str
    category: Category
    params: tuple[str, ...]
    bodies: dict[Language, str]


_GRIEVANCE_LINE = {
    "hi": "शिकायत के लिए: {{grievance}}",
    "hinglish": "Shikayat ke liye: {{grievance}}",
    "en": "For grievances: {{grievance}}",
}

TEMPLATES: dict[str, Template] = {
    "av_payment_link_v1": Template(
        name="av_payment_link_v1",
        category="utility",
        params=("client", "first_name", "city", "amount", "link", "grievance"),
        bodies={
            "hinglish": "Namaste {{first_name}} ji, aapki {{city}} wali {{client}} booking ka payment "
            "{{amount}} baaki hai. Aap is surakshit link par payment kar sakte hain: "
            "{{link}}. Card ya OTP kabhi kisi ko na batayein. " + _GRIEVANCE_LINE["hinglish"],
            "hi": "नमस्ते {{first_name}} जी, आपकी {{city}} वाली {{client}} बुकिंग का भुगतान {{amount}} "
            "बाकी है। आप इस सुरक्षित लिंक पर भुगतान कर सकते हैं: {{link}}। कार्ड या OTP कभी "
            "किसी को न बताएं। " + _GRIEVANCE_LINE["hi"],
            "en": "Hello {{first_name}}, the payment of {{amount}} for your {{client}} booking in "
            "{{city}} is pending. You can pay on this secure page: {{link}}. Never share "
            "card details or OTPs with anyone. " + _GRIEVANCE_LINE["en"],
        },
    ),
    "av_payment_pending_v1": Template(
        name="av_payment_pending_v1",
        category="utility",
        params=("client", "first_name", "city", "amount", "link", "grievance"),
        bodies={
            "hinglish": "Namaste {{first_name}} ji, humne aapko call kiya tha. Aapki {{city}} wali "
            "booking ka payment {{amount}} baaki hai. Payment link: {{link}}. "
            + _GRIEVANCE_LINE["hinglish"],
            "hi": "नमस्ते {{first_name}} जी, हमने आपको कॉल किया था। आपकी {{city}} वाली बुकिंग का "
            "भुगतान {{amount}} बाकी है। भुगतान लिंक: {{link}}। " + _GRIEVANCE_LINE["hi"],
            "en": "Hello {{first_name}}, we tried to call you. The payment of {{amount}} for your "
            "booking in {{city}} is pending. Payment link: {{link}}. " + _GRIEVANCE_LINE["en"],
        },
    ),
    "av_app_link_v1": Template(
        name="av_app_link_v1",
        category="utility",
        params=("client", "first_name", "link"),
        bodies={
            "hinglish": "Namaste {{first_name}} ji, aapne jo poocha tha, woh {{client}} app mein yahan "
            "dekh sakte hain: {{link}}",
            "hi": "नमस्ते {{first_name}} जी, आपने जो पूछा था, वह {{client}} ऐप में यहाँ देख सकते हैं: " "{{link}}",
            "en": "Hello {{first_name}}, you can find what you asked about in the {{client}} app here: "
            "{{link}}",
        },
    ),
    "av_privacy_notice_v1": Template(
        name="av_privacy_notice_v1",
        category="utility",
        params=("first_name", "link"),
        bodies={
            "hinglish": "Namaste {{first_name}} ji, aaj ki call aur aapke data ke baare mein poori "
            "jaankari, aapke adhikaar aur consent wapas lene ka tareeka: {{link}}. "
            "Consent wapas lene ke liye STOP reply karein.",
            "hi": "नमस्ते {{first_name}} जी, आज की कॉल और आपके डेटा के बारे में पूरी जानकारी, आपके "
            "अधिकार और सहमति वापस लेने का तरीका: {{link}}। सहमति वापस लेने के लिए STOP "
            "भेजें।",
            "en": "Hello {{first_name}}, full details of today's call, how we use your data, your "
            "rights and how to withdraw consent: {{link}}. Reply STOP to withdraw consent.",
        },
    ),
    "av_csat_v1": Template(
        name="av_csat_v1",
        category="utility",
        params=("first_name",),
        bodies={
            "hinglish": "Namaste {{first_name}} ji, aaj ki call kaisi rahi? 1 se 5 tak reply "
            "karein. Reply karna zaroori nahi hai.",
            "hi": "नमस्ते {{first_name}} जी, आज की कॉल कैसी रही? 1 से 5 तक जवाब दें। जवाब देना "
            "ज़रूरी नहीं है।",
            "en": "Hello {{first_name}}, how was today's call? Reply 1 to 5. Replying is optional.",
        },
    ),
}


def render(template: Template, language: Language, params: dict[str, str]) -> str:
    body = template.bodies["hinglish" if language == "unknown" else language]
    for key in template.params:
        body = body.replace("{{" + key + "}}", params[key])
    return body

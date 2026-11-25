"""Deterministic guardrails that run outside the LLM on every customer turn (D-009).

`classify` reads one redacted customer utterance and returns Signals. The
conversation engine acts on Signals before the LLM is consulted, so P1-P3 hold
even when the model misbehaves. Lexicons cover Hinglish, Hindi and English.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.redaction import Finding, find_sensitive, is_payment_credential
from app.core.types import Language


def _rx(*patterns: str) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)


OPT_OUT = _rx(
    r"\bdon'?t call\b",
    r"\bdo not call\b",
    r"\bstop calling\b",
    r"\bcall mat (karo|kijiye|karna)\b",
    r"\bphone mat (karo|kijiye|karna)\b",
    r"\bband karo\b",
    r"\bband kijiye\b",
    r"\bnumber hata (do|dijiye)\b",
    r"\bremove my number\b",
    r"\bdobara (call|phone) mat\b",
    r"कॉल मत (करो|कीजिए|करना)",
    r"फ़?फोन मत (करो|कीजिए)",
    r"बंद करो",
    r"नंबर हटा",
)
WANTS_HUMAN = _rx(
    r"(?<!ai )\bagent\b",
    r"\bhuman se\b",
    r"\bto a human\b",
    r"\bspeak to (a )?(person|human)\b",
    r"\binsaan se (baat|jod)",
    r"\bkisi aadmi se\b",
    r"\bmanager\b",
    r"\breal person se\b",
    r"\bcustomer care\b",
    r"इंसान से",
    r"किसी आदमी से",
    r"मैनेजर",
)
DISPUTE = _rx(
    r"\bdispute\b",
    r"\blegal\b",
    r"\blawyer\b",
    r"\bvakeel\b",
    r"\bchargeback\b",
    r"\bfraud\b",
    r"\bpolice\b",
    r"\bconsumer (court|forum)\b",
    r"\bcourt\b",
    r"\bcase (karunga|karungi|kar dunga)\b",
    r"\bfir\b",
    r"\bpaise kat gaye\b",
    r"\bpaisa kat gaya\b",
    r"\bdouble charge",
    r"\bdeducted\b",
    r"\bcomplaint (karunga|karungi|karoonga)\b",
    r"वकील",
    r"पुलिस",
    r"कोर्ट",
    r"पैसे कट गए",
    r"धोखा",
)
MONEY_REQUEST = _rx(
    r"\brefund\b",
    r"\bcancel",
    r"\bpaise? wapas\b",
    r"\bpaisa wapas\b",
    r"\bdiscount\b",
    r"\b\d+\s?% off\b",
    r"\bchhoot\b",
    r"\bwaive\b",
    r"\bmaaf kar",
    r"\bagoda cash\b",
    r"\bcashback\b",
    r"\b(price|keemat|daam) kam\b",
    r"\bfree (kar|me)\b",
    r"रिफ़ंड",
    r"कैंसिल",
    r"पैसे वापस",
    r"छूट",
)
EMERGENCY = _rx(
    r"\bhospital\b",
    r"\bemergency\b",
    r"\baccident\b",
    r"\bambulance\b",
    r"\bheart attack\b",
    r"\bpassed away\b",
    r"\bdied\b",
    r"\bdeath\b",
    r"\bguzar gaye\b",
    r"\bmaut\b",
    r"\bnahi rahe\b",
    r"\bunsafe\b",
    r"\bkhatre mein\b",
    r"\bdanger\b",
    r"\bbachao\b",
    r"अस्पताल",
    r"इमरजेंसी",
    r"गुज़र गए",
    r"एक्सीडेंट",
)
BOT_QUESTION = _rx(
    r"\bare you (a )?(bot|robot|human|real|machine|computer|ai)\b",
    r"\bbot ho\b",
    r"\brobot ho\b",
    r"\bmachine ho\b",
    r"\binsaan ho\b",
    r"\binsaan hain\b",
    r"\breal (person|insaan) ho\b",
    r"\bai ho\b",
    r"\bcomputer ho\b",
    r"\byou are (a )?(human|real person)\b",
    r"क्या आप इंसान",
    r"रोबोट",
    r"मशीन हो",
)
INJECTION = _rx(
    r"\bignore (all |your )?(previous|prior|above) instructions\b",
    r"\bsystem prompt\b",
    r"\byou are now\b",
    r"\bdeveloper mode\b",
    r"\bpretend (you|to be)\b",
    r"\bgive (me )?\d+\s?% off\b",
    r"\bact as\b",
    r"\bnew instructions\b",
    r"\bjailbreak\b",
    r"\binstructions bhool",
    r"\bsab bhool ja",
)
MINOR = _rx(
    r"\bmain bach+(a|i|chi)\b",
    r"\bi am (a )?(kid|child)\b",
    r"\bi'?m \d{1,2} years old\b",
    r"\bmain (\d|ek|do|teen|chaar|paanch|chhah|saat|aath|nau|das|gyaarah|baarah) saal (ka|ki)\b",
    r"\b(papa|mummy|mumma|daddy) (ghar pe|ghar par)? ?nahi (hain|hai)\b",
    r"\b(papa|mummy) bahar\b",
    r"\bschool\b",
    r"मैं बच्चा",
    r"मैं बच्ची",
    r"पापा घर पर नहीं",
)
BOOKER_UNAVAILABLE = _rx(
    r"\bnahi hain\b",
    r"\bbahar (gaye|gayi)\b",
    r"\boffice\b",
    r"\bnot (at )?home\b",
    r"\bnot here\b",
    r"\bnahi hai\b",
    r"\bbaad mein\b",
    r"घर पर नहीं",
    r"बाहर",
)
THIRD_PARTY = _rx(
    r"\bmain (unki|unka|inki|inka) (wife|patni|pati|husband|beti|beta|bhai|behen|sister|brother)\b",
    r"\b(his|her) (wife|husband|son|daughter|brother|sister)\b",
    r"\bfront desk\b",
    r"\breception\b",
    r"\bhotel se bol\b",
    r"\bwoh abhi (nahi|bahar)\b",
    r"\b(she|he)'?s not here\b",
    r"\byeh unka phone\b",
    r"\bmain (unki|unka) (dost|friend)\b",
    r"उनकी पत्नी",
    r"रिसेप्शन",
)
WRONG_NUMBER = _rx(
    r"\bgalat number\b",
    r"\bwrong number\b",
    r"\byahan koi .* nahi\b",
    r"\bkoi \w+ nahi (hai|rehta|rehti)\b",
    r"\bdon'?t know any\b",
    r"\bno one (by|named)\b",
    r"गलत नंबर",
)
MACHINE = _rx(
    r"\bleave (a|your) message\b",
    r"\bafter the (tone|beep)\b",
    r"\bpress \d\b",
    r"\bnumber you have (dialled|dialed)\b",
    r"\bnot available\b.*\bmessage\b",
    r"\bvoicemail\b",
    r"\bdabaye?n\b",
    r"\babhi uplabdh nahi\b",
    r"कृपया संदेश",
)
ADD_ON = _rx(
    r"\badd-?ons?\b",
    r"\bflight\b",
    r"\btour\b",
    r"\bactivity\b",
    r"\bactivities\b",
    r"\bairport (pickup|transfer)\b",
    r"\bpackage\b",
    r"\bcab\b",
    r"\btaxi\b",
)
BNPL_CONFUSION = _rx(
    r"\bpay later\b",
    r"\bbnpl\b",
    r"\bpay now\b",
    r"\bbaad mein (pay|payment)\b",
    r"\bmaine to (pay later|baad mein)\b",
    r"\bpehle hi pay\b",
    r"\bkyun pay\b",
)
CLARIFY = _rx(
    r"\bkaun\b",
    r"\bwho is (this|it)\b",
    r"\bkya matlab\b",
    r"\bsamajh nahi\b",
    r"\bwhat\?",
    r"\bpardon\b",
    r"\bsorry\?",
    r"कौन",
    r"समझ नहीं",
)
QUESTION = _rx(
    r"\?",
    r"\bkya\b.*\b(hai|hain|milega|hoga)\b",
    r"\bkahan\b",
    r"\bkitna\b",
    r"\bkaise\b",
    r"\bhow\b",
    r"\bwhere\b",
    r"\bwhat\b",
    r"कहाँ",
    r"कैसे",
)
YES = _rx(
    r"\bhaan\b",
    r"\bha\b",
    r"\bhan ji\b",
    r"\byes\b",
    r"\byeah\b",
    r"\bbhej (do|dijiye|dena)\b",
    r"\bbhejiye\b",
    r"\btheek hai\b",
    r"\bthik hai\b",
    r"\bok(ay)?\b",
    r"\bsure\b",
    r"\bbilkul\b",
    r"\bzaroor\b",
    r"\bjarur\b",
    r"\bsahi hai\b",
    r"\bcorrect\b",
    r"\bright\b",
    r"\bplease do\b",
    r"\bsend it\b",
    r"\bgo ahead\b",
    r"\bsend (me )?the link\b",
    r"\balright\b",
    r"\bfine\b",
    r"\blink bhej",
    r"\bhaan ji\b",
    r"\bji haan\b",
    r"हाँ",
    r"हां",
    r"भेज दो",
    r"भेजिए",
    r"ठीक है",
    r"सही है",
    r"जी हाँ",
)
NO = _rx(
    r"\bnahi\b",
    r"\bnahin\b",
    r"\bno\b",
    r"\bnope\b",
    r"\bmat bhejo\b",
    r"\brehne do\b",
    r"\bdon'?t send\b",
    r"\bnot now\b",
    r"\bgalat hai\b",
    r"\bwrong\b",
    r"नहीं",
    r"मत भेजो",
)
NOTHING = _rx(
    r"\bkuch nahi\b",
    r"\bnothing\b",
    r"\bno request\b",
    r"\bnahi,? (koi|kuch)\b",
    r"\bno,? (thanks|thank you)\b",
    r"कुछ नहीं",
    r"कोई नहीं",
)
BACKCHANNEL_ONLY = re.compile(
    r"^\s*(hmm+|hm+|achha|acha|accha|haan haan|ha ha|uh[- ]?huh|ohh*|mm+|ji ji|अच्छा|हम्म|हाँ हाँ)"
    r"(\s*[,.]?\s*(hmm+|hm+|achha|acha|accha|haan haan|ji|ohh*|mm+|अच्छा|हम्म|हाँ हाँ))*\s*[.!]*\s*$",
    re.IGNORECASE,
)
_ANGER = _rx(
    r"\bbakwaas\b",
    r"\bbakwas\b",
    r"\bpagal\b",
    r"\bchor\b",
    r"\bdhokha\b",
    r"\bgussa\b",
    r"\bworst\b",
    r"\bidiot\b",
    r"\bstupid\b",
    r"\bridiculous\b",
    r"\bnonsense\b",
    r"\bshut up\b",
    r"\bbewakoof\b",
    r"\bhad hai\b",
    r"\bkya tamasha\b",
    r"\bfaltu\b",
    r"बकवास",
    r"पागल",
    r"चोर",
)
_HINGLISH_MARKERS = _rx(
    r"\b(hai|hain|nahi|kya|ji|haan|bhej|karo|kijiye|main|aap|mera|meri|abhi|theek|kab|baad|mein|"
    r"ko|se|par|wala|wali|kar|do|hoon|tha|thi|bolo|batao|achha|paise|kyun|ghar)\b"
)
_ENGLISH_MARKERS = _rx(
    r"\b(the|is|are|you|please|what|when|send|my|this|that|i|it|and|of|to|for|with|not|can|will|"
    r"yes|no|okay|call|me|do|don't|why|how)\b"
)
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def detect_language(text: str) -> Language:
    """Devanagari means Hindi; otherwise compare Hinglish and English function-word counts."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "unknown"
    devanagari = sum(1 for c in letters if _DEVANAGARI.match(c))
    if devanagari / len(letters) > 0.5:
        return "hi"
    hinglish = len(_HINGLISH_MARKERS.findall(text))
    english = len(_ENGLISH_MARKERS.findall(text))
    if hinglish == 0 and english == 0:
        return "unknown"
    return "hinglish" if hinglish >= english else "en"


def anger_score(text: str) -> float:
    hits = len(_ANGER.findall(text))
    exclaim = min(text.count("!"), 3)
    shouting = sum(1 for w in text.split() if len(w) > 2 and w.isupper())
    return min(1.0, 0.4 * hits + 0.1 * exclaim + 0.15 * shouting)


@dataclass(frozen=True)
class Signals:
    language: Language
    silence: bool
    sensitive: frozenset[Finding]
    payment_credential: bool
    opt_out: bool
    wants_human: bool
    dispute: bool
    money_request: bool
    emergency: bool
    bot_question: bool
    injection: bool
    minor: bool
    booker_unavailable: bool
    third_party: bool
    wrong_number: bool
    machine: bool
    add_on: bool
    bnpl_confusion: bool
    clarify: bool
    question: bool
    yes: bool
    no: bool
    nothing: bool
    backchannel: bool
    anger: float


def classify(raw_text: str, overlap: bool = False) -> Signals:
    """Classifies one customer utterance. `raw_text` is pre-redaction STT output; only
    credential detection reads it, so the LLM and storage see the redacted form only."""
    text = raw_text.strip()
    sensitive = frozenset(find_sensitive(text))
    backchannel = bool(BACKCHANNEL_ONLY.match(text)) or (overlap and len(text.split()) <= 2)
    yes = bool(YES.search(text)) and not backchannel
    no = bool(NO.search(text)) and not bool(re.search(r"\bnahi\b.*\b(samajh|pata)\b", text))
    return Signals(
        language=detect_language(text),
        silence=text == "",
        sensitive=sensitive,
        # A long digit run that is not Luhn-valid is still treated as a card: line loss can
        # corrupt one digit of a real PAN, and failing closed costs only a warning.
        payment_credential=is_payment_credential(set(sensitive)) or "long_number" in sensitive,
        opt_out=bool(OPT_OUT.search(text)),
        wants_human=bool(WANTS_HUMAN.search(text)),
        dispute=bool(DISPUTE.search(text)),
        money_request=bool(MONEY_REQUEST.search(text)),
        emergency=bool(EMERGENCY.search(text)),
        bot_question=bool(BOT_QUESTION.search(text)),
        injection=bool(INJECTION.search(text)),
        minor=bool(MINOR.search(text)),
        booker_unavailable=bool(BOOKER_UNAVAILABLE.search(text)),
        third_party=bool(THIRD_PARTY.search(text)),
        wrong_number=bool(WRONG_NUMBER.search(text)),
        machine=bool(MACHINE.search(text)),
        add_on=bool(ADD_ON.search(text)),
        bnpl_confusion=bool(BNPL_CONFUSION.search(text)),
        clarify=bool(CLARIFY.search(text)),
        question=bool(QUESTION.search(text)),
        yes=yes and not no,
        no=no and not yes,
        nothing=bool(NOTHING.search(text)),
        backchannel=backchannel,
        anger=anger_score(text),
    )

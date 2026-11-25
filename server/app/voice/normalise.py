"""Spoken read-back of amounts and dates in the customer's language (10.5, REQ-PAY-03).

All normalisation lives here. Amounts use Indian grouping (hazaar, lakh,
crore). Hindi and Hinglish use the irregular 0-99 word table: Hindi numbers
below one hundred are not compositional, so a table is the only correct
implementation.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.errors import ReadBackMismatchError
from app.core.types import Language

_HINGLISH_0_99 = (
    "shunya ek do teen chaar paanch chhah saat aath nau "
    "das gyaarah baarah terah chaudah pandrah solah satrah athaarah unnees "
    "bees ikkees baaees teyees chaubees pachchees chhabbees sattaees atthaaees untees "
    "tees ikattees battees taintees chauntees paintees chhattees saintees adtees untaalees "
    "chaalees iktaalees bayaalees taintaalees chauvaalees paintaalees chhiyaalees saintaalees "
    "adtaalees unchaas "
    "pachaas ikyaavan baavan tirpan chauvan pachpan chhappan sattaavan atthaavan unsath "
    "saath iksath baasath tirsath chaunsath painsath chhiyaasath sadsath adsath unhattar "
    "sattar ikhattar bahattar tihattar chauhattar pachhattar chhihattar sathattar athhattar "
    "unaasi "
    "assi ikyaasi bayaasi tiraasi chauraasi pachaasi chhiyaasi sattaasi atthaasi nawaasi "
    "nabbe ikyaanave baanave tiraanave chauraanave pachaanave chhiyaanave sattaanave "
    "atthaanave ninyaanave"
).split()

_HINDI_0_99 = (
    "शून्य एक दो तीन चार पाँच छह सात आठ नौ "
    "दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस "
    "बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस "
    "तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस "
    "चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास "
    "पचास इक्यावन बावन तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ "
    "साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर "
    "सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उन्यासी "
    "अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी "
    "नब्बे इक्यानवे बानवे तिरानवे चौरानवे पचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे"
).split()

_EN_ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen"
).split()
_EN_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()

if len(_HINGLISH_0_99) != 100 or len(_HINDI_0_99) != 100:
    raise RuntimeError("Hindi number tables must have exactly 100 entries")

# (value, hinglish, hindi, english), largest first. Indian grouping.
_SCALES = (
    (10_000_000, "crore", "करोड़", "crore"),
    (100_000, "lakh", "लाख", "lakh"),
    (1_000, "hazaar", "हज़ार", "thousand"),
    (100, "sau", "सौ", "hundred"),
)
_SCALE_INDEX = {"hinglish": 1, "hi": 2, "en": 3}

_MONTHS = {
    "hinglish": "January February March April May June July August September October "
    "November December".split(),
    "en": "January February March April May June July August September October "
    "November December".split(),
    "hi": "जनवरी फ़रवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्टूबर नवंबर दिसंबर".split(),
}

CURRENCY_WORDS = {
    "INR": {"hinglish": ("rupaye", "paise"), "hi": ("रुपये", "पैसे"), "en": ("rupees", "paise")},
}
_AND = {"hinglish": "aur", "hi": "और", "en": "and"}


def spoken_lang(language: Language) -> str:
    """Unknown language reads back in Hinglish, the default persona language (10.1)."""
    return "hinglish" if language == "unknown" else language


def _below_100(n: int, lang: str) -> str:
    if lang == "hinglish":
        return _HINGLISH_0_99[n]
    if lang == "hi":
        return _HINDI_0_99[n]
    if n < 20:
        return _EN_ONES[n]
    tens, ones = divmod(n, 10)
    return _EN_TENS[tens] if ones == 0 else f"{_EN_TENS[tens]}-{_EN_ONES[ones]}"


def number_words(n: int, language: Language) -> str:
    """Integer in words with Indian grouping. 4250 -> 'chaar hazaar do sau pachaas'."""
    if n < 0:
        raise ValueError("negative amounts are never read back")
    lang = spoken_lang(language)
    if n < 100:
        return _below_100(n, lang)
    parts: list[str] = []
    remaining = n
    for scale in _SCALES:
        value = scale[0]
        if remaining >= value:
            count, remaining = divmod(remaining, value)
            parts.append(f"{number_words(count, language)} {scale[_SCALE_INDEX[lang]]}")
    if remaining:
        parts.append(_below_100(remaining, lang))
    return " ".join(parts)


def amount_words(value: str, currency: str, language: Language) -> str:
    """Read-back of booking.amount_due. Called only with the booking record's own value."""
    if currency not in CURRENCY_WORDS:
        raise ReadBackMismatchError(f"no read-back defined for currency {currency}")
    lang = spoken_lang(language)
    unit, sub_unit = CURRENCY_WORDS[currency][lang]
    amount = Decimal(value)
    whole = int(amount)
    paise = int((amount - whole) * 100)
    spoken = f"{number_words(whole, language)} {unit}"
    if paise:
        spoken += f" {_AND[lang]} {number_words(paise, language)} {sub_unit}"
    return spoken


def date_words(d: date, language: Language) -> str:
    """12 Dec -> 'baarah December' / 'बारह दिसंबर' / 'twelve December'."""
    lang = spoken_lang(language)
    return f"{number_words(d.day, language)} {_MONTHS[lang][d.month - 1]}"


def number_word_set(language: Language) -> frozenset[str]:
    """Every word that can appear inside a spoken number; used by the read-back verifier."""
    lang = spoken_lang(language)
    if lang == "en":
        words = set(_EN_ONES) | {w for w in _EN_TENS if w != "_"}
    else:
        words = set(_HINGLISH_0_99 if lang == "hinglish" else _HINDI_0_99)
    words |= {str(scale[_SCALE_INDEX[lang]]) for scale in _SCALES}
    return frozenset(words)


def words_to_number(text: str, language: Language) -> int:
    """Inverse of number_words, so the read-back can be verified and property-tested."""
    lang = spoken_lang(language)
    if lang == "en":
        table = {w: i for i, w in enumerate(_EN_ONES)}
        table.update({w: i * 10 for i, w in enumerate(_EN_TENS) if w != "_"})
    else:
        source = _HINGLISH_0_99 if lang == "hinglish" else _HINDI_0_99
        table = {w: i for i, w in enumerate(source)}
    scales = {str(scale[_SCALE_INDEX[lang]]): int(scale[0]) for scale in _SCALES}
    total = 0
    group = 0
    for token in text.replace("-", " ").split():
        if token in table:
            group += table[token]
        elif token in scales:
            scale_value = scales[token]
            if scale_value == 100:
                group *= 100
            else:
                total += group * scale_value
                group = 0
        else:
            raise ReadBackMismatchError(f"not a number word: {token!r}")
    return total + group

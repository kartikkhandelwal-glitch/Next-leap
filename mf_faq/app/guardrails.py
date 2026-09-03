"""Input safety layer: PII detection and answer-vs-refuse classification.

Runs before retrieval. Nothing here reaches the corpus or any log in raw form -
PII is redacted at the boundary and the original string is dropped.
"""

import re

# --- PII patterns ------------------------------------------------------------
# Ordered most-specific first so PAN is not swallowed by a generic alnum rule.
PII_PATTERNS = [
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I)),
    ("Aadhaar", re.compile(r"\b[2-9][0-9]{3}[ -]?[0-9]{4}[ -]?[0-9]{4}\b")),
    ("email address", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")),
    # Indian mobile numbers, tolerating the common "+91 98765 43210" grouping.
    ("phone number", re.compile(r"(?:\+?91[ -]?)?\b[6-9][0-9]{4}[ -]?[0-9]{5}\b")),
    ("OTP", re.compile(r"\botp\b[^0-9]{0,20}[0-9]{4,8}\b", re.I)),
    ("folio or account number", re.compile(r"\b(?:folio|account|a/c|acct)\D{0,10}[0-9]{6,18}\b", re.I)),
    ("bank account number", re.compile(r"\b[0-9]{9,18}\b")),
]

REDACTION = "[redacted]"


def scan_and_redact(text):
    """Return (redacted_text, [labels found]). The caller must use the redacted
    text from here on and discard the original."""
    found, redacted = [], text
    for label, pattern in PII_PATTERNS:
        if pattern.search(redacted):
            found.append(label)
            redacted = pattern.sub(REDACTION, redacted)
    return redacted, found


# --- Intent classification ---------------------------------------------------
# Each rule is (intent, compiled pattern). First match wins, so the more
# specific advice/performance rules are listed before anything else.

_ADVICE = re.compile(
    r"\b(should i|shall i|should we|can you recommend|do you recommend|recommend me|"
    r"suggest me|which (?:one |fund |scheme )?(?:is |should )?(?:the )?(?:better|best|good)|"
    r"is it (?:a )?(?:good|bad|safe|wise|worth)|worth (?:buying|investing|it)|"
    r"(?:good|bad|safe|right|suitable|okay|ok|fine) (?:choice |option |pick |bet )?for (?:me|my)\b|"
    r"suits? me|suitable for me|"
    r"advise|advice|what should i (?:do|buy|pick|choose)|"
    r"(?:buy|sell|switch|exit|redeem|hold|invest in) (?:or|now|it|this|that)\b|"
    r"help me (?:choose|pick|decide|build)|"
    r"(?:my|build a|review my|rebalance) portfolio|asset allocation for me|"
    r"how much should i (?:invest|put)|"
    r"will (?:it|this|the fund) (?:go up|grow|give|beat|outperform)|"
    r"(?:good|best) (?:fund|scheme)s? (?:to|for) (?:buy|invest))\b",
    re.I,
)

_PERFORMANCE = re.compile(
    r"\b(returns?|cagr|xirr|performance|how much (?:will|would|did) i (?:get|make|earn)|"
    r"profit|gain[s]? (?:will|would)|compare (?:the )?(?:returns|performance)|"
    r"(?:1|3|5|ten|10)[ -]?(?:year|yr) (?:return|performance)|past performance|"
    r"which (?:fund|scheme) (?:gave|has given|performed))\b",
    re.I,
)

_GREETING = re.compile(r"^\s*(hi|hey|hello|namaste|thanks|thank you|ok|okay)\b[\s!.?]*$", re.I)


def classify(text):
    """Return one of: 'pii', 'greeting', 'advice', 'performance', 'fact'.

    'pii' is decided by the caller (it needs the scan result), so this handles
    the rest. Advice is checked before performance because "should I buy the
    fund with the best returns" is an advice question first.
    """
    if _GREETING.match(text):
        return "greeting"
    if _ADVICE.search(text):
        return "advice"
    if _PERFORMANCE.search(text):
        return "performance"
    return "fact"

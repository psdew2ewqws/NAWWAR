"""
Core utilities - Helper functions used across the app.
"""
import hashlib
import re
import unicodedata
from typing import Any, TypeVar

from django.conf import settings
from django.db.models import Model

T = TypeVar('T', bound=Model)


def get_object_or_none(model: type[T], **kwargs) -> T | None:
    """Get object or return None instead of raising DoesNotExist."""
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None


def get_object_or_404(model: type[T], **kwargs) -> T:
    """Get object or raise NotFoundError."""
    from apps.core.exceptions import NotFoundError

    obj = get_object_or_none(model, **kwargs)
    if obj is None:
        raise NotFoundError(f'{model.__name__} not found')
    return obj


def inline_serializer(*, fields: dict, data: Any = None, **kwargs):
    """Create an inline serializer for quick API responses."""
    from rest_framework import serializers

    serializer_class = type('InlineSerializer', (serializers.Serializer,), fields)
    if data is not None:
        return serializer_class(data=data, **kwargs)
    return serializer_class(**kwargs)


# =============================================================================
# T9.4 — Input Sanitisation
# =============================================================================

# Tags and patterns to strip from user input / AI output
_HTML_TAG_RE = re.compile(r'<(script|style|iframe|object|embed|form|input|textarea|button|link)[^>]*>.*?</\1>', re.DOTALL | re.IGNORECASE)
_ANY_TAG_RE = re.compile(r'<[^>]+>')
_JS_URI_RE = re.compile(r'javascript\s*:', re.IGNORECASE)
_CONTROL_CHAR_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
_EXCESS_WHITESPACE_RE = re.compile(r'\n{3,}')


def sanitise_text(text: str) -> str:
    """
    Sanitise user input or AI output for safe storage and display.

    Strips dangerous HTML tags, javascript: URIs, control characters,
    and truncates to MAX_MESSAGE_LENGTH.
    """
    if not text:
        return ''
    if not isinstance(text, str):
        text = str(text)

    # Strip dangerous tags with content (script, style, iframe, etc.)
    text = _HTML_TAG_RE.sub('', text)
    # Strip remaining HTML tags (keep text content)
    text = _ANY_TAG_RE.sub('', text)
    # Strip javascript: URIs
    text = _JS_URI_RE.sub('', text)
    # Strip control characters (keep \n, \r, \t)
    text = _CONTROL_CHAR_RE.sub('', text)
    # Collapse excessive newlines
    text = _EXCESS_WHITESPACE_RE.sub('\n\n', text)

    # Truncate to max length
    max_len = getattr(settings, 'MAX_MESSAGE_LENGTH', 4096)
    if len(text) > max_len:
        text = text[:max_len]

    return text.strip()


# =============================================================================
# T9.6 — PII-Safe Logging Utilities
# =============================================================================

def mask_phone(phone: str) -> str:
    """Mask phone number for safe logging: '962791234567' → '962***4567'."""
    if not phone:
        return ''
    phone = str(phone)
    if len(phone) <= 4:
        return '***' + phone[-2:]
    return phone[:3] + '***' + phone[-4:]


def mask_content(text: str, max_chars: int = 20) -> str:
    """Truncate text for safe logging: shows first N chars + '[redacted]'."""
    if not text:
        return ''
    text = str(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + '...[redacted]'


def mask_subscriber(number: str) -> str:
    """Mask subscriber/file number for safe logging: '1234567890' → '***890'."""
    if not number:
        return ''
    number = str(number)
    return '***' + number[-3:] if len(number) > 3 else '***'


# =============================================================================
# T9.5 — Cache Key Generation
# =============================================================================

def normalise_and_hash(text: str, prefix: str = '') -> str:
    """
    Normalise text and generate a SHA256 cache key.

    Lowercases, strips whitespace, removes Arabic diacritics,
    then hashes for a fixed-length key.
    """
    if not text:
        return f'{prefix}:empty'
    # Lowercase and strip
    normalised = text.lower().strip()
    # Remove Arabic diacritics (tashkeel)
    normalised = ''.join(
        c for c in unicodedata.normalize('NFD', normalised)
        if unicodedata.category(c) != 'Mn'
    )
    # Collapse whitespace
    normalised = re.sub(r'\s+', ' ', normalised)
    digest = hashlib.sha256(normalised.encode('utf-8')).hexdigest()[:16]
    return f'{prefix}:{digest}' if prefix else digest


# =============================================================================
# T9.3 — Prompt Injection Pre-Screening
# =============================================================================

_INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(previous|all|above)\s+instructions?', re.IGNORECASE),
    re.compile(r'(system|internal)\s+prompt', re.IGNORECASE),
    re.compile(r'you\s+are\s+now\b', re.IGNORECASE),
    re.compile(r'\bact\s+as\b', re.IGNORECASE),
    re.compile(r'reveal\s+(your\s+)?instructions?', re.IGNORECASE),
    re.compile(r'تجاهل\s+(التعليمات|الأوامر)', re.IGNORECASE),
    re.compile(r'اكشف\s+(عن\s+)?تعليمات', re.IGNORECASE),
    re.compile(r'أنت\s+الآن\b', re.IGNORECASE),
    re.compile(r'غير\s+دورك', re.IGNORECASE),
    # Additional English patterns
    re.compile(r'forget\s+(everything|all|previous)', re.IGNORECASE),
    re.compile(r'new\s+instructions?', re.IGNORECASE),
    re.compile(r'override\s+(your\s+)?rules?', re.IGNORECASE),
    re.compile(r'pretend\s+(you|to)\s+', re.IGNORECASE),
    re.compile(r'role\s*play', re.IGNORECASE),
    re.compile(r'jailbreak', re.IGNORECASE),
    re.compile(r'DAN\s+mode', re.IGNORECASE),
    re.compile(r'developer\s+mode', re.IGNORECASE),
    re.compile(r'(print|output|show)\s+(your\s+)?(system|initial)\s+(prompt|instructions?)', re.IGNORECASE),
    re.compile(r'what\s+are\s+your\s+(instructions?|rules?|system\s+prompt)', re.IGNORECASE),
    # Additional Arabic patterns
    re.compile(r'انسَ?\s+(كل|جميع)', re.IGNORECASE),
    re.compile(r'تعليمات\s+جديدة', re.IGNORECASE),
    re.compile(r'تخطى\s+(القواعد|التعليمات)', re.IGNORECASE),
    re.compile(r'تظاهر\s+(أنك|بأنك|انك)', re.IGNORECASE),
    re.compile(r'ما\s+هي\s+تعليماتك', re.IGNORECASE),
    re.compile(r'اعرض\s+(تعليمات|أوامر)\s+النظام', re.IGNORECASE),
]

INJECTION_SAFE_RESPONSE = (
    "عذراً، لا أستطيع تنفيذ هذا الطلب. "
    "أنا نوّار، مساعد متخصص في قطاع الكهرباء الأردني. "
    "كيف يمكنني مساعدتك بخصوص الكهرباء؟"
)


_ZERO_WIDTH_RE = re.compile(r'[\u200b\u200c\u200d\ufeff\u200e\u200f]')


def check_prompt_injection(text: str) -> str | None:
    """
    Screen user input for prompt injection patterns.

    Returns the matched pattern string if injection detected, None otherwise.
    Normalises Unicode before matching to prevent bypass via
    zero-width characters, Arabic diacritics, or extra whitespace.
    """
    if not text:
        return None
    # Strip zero-width / invisible characters
    normalised = _ZERO_WIDTH_RE.sub('', text)
    # Remove Arabic diacritics (tashkeel) so patterns match bare letters
    normalised = ''.join(
        c for c in unicodedata.normalize('NFD', normalised)
        if unicodedata.category(c) != 'Mn'
    )
    # Collapse multiple spaces into one
    normalised = re.sub(r'\s+', ' ', normalised)
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(normalised)
        if match:
            return match.group(0)
    return None


def check_indirect_injection(data: Any) -> bool:
    """Screen external API data for injection hidden in field values."""
    if isinstance(data, str):
        return check_prompt_injection(data) is not None
    if isinstance(data, dict):
        return any(check_indirect_injection(v) for v in data.values())
    if isinstance(data, list):
        return any(check_indirect_injection(item) for item in data[:50])
    return False

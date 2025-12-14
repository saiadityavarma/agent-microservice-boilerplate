"""
Custom validation functions.

Provides validators for common security checks including prompt injection
detection, XSS prevention, path traversal, and format validation.
"""

import re
import uuid as uuid_lib
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


# Prompt injection patterns to detect
PROMPT_INJECTION_PATTERNS = [
    # System prompt overrides
    r'ignore\s+(previous|above|all)\s+(instructions|prompts?|commands?)',
    r'disregard\s+(previous|above|all)\s+(instructions|prompts?|commands?)',
    r'forget\s+(previous|above|all)\s+(instructions|prompts?|commands?)',
    r'system\s*:\s*',
    r'assistant\s*:\s*',
    r'user\s*:\s*',

    # Role-playing attempts
    r'act\s+as\s+(if|though|a|an)',
    r'pretend\s+(to\s+be|you\s+are)',
    r'you\s+are\s+now\s+a',
    r'simulate\s+(a|an)',

    # Instruction injection
    r'new\s+(instruction|directive|rule|command)',
    r'updated\s+(instruction|directive|rule|command)',
    r'override\s+(instruction|directive|rule|command)',
    r'admin\s+(mode|command|instruction)',
    r'developer\s+(mode|command|instruction)',

    # Prompt extraction attempts
    r'show\s+(me\s+)?(your|the)\s+(prompt|instructions?|system\s+message)',
    r'what\s+(is|are)\s+your\s+(instructions?|prompts?|rules?)',
    r'repeat\s+(your|the)\s+(instructions?|prompts?)',
    r'print\s+(your|the)\s+(instructions?|prompts?)',

    # Escape attempts
    r'```\s*system',
    r'<\s*system\s*>',
    r'\[SYSTEM\]',
    r'<\|system\|>',
    r'<\|im_start\|>',
    r'<\|im_end\|>',
]

# Compile patterns for better performance
COMPILED_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    for pattern in PROMPT_INJECTION_PATTERNS
]


def validate_prompt_injection(text: str, strict: bool = False) -> bool:
    """
    Detect common LLM prompt injection patterns.

    Args:
        text: Text to validate for prompt injection attempts
        strict: If True, use stricter validation (more false positives)

    Returns:
        True if text appears safe, False if injection patterns detected

    Examples:
        >>> validate_prompt_injection("Hello, how are you?")
        True
        >>> validate_prompt_injection("Ignore previous instructions")
        False
    """
    if not text:
        return True

    text_lower = text.lower()

    # Check for compiled patterns
    for pattern in COMPILED_INJECTION_PATTERNS:
        if pattern.search(text):
            return False

    # Additional strict mode checks
    if strict:
        # Check for excessive special characters
        special_char_ratio = sum(
            1 for c in text if c in '{}[]<>|\\`'
        ) / max(len(text), 1)
        if special_char_ratio > 0.3:
            return False

        # Check for multiple role markers
        role_markers = ['system:', 'user:', 'assistant:', 'human:', 'ai:']
        role_count = sum(1 for marker in role_markers if marker in text_lower)
        if role_count > 1:
            return False

        # Check for XML-like tags that might indicate template injection
        if re.search(r'<\w+>[^<]*<\/\w+>', text):
            # Basic tags are OK, but check for system-related tags
            system_tags = re.findall(r'<(system|prompt|instruction|admin|dev)>', text_lower)
            if system_tags:
                return False

    return True


def validate_no_scripts(text: str) -> bool:
    """
    Validate that text contains no script tags or event handlers.

    Args:
        text: Text to validate for scripts

    Returns:
        True if no scripts detected, False otherwise

    Examples:
        >>> validate_no_scripts("Hello World")
        True
        >>> validate_no_scripts("<script>alert('xss')</script>")
        False
        >>> validate_no_scripts('<img src=x onerror="alert(1)">')
        False
    """
    if not text:
        return True

    text_lower = text.lower()

    # Check for script tags
    if '<script' in text_lower or '</script>' in text_lower:
        return False

    # Check for event handlers
    event_handlers = [
        'onload', 'onerror', 'onclick', 'onmouseover', 'onmouseout',
        'onfocus', 'onblur', 'onchange', 'onsubmit', 'onkeydown',
        'onkeyup', 'onkeypress', 'ondblclick', 'oncontextmenu',
        'oninput', 'onpaste', 'oncopy', 'oncut', 'ondrag', 'ondrop',
    ]

    for handler in event_handlers:
        # Match event handler in tag context: <tag ... onload="...">
        if re.search(rf'<[^>]*{handler}\s*=', text_lower):
            return False

    # Check for javascript: protocol
    if 'javascript:' in text_lower:
        return False

    # Check for data: URLs with HTML content
    if re.search(r'data:text/html', text_lower):
        return False

    # Check for <iframe>, <embed>, <object> tags
    dangerous_tags = ['<iframe', '<embed', '<object', '<applet']
    for tag in dangerous_tags:
        if tag in text_lower:
            return False

    return True


def validate_safe_path(path: str, allow_absolute: bool = False) -> bool:
    """
    Validate that a path contains no path traversal attempts.

    Args:
        path: Path to validate
        allow_absolute: If True, allow absolute paths

    Returns:
        True if path is safe, False if path traversal detected

    Examples:
        >>> validate_safe_path("files/document.txt")
        True
        >>> validate_safe_path("../../../etc/passwd")
        False
        >>> validate_safe_path("/etc/passwd")
        False
        >>> validate_safe_path("/etc/passwd", allow_absolute=True)
        True
    """
    if not path:
        return True

    # Check for path traversal sequences
    if '..' in path:
        return False

    # Check for null bytes
    if '\x00' in path or '\u0000' in path:
        return False

    # Check for absolute paths if not allowed
    if not allow_absolute:
        # Check for Unix absolute paths
        if path.startswith('/'):
            return False
        # Check for Windows absolute paths
        if len(path) > 1 and path[1] == ':':
            return False
        # Check for UNC paths
        if path.startswith('\\\\'):
            return False

    # Check for dangerous path components
    dangerous_parts = ['etc', 'passwd', 'shadow', 'hosts', 'config']
    path_lower = path.lower()
    path_parts = Path(path_lower).parts

    # Block if trying to access system directories
    if any(part in dangerous_parts for part in path_parts):
        return False

    return True


def validate_uuid(value: str) -> bool:
    """
    Validate that a string is a valid UUID.

    Args:
        value: String to validate as UUID

    Returns:
        True if valid UUID, False otherwise

    Examples:
        >>> validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> validate_uuid("not-a-uuid")
        False
        >>> validate_uuid("550e8400e29b41d4a716446655440000")  # No hyphens
        True
    """
    if not value:
        return False

    try:
        # Try to parse as UUID
        uuid_obj = uuid_lib.UUID(value)
        # Verify string representation matches (case-insensitive)
        return str(uuid_obj) == value.lower() or value.replace('-', '') == str(uuid_obj).replace('-', '')
    except (ValueError, AttributeError):
        return False


def validate_email(value: str, strict: bool = True) -> bool:
    """
    Validate email address format.

    Args:
        value: Email address to validate
        strict: If True, use stricter RFC-compliant validation

    Returns:
        True if valid email format, False otherwise

    Examples:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid.email")
        False
        >>> validate_email("user+tag@example.co.uk")
        True
    """
    if not value:
        return False

    # Basic length check
    if len(value) > 254:  # RFC 5321
        return False

    if strict:
        # Stricter RFC 5322 compliant pattern
        pattern = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    else:
        # More lenient pattern
        pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'

    if not re.match(pattern, value):
        return False

    # Split and validate parts
    try:
        local, domain = value.rsplit('@', 1)
    except ValueError:
        return False

    # Validate local part length
    if len(local) > 64:  # RFC 5321
        return False

    # Validate domain part
    if len(domain) > 253:
        return False

    # Domain should have at least one dot
    if '.' not in domain:
        return False

    return True


def validate_url(
    value: str,
    allowed_schemes: Optional[set[str]] = None,
    require_tld: bool = True
) -> bool:
    """
    Validate URL format.

    Args:
        value: URL to validate
        allowed_schemes: Set of allowed URL schemes (default: {'http', 'https'})
        require_tld: If True, require a top-level domain

    Returns:
        True if valid URL format, False otherwise

    Examples:
        >>> validate_url("https://example.com")
        True
        >>> validate_url("http://localhost:8000")
        True
        >>> validate_url("ftp://example.com")
        False
        >>> validate_url("javascript:alert(1)")
        False
    """
    if not value:
        return False

    if allowed_schemes is None:
        allowed_schemes = {'http', 'https'}

    try:
        result = urlparse(value)

        # Check scheme
        if result.scheme not in allowed_schemes:
            return False

        # Check that netloc (domain) exists
        if not result.netloc:
            return False

        # Check for TLD if required (not needed for localhost, IPs)
        if require_tld:
            # Allow localhost and IP addresses
            netloc = result.netloc.split(':')[0]  # Remove port
            if netloc not in ['localhost', '127.0.0.1', '::1']:
                # Check for at least one dot (indicating TLD)
                if '.' not in netloc:
                    return False

        # Basic sanity checks
        if len(value) > 2048:  # Reasonable URL length limit
            return False

        # Check for suspicious patterns
        if any(char in value for char in ['\x00', '\n', '\r']):
            return False

        return True

    except Exception:
        return False


def validate_alphanumeric(value: str, allow_spaces: bool = False) -> bool:
    """
    Validate that string contains only alphanumeric characters.

    Args:
        value: String to validate
        allow_spaces: If True, allow spaces in the string

    Returns:
        True if alphanumeric, False otherwise

    Examples:
        >>> validate_alphanumeric("Hello123")
        True
        >>> validate_alphanumeric("Hello 123")
        False
        >>> validate_alphanumeric("Hello 123", allow_spaces=True)
        True
        >>> validate_alphanumeric("Hello@123")
        False
    """
    if not value:
        return False

    if allow_spaces:
        return all(c.isalnum() or c.isspace() for c in value)

    return value.isalnum()


def validate_length(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
) -> bool:
    """
    Validate string length is within bounds.

    Args:
        value: String to validate
        min_length: Minimum allowed length (inclusive)
        max_length: Maximum allowed length (inclusive)

    Returns:
        True if length is valid, False otherwise

    Examples:
        >>> validate_length("hello", min_length=3, max_length=10)
        True
        >>> validate_length("hi", min_length=3)
        False
        >>> validate_length("very long string", max_length=10)
        False
    """
    if value is None:
        return False

    length = len(value)

    if min_length is not None and length < min_length:
        return False

    if max_length is not None and length > max_length:
        return False

    return True

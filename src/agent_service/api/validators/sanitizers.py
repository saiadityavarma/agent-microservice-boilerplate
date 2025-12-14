"""
Input sanitization functions.

Provides utilities for cleaning and sanitizing user input to prevent
injection attacks, XSS, and other security vulnerabilities.
"""

import re
import html
from typing import Optional


def sanitize_html(text: str, allowed_tags: Optional[set[str]] = None) -> str:
    """
    Remove or escape HTML tags from text.

    Args:
        text: Input text that may contain HTML
        allowed_tags: Set of allowed HTML tags (if None, all tags are escaped)

    Returns:
        Sanitized text with HTML tags removed or escaped

    Examples:
        >>> sanitize_html("<script>alert('xss')</script>Hello")
        "&lt;script&gt;alert('xss')&lt;/script&gt;Hello"
        >>> sanitize_html("<b>Hello</b>", allowed_tags={'b'})
        "<b>Hello</b>"
    """
    if not text:
        return text

    # If no allowed tags, escape all HTML
    if allowed_tags is None or not allowed_tags:
        return html.escape(text)

    # Simple whitelist approach: escape tags not in allowed list
    # This is a basic implementation - for production, consider using bleach
    def replace_tag(match):
        tag_name = match.group(1).lower()
        if tag_name in allowed_tags:
            return match.group(0)
        return html.escape(match.group(0))

    # Match opening and closing tags
    pattern = r'<(/?\w+)[^>]*>'
    result = re.sub(pattern, replace_tag, text)

    # Escape any remaining < and > that aren't part of allowed tags
    result = re.sub(r'<(?!/?\w)', '&lt;', result)

    return result


def sanitize_sql(text: str) -> str:
    """
    Escape SQL special characters.

    Note: This is NOT a replacement for parameterized queries.
    Always use parameterized queries with your database driver.
    This is a defense-in-depth measure.

    Args:
        text: Input text that may contain SQL special characters

    Returns:
        Text with SQL special characters escaped

    Examples:
        >>> sanitize_sql("'; DROP TABLE users; --")
        "\\'; DROP TABLE users; --"
    """
    if not text:
        return text

    # Escape single quotes (most common SQL injection vector)
    text = text.replace("'", "\\'")

    # Escape double quotes
    text = text.replace('"', '\\"')

    # Escape backslashes
    text = text.replace("\\", "\\\\")

    # Remove null bytes
    text = text.replace("\x00", "")

    return text


def strip_null_bytes(text: str) -> str:
    """
    Remove null bytes from text.

    Null bytes can cause issues with C-based systems and can be used
    to bypass security filters.

    Args:
        text: Input text that may contain null bytes

    Returns:
        Text with null bytes removed

    Examples:
        >>> strip_null_bytes("hello\\x00world")
        "helloworld"
    """
    if not text:
        return text

    return text.replace("\x00", "").replace("\u0000", "")


def normalize_whitespace(text: str) -> str:
    """
    Collapse multiple consecutive whitespace characters into single spaces.

    Also strips leading and trailing whitespace.

    Args:
        text: Input text with potentially irregular whitespace

    Returns:
        Text with normalized whitespace

    Examples:
        >>> normalize_whitespace("  hello    world  \\n  ")
        "hello world"
    """
    if not text:
        return text

    # Replace all whitespace sequences with single space
    text = re.sub(r'\s+', ' ', text)

    # Strip leading and trailing whitespace
    return text.strip()


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to maximum length.

    Args:
        text: Input text to truncate
        max_length: Maximum allowed length (including suffix)
        suffix: String to append to truncated text (default: "...")

    Returns:
        Truncated text if longer than max_length, otherwise original text

    Examples:
        >>> truncate_string("Hello World", 8)
        "Hello..."
        >>> truncate_string("Hi", 10)
        "Hi"
    """
    if not text:
        return text

    if max_length <= 0:
        return ""

    if len(text) <= max_length:
        return text

    # Account for suffix length
    suffix_len = len(suffix)
    if suffix_len >= max_length:
        return text[:max_length]

    truncate_at = max_length - suffix_len
    return text[:truncate_at] + suffix


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename by removing dangerous characters.

    Args:
        filename: Original filename
        max_length: Maximum allowed filename length

    Returns:
        Sanitized filename safe for filesystem operations

    Examples:
        >>> sanitize_filename("../../etc/passwd")
        "etc_passwd"
        >>> sanitize_filename("file<>name.txt")
        "file__name.txt"
    """
    if not filename:
        return "unnamed"

    # Remove path separators
    filename = filename.replace("/", "_").replace("\\", "_")

    # Remove dangerous characters
    # Keep alphanumeric, dots, hyphens, underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Remove leading dots (hidden files)
    filename = filename.lstrip('.')

    # Ensure it's not empty after sanitization
    if not filename:
        filename = "unnamed"

    # Truncate to max length
    if len(filename) > max_length:
        # Try to preserve extension
        parts = filename.rsplit('.', 1)
        if len(parts) == 2:
            name, ext = parts
            # Keep extension, truncate name
            max_name_len = max_length - len(ext) - 1
            filename = f"{name[:max_name_len]}.{ext}"
        else:
            filename = filename[:max_length]

    return filename


def sanitize_email(email: str) -> str:
    """
    Basic email sanitization.

    Normalizes email addresses by converting to lowercase and stripping whitespace.

    Args:
        email: Email address to sanitize

    Returns:
        Sanitized email address

    Examples:
        >>> sanitize_email("  User@Example.COM  ")
        "user@example.com"
    """
    if not email:
        return email

    # Strip whitespace and convert to lowercase
    email = email.strip().lower()

    # Remove null bytes
    email = strip_null_bytes(email)

    return email


def remove_control_characters(text: str, keep_newlines: bool = False) -> str:
    """
    Remove control characters from text.

    Control characters can cause issues with text processing and display.

    Args:
        text: Input text
        keep_newlines: If True, preserve newline characters (\\n, \\r)

    Returns:
        Text with control characters removed

    Examples:
        >>> remove_control_characters("hello\\x01world")
        "helloworld"
    """
    if not text:
        return text

    if keep_newlines:
        # Remove all control characters except newlines and carriage returns
        pattern = r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]'
    else:
        # Remove all control characters
        pattern = r'[\x00-\x1F\x7F]'

    return re.sub(pattern, '', text)


def sanitize_json_string(text: str) -> str:
    """
    Sanitize a string for safe inclusion in JSON.

    Args:
        text: Input text to sanitize

    Returns:
        Sanitized text safe for JSON

    Examples:
        >>> sanitize_json_string('Hello "World"')
        'Hello \\\\"World\\\\"'
    """
    if not text:
        return text

    # Remove null bytes
    text = strip_null_bytes(text)

    # Remove control characters but keep newlines
    text = remove_control_characters(text, keep_newlines=True)

    # Escape backslashes first
    text = text.replace("\\", "\\\\")

    # Escape quotes
    text = text.replace('"', '\\"')

    return text

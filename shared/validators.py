# ============================================================================
# shared/validators.py - Input validation and sanitization utilities
# ============================================================================

import re
import json
import html
import ipaddress
from typing import Optional, Tuple, Union, List
from lxml import etree


# ==========================================================================
# Security: Dangerous patterns to block
# ==========================================================================

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)",
    r"(--|#|/\*|\*/)",  # SQL comments
    r"(\bOR\b\s+\d+\s*=\s*\d+)",  # OR 1=1 pattern
    r"(\bAND\b\s+\d+\s*=\s*\d+)",  # AND 1=1 pattern
    r"(;\s*(SELECT|INSERT|UPDATE|DELETE|DROP))",  # Stacked queries
]

# Command injection patterns
COMMAND_INJECTION_PATTERNS = [
    r"[;&|`$]",  # Shell metacharacters
    r"\$\(",  # Command substitution
    r"\$\{",  # Variable expansion
    r">\s*/",  # Redirect to root
    r"\.\./",  # Path traversal
]

# XSS patterns
XSS_PATTERNS = [
    r"<script",
    r"javascript:",
    r"on\w+\s*=",  # Event handlers
    r"<iframe",
    r"<object",
    r"<embed",
]


def check_dangerous_patterns(value: str, patterns: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Check if value contains dangerous patterns.

    Returns:
        (is_safe, matched_pattern) - is_safe is False if dangerous pattern found
    """
    if not isinstance(value, str):
        return True, None

    for pattern in patterns:
        if re.search(pattern, value, re.IGNORECASE):
            return False, pattern

    return True, None


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize a string by removing dangerous characters.

    Args:
        value: String to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value)[:max_length]

    # Truncate to max length
    value = value[:max_length]

    # HTML escape
    value = html.escape(value)

    # Remove null bytes
    value = value.replace('\x00', '')

    return value


def validate_safe_string(
    value: str,
    field_name: str = "value",
    max_length: int = 1000,
    check_sql: bool = True,
    check_cmd: bool = True,
    check_xss: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a string is safe from injection attacks.

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(value, str):
        return False, f"{field_name} must be a string"

    if len(value) > max_length:
        return False, f"{field_name} exceeds maximum length of {max_length}"

    if check_sql:
        is_safe, pattern = check_dangerous_patterns(value, SQL_INJECTION_PATTERNS)
        if not is_safe:
            return False, f"{field_name} contains potentially dangerous SQL pattern"

    if check_cmd:
        is_safe, pattern = check_dangerous_patterns(value, COMMAND_INJECTION_PATTERNS)
        if not is_safe:
            return False, f"{field_name} contains potentially dangerous command pattern"

    if check_xss:
        is_safe, pattern = check_dangerous_patterns(value, XSS_PATTERNS)
        if not is_safe:
            return False, f"{field_name} contains potentially dangerous script pattern"

    return True, None


# ==========================================================================
# Network validation
# ==========================================================================

def validate_xml(xml_string: str) -> bool:
    """Validate XML string"""
    try:
        etree.fromstring(xml_string.encode())
        return True
    except etree.XMLSyntaxError:
        return False

def validate_xpath(xpath_string: str) -> bool:
    """Validate XPath expression"""
    try:
        etree.XPath(xpath_string)
        return True
    except etree.XPathSyntaxError:
        return False

def validate_hostname(hostname: str) -> bool:
    """Validate hostname format"""
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
    return bool(re.match(pattern, hostname))

def validate_ip(ip: str) -> bool:
    """Validate IP address"""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    return all(0 <= int(octet) <= 255 for octet in ip.split('.'))

def validate_and_fix_json(json_str: str, auto_fix: bool = True) -> Tuple[bool, Optional[Union[dict, list]], Optional[str]]:
    """
    Validate JSON string and optionally attempt to fix common issues
    
    Args:
        json_str: JSON string to validate
        auto_fix: If True, attempt to fix common JSON syntax errors
        
    Returns:
        Tuple of (is_valid, parsed_data, error_message)
        - is_valid: True if JSON is valid or was successfully fixed
        - parsed_data: Parsed JSON data if valid, None otherwise
        - error_message: Error message if invalid and couldn't be fixed, None otherwise
    """
    if not isinstance(json_str, str):
        return False, None, f"Expected string, got {type(json_str)}"
    
    json_str = json_str.strip()
    
    # First attempt: parse as-is
    try:
        parsed = json.loads(json_str)
        return True, parsed, None
    except json.JSONDecodeError as e:
        if not auto_fix:
            return False, None, str(e)
    
    # Attempt fixes
    fixed_json = json_str
    
    # Fix 1: Remove trailing commas before closing braces/brackets
    fixed_json = re.sub(r',(\s*[}\]])', r'\1', fixed_json)
    
    # Fix 2: Remove trailing commas at end of lines before closing braces/brackets
    lines = fixed_json.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        stripped_line = line.rstrip()
        
        # Check if line ends with comma
        if stripped_line.endswith(','):
            # Look ahead to see if next non-empty line starts with } or ]
            next_is_closing = False
            for j in range(i + 1, len(lines)):
                next_stripped = lines[j].strip()
                if next_stripped:
                    if next_stripped[0] in ('}', ']'):
                        next_is_closing = True
                    break
            
            # Remove trailing comma if next line is closing bracket
            if next_is_closing:
                stripped_line = stripped_line[:-1]
        
        fixed_lines.append(stripped_line if stripped_line != line.rstrip() else line)
    
    fixed_json = '\n'.join(fixed_lines)
    
    # Try parsing the fixed JSON
    try:
        parsed = json.loads(fixed_json)
        return True, parsed, None
    except json.JSONDecodeError as e:
        return False, None, f"Could not fix JSON: {str(e)}"


def validate_cidr(cidr: str) -> Tuple[bool, Optional[str]]:
    """
    Validate CIDR notation for subnet.

    Returns:
        (is_valid, error_message)
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        return True, None
    except ValueError as e:
        return False, str(e)


def validate_port(port: int) -> Tuple[bool, Optional[str]]:
    """
    Validate port number.

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(port, int):
        return False, "Port must be an integer"

    if port < 1 or port > 65535:
        return False, "Port must be between 1 and 65535"

    return True, None


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """
    Validate username format.

    Rules:
    - 3-50 characters
    - Alphanumeric, underscore, hyphen only
    - Must start with letter

    Returns:
        (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(username) > 50:
        return False, "Username must be at most 50 characters"

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', username):
        return False, "Username must start with a letter and contain only letters, numbers, underscores, and hyphens"

    return True, None


def validate_password_strength(password: str) -> Tuple[bool, Optional[str], int]:
    """
    Validate password meets minimum security requirements.

    Returns:
        (is_valid, error_message, strength_score)
        strength_score: 0-100
    """
    if not password:
        return False, "Password is required", 0

    if len(password) < 8:
        return False, "Password must be at least 8 characters", 10

    score = 0
    issues = []

    # Length scoring
    if len(password) >= 8:
        score += 20
    if len(password) >= 12:
        score += 10
    if len(password) >= 16:
        score += 10

    # Character variety
    if re.search(r'[a-z]', password):
        score += 15
    else:
        issues.append("lowercase letter")

    if re.search(r'[A-Z]', password):
        score += 15
    else:
        issues.append("uppercase letter")

    if re.search(r'\d', password):
        score += 15
    else:
        issues.append("number")

    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 15
    else:
        issues.append("special character")

    # Minimum requirements
    if score < 50:
        return False, f"Password should include: {', '.join(issues)}", score

    return True, None, score


# ============================================================================
# Example usage in main.py would be:
# ============================================================================

"""
from fastapi import FastAPI
from api.routes import devices, rules, audits
from config import settings
from utils.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version
)

# Include routers
app.include_router(devices.router, prefix="/devices", tags=["devices"])
app.include_router(rules.router, prefix="/rules", tags=["rules"])
app.include_router(audits.router, prefix="/audit", tags=["audits"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
"""
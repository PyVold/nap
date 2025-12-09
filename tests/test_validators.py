# ============================================================================
# tests/test_validators.py - Input validation tests
# ============================================================================

import pytest
from shared.validators import (
    validate_hostname,
    validate_ip,
    validate_email,
    validate_username,
    validate_password_strength,
    validate_port,
    validate_cidr,
    validate_safe_string,
    sanitize_string,
    check_dangerous_patterns,
    SQL_INJECTION_PATTERNS,
    COMMAND_INJECTION_PATTERNS,
    XSS_PATTERNS,
)


class TestHostnameValidation:
    """Test hostname validation"""

    def test_valid_hostnames(self):
        """Test valid hostname formats"""
        valid = ["router1", "switch-01", "fw01", "R1", "device123"]
        for hostname in valid:
            assert validate_hostname(hostname) is True, f"{hostname} should be valid"

    def test_invalid_hostnames(self):
        """Test invalid hostname formats"""
        invalid = ["-router", "router-", ".invalid", "has space", "too" + "x" * 100]
        for hostname in invalid:
            assert validate_hostname(hostname) is False, f"{hostname} should be invalid"


class TestIPValidation:
    """Test IP address validation"""

    def test_valid_ips(self):
        """Test valid IP addresses"""
        valid = ["192.168.1.1", "10.0.0.1", "0.0.0.0", "255.255.255.255"]
        for ip in valid:
            assert validate_ip(ip) is True, f"{ip} should be valid"

    def test_invalid_ips(self):
        """Test invalid IP addresses"""
        invalid = ["256.1.1.1", "1.2.3", "1.2.3.4.5", "abc.def.ghi.jkl", ""]
        for ip in invalid:
            assert validate_ip(ip) is False, f"{ip} should be invalid"


class TestEmailValidation:
    """Test email validation"""

    def test_valid_emails(self):
        """Test valid email formats"""
        valid = ["user@example.com", "test.user@domain.org", "admin@company.co.uk"]
        for email in valid:
            assert validate_email(email) is True, f"{email} should be valid"

    def test_invalid_emails(self):
        """Test invalid email formats"""
        invalid = ["notanemail", "@nodomain.com", "user@", "user@.com"]
        for email in invalid:
            assert validate_email(email) is False, f"{email} should be invalid"


class TestUsernameValidation:
    """Test username validation"""

    def test_valid_usernames(self):
        """Test valid username formats"""
        valid = ["admin", "user123", "john_doe", "jane-doe"]
        for username in valid:
            is_valid, error = validate_username(username)
            assert is_valid is True, f"{username} should be valid: {error}"

    def test_invalid_usernames(self):
        """Test invalid username formats"""
        test_cases = [
            ("ab", "too short"),
            ("123user", "starts with number"),
            ("", "empty"),
            ("user@name", "special char"),
        ]
        for username, reason in test_cases:
            is_valid, error = validate_username(username)
            assert is_valid is False, f"{username} ({reason}) should be invalid"


class TestPasswordStrength:
    """Test password strength validation"""

    def test_weak_password(self):
        """Test weak passwords are rejected"""
        weak = ["123", "password", "abc123"]
        for pwd in weak:
            is_valid, error, score = validate_password_strength(pwd)
            assert is_valid is False or score < 50

    def test_strong_password(self):
        """Test strong passwords are accepted"""
        strong = ["P@ssw0rd123!", "MySecure#Pass1", "C0mplex!Pass"]
        for pwd in strong:
            is_valid, error, score = validate_password_strength(pwd)
            assert is_valid is True, f"{pwd} should be valid: {error}"
            assert score >= 50


class TestPortValidation:
    """Test port number validation"""

    def test_valid_ports(self):
        """Test valid port numbers"""
        valid = [22, 80, 443, 830, 8080, 65535]
        for port in valid:
            is_valid, error = validate_port(port)
            assert is_valid is True

    def test_invalid_ports(self):
        """Test invalid port numbers"""
        invalid = [0, -1, 65536, 100000]
        for port in invalid:
            is_valid, error = validate_port(port)
            assert is_valid is False


class TestCIDRValidation:
    """Test CIDR notation validation"""

    def test_valid_cidr(self):
        """Test valid CIDR notations"""
        valid = ["192.168.1.0/24", "10.0.0.0/8", "172.16.0.0/16"]
        for cidr in valid:
            is_valid, error = validate_cidr(cidr)
            assert is_valid is True, f"{cidr} should be valid: {error}"

    def test_invalid_cidr(self):
        """Test invalid CIDR notations"""
        invalid = ["192.168.1.0/33", "invalid", "192.168.1.1"]
        for cidr in invalid:
            is_valid, error = validate_cidr(cidr)
            assert is_valid is False, f"{cidr} should be invalid"


class TestInjectionDetection:
    """Test injection pattern detection"""

    def test_sql_injection_detection(self):
        """Test SQL injection patterns are detected"""
        malicious = [
            "'; DROP TABLE users;--",
            "1 OR 1=1",
            "UNION SELECT * FROM passwords",
        ]
        for payload in malicious:
            is_safe, pattern = check_dangerous_patterns(payload, SQL_INJECTION_PATTERNS)
            assert is_safe is False, f"SQL injection should be detected: {payload}"

    def test_command_injection_detection(self):
        """Test command injection patterns are detected"""
        malicious = [
            "test; rm -rf /",
            "$(whoami)",
            "../../../etc/passwd",
        ]
        for payload in malicious:
            is_safe, pattern = check_dangerous_patterns(payload, COMMAND_INJECTION_PATTERNS)
            assert is_safe is False, f"Command injection should be detected: {payload}"

    def test_xss_detection(self):
        """Test XSS patterns are detected"""
        malicious = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img onerror='alert(1)'>",
        ]
        for payload in malicious:
            is_safe, pattern = check_dangerous_patterns(payload, XSS_PATTERNS)
            assert is_safe is False, f"XSS should be detected: {payload}"

    def test_safe_strings_allowed(self):
        """Test that legitimate strings pass validation"""
        safe = [
            "router-01",
            "192.168.1.1",
            "normal text",
            "user@example.com",
        ]
        for value in safe:
            is_valid, error = validate_safe_string(value)
            assert is_valid is True, f"{value} should be safe: {error}"


class TestSanitization:
    """Test string sanitization"""

    def test_html_escaping(self):
        """Test HTML characters are escaped"""
        dangerous = "<script>alert('xss')</script>"
        sanitized = sanitize_string(dangerous)
        assert "<script>" not in sanitized
        assert "&lt;script&gt;" in sanitized

    def test_null_byte_removal(self):
        """Test null bytes are removed"""
        with_null = "test\x00string"
        sanitized = sanitize_string(with_null)
        assert "\x00" not in sanitized

    def test_length_truncation(self):
        """Test strings are truncated to max length"""
        long_string = "x" * 2000
        sanitized = sanitize_string(long_string, max_length=100)
        assert len(sanitized) == 100

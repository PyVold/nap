# ============================================================================
# utils/validators.py
# ============================================================================

import re
import json
from typing import Optional, Tuple, Union
from lxml import etree

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
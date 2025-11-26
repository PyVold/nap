# ============================================================================
# utils/validators.py
# ============================================================================

import re
from typing import Optional
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
# ============================================================================
# connectors/vendor_adapters.py
# ============================================================================

from typing import Optional
from models.enums import VendorType

class VendorAdapter:
    """Adapter for vendor-specific operations"""
    
    @staticmethod
    def get_filter_for_vendor(vendor: VendorType, filter_xml: Optional[str], xpath: Optional[str]) -> tuple:
        """Get appropriate filter based on vendor"""
        if vendor == VendorType.CISCO_XR and filter_xml:
            return ('subtree', filter_xml)
        elif vendor == VendorType.NOKIA_SROS and xpath:
            return ('xpath', xpath)
        return None
    
    @staticmethod
    def adapt_config_output(vendor: VendorType, raw_output: str) -> str:
        """Adapt configuration output for vendor-specific parsing"""
        # Vendor-specific adaptations can be added here
        return raw_output

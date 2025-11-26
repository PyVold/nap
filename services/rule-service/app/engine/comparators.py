# ============================================================================
# engine/comparators.py
# ============================================================================

import re
import difflib
from typing import Tuple, Dict
from lxml import etree
from models.enums import ComparisonType
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ConfigComparator:
    """Handles configuration comparison operations"""

    @staticmethod
    def compare(
        config_data: str,
        comparison: ComparisonType,
        reference_value: str = None,
        reference_config: str = None
    ) -> Tuple[bool, str, Dict[str, str]]:
        """
        Compare configuration data against reference
        Returns: (passed, details, comparison_info)
        where comparison_info contains actual_config, expected_config, and diff
        """
        
        config_lower = config_data.lower()

        if comparison == ComparisonType.EXACT:
            return ConfigComparator._compare_exact(config_data, reference_config)

        elif comparison == ComparisonType.CONTAINS:
            return ConfigComparator._compare_contains(config_data, config_lower, reference_value)

        elif comparison == ComparisonType.NOT_CONTAINS:
            return ConfigComparator._compare_not_contains(config_data, config_lower, reference_value)

        elif comparison == ComparisonType.REGEX:
            return ConfigComparator._compare_regex(config_data, reference_value)

        elif comparison == ComparisonType.EXISTS:
            return ConfigComparator._compare_exists(config_data)

        elif comparison == ComparisonType.NOT_EXISTS:
            return ConfigComparator._compare_not_exists(config_data)

        elif comparison == ComparisonType.COUNT:
            return ConfigComparator._compare_count(config_data, reference_value)

        else:
            return False, f"Unknown comparison type: {comparison}", {}
    
    @staticmethod
    def _compare_exact(config_data: str, reference_config: str) -> Tuple[bool, str, Dict[str, str]]:
        """Exact match comparison"""
        if not reference_config:
            return False, "No reference configuration provided", {}

        passed = config_data.strip() == reference_config.strip()
        details = "Configuration matches exactly" if passed else "Configuration differs"

        # Generate diff for failed comparisons
        diff = ""
        if not passed:
            diff_lines = difflib.unified_diff(
                reference_config.splitlines(keepends=True),
                config_data.splitlines(keepends=True),
                fromfile='Expected',
                tofile='Actual',
                lineterm=''
            )
            diff = ''.join(diff_lines)

        comparison_info = {
            "actual_config": config_data.strip(),
            "expected_config": reference_config.strip(),
            "diff": diff
        }
        return passed, details, comparison_info
    
    @staticmethod
    def _compare_contains(config_data: str, config_lower: str, reference_value: str) -> Tuple[bool, str, Dict[str, str]]:
        """Contains comparison"""
        if not reference_value:
            return False, "No reference value provided", {}

        passed = reference_value.lower() in config_lower
        details = f"Found '{reference_value}'" if passed else f"'{reference_value}' not found"

        comparison_info = {
            "actual_config": config_data,
            "expected_config": f"Should contain: {reference_value}",
            "diff": ""
        }
        return passed, details, comparison_info

    @staticmethod
    def _compare_not_contains(config_data: str, config_lower: str, reference_value: str) -> Tuple[bool, str, Dict[str, str]]:
        """Does not contain comparison"""
        if not reference_value:
            return True, "No forbidden value specified", {}

        passed = reference_value.lower() not in config_lower
        details = f"'{reference_value}' correctly absent" if passed else f"Found '{reference_value}'"

        comparison_info = {
            "actual_config": config_data,
            "expected_config": f"Should NOT contain: {reference_value}",
            "diff": ""
        }
        return passed, details, comparison_info

    @staticmethod
    def _compare_regex(config_data: str, reference_value: str) -> Tuple[bool, str, Dict[str, str]]:
        """Regex pattern comparison"""
        if not reference_value:
            return False, "No regex pattern provided", {}

        try:
            pattern = re.compile(reference_value, re.IGNORECASE)
            match = pattern.search(config_data)
            passed = match is not None
            details = f"Pattern matched: {match.group()}" if match else f"Pattern '{reference_value}' not found"

            comparison_info = {
                "actual_config": config_data,
                "expected_config": f"Should match regex: {reference_value}",
                "diff": f"Match: {match.group()}" if match else "No match"
            }
            return passed, details, comparison_info
        except re.error as e:
            return False, f"Invalid regex pattern: {str(e)}", {}

    @staticmethod
    def _compare_exists(config_data: str) -> Tuple[bool, str, Dict[str, str]]:
        """Check if configuration exists"""
        passed = len(config_data.strip()) > 0 and config_data.strip() != '<data/>'
        details = "Configuration exists" if passed else "No configuration found"

        comparison_info = {
            "actual_config": config_data,
            "expected_config": "Configuration should exist",
            "diff": ""
        }
        return passed, details, comparison_info

    @staticmethod
    def _compare_not_exists(config_data: str) -> Tuple[bool, str, Dict[str, str]]:
        """Check if configuration does not exist"""
        passed = len(config_data.strip()) == 0 or config_data.strip() == '<data/>'
        details = "Configuration correctly absent" if passed else "Configuration exists"

        comparison_info = {
            "actual_config": config_data,
            "expected_config": "Configuration should NOT exist",
            "diff": ""
        }
        return passed, details, comparison_info

    @staticmethod
    def _compare_count(config_data: str, reference_value: str) -> Tuple[bool, str, Dict[str, str]]:
        """Count elements comparison"""
        if not reference_value:
            return False, "No count value provided", {}

        try:
            root = etree.fromstring(config_data.encode())
            count = len(root.xpath('//*'))
            expected_count = int(reference_value)
            passed = count >= expected_count
            details = f"Found {count} elements (expected: {expected_count})"

            comparison_info = {
                "actual_config": config_data,
                "expected_config": f"Should have at least {expected_count} elements",
                "diff": f"Actual count: {count}"
            }
            return passed, details, comparison_info
        except Exception as e:
            return False, f"Error counting elements: {str(e)}", {}

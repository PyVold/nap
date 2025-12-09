# ============================================================================
# engine/rule_executor.py
# ============================================================================

from typing import List, Dict, Any, Union
from models.device import Device
from models.rule import AuditRule, RuleCheck
from models.audit import AuditFinding
from models.enums import AuditStatus, VendorType
from connectors import NetconfConnector, BaseConnector
from engine.comparators import ConfigComparator
from shared.logger import setup_logger
from shared.exceptions import RuleExecutionError

logger = setup_logger(__name__)

class RuleExecutor:
    """Executes individual audit rules against devices"""

    @staticmethod
    async def execute_rule(
        connector: Union[NetconfConnector, BaseConnector],
        device: Device,
        rule: AuditRule
    ) -> AuditFinding:
        """Execute a single audit rule with all its checks"""
        
        check_results = []
        
        for check in rule.checks:
            try:
                result = await RuleExecutor._execute_check(connector, device, check)
                check_results.append(result)
                
            except Exception as e:
                logger.error(f"Error executing check '{check.name}' on {device.hostname}: {str(e)}")
                check_results.append({
                    'passed': False,
                    'check_name': check.name,
                    'details': str(e),
                    'message': f"Check failed: {str(e)}"
                })
        
        # Determine overall rule status
        return RuleExecutor._aggregate_check_results(rule, check_results)
    
    @staticmethod
    async def _execute_check(
        connector: Union[NetconfConnector, BaseConnector],
        device: Device,
        check: RuleCheck
    ) -> Dict[str, Any]:
        """Execute a single check"""

        # Get configuration data
        if device.vendor == VendorType.CISCO_XR and check.filter_xml:
            # Cisco XR uses subtree filter
            config_data = await connector.get_config(filter_data=check.filter_xml)
        elif device.vendor == VendorType.NOKIA_SROS and check.xpath:
            # Nokia SROS uses XPath and returns configuration (not operational state)
            # If filter is provided, use it to narrow down the query
            if check.filter:
                config_data = await connector.get_config(xpath=check.xpath, filter=check.filter)
            else:
                config_data = await connector.get_config(xpath=check.xpath)
        else:
            # Fallback to full config
            config_data = await connector.get_config()

        # Perform comparison - now returns (passed, details, comparison_info)
        check_passed, details, comparison_info = ConfigComparator.compare(
            config_data,
            check.comparison,
            check.reference_value,
            check.reference_config
        )

        return {
            'passed': check_passed,
            'check_name': check.name,
            'details': details,
            'message': check.success_message if check_passed else check.error_message,
            'actual_config': comparison_info.get('actual_config', ''),
            'expected_config': comparison_info.get('expected_config', ''),
            'diff': comparison_info.get('diff', ''),
            'xpath': check.xpath,  # Store xpath for Nokia remediation
            'filter_xml': check.filter_xml,  # Store filter for Cisco remediation
            'reference_config': check.reference_config  # Store actual reference value for remediation
        }
    
    @staticmethod
    def _aggregate_check_results(rule: AuditRule, check_results: List[Dict]) -> AuditFinding:
        """Aggregate multiple check results into a single finding"""

        all_passed = all(r['passed'] for r in check_results)
        any_failed = any(not r['passed'] for r in check_results)

        if all_passed:
            status = AuditStatus.PASS
            message = check_results[0]['message'] if check_results else "All checks passed"
            details = None
        elif any_failed:
            failed_checks = [r for r in check_results if not r['passed']]
            status = AuditStatus.FAIL
            message = failed_checks[0]['message']
            details = "\n".join([
                f"{r['check_name']}: {r['details']}"
                for r in failed_checks if r['details']
            ])
        else:
            status = AuditStatus.WARNING
            message = "Some checks incomplete"
            details = None

        # Get config details from the first failed check, or first check if all passed
        config_source = failed_checks[0] if any_failed and failed_checks else (check_results[0] if check_results else {})
        actual_config = config_source.get('actual_config', '')
        expected_config = config_source.get('expected_config', '')
        comparison_details = config_source.get('diff', '')
        xpath = config_source.get('xpath')
        filter_xml = config_source.get('filter_xml')
        reference_config = config_source.get('reference_config')

        return AuditFinding(
            rule=rule.name,
            status=status,
            message=message,
            details=details,
            severity=rule.severity,
            check_name=check_results[0]['check_name'] if check_results else None,
            actual_config=actual_config if actual_config else None,
            expected_config=reference_config if reference_config else expected_config if expected_config else None,
            comparison_details=comparison_details if comparison_details else None,
            xpath=xpath,
            filter_xml=filter_xml
        )

# ============================================================================
# engine/protocol_parsers/bgp_parser.py
# BGP Protocol Parser
# ============================================================================

import re
import operator
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class BGPParser:
    """Parser for BGP protocol data"""

    def parse_summary(self, output: str) -> Dict[str, Any]:
        """
        Parse 'show ip bgp summary' or 'show bgp summary' output

        Returns:
            {
                'router_id': str,
                'local_as': int,
                'neighbor_count': int,
                'neighbors': [
                    {
                        'peer': str,
                        'remote_as': int,
                        'state': str,
                        'prefixes': int,
                        'uptime': str
                    }
                ]
            }
        """
        result = {
            'router_id': None,
            'local_as': None,
            'neighbor_count': 0,
            'neighbors': []
        }

        # Parse router ID and local AS
        router_id_match = re.search(r'BGP router identifier\s+(\d+\.\d+\.\d+\.\d+).*?local AS number\s+(\d+)', output, re.IGNORECASE)
        if router_id_match:
            result['router_id'] = router_id_match.group(1)
            result['local_as'] = int(router_id_match.group(2))

        # Parse neighbor table
        # Looking for lines like: 10.0.1.2    4      65001    100    200    0    0 00:15:30    1
        neighbor_pattern = r'(\d+\.\d+\.\d+\.\d+)\s+\d+\s+(\d+)\s+\d+\s+\d+\s+\d+\s+\d+\s+([\d:]+)\s+(\d+)'
        for match in re.finditer(neighbor_pattern, output):
            result['neighbors'].append({
                'peer': match.group(1),
                'remote_as': int(match.group(2)),
                'uptime': match.group(3),
                'prefixes': int(match.group(4)),
                'state': 'Established'  # If we see prefixes, it's established
            })

        # Check for idle/active/connect states
        idle_pattern = r'(\d+\.\d+\.\d+\.\d+)\s+\d+\s+(\d+).*?(Idle|Active|Connect)'
        for match in re.finditer(idle_pattern, output):
            # Update or add neighbor with non-established state
            peer = match.group(1)
            existing = next((n for n in result['neighbors'] if n['peer'] == peer), None)
            if existing:
                existing['state'] = match.group(3)
            else:
                result['neighbors'].append({
                    'peer': peer,
                    'remote_as': int(match.group(2)),
                    'state': match.group(3),
                    'prefixes': 0,
                    'uptime': 'never'
                })

        result['neighbor_count'] = len(result['neighbors'])
        return result

    def parse_neighbors(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse 'show ip bgp neighbors' or 'show bgp neighbors' output

        Returns list of detailed neighbor info
        """
        neighbors = []

        # Split by "BGP neighbor is" to get individual neighbor sections
        sections = re.split(r'BGP neighbor is', output)[1:]  # Skip first empty split

        for section in sections:
            neighbor = {}

            # Peer address and AS
            peer_match = re.search(r'(\d+\.\d+\.\d+\.\d+).*?remote AS\s+(\d+)', section)
            if peer_match:
                neighbor['peer'] = peer_match.group(1)
                neighbor['remote_as'] = int(peer_match.group(2))

            # BGP state
            state_match = re.search(r'BGP state\s*=\s*(\w+)', section)
            if state_match:
                neighbor['state'] = state_match.group(1)

            # Received prefixes
            prefix_match = re.search(r'(\d+)\s+accepted prefixes', section)
            if prefix_match:
                neighbor['prefixes'] = int(prefix_match.group(1))

            # Connection time
            uptime_match = re.search(r'up for\s+([\d:]+)', section)
            if uptime_match:
                neighbor['uptime'] = uptime_match.group(1)

            if neighbor:
                neighbors.append(neighbor)

        return neighbors

    def collect_facts(self, device_connection) -> Dict[str, Any]:
        """
        Collect BGP facts from device

        Args:
            device_connection: Active device connection (NETCONF, SSH, etc.)

        Returns:
            Dictionary with BGP facts
        """
        # Execute show commands
        summary_output = device_connection.execute_command('show ip bgp summary')
        neighbors_output = device_connection.execute_command('show ip bgp neighbors')

        # Parse outputs
        summary_data = self.parse_summary(summary_output)
        detailed_neighbors = self.parse_neighbors(neighbors_output)

        # Merge detailed info
        for summary_neighbor in summary_data['neighbors']:
            detailed = next(
                (n for n in detailed_neighbors if n['peer'] == summary_neighbor['peer']),
                None
            )
            if detailed:
                summary_neighbor.update(detailed)

        return summary_data

    def validate_assertion(self, parsed_data: Dict[str, Any], assertion: str, variables: Dict[str, Any]) -> bool:
        """
        Validate an assertion against parsed BGP data safely without eval()

        Args:
            parsed_data: Parsed BGP data
            assertion: Assertion string (e.g., "neighbor_count >= 2", "bgp.neighbor_count >= 2")
            variables: Template variables for substitution

        Returns:
            True if assertion passes, False otherwise
        """
        # Create evaluation context
        context = {
            'bgp': parsed_data,
            **variables
        }

        try:
            # Safely evaluate assertion without using eval()
            return self._safe_evaluate(assertion.strip(), context)
        except Exception as e:
            logger.error(f"Error evaluating assertion '{assertion}': {e}")
            return False

    def _safe_evaluate(self, expr: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate a simple boolean expression without using eval()"""
        # Supported comparison operators (check longer ones first)
        ops = [
            ('>=', operator.ge),
            ('<=', operator.le),
            ('!=', operator.ne),
            ('==', operator.eq),
            ('>', operator.gt),
            ('<', operator.lt),
        ]

        # Try simple comparisons
        for op_str, op_func in ops:
            if op_str in expr:
                parts = expr.split(op_str, 1)
                if len(parts) == 2:
                    left = self._resolve_value(parts[0].strip(), context)
                    right = self._resolve_value(parts[1].strip(), context)
                    return op_func(left, right)

        # Check for 'not in' operator
        if ' not in ' in expr:
            parts = expr.split(' not in ', 1)
            if len(parts) == 2:
                left = self._resolve_value(parts[0].strip(), context)
                right = self._resolve_value(parts[1].strip(), context)
                return left not in right

        # Check for 'in' operator
        if ' in ' in expr:
            parts = expr.split(' in ', 1)
            if len(parts) == 2:
                left = self._resolve_value(parts[0].strip(), context)
                right = self._resolve_value(parts[1].strip(), context)
                return left in right

        # Try to resolve as a single value (truthy check)
        value = self._resolve_value(expr, context)
        return bool(value)

    def _resolve_value(self, value_str: str, context: Dict[str, Any]) -> Any:
        """Resolve a value from string representation safely"""
        value_str = value_str.strip()

        # Handle quoted strings
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]

        # Handle numeric values
        try:
            if '.' in value_str and not any(c.isalpha() for c in value_str):
                return float(value_str)
            if value_str.isdigit() or (value_str.startswith('-') and value_str[1:].isdigit()):
                return int(value_str)
        except ValueError:
            pass

        # Handle boolean literals
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False
        if value_str.lower() == 'none':
            return None

        # Look up in context (supports dot notation like bgp.neighbor_count)
        if '.' in value_str:
            parts = value_str.split('.')
            current = context
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                elif hasattr(current, part):
                    current = getattr(current, part)
                else:
                    return value_str  # Return as string if not found
            return current

        # Simple context lookup
        if value_str in context:
            return context[value_str]

        # Return as-is (string)
        return value_str

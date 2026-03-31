# ============================================================================
# engine/protocol_parsers/bgp_parser.py
# BGP Protocol Parser
# ============================================================================

import ast
import operator
import re
from typing import Dict, List, Any, Optional


# Safe expression evaluation helpers — no eval() or exec() used
_SAFE_OPERATORS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.Not: operator.not_,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}


def _safe_eval(expression: str, context: Dict[str, Any]) -> bool:
    """Safely evaluate a boolean expression with context variables."""
    try:
        tree = ast.parse(expression, mode='eval')
        return _eval_node(tree.body, context)
    except Exception:
        return False


def _eval_node(node: ast.expr, context: Dict[str, Any]) -> Any:
    """Recursively evaluate an AST node using only whitelisted operations."""
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_eval_node(v, context) for v in node.values)
        elif isinstance(node.op, ast.Or):
            return any(_eval_node(v, context) for v in node.values)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval_node(node.operand, context)
    elif isinstance(node, ast.Compare):
        left = _eval_node(node.left, context)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, context)
            if type(op) not in _SAFE_OPERATORS:
                raise ValueError(f"Unsupported operator: {type(op).__name__}")
            if not _SAFE_OPERATORS[type(op)](left, right):
                return False
            left = right
        return True
    elif isinstance(node, ast.Name):
        if node.id in context:
            return context[node.id]
        raise ValueError(f"Unknown variable: {node.id}")
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Attribute):
        value = _eval_node(node.value, context)
        if isinstance(value, dict):
            return value.get(node.attr)
        return getattr(value, node.attr, None)
    elif isinstance(node, ast.Subscript):
        value = _eval_node(node.value, context)
        key = _eval_node(node.slice, context)
        return value[key]
    raise ValueError(f"Unsupported expression: {type(node).__name__}")


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
        Validate an assertion against parsed BGP data

        Args:
            parsed_data: Parsed BGP data
            assertion: Assertion string (e.g., "neighbor_count >= 2")
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
            return bool(_safe_eval(assertion.strip(), context))
        except Exception as e:
            print(f"Error evaluating assertion '{assertion}': {e}")
            return False

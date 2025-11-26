# ============================================================================
# engine/protocol_parsers/ospf_parser.py
# OSPF Protocol Parser
# ============================================================================

import re
from typing import Dict, List, Any


class OSPFParser:
    """Parser for OSPF protocol data"""

    def parse_neighbors(self, output: str) -> Dict[str, Any]:
        """
        Parse 'show ip ospf neighbor' output

        Returns:
            {
                'neighbor_count': int,
                'neighbors': [
                    {
                        'neighbor_id': str,
                        'priority': int,
                        'state': str,
                        'interface': str,
                        'address': str
                    }
                ]
            }
        """
        result = {
            'neighbor_count': 0,
            'neighbors': []
        }

        # Pattern for OSPF neighbor lines
        # Example: 10.0.1.2    1    FULL/DR    00:05:30    GigabitEthernet0/0    10.0.1.2
        neighbor_pattern = r'(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(\w+\/?\w*)\s+[\d:]+\s+(\S+)\s+(\d+\.\d+\.\d+\.\d+)'

        for match in re.finditer(neighbor_pattern, output):
            result['neighbors'].append({
                'neighbor_id': match.group(1),
                'priority': int(match.group(2)),
                'state': match.group(3),
                'interface': match.group(4),
                'address': match.group(5)
            })

        result['neighbor_count'] = len(result['neighbors'])
        return result

    def collect_facts(self, device_connection) -> Dict[str, Any]:
        """Collect OSPF facts from device"""
        output = device_connection.execute_command('show ip ospf neighbor')
        return self.parse_neighbors(output)

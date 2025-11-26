# ============================================================================
# engine/protocol_parsers/isis_parser.py
# ISIS Protocol Parser
# ============================================================================

import re
from typing import Dict, List, Any


class ISISParser:
    """Parser for ISIS protocol data"""

    def parse_neighbors(self, output: str) -> Dict[str, Any]:
        """
        Parse 'show isis neighbors' output

        Returns:
            {
                'neighbor_count': int,
                'neighbors': [
                    {
                        'system_id': str,
                        'interface': str,
                        'level': str,  # L1, L2, L1L2
                        'state': str,  # UP, INIT, DOWN
                        'holdtime': int
                    }
                ]
            }
        """
        result = {
            'neighbor_count': 0,
            'neighbors': []
        }

        # Pattern for ISIS neighbor lines
        # Example: router2    Gi0/0/0     L2    UP    25
        neighbor_pattern = r'(\S+)\s+(\S+)\s+(L\d(?:L\d)?)\s+(UP|INIT|DOWN)\s+(\d+)'

        for match in re.finditer(neighbor_pattern, output):
            result['neighbors'].append({
                'system_id': match.group(1),
                'interface': match.group(2),
                'level': match.group(3),
                'state': match.group(4),
                'holdtime': int(match.group(5))
            })

        result['neighbor_count'] = len(result['neighbors'])
        return result

    def collect_facts(self, device_connection) -> Dict[str, Any]:
        """Collect ISIS facts from device"""
        output = device_connection.execute_command('show isis neighbors')
        return self.parse_neighbors(output)

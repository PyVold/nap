# ============================================================================
# engine/protocol_parsers/interface_parser.py
# Interface Parser
# ============================================================================

import re
from typing import Dict, List, Any


class InterfaceParser:
    """Parser for interface data"""

    def parse_interfaces(self, output: str) -> Dict[str, Any]:
        """
        Parse 'show interfaces' or 'show ip interface brief' output

        Returns:
            {
                'interface_count': int,
                'interfaces': [
                    {
                        'name': str,
                        'status': str,  # up, down, admin-down
                        'protocol': str,  # up, down
                        'ip_address': str,
                        'mtu': int
                    }
                ]
            }
        """
        result = {
            'interface_count': 0,
            'interfaces': []
        }

        # Pattern for interface brief
        # Example: GigabitEthernet0/0    10.0.1.1    YES manual up    up
        brief_pattern = r'(\S+)\s+(\d+\.\d+\.\d+\.\d+|unassigned)\s+\w+\s+\w+\s+(up|down|administratively down)\s+(up|down)'

        for match in re.finditer(brief_pattern, output):
            result['interfaces'].append({
                'name': match.group(1),
                'ip_address': match.group(2) if match.group(2) != 'unassigned' else None,
                'status': match.group(3),
                'protocol': match.group(4)
            })

        result['interface_count'] = len(result['interfaces'])
        return result

    def collect_facts(self, device_connection) -> Dict[str, Any]:
        """Collect interface facts from device"""
        output = device_connection.execute_command('show ip interface brief')
        return self.parse_interfaces(output)

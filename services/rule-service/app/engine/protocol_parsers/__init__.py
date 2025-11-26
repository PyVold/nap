# ============================================================================
# engine/protocol_parsers/__init__.py
# Protocol-aware parsers for audit orchestrator
# ============================================================================

from .bgp_parser import BGPParser
from .isis_parser import ISISParser
from .ospf_parser import OSPFParser
from .interface_parser import InterfaceParser

# Protocol parser registry
PROTOCOL_PARSERS = {
    'bgp': BGPParser,
    'isis': ISISParser,
    'ospf': OSPFParser,
    'interface': InterfaceParser,
}


def get_parser(protocol: str):
    """Get parser instance for protocol"""
    parser_class = PROTOCOL_PARSERS.get(protocol.lower())
    if not parser_class:
        raise ValueError(f"Unknown protocol: {protocol}")
    return parser_class()


__all__ = [
    'BGPParser',
    'ISISParser',
    'OSPFParser',
    'InterfaceParser',
    'get_parser',
    'PROTOCOL_PARSERS',
]

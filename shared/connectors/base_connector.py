# ============================================================================
# connectors/base_connector.py
# ============================================================================

from abc import ABC, abstractmethod
from typing import Optional

class BaseConnector(ABC):
    """Abstract base class for device connectors"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to device"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close connection to device"""
        pass
    
    @abstractmethod
    async def get_config(self, source: str = 'running', filter_data: Optional[str] = None) -> str:
        """Retrieve device configuration"""
        pass
    
    @abstractmethod
    async def get_operational_state(self, filter_data: Optional[str] = None) -> str:
        """Retrieve operational state data"""
        pass

# ============================================================================
# config.py
# ============================================================================

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 3000
    api_title: str = "Network Router Audit Platform"
    api_version: str = "2.0.0"
    
    # NETCONF Settings
    netconf_timeout: int = 30
    netconf_port: int = 830
    
    # Database (optional)
    database_url: Optional[str] = None
    
    # Redis (optional)
    redis_url: Optional[str] = None
    
    # Logging
    log_level: str = "DEBUG"
    log_format: str = "json"
    debug_mode: bool = True
    log_file: str = "logs/network_audit.log"
    log_file_max_bytes: int = 10485760  # 10MB
    log_file_backup_count: int = 5

    # Health Check Settings
    health_check_enabled: bool = True
    health_check_interval_minutes: int = 5  # How often to run health checks

    # Config Backup Settings
    config_backup_enabled: bool = True
    config_backup_interval_minutes: int = 3  # How often to run automated config backups (default: hourly)
    nokia_backup_format: str = "cli"  # Options: "json" (NETCONF) or "cli" (SSH)

    # Security
    enable_auth: bool = False
    api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

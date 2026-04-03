"""
DB Models re-export for ai-service.

The ai-service uses shared.db_models for all ORM models.
This module re-exports them so that bare imports like
`from db_models import UserDB` (used by shared/deps.py) resolve correctly.
"""

from shared.db_models import *  # noqa: F401,F403

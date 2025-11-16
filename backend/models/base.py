"""
Re-export Base from core.database for backward compatibility with tests.
"""

from backend.core.database import Base

__all__ = ["Base"]

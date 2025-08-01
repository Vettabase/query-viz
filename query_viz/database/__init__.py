"""
Database connections package
"""

from .base import DatabaseConnection, SUCCESS, FAIL
from .mariadb import MariaDBConnection

__all__ = ['DatabaseConnection', 'MariaDBConnection', 'SUCCESS', 'FAIL']

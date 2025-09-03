"""
Database connections package
"""

from .base import DatabaseConnection, SUCCESS, FAIL
from .mariadb import MariaDBConnection
from .mysql import MySQLConnection

__all__ = [
    # Generic requirements
    'DatabaseConnection',
    'SUCCESS',
    'FAIL',
    # Connectors
    'MariaDBConnection',
    'MySQLConnection'
]

"""
Connection management for QueryViz - handles database connections and retries
"""

from .database import MariaDBConnection
from .exceptions import QueryVizError


class ConnectionManager:
    """Manages database connections for QueryViz"""
    
    def __init__(self):
        """Initialize connection manager"""
        pass
    
    @staticmethod
    def get_connection_class(dbms_type):
        """
        Get the appropriate connection class for a DBMS type
        
        Args:
            dbms_type (str): The DBMS type ('mariadb', etc.)
            
        Returns:
            class: The appropriate DatabaseConnection subclass
            
        Raises:
            QueryVizError: If DBMS type is not supported
        """
        # TODO: DBMS types should not be hardcoded
        if dbms_type == 'mariadb':
            return MariaDBConnection
        else:
            raise QueryVizError(f"Unsupported DBMS: {dbms_type}")
    
    @staticmethod
    def validate_connection_config(conn_config, index):
        """
        Validate a single connection configuration
        
        Args:
            conn_config (dict): Connection configuration
            index (int): Index of this connection (for error messages)
            
        Raises:
            QueryVizError: If configuration is invalid
        """
        required_fields = ['name', 'dbms', 'host', 'port', 'user', 'password']
        for field in required_fields:
            if field not in conn_config:
                raise QueryVizError(f"Connection {index}: '{field}' is required")

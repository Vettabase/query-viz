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
    
    def setup_connections_for(self, connections_dict, connections_config, db_timeout):
        """
        Setup database connections in the provided dictionary (facade pattern)
        
        Args:
            connections_dict (dict): Dictionary to store connections in
            connections_config (list): List of connection configurations
            db_timeout (int): Database connection timeout in seconds
            
        Returns:
            str: Name of the default connection (first in list)
            
        Raises:
            QueryVizError: If connection setup fails
        """
        for i, conn_config in enumerate(connections_config):
            # Use existing helper methods
            self.validate_connection_config(conn_config, i)
            connection_class = self.get_connection_class(conn_config['dbms'])
            
            # Create connection instance
            conn = connection_class(conn_config, db_timeout)
            connections_dict[conn_config['name']] = conn
        
        # Return default connection name
        return connections_config[0]['name']
    
    def test_connections(self):
        """Test all database connections before starting main loop"""
        connection_manager = ConnectionManager()
        
        grace_period_retry_interval = self.config['grace_period_retry_interval']
        initial_grace_period = self.config['initial_grace_period']
        
        # Use ConnectionManager facade to test connections
        return connection_manager.test_connections_for(
            self.connections,
            initial_grace_period,
            grace_period_retry_interval
        )

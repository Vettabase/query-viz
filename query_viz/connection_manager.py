"""
Connection management for QueryViz - handles database connections and retries
"""

import time

from .database import MariaDBConnection, SUCCESS, FAIL
from .exceptions import QueryVizError


class ConnectionManager:
    """Manages database connections for QueryViz"""
    
    def __init__(self):
        """Initialize connection manager"""
        self._connections = {}
    
    @property
    def connections(self):
        """Get connections dictionary"""
        return self._connections
    
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
    
    def test_connections_for(self, connections_dict, initial_grace_period, grace_period_retry_interval):
        """Test all database connections with grace period (facade pattern)"""
        import time
        
        print("Testing connections...")
        start_time = time.time()
        
        while True:
            failed_connections = 0
            total_connections = len(connections_dict)
            
            for conn_name, connection in connections_dict.items():
                try:
                    print(f"Connection attempt to '{connection.host}'... ", end="")
                    connection.connect()
                    print("success")
                except QueryVizError as e:
                    failed_connections += 1
                    elapsed_time = time.time() - start_time
                    if elapsed_time >= initial_grace_period:
                        print("fail. WON'T RETRY")
                    else:
                        print("fail. Will retry")
                    print(f"    Reason: {e}")
            
            if failed_connections > 0:
                print(f"{failed_connections}/{total_connections} connections are not working")
            
            if failed_connections == 0:
                print("Execution will continue")
                return True
            
            elapsed_time = time.time() - start_time
            if elapsed_time >= initial_grace_period:
                print("Aborting")
                for conn in connections_dict.values():
                    conn.close()
                return False
            
            time.sleep(grace_period_retry_interval)
    
    def start_connection_retry_thread(self, config, query_viz_instance):
        """
        Start the connection retry thread
        
        Args:
            config (dict): Configuration dictionary with failed_connections_interval
            query_viz_instance: Reference to QueryViz instance to check running flag
            
        Returns:
            threading.Thread: The started thread
        """
        import threading
        
        retry_thread = threading.Thread(target=self._retry_thread_worker, args=(config, query_viz_instance))
        retry_thread.daemon = True
        retry_thread.start()
        return retry_thread
    
    def _retry_thread_worker(self, config, query_viz_instance):
        """
        Worker function for the connection retry thread
        
        Args:
            config (dict): Configuration dictionary with failed_connections_interval
            query_viz_instance: Reference to QueryViz instance to check running flag
        """
        failed_connections_interval = config['failed_connections_interval']
        
        while query_viz_instance.running:
            time.sleep(failed_connections_interval)
            
            if not query_viz_instance.running:
                break
            
            # Retry failed connections
            self.retry_failed_connections_for(
                self.connections, 
                failed_connections_interval
            )
	
    def retry_failed_connections_for(self, connections_dict, failed_connections_interval):
        """
        Retry failed connections once (facade pattern)
        
        Args:
            connections_dict (dict): Dictionary of connections to check
            failed_connections_interval (float): Interval between retries in seconds
            
        Returns:
            bool: True if any connections were retried, False if none needed retry
        """
        import time
        
        retries_attempted = False
        
        # Check for failed connections and try to reconnect
        for conn_name, connection in connections_dict.items():
            if connection.status == FAIL:
                try:
                    print(f"Retrying connection '{conn_name}'...")
                    connection.connect()
                    print(f"Connection '{conn_name}': Reconnected successfully")
                    retries_attempted = True
                except QueryVizError:
                    # Connection still failed, status already set to FAIL in connect()
                    pass
        
        return retries_attempted

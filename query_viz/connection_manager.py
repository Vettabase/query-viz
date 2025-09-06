"""
Connection management for QueryViz - handles database connections and retries
"""

import importlib.util
import time
import os

from .database import SUCCESS, FAIL
from .database.base import DatabaseConnection
from .exceptions import QueryVizError


class ConnectionManager:
    """Manages database connections for QueryViz"""
    
    def __init__(self):
        """Initialize connection manager"""
        self._connections = {}
        # List of imported database classes. The key is the DBMS type
        # and the value is the class itself
        self._dbms_list = {}
    
    def list_dbms(self):
        """
        Scan the database directory and return a list of available DBMS connectors.
        
        Returns:
            list: Sorted list of available DBMSs.
        """
        dbms_list = []
        
        # Get the path to the database directory
        try:
            import query_viz.database
            database_dir = os.path.dirname(query_viz.database.__file__)
        except ImportError:
            return []
        
        # Scan for Python files in the database directory
        for filename in os.listdir(database_dir):
            if filename.endswith('.py') and filename not in ['__init__.py', 'base.py']:
                # Remove filename extension
                module_name = filename[:-3]
                
                # Try to load the module and check for valid connection class
                # Let's not catch Python errors, or debugging failed imports will be impossible
                module_path = os.path.join(database_dir, filename)
                spec = importlib.util.spec_from_file_location(f"query_viz.database.{module_name}", module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Look for classes that end with "Connection" and inherit from DatabaseConnection
                for attr_name in dir(module):
                    if attr_name.endswith('Connection') and attr_name != 'DatabaseConnection':
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, DatabaseConnection) and 
                            attr is not DatabaseConnection):
                            
                            # Extract DBMS name from class name
                            # MariaDBConnection -> MariaDB
                            
                            # Remove Connection (10 chars)
                            dbms_name = attr_name[:-10]
                            dbms_list.append(dbms_name)
                            break
        
        return sorted(dbms_list)
    
    def get_dbms_info(self, dbms_type):
        """
        Get detailed information about a specific Connector
        
        Args:
            dbms_type (str): The Connector to get info for (case-sensitive)
            
        Returns:
            dict: Information dictionary from the connector's info property
            
        Raises:
            QueryVizError: If the DBMS module cannot be loaded or has no info
        """
        try:
            db_class = self._load_database_class(dbms_type)
            return db_class.info
        except Exception as e:
            raise QueryVizError(f"Failed to get information for DBMS '{dbms_type}': {e}")
    
    def _load_database_class(self, dbms_type):
        """
        Dynamically load database class for the specified DBMS type
        
        Args:
            dbms_type (str): The DBMS type to load (case-sensitive)
            
        Returns:
            class: The DatabaseConnection subclass
            
        Raises:
            QueryVizError: If the DBMS module cannot be loaded
        """
        # Check if already loaded
        if dbms_type in self._dbms_list:
            return self._dbms_list[dbms_type]
            
        try:
            # Import the module dynamically (convert to lowercase for module name)
            module_name = f"query_viz.database.{dbms_type.lower()}"
            module = __import__(module_name, fromlist=[dbms_type.lower()])
            
            # Construct expected class name, eg: MariaDBConnection
            class_name = f"{dbms_type}Connection"
            
            # Get the class from the module
            if not hasattr(module, class_name):
                raise QueryVizError(f"Class '{class_name}' not found in module '{module_name}'")
            
            db_class = getattr(module, class_name)
            
            # Verify it's a DatabaseConnection subclass
            if not issubclass(db_class, DatabaseConnection):
                raise QueryVizError(f"Class '{class_name}' is not a DatabaseConnection subclass")
            
            # Cache the class
            self._dbms_list[dbms_type] = db_class
            
            print(f"Successfully loaded database support for: {dbms_type}")
            return db_class
            
        except ImportError as e:
            raise QueryVizError(f"Failed to import database module for '{dbms_type}': {e}")
        except Exception as e:
            raise QueryVizError(f"Failed to load database class for '{dbms_type}': {e}")
    
    @property
    def connections(self):
        """Get connections dictionary"""
        return self._connections
    
    def connection_exists(self, connection_name):
        """
        Return whether a connection with the given name exists.
        
        Args:
            connection_name (str): Name of the connection to look for
            
        Returns:
            bool: True if connection exists, False otherwise
        """
        return connection_name in self.connections
    
    def connection_has_failed(self, connection_name):
        """
        Check if a connection has failed
        
        Args:
            connection_name (str): Name of the connection to check
            
        Returns:
            bool: True if connection has failed, False otherwise
            
        Raises:
            QueryVizError: If connection name doesn't exist
        """
        if connection_name not in self.connections:
            raise QueryVizError(f"Connection '{connection_name}' not found")
        
        return self.connections[connection_name].status == FAIL
    
    def execute_query(self, connection_name, query):
        """
        Execute a query on the specified connection
        
        Args:
            connection_name (str): Name of the connection to use
            query (str): SQL query to execute
            
        Returns:
            tuple: (columns, results) where columns is list of column names
                   and results is list of result rows
            
        Raises:
            QueryVizError: If connection doesn't exist or query execution fails
        """
        if connection_name not in self.connections:
            raise QueryVizError(f"Connection '{connection_name}' not found")
        
        connection = self.connections[connection_name]
        return connection.execute_query(query)
    
    def validate_connection_config(self, conn_config, index):
        """
        Validate a single connection configuration by delegating to the appropriate connector
        
        Args:
            conn_config (dict): Connection configuration
            index (int): Index of this connection (for error messages)
            
        Raises:
            QueryVizError: If configuration is invalid or database cannot be loaded
        """
        # Check basic required fields first
        if 'dbms' not in conn_config:
            raise QueryVizError(f"Connection {index}: 'dbms' is required")
        
        # Load the database class and delegate validation to it
        dbms_type = conn_config['dbms']
        try:
            db_class = self._load_database_class(dbms_type)
            # Delegate validation to the connector class
            db_class.validate_config(conn_config)
        except QueryVizError as e:
            raise QueryVizError(f"Connection {index}: {e}")
    
    def setup_connections(self, connections_config, db_timeout):
        """
        Setup database connections, except for disabled connections.
        
        Args:
            connections_config (list): List of connection configurations
            db_timeout (int): Database connection timeout in seconds
            
        Returns:
            str: Name of the default connection (first in list)
            
        Raises:
            QueryVizError: If connection setup fails or no enabled
                           connections were found.
        """
        for i, conn_config in enumerate(connections_config):
            # If the connection is disabled, skip it
            if 'enabled' in conn_config:
                enabled_value = str(conn_config['enabled']).lower()
                if enabled_value in ['no', 'n', 'false', '0']:
                    print("Found disabled connection: " + conn_config['name'])
                    continue
            
            # Use existing helper methods
            self.validate_connection_config(conn_config, i)
            connection_class = self._load_database_class(conn_config['dbms'])
            
            # Create connection instance
            conn = connection_class(conn_config, db_timeout)
            self.connections[conn_config['name']] = conn
        
        if not self.connections:
            raise QueryVizError("No enabled connections found")

        # Return default connection name
        return list(self.connections.keys())[0]
    
    def close_all_connections(self):
        """Close all database connections"""
        for conn in self.connections.values():
            try:
                conn.close()
            except Exception as e:
                # Log error but continue closing other connections
                print(f"Warning: Error closing connection '{conn.name}': {e}")
    
    def test_connections(self, initial_grace_period, grace_period_retry_interval):
        """
        Test all database connections with grace period
        
        Args:
            initial_grace_period (float): Grace period in seconds
            grace_period_retry_interval (float): Retry interval in seconds
            
        Returns:
            bool: True if at least one connection succeeded, False otherwise
        """
        print("Testing connections...")
        start_time = time.time()
        
        while True:
            failed_connections = 0
            total_connections = len(self.connections)
            
            for conn_name, connection in self.connections.items():
                if connection.status == SUCCESS:
                    continue
                try:
                    print("Connection attempt to '" + connection.config['host'] + "'... ", end="")
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
                for conn in self.connections.values():
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
            self.retry_failed_connections(failed_connections_interval)
    
    def retry_failed_connections(self, failed_connections_interval):
        """
        Retry failed connections once
        
        Args:
            failed_connections_interval (float): Interval between retries in seconds
            
        Returns:
            bool: True if any connections were retried, False if none needed retry
        """
        retries_attempted = False
        
        # Check for failed connections and try to reconnect
        for conn_name, connection in self.connections.items():
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

"""
MySQL database connection implementation
"""

import mysql.connector
from mysql.connector import pooling
from .base import DatabaseConnection, SUCCESS, FAIL
from ..exceptions import QueryVizError


class MySQLConnection(DatabaseConnection):
    """MySQL database connection, with connection pooling support"""
    
    # Connector metadata
    info = DatabaseConnection.info.copy()
    info.update({
        "connector-name": "QV-MySQL",
        "connector-url": "https://github.com/Vettabase/query-viz",
        "version": "0.1",
        "maturity": "gamma", 
        "license": "AGPLv3",
        "copyright": "2025, Vettabase Ltd",
        "authors": [{"name": "Vettabase Ltd", "url": "https://vettabase.com"}]
    })
    
    # Default configuration values for MySQL connections
    defaults = {
        'host': 'localhost',
        'port': 3306,
        'user': None,
        'password': None
    }
    
    def __init__(self, config, db_timeout):
        super().__init__(config, db_timeout)
        super()._auto_validate(config)
        self.pool = None
    
    @classmethod
    def validate_config(cls, config):
        """
        Validate MySQL-specific configuration
        
        Args:
            config (dict): Connection configuration to validate
            
        Raises:
            QueryVizError: If configuration is invalid
        """
        connection_name = config.get('name', None)

        # Validate all required fields for MySQL
        required_fields = ['name', 'dbms', 'host', 'port', 'user', 'password']
        for field in required_fields:
            if field not in config:
                cls.validationError(connection_name, f"'{field}' is required")
        
        # MySQL-specific validation
        port = config['port']
        if not isinstance(port, int) or port <= 0 or port > 65535:
            cls.validationError(connection_name, "'port' must be a valid port number (1-65535)")
    
    def connect(self):
        """Create connection pool"""
        try:
            if ':' in host:
                host = self.config['host'].split(':')[0]
                port = self.config['port'].split(':')[1]
            else:
                host = self.config['host']
                port = self.config['port']
            self.pool = pooling.MySQLConnectionPool(
                pool_name='pool_' + self.config['name'],
                pool_size=5,
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                connection_timeout=self.db_timeout
            )
            print(f"[mysql] Created connection pool to {self.config['host']}:{self.config['port']}")
            self.status = SUCCESS
        except mysql.connector.Error as e:
            self.status = FAIL
            raise QueryVizError(f"[mysql] Failed to create connection pool for {self.config['host']}: {str(e)}")
    
    def execute_query(self, query):
        """Get connection from pool, execute query, return connection"""
        if not self.pool:
            raise QueryVizError("[mysql] No connection")
        
        connection = self.pool.get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()
            cursor.close()
            return columns, results
        except mysql.connector.Error as e:
            raise QueryVizError(f"[mysql] Query execution failed on {self.config['name']}: {str(e)}")
        finally:
            # Return connection to pool
            connection.close()
    
    def close(self):
        """Close connection pool"""
        if not self.maybe_connected:
            return False
        if not self.pool:
            raise QueryVizError(f"[mysql] No connection to close")
        self.pool = None
        return True

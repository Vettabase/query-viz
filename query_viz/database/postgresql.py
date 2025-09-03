"""
PostgreSQL database connection implementation
"""

import psycopg2
from psycopg2 import pool
from .base import DatabaseConnection, SUCCESS, FAIL
from ..exceptions import QueryVizError


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL database connection"""
    
    # Connector metadata
    info = DatabaseConnection.info.copy()
    info.update({
        "connector-name": "QV-PostgreSQL",
        "connector-url": "https://github.com/Vettabase/query-viz",
        "version": "0.1",
        "maturity": "gamma", 
        "license": "AGPLv3",
        "copyright": "2025, Vettabase Ltd",
        "authors": [{"name": "Vettabase Ltd", "url": "https://vettabase.com"}]
    })
    
    # Default configuration values for PostgreSQL connections
    defaults = {
        'host': 'localhost',
        'port': 5432,
        'user': None,
        'password': None,
        'database': 'postgres'
    }
    
    def __init__(self, config, db_timeout):
        super().__init__(config, db_timeout)
        super()._auto_validate(config)
        self.pool = None
    
    @classmethod
    def validate_config(cls, config):
        """
        Validate PostgreSQL-specific configuration
        
        Args:
            config (dict): Connection configuration to validate
            
        Raises:
            QueryVizError: If configuration is invalid
        """
        connection_name = config.get('name', None)

        # Validate all required fields for PostgreSQL
        required_fields = ['name', 'dbms', 'host', 'port', 'user', 'password']
        for field in required_fields:
            if field not in config:
                cls.validationError(connection_name, f"'{field}' is required")
        
        # PostgreSQL-specific validation
        port = config['port']
        if not isinstance(port, int) or port <= 0 or port > 65535:
            cls.validationError(connection_name, "'port' must be a valid port number (1-65535)")
    
    def connect(self):
        """Create connection pool"""
        try:
            # Use SimpleConnectionPool for single-threaded applications
            # (matching the pattern used by MariaDB/MySQL connectors)
            self.pool = psycopg2.pool.SimpleConnectionPool(
                1, 5,  # minconn, maxconn
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                connect_timeout=self.db_timeout
            )
            print(f"[postgresql] Created connection pool to {self.config['host']}:{self.config['port']}")
            self.status = SUCCESS
        except psycopg2.Error as e:
            self.status = FAIL
            raise QueryVizError(f"[postgresql] Failed to create connection pool for {self.config['host']}: {str(e)}")
    
    def execute_query(self, query):
        """Get connection from pool, execute query, return connection"""
        if not self.pool:
            raise QueryVizError("[postgresql] No connection")
        
        connection = self.pool.getconn()
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()
            cursor.close()
            return columns, results
        except psycopg2.Error as e:
            raise QueryVizError(f"[postgresql] Query execution failed on {self.config['name']}: {str(e)}")
        finally:
            # Return connection to pool
            self.pool.putconn(connection)
    
    def close(self):
        """Close connection pool"""
        if not self.pool:
            raise QueryVizError(f"[postgresql] No connection to close")
        self.pool.closeall()
        self.pool = None

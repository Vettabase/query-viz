"""
MariaDB database connection implementation
"""

import mariadb
from .base import DatabaseConnection, SUCCESS, FAIL
from ..exceptions import QueryVizError


class MariaDBConnection(DatabaseConnection):
    """MariaDB database connection, with connection pooling support"""
    
    def __init__(self, config, db_timeout):
        super().__init__(config, db_timeout)
        self.pool = None
        
    def connect(self):
        """Create connection pool"""
        try:
            self.pool = mariadb.ConnectionPool(
                pool_name=f"pool_{self.name}",
                pool_size=5,  # Adjustable
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                connect_timeout=self.db_timeout
            )
            print(f"[mariadb] Created connection pool to {self.host}:{self.port}")
            self.status = SUCCESS
        except mariadb.Error as e:
            self.status = FAIL
            raise QueryVizError(f"[mariadb] Failed to create connection pool for {self.host}: {e}")
    
    def execute_query(self, query):
        """Get connection from pool, execute query, return connection"""
        if not self.pool:
            self.connect()
        
        connection = self.pool.get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()
            cursor.close()
            return columns, results
        except mariadb.Error as e:
            raise QueryVizError(f"[mariadb] Query execution failed on {self.name}: {e}")
        finally:
            # Return connection to pool
            connection.close()
    
    def close(self):
        """Close connection pool"""
        if self.pool:
            raise QueryVizError(f"[mariadb] No connection to close")
        self.pool = None

"""
Base database connection class
"""

# Global constants for connection status
SUCCESS = "SUCCESS"
FAIL = "FAIL"


class DatabaseConnection:
    """Base class for database connections"""
    
    def __init__(self, config, db_timeout):
        self.name = config['name']
        self.dbms = config['dbms']
        self.host = config['host']
        self.port = config['port']
        self.user = config['user']
        self.password = config['password']
        self.status = None
        self.db_timeout = db_timeout
        
    def connect(self):
        """Establish database connection (abstract method)"""
        raise NotImplementedError("connect() is an abstract method")
    
    def execute_query(self, query):
        """Execute a query and return results (abstract method)"""
        raise NotImplementedError("execute_query() is an abstract method")
    
    def close(self):
        """Close database connection (abstract method)"""
        raise NotImplementedError("close() is an abstract method")

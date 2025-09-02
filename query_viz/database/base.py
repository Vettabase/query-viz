"""
Base database connection class
"""

from abc import ABC, abstractmethod
from ..exceptions import QueryVizError

# Global constants for connection status
SUCCESS = "SUCCESS"
FAIL = "FAIL"


class DatabaseConnection(ABC):
    """Abstract class for database connections"""
    
    info = {
        "connector-name": "",
        "connector-url": "https://github.com/Vettabase/query-viz",
        "version": "0.0.0",
        "maturity": "dev",
        "license": "",
        "copyright": "",
        "authors": []
    }
    
    # Default configuration values
    defaults = {}
    
    def __init__(self, config, db_timeout):
        self._set_defaults(config)
        self.config = config
        self.status = None
        self.db_timeout = db_timeout
    
    def _set_defaults(self, config):
        """
        Set default values for configuration keys that are missing
        
        Args:
            config (dict): Connection configuration to modify
            
        Raises:
            QueryVizError: If a required field (with None default) is missing
        """
        for key, default_value in self.defaults.items():
            if key not in config:
                if default_value is None:
                    self.validationError(connection_name, f"Configuration error: '{key}' is required")
                    raise QueryVizError(f"Connection '{connection_name}': '{key}' is required")
                else:
                    config[key] = default_value
    
    @classmethod
    def validate_config(cls, config):
        """
        Validate connection configuration for this connector type
        
        Args:
            config (dict): Connection configuration to validate
        
        Raises:
            NotImplementedError: Always, as this must be implemented by subclasses
        """
        raise NotImplementedError("validate_config() must be implemented by subclasses")
    
    @classmethod
    def validationError(cls, connection_name, message):
        """
        Raise a validation error with connection name prefix
        
        Args:
            connection_name (str): Name of the connection
            message (str): Error message
            
        Raises:
            QueryVizError: Always, with formatted message
        """
        if connection_name is not None and connection_name > '':
            raise QueryVizError(f"Connection '{connection_name}': {message}")
        else:
            raise QueryVizError(message)
    
    @abstractmethod
    def connect(self):
        """Establish database connection"""
        pass
    
    @abstractmethod
    def execute_query(self, query):
        """Execute a query and return results"""
        pass
    
    @abstractmethod
    def close(self):
        """Close database connection"""
        pass

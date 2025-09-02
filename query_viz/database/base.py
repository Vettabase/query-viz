"""
Base database connection class
"""

import re
import ipaddress

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
        connection_name = config.get('name', None)
        for key, default_value in self.defaults.items():
            if key not in config:
                if default_value is None:
                    self.validationError(connection_name, f"Configuration error: '{key}' is required")
                else:
                    config[key] = default_value
    
    @classmethod
    def _is_valid_port(cls, port):
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except (ValueError, TypeError):
            return False

    @classmethod
    def _is_valid_host(cls, host, allow_port=True):
        if not host:
            return False

        # Check if port is included
        if ':' in host:
            if not allow_port:
                return False

            # Handle IPv6 with port [::1]:8080
            if host.startswith('[') and ']:' in host:
                bracket_end = host.find(']:')
                host_part = host[1:bracket_end]
                port_part = host[bracket_end + 2:]
            else:
                # IPv4 or hostname with port
                parts = host.rsplit(':', 1)
                if len(parts) != 2:
                    return False
                host_part, port_part = parts
            
            # Validate port
            if not cls._is_valid_port(port_part):
                return False
        else:
            host_part = host

        # Try hostname first
        if cls._is_valid_hostname(host_part):
            return True
        
        # Try IPv4
        try:
            ipaddress.IPv4Address(host_part)
            return True
        except:
            pass
        
        # Try IPv6
        try:
            ipaddress.IPv6Address(host_part)
            return True
        except:
            pass
        
        return False
    
    @classmethod
    def _is_valid_hostname(cls, hostname):
        if not hostname or len(hostname) > 253:
            return False
       
        labels = hostname.split('.')
        for label in labels:
            if not label or len(label) > 63:
                return False
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label):
                return False
        return True
    
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

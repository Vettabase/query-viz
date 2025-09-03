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
    
    def _auto_validate(self, config):
        """
        Validate standard configuration properties that are present.
        Subclasses can call this method if they use standard properties.
        DatabaseConnection does not call this, to leave subclasses free
        to use non-standard configuration properties.
        Return an error if configuration is not valid.
        
        Args:
            config (dict): Connection configuration to validate
            
        Raises:
            QueryVizError: If validation fails
        """
        connection_name = config.get('name', None)
        
        # Validate port if present
        if 'port' in config:
            if not self._is_valid_port(config['port']):
                self.validationError(connection_name, f"Invalid port: {config['port']}")
        
        # Validate host if present
        if 'host' in config:
            is_valid, host_part, port_part = self._is_valid_host(config['host'], allow_port=True)
            
            if not is_valid:
                self.validationError(connection_name, f"Invalid host: {config['host']}")
            
            # If host contains a port and config.port is also present, host's port overwrites config.port
            if port_part is not None and 'port' in config:
                config['port'] = int(port_part)
    
    @classmethod
    def _is_valid_port(cls, port):
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except (ValueError, TypeError):
            return False

    @classmethod
    def _is_valid_host(cls, host, allow_port=True):
        """
        Validates host. host can be a hostname (even multi-part),
        an IPv4 or an IPv6. If allow_port is True, it can also contain
        a port.
        Return a triple with 3 elements:
        (bool is_valid, str host_part, str port_part)
        When not specified, port_part is None.
        When the host is not valid, host_part and port_part might be None
        even when specified.
        """
        if not host:
            return (False, None, None)
        host_part = port_part = None

        # Check if port is included
        if ':' in host:
            if not allow_port:
                return (False, host_part, port_part)
            
            # Handle IPv6 with port [::1]:8080
            if host.startswith('[') and ']:' in host:
                bracket_end = host.find(']:')
                host_part = host[1:bracket_end]
                port_part = host[bracket_end + 2:]
            else:
                # IPv4 or hostname with port
                parts = host.rsplit(':', 1)
                if len(parts) != 2:
                    return (False, host_part, port_part)
                host_part, port_part = parts
            
            # Validate port
            if not cls._is_valid_port(port_part):
                return (False, host_part, port_part)
        else:
            host_part = host

        # Try hostname first
        if cls._is_valid_hostname(host_part):
            return (True, host_part, port_part)
        
        # Try IPv4
        try:
            ipaddress.IPv4Address(host_part)
            return (True, host_part, port_part)
        except:
            pass
        
        # Try IPv6
        try:
            ipaddress.IPv6Address(host_part)
            return (True, host_part, port_part)
        except:
            pass
        
        return (False, host_part, port_part)
    
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

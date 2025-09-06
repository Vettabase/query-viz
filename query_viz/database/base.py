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
    # Indicates whether multi-host logic is supported by this connector
    supports_multiple_hosts = False
    # Only relevant is supports_multiple_hosts = True
    # Indicates if each host might contain a port part: "localhost:12345"
    supports_multiple_ports = False
    
    
    def __init__(self, config, db_timeout):
        self._set_defaults(config)
        self.config = config
        self.status = None
        self.db_timeout = db_timeout
        # When True, a connection is supposed to be open but it's not guaranteed.
        # When False, no connection is open or the Connector doesn't update this variable.
        self.maybe_connected = False
    
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
    def _make_list(cls, host_list):
        """
        Merge a list of host strings into a single comma-separated string.
        Different database drivers have different syntax for this,
        so some subclasses are expected to override this method.
        
        Args:
            host_list (list): List of host strings with ports included
            
        Returns:
            str: Comma-separated string of hosts
        """
        return ','.join(host_list)
    
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
            if self.supports_multiple_hosts:
                # Use multi-host validation
                default_port = config.get('port', 3306)  # Default port for validation
                try:
                    validated_hosts = self._validate_host_list(config['host'], default_port)
                    # Update config with validated hosts
                    config['host'] = validated_hosts
                except QueryVizError as e:
                    self.validationError(connection_name, f"Invalid host list: {e}")
            else:
                # Use single host validation (existing logic)
                is_valid, host_part, port_part = self._is_valid_host(config['host'], allow_port=True)
                
                if not is_valid:
                    self.validationError(connection_name, f"Invalid host: {config['host']}")
                
                # If host contains a port and config.port is also present, host's port overwrites config.port
                if port_part is not None and 'port' in config:
                    config['port'] = int(port_part)
    
    @classmethod
    def _validate_host_list(cls, hosts, default_port):
        """
        Validate a comma-separated list of hosts and add default ports where missing.
        
        Args:
            hosts (str): Comma-separated list of hosts (hostname, IPv4, or IPv6, optionally with port)
            default_port (int): Default port to use when not specified in host
            
        Returns:
            str: Comma-separated list of validated hosts with ports included
            
        Raises:
            QueryVizError: If any host is invalid or default_port is invalid
        """
        # Validate default port first
        if not cls._is_valid_port(default_port):
            raise QueryVizError(f"Invalid default port: {default_port}")
        
        if not hosts or not hosts.strip():
            raise QueryVizError("Host list cannot be empty")
        
        # Split hosts by comma and clean whitespace
        host_list = [host.strip() for host in hosts.split(',')]
        validated_hosts = []

        if cls.supports_multiple_ports:
            for host in host_list:
                if not host:
                    raise QueryVizError('Empty host found in the list')
                    
                is_valid, host_part, port_part = cls._is_valid_host(host, allow_port=True)
                if not is_valid:
                    raise QueryVizError(f"Invalid host: {host}")
                
                # Add default port if no port was specified
                if port_part is None:
                    validated_host = f"{host_part}:{default_port}"
                else:
                    validated_host = f"{host_part}:{port_part}"
                
                validated_hosts.append(validated_host)
        else:
            for host in host_list:
                if not host:
                    raise QueryVizError('Empty host found in the list')
                
                is_valid, host_part, port_part = cls._is_valid_host(host, allow_port=True)
                if not is_valid:
                    raise QueryVizError(f"Invalid host: {host}")
                
                if port_part is not None and int(port_part) != default_port:
                    raise QueryVizError(f"All hosts must use the same port: {host}")
                validated_hosts.append(host_part)
        
        if not validated_hosts:
            raise QueryVizError("No hosts found in list")
        
        return cls._make_list(validated_hosts)
    
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

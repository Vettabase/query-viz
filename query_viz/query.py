"""
Query configuration
"""


from .interval import Interval


QUERY_INTERVAL_SPECIAL_VALUES = ['once']


class QueryConfig:
    """Query configuration.
    The keyed singleton guarantees that only an instance can exist for each query.
    The unique key is name."""
    
    # Instance dictionary. The key is query name
    _instances = {}
    
    def __new__(cls, config, default_connection, global_interval):
        """
        Ensure only one QueryConfig instance per query name.
        """
        key = config['name']
        
        if key not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[key] = instance
            instance._initialized = False
        return cls._instances[key]
    
    def __init__(self, config, default_connection, global_interval):
        # Prevent re-initialization of existing instances
        if self._initialized:
            return
        
        self.name = config['name']
        self.query = config['query']
        self.connection_name = config.get('connection', default_connection)
        self.interval = config.get('interval', global_interval)
        self.description = config.get('description')
        self.color = config.get('color')
        self.time_type = config.get('time_type', 'timestamp')
        self.on_rotation_keep_datapoints = config['on_rotation_keep_datapoints']
        self.on_file_rotation_keep_history = config.get('on_file_rotation_keep_history')
        # For recurring queries, this will be set on first run
        self.start_time = None
        
        interval_parser = Interval(QUERY_INTERVAL_SPECIAL_VALUES)
        interval_parser.validate(self.interval)
        self.is_recurring = not interval_parser.is_special_value()
        interval_parser = None
        if self.time_type == 'elapsed_seconds' and not self.is_recurring:
            raise ValueError(f"Query '{self.name}': time_type 'elapsed_seconds' is only allowed for recurring queries")
        
        # Handle both column formats
        if 'columns' in config and config['columns'] is not None:
            # New format: multiple columns
            self.columns = config['columns'].copy()  # List of column names
        elif 'column' in config and config['column'] is not None:
            # Old format: single column (backward compatibility)
            self.columns = [config['column']]  # Convert to list
        else:
            # This should be caught by validation, but just in case
            raise ValueError("Either 'column' or 'columns' must be specified")
        
        # Legacy attribute for backward compatibility
        self.column = config.get('column')
        
        # If a 'time' exists, move it to the beginning of the list
        if 'time' in self.columns:
            self.columns.remove('time')
            self.columns.insert(0, 'time')
        
        self._initialized = True

    def get_metrics(self):
        """Get list of metric columns"""
        return [col for col in self.columns if col != 'time']
    
    def get_metrics_count(self):
        """Get number of metric columns"""
        return len(self.get_metrics())
    
    @classmethod
    def clear_all_instances(cls):
        """Remove all cached instances"""
        cls._instances.clear()
    
    @classmethod
    def clear_instance(cls, name):
        """Remove a cached instance"""
        del cls._instances[name]

"""
Query configuration
"""


from .exceptions import QueryVizError
from .interval import Interval
from .temporal_column import TemporalColumnRegistry


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
        
        # Validate the config before proceeding
        self._validate_config(config)
        
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
    
    def _validate_config(self, config):
        """Validate query configuration"""
        required_fields = ['name', 'query']
        for field in required_fields:
            if field not in config:
                raise QueryVizError(f"Query: '{field}' is required")

        # Validate time_type if specified
        if 'time_type' in config:
            if not TemporalColumnRegistry.validate(config['time_type']):
                raise QueryVizError(f"Query '{config['name']}': invalid time_type '{config['time_type']}'")
        
        # Validate column specification - column and columns are mutually exclusive
        has_column = 'column' in config and config['column'] is not None
        has_columns = 'columns' in config and config['columns'] is not None
        if has_column == has_columns:
            raise QueryVizError(f"Query '{config['name']}': 'column' and 'columns' are mutually exclusive, but one of them must be specified")

        # Recommended format: "columns"
        if has_columns:
            if not isinstance(config['columns'], list) or len(config['columns']) == 0:
                raise QueryVizError(f"Query '{config['name']}': 'columns' must be a non-empty list")
            has_metrics = False
            for col in config['columns']:
                if not isinstance(col, str) or not col.strip():
                    raise QueryVizError(f"Query '{config['name']}': all column names must be non-empty strings")
                if col != 'time':
                    has_metrics = True
            if not has_metrics:
                raise QueryVizError(f"Query '{config['name']}': at least one metric-column must be specified")

        # Legacy format: "column"
        if has_column:
            if not isinstance(config['column'], str) or not config['column'].strip():
                raise QueryVizError(f"Query '{config['name']}': 'column' must be a non-empty string")
            if config['column'] == 'time':
                raise QueryVizError(f"Query '{config['name']}': at least one metric-column must be specified")

            def get_metrics(self):
                """Get list of metric columns"""
                return [col for col in self.columns if col != 'time']
            
            def get_metrics_count(self):
                """Get number of metric columns"""
                return len(self.get_metrics())
        
        # Validate optional query.interval
            if 'interval' in config:
                # Handle special 'once' value, which means:
                # There is no interval, the query will run once
                Interval(QUERY_INTERVAL_SPECIAL_VALUES).setget(config['interval'], MIN_QUERY_INTERVAL)
    
    @classmethod
    def clear_all_instances(cls):
        """Remove all cached instances"""
        cls._instances.clear()
    
    @classmethod
    def clear_instance(cls, name):
        """Remove a cached instance"""
        del cls._instances[name]

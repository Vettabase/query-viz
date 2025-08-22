"""
Query configuration
"""


from .exceptions import QueryVizError
from .interval import Interval
from .temporal_column import TemporalColumnRegistry


# Minimum allowed value for on_rotation_keep_datapoints
MIN_ON_ROTATION_KEEP_DATAPOINTS = 60


class QueryConfig:
    """Query configuration.
    The keyed singleton guarantees that only an instance can exist for each query.
    The unique key is name."""
    
    # Instance dictionary. The key is query name
    _instances = {}

    # Global values serve as defaults for query-level values
    defaults = {}
    
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
        
        self.defaults = {}
        
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
        
        interval_parser = Interval('query_interval')
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
        
        # Now that needed attributes are set, validate the config
        self._validate_config(config)
        
        self._initialized = True
    
    @classmethod
    def set_global_interval(cls, setting_name, setting_value):
        """Validate a global interval-type setting and remember it.
        It might be used later as a default.
        Defaults are shared between all instances."""
        interval_parser = Interval(setting_name)
        interval_parser.validate(setting_value)
        cls.defaults[setting_name] = setting_value
        return setting_value
    
    def _set_local_interval(self, config, setting_name):
        """Validate a local (query-level) interval-type setting and remember it.
        If not set, use the corresponding default.
        If the setting is query_interval, set is_recurring.
        Defaults are shared between all instances."""

        # global values are mandatory, no matter if they're used
        if setting_name not in self.defaults or self.defaults[setting_name] is None:
            raise QueryVizError(f"Missing global value: {setting_name}")
        # the setting must be in the configuration object
        if setting_name not in config:
            raise QueryVizError(f"Missing key in config: {setting_name}")

        setting_value = config[setting_name]
        if setting_value is None:
            setting_value = self.defaults[setting_name]
        interval_parser = Interval(setting_name)
        interval_parser.validate(setting_value)
        # special case must be handled here
        # FIXME: After renaming the setting to query_interval, we must
        # remove every reference to the generic name "interval"
        if setting_name == 'interval' or setting_name == 'query_interval':
            self.is_recurring = not interval_parser.is_special_value()
        setattr(self, setting_name, setting_value)
    
    def _error_if_local_is_set(self, config, setting_name, reason):
        """Raise an error if a local (query-level) setting is set,
        but it's not allowed here. The error message contains the reason.
        The global setting is not checked."""
        if setting_name in config:
            raise ValueError(f"Query '{self.name}': setting not allowed: {setting_name}. Reason: {reason}.")
    
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
        
        # Validate optional query.interval
        if 'interval' in config:
            # Handle special 'once' value, which means:
            # There is no interval, the query will run once
            Interval('query_interval').setget(config['interval'])
        
        # Validate on_rotation_keep_datapoints
        if 'on_rotation_keep_datapoints' in config:
            query_keep_datapoints = config['on_rotation_keep_datapoints']
            if not isinstance(query_keep_datapoints, int) or query_keep_datapoints < MIN_ON_ROTATION_KEEP_DATAPOINTS:
                raise QueryVizError(f"Query '{config['name']}': 'on_rotation_keep_datapoints' must be a positive integer. Minimum value: {MIN_ON_ROTATION_KEEP_DATAPOINTS}")
        
        # Validate on_file_rotation_keep_history
        if 'on_file_rotation_keep_history' in config:
            # Check that it's only specified for timestamp queries
            time_type = self.time_type
            if time_type != 'timestamp':
                self._error_if_local_is_set(config, 'on_file_rotation_keep_history',
                    f"'on_file_rotation_keep_history' can only be specified for queries with time_type='timestamp'. Current value: {time_type}")
            else:
                try:
                    self.on_file_rotation_keep_history = Interval('on_file_rotation_keep_history').setget(config['on_file_rotation_keep_history'])
                except QueryVizError as e:
                    raise QueryVizError(f"Query '{config['name']}': invalid 'on_file_rotation_keep_history' format: {e}")
    
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

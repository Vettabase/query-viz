"""
Query configuration
"""


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
        self.column = config.get('column') # OBSOLETE
        self.interval = config.get('interval', global_interval)
        self.description = config.get('description')
        # FIXME: to implement multi-metric queries, we'll need to move
        #        this information into the columns list
        self.color = config.get('color')

        if self.column:
            self.columns = ['time', self.column]
        else:
            self.columns = ['time', 'value']
        
        self._initialized = True
    
    @classmethod
    def clear_all_instances(cls):
        """Remove all cached instances"""
        cls._instances.clear()
    
    @classmethod
    def clear_instance(cls, name):
        """Remove a cached instance"""
        del cls._instances[name]

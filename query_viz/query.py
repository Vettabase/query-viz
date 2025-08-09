"""
Query configuration class
"""


class QueryConfig:
    """Represents a query configuration"""
    
    def __init__(self, config, default_connection, global_interval):
        self.name = config['name']
        self.query = config['query']
        self.connection_name = config.get('connection', default_connection)
        self.column = config.get('column') # OBSOLETE
        self.interval = config.get('interval', global_interval)
        self.description = config.get('description')
        self.color = config.get('color')

        if self.column:
            self.columns = ['time', self.column]
        else:
            self.columns = ['time', 'value']

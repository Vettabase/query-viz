"""
Main QueryViz application class
"""

import sys
import time
import yaml
import threading
import signal
import re
import os
from collections import defaultdict, deque

from .database import DatabaseConnection, MariaDBConnection, FAIL
from .query import QueryConfig
from .chart import ChartGenerator
from .data_file import DataFile
from .data_file_set import DataFileSet
from .exceptions import QueryVizError


class QueryViz:
    """Main query-viz application"""
    
    def __init__(self, config_file='config.yaml'):
        self.config_file = config_file
        self.config = None
        self.connections = {}
        self.queries = []
        # fast loopup of a single query object
        self.queries_by_name = {}
        # query list per chart
        self.chart_queries = {}
        # chart generators per chart
        self.chart_generators = {}
        # store max 1000 data points
        self.data = defaultdict(lambda: deque(maxlen=1000))
        # store max 1000 timestamps
        self.timestamps = deque(maxlen=1000)
        # if True, we'll cleanly exit the execution loop
        self.running = False
        self.threads = []
        self.data_files = {}
        # this is a basic, incomplete protection
        # but it's enough, because in practice no file can be written by multiple threads
        self.data_lock = threading.Lock()
        # TODO: output_dir should be created if it doesn't exist
        self.output_dir = '/app/output'
    
    def normalise_filename(self, basename, extension):
        """Normalise a filename by removing special characters and standardising format"""
        # Remove special characters (keep only alphanumeric, spaces, underscores, and hyphens)
        normalised = re.sub(r'[^a-zA-Z0-9\s_-]', '', basename)
        # Convert spaces and underscores to dashes
        normalised = re.sub(r'[\s_]+', '-', normalised)
        # Collapse consecutive dashes into one dash
        normalised = re.sub(r'-+', '-', normalised)
        # Remove leading/trailing dashes
        normalised = normalised.strip('-')
        # Make lowercase
        normalised = normalised.lower()
        # Add extension
        return f"{normalised}.{extension}"
    
    def _parse_interval(self, interval_str):
        """Parse interval string to seconds"""
        if isinstance(interval_str, (int, float)):
            return float(interval_str)
        
        # ignore all space-like characters
        interval_str = str(interval_str).translate(str.maketrans('', '', ' \t\n\r\f\v'))
        
        # Extract numeric part and unit
        if interval_str[-1].isalpha():
            unit = interval_str[-1]
            value = float(interval_str[:-1])
        else:
            unit = 's'  # default to seconds
            value = float(interval_str)
        
        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        elif unit == 'd':
            return value * 86400
        elif unit == 'w':
            return value * 604800
        else:
            raise QueryVizError(f"Invalid interval format: {interval_str}")
    
    def exit(self, code=0):
        """Exit with code 0 if running in Docker, otherwise use specified code"""
        if os.environ.get('IN_DOCKER') == '1':
            sys.exit(0)
        else:
            sys.exit(code)
        
    def clean_shutdown(self, signum = None, frame = None):
        """Handle SIGINT and SIGTERM for clean shutdown"""
        if signum is not None:
            print(f"\nReceived signal {signum}")
        print(f"\nShutting down...")
        self.running = False
        DataFileSet.close_all()
        for conn in self.connections.values():
            conn.close()
        self.exit(0)
        
    def load_config(self):
        """Load and validate configuration"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            raise QueryVizError(f"Configuration file not found: {self.config_file}")
        except yaml.YAMLError as e:
            raise QueryVizError(f"Invalid YAML in configuration file: {e}")
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration structure and required fields"""
        if not isinstance(self.config, dict):
            raise QueryVizError("Configuration must be a dictionary")
        
        # Validate connections
        if 'connections' not in self.config:
            raise QueryVizError("'connections' section is required")
        
        connections = self.config['connections']
        if not isinstance(connections, list) or len(connections) == 0:
            raise QueryVizError("At least one connection must be specified")
        
        for i, conn in enumerate(connections):
            required_fields = ['name', 'dbms', 'host', 'port', 'user', 'password']
            for field in required_fields:
                if field not in conn:
                    raise QueryVizError(f"Connection {i}: '{field}' is required")
        
        # Validate queries
        if 'queries' not in self.config:
            raise QueryVizError("'queries' section is required")
        
        queries = self.config['queries']
        if not isinstance(queries, list) or len(queries) == 0:
            raise QueryVizError("At least one query must be specified")
        
        query_names = set()
        for i, query in enumerate(queries):
            required_fields = ['name', 'query']
            for field in required_fields:
                if field not in query:
                    raise QueryVizError(f"Query {i}: '{field}' is required")
            
            # Check for duplicate query names
            if query['name'] in query_names:
                raise QueryVizError(f"Query {i}: duplicate query name '{query['name']}'")
            query_names.add(query['name'])
        
        unused_queries = list(query_names)
        
        # Validate charts configuration
        if 'charts' not in self.config:
            raise QueryVizError("'charts' section is required")
        
        charts = self.config['charts']
        if not isinstance(charts, list) or len(charts) == 0:
            raise QueryVizError("The 'charts' list cannot be empty")
        
        for i, chart in enumerate(charts):
            required_chart_fields = ['xlabel', 'ylabel', 'terminal', 
                                   'grid', 'key_position', 'line_width', 'point_type']
            for field in required_chart_fields:
                if field not in chart:
                    raise QueryVizError(f"Chart {i}: '{field}' is required")
            
            # Validate per-chart queries
            if 'queries' not in chart:
                raise QueryVizError(f"Chart {i}: 'queries' field is required")
            
            chart_queries = chart['queries']
            if not isinstance(chart_queries, list):
                raise QueryVizError(f"Chart {i}: 'queries' must be a list")
            
            # Warning if the query list is empty
            if not chart_queries:
                print(f"Warning: Chart {i} has an empty query list")

            # Validate that all referenced queries exist and mark them as used
            for query_name in chart_queries:
                if query_name not in query_names:
                    raise QueryVizError(f"Chart {i}: query '{query_name}' not found")
                if query_name in unused_queries:
                    unused_queries.remove(query_name)
            
            # Set default values where necessary
            if 'type' not in chart:
                chart['type'] = 'line_chart'
            if 'title' not in chart:
                chart['title'] = f"Chart #{i}"
            
            # Set default output_file if not specified or empty
            if 'output_file' not in chart or not chart['output_file']:
                chart['output_file'] = self.normalise_filename(chart['title'], 'png')
        
        # Warning on unused queries
        if unused_queries:
            print("Warning: Unused queries found:")
            for query_name in unused_queries:
                print(f"  - {query_name}")
        unused_queries = None
        
        # Validate global interval
        if 'interval' not in self.config:
            raise QueryVizError("Global 'interval' is required")
        
        # Validate failed connections interval
        if 'failed_connections_interval' not in self.config:
            raise QueryVizError("'failed_connections_interval' is required")
        
        # Validate initial grace period
        if 'initial_grace_period' not in self.config:
            raise QueryVizError("'initial_grace_period' is required")
        
        # Validate grace period retry interval
        if 'grace_period_retry_interval' not in self.config:
            raise QueryVizError("'grace_period_retry_interval' is required")
        
        # Validate database connection timeout
        if 'db_connection_timeout_seconds' not in self.config:
            raise QueryVizError("'db_connection_timeout_seconds' is required")
        
        timeout = self.config['db_connection_timeout_seconds']
        if not isinstance(timeout, int) or timeout <= 0:
            raise QueryVizError("'db_connection_timeout_seconds' must be a positive integer")
        
        # Intervals specified in the "10m" format can now be parsed
        self.config['interval'] = self._parse_interval(self.config['interval'])
        self.config['failed_connections_interval'] = self._parse_interval(self.config['failed_connections_interval'])
        self.config['initial_grace_period'] = self._parse_interval(self.config['initial_grace_period'])
        self.config['grace_period_retry_interval'] = self._parse_interval(self.config['grace_period_retry_interval'])

    def setup_connections(self):
        """Setup database connections"""
        db_timeout = self.config['db_connection_timeout_seconds']
        for conn_config in self.config['connections']:
            if conn_config['dbms'] == 'mariadb':
                conn = MariaDBConnection(conn_config, db_timeout)
            else:
                raise QueryVizError(f"Unsupported DBMS: {conn_config['dbms']}")
            self.connections[conn_config['name']] = conn
        
        # Set default connection
        self.default_connection = self.config['connections'][0]['name']
    
    def test_connections(self):
        """Test all database connections before starting main loop"""
        print("Testing connections...")
        
        grace_period_retry_interval = self.config['grace_period_retry_interval']
        initial_grace_period = self.config['initial_grace_period']
        
        start_time = time.time()
        
        while True:
            failed_connections = 0
            total_connections = len(self.connections)
            
            for conn_name, connection in self.connections.items():
                try:
                    print(f"Connection attempt to '{connection.host}'... ", end="")
                    connection.connect()
                    print("success")
                    # Keep connection open for reuse
                except QueryVizError as e:
                    failed_connections += 1
                    # Check if grace period has expired to determine retry message
                    elapsed_time = time.time() - start_time
                    if elapsed_time >= initial_grace_period:
                        print("fail. WON'T RETRY")
                    else:
                        print("fail. Will retry")
                    print(f"    Reason: {e}")
            
            if failed_connections > 0:
                print(f"{failed_connections}/{total_connections} connections are not working")
            
            if failed_connections == 0:
                print("Execution will continue")
                return True
            
            # Check if grace period has expired
            elapsed_time = time.time() - start_time
            if elapsed_time >= initial_grace_period:
                print("Aborting")
                # Close any connections that might have been opened
                for conn in self.connections.values():
                    conn.close()
                return False
            
            # Wait before retrying
            time.sleep(grace_period_retry_interval)
    
    def retry_failed_connections(self):
        """Periodically retry failed connections"""
        failed_connections_interval = self.config['failed_connections_interval']
        
        while self.running:
            time.sleep(failed_connections_interval)
            
            if not self.running:
                break
                
            # Check for failed connections and try to reconnect
            for conn_name, connection in self.connections.items():
                if connection.status == FAIL:
                    try:
                        print(f"Retrying connection '{conn_name}'...")
                        connection.connect()
                        print(f"Connection '{conn_name}': Reconnected successfully")
                    except QueryVizError:
                        # Connection still failed, status already set to FAIL in connect()
                        pass
    
    def setup_queries(self):
        """Setup query configurations"""
        global_interval = self.config['interval']
        
        for i, query_config in enumerate(self.config['queries']):
            query = QueryConfig(query_config, self.default_connection, global_interval)
            
            # Parse query interval
            query.interval = self._parse_interval(query.interval)
            
            # Validate connection exists
            if query.connection_name not in self.connections:
                raise QueryVizError(f"Query '{query.name}': connection '{query.connection_name}' not found")
            
            self.queries.append(query)
            
            # Initialize DataFile for this query
            data_file = DataFile(query, self.output_dir)
            self.data_files[query.name] = data_file
        
        # For fast access, build a query objects lookup
        # and a pre-computed chart-to-queries map
        self.queries_by_name = {q.name: q for q in self.queries}
        self.chart_queries = {}
        self.chart_generators = {}
        
        for i, chart in enumerate(self.config['charts']):
            # Pre-compute query objects for this chart
            self.chart_queries[i] = [self.queries_by_name[name] for name in chart['queries']]
            
            # Instantiate ChartGenerator for each chart
            chart_type = chart['type']
            self.chart_generators[i] = ChartGenerator(
                chart, 
                self.output_dir, 
                chart_type
            )
    
    def execute_query_thread(self, query_config):
        """Execute a single query in a loop"""
        connection = self.connections[query_config.connection_name]
        data_file = DataFileSet.get(query_config.name)
        
        while self.running:
            try:
                # Skip query if connection has failed
                if connection.status == FAIL:
                    time.sleep(query_config.interval)
                    continue
                
                start_time = time.time()
                columns, results = connection.execute_query(query_config.query)
                
                if not results:
                    print(f"Warning: Query '{query_config.name}' returned no results")
                    time.sleep(query_config.interval)
                    continue
                
                # Extract metric value
                if query_config.column:
                    if query_config.column not in columns:
                        raise QueryVizError(f"Column '{query_config.column}' not found in query results for '{query_config.name}'. Available columns: {columns}")
                    
                    col_index = columns.index(query_config.column)
                    value = results[0][col_index]
                else:
                    if len(columns) > 1:
                        raise QueryVizError(f"Query '{query_config.name}' returns multiple columns but no 'column' attribute specified")
                    value = results[0][0]
                
                # Convert to numeric
                try:
                    numeric_value = float(value)
                except (ValueError, TypeError):
                    raise QueryVizError(f"Value '{value}' from query '{query_config.name}' is not numeric")
                
                # Store data point and write to file incrementally
                current_time = time.time()
                
                with self.data_lock:
                    self.data[query_config.name].append(numeric_value)
                    
                    # Update timestamps (shared across all queries)
                    if len(self.timestamps) == 0 or current_time > self.timestamps[-1]:
                        self.timestamps.append(current_time)
                    
                    # Write data point to file
                    data_file.write_data_point(numeric_value)
                
                print(f"Query '{query_config.name}': {numeric_value}")
                
                # Sleep for remaining interval time
                elapsed = time.time() - start_time
                sleep_time = max(0, query_config.interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"Error executing query '{query_config.name}': {e}")
                time.sleep(query_config.interval)
    
    def create_chart_index(self, chart_filenames):
        """Write the chart index file with all generated chart filenames"""
        index_file = os.path.join(self.output_dir, '_CHART_INDEX')
        
        try:
            with open(index_file, 'w') as f:
                for filename in chart_filenames:
                    f.write(f"{filename}\n")
            print(f"Chart index written: {index_file}")
        except Exception as e:
            print(f"Error writing chart index: {e}")

    def generate_plots(self):
        """Generate all plots using chart generators"""
        chart_filenames = []
        
        for chart_index, chart_generator in self.chart_generators.items():
            chart_queries = self.chart_queries[chart_index]
            
            if chart_generator.generate_chart(chart_queries):
                # Get the output filename from the chart config
                chart_config = self.config['charts'][chart_index]
                chart_filenames.append(chart_config['output_file'])
        
        # Write _CHART_INDEX
        self.create_chart_index(chart_filenames)
    
    def run(self):
        """Run the main application"""
        print("Starting query-viz...")
        
        # Register signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self.clean_shutdown)
        signal.signal(signal.SIGTERM, self.clean_shutdown)
        
        try:
            self.load_config()
            self.setup_connections()
            
            # Test connections before proceeding
            if not self.test_connections():
                self.exit(1)
            
            self.setup_queries()
            
            # Create DataFileSet entries for all queries
            for query in self.queries:
                DataFileSet.set(query, self.output_dir)
            
            # Open data files for writing
            DataFileSet.open_all()
            
            # Start query threads
            self.running = True
            for query in self.queries:
                thread = threading.Thread(target=self.execute_query_thread, args=(query,))
                thread.daemon = True
                thread.start()
                self.threads.append(thread)
            
            # Start failed connection retry thread
            retry_thread = threading.Thread(target=self.retry_failed_connections)
            retry_thread.daemon = True
            retry_thread.start()
            self.threads.append(retry_thread)
            
            print(f"Started {len(self.queries)} query threads")
            print("Started connection retry thread")
            
            # Main loop - generate plots periodically
            plot_interval = 30  # Generate plot every 30 seconds
            last_plot_time = 0
            
            while self.running:
                current_time = time.time()
                
                if current_time - last_plot_time >= plot_interval and self.timestamps:
                    self.generate_plots()
                    last_plot_time = current_time
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error: {e}")
            self.exit(1)
        finally:
            self.running = False
            DataFileSet.close_all()
            for conn in self.connections.values():
                conn.close()
        
        self.exit(0)

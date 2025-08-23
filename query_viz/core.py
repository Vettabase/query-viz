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
from .interval import Interval


# Minimum allowed value for on_rotation_keep_datapoints
MIN_ON_ROTATION_KEEP_DATAPOINTS = 60


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
        # Only keep alphanumeric, spaces, underscores, hyphens
        normalised = re.sub(r'[^a-zA-Z0-9\s_-]', '', basename)
        # Convert spaces and underscores to dashes
        normalised = re.sub(r'[\s_]+', '-', normalised)
        # Collapse consecutive dashes into one dash
        normalised = re.sub(r'-+', '-', normalised)
        normalised = normalised.strip('-')
        normalised = normalised.lower()
        if extension:
            return f"{normalised}.{extension}"
        return normalised
    
    def exit(self, code=0):
        """Exit with code 0 if running in Docker, otherwise use specified code"""
        if os.environ.get('IN_DOCKER') == '1':
            code = 0
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
            required_chart_fields = ['ylabel', 'terminal', 
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
            
            # FIXME: At this point, time_type can be None (if not specified).
            #        We don't want more hacks, so let's disable this validation for now.
            #        We need to refactor the code to handle time_type defaults cleanly.
            # Validate that all queries in a chart have the same time_type
            #if chart_queries:
            #    last_time_type = None
            #    for query_name in chart_queries:
            #        # Get current query's config
            #        query_config = next(q for q in queries if q['name'] == query_name)
            #        time_type = query_config.get('time_type', 'timestamp')
            #        
            #        if last_time_type is None:
            #            last_time_type = time_type
            #        elif last_time_type != time_type:
            #            raise QueryVizError(f"Chart {i}: all queries must have the same time_type. Found '{last_time_type}' and '{time_type}'")
            
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
        
        # Parse and validate global interval
        self.config['interval'] = Interval('query_interval').setget(self.config['interval'])
        
        # Intervals specified in the "10m" format can now be parsed
        interval_settings = [
              'failed_connections_interval'
            , 'initial_grace_period'
            , 'grace_period_retry_interval'
        ]
        for setting in interval_settings:
            self.config[setting] = Interval(setting).setget(self.config[setting])
        interval_settings = None
    
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
        QueryConfig.set_global_int('on_rotation_keep_datapoints', self.config['on_rotation_keep_datapoints'], min=MIN_ON_ROTATION_KEEP_DATAPOINTS)
        QueryConfig.set_global_interval('on_file_rotation_keep_history', self.config['on_file_rotation_keep_history'])
        QueryConfig.set_global_interval('interval', self.config['interval'])
        
        for i, query_config in enumerate(self.config['queries']):
            query = QueryConfig(query_config, self.default_connection)
            
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
    
    def process_query_results(self, query_config, columns, results, data_file):
        """
        Process query results and write data points to file.
        
        Args:
            query_config: QueryConfig object
            columns: List of column names from query results
            results: List of result rows from query execution
            data_file: DataFile object for writing
            
        Returns:
            int: Number of rows processed
            
        Raises:
            QueryVizError: If column mapping fails or data writing fails
        """
        if not results:
            print(f"Warning: Query '{query_config.name}' returned no results")
            return 0
        
        rows_processed = 0
        
        for row in results:
            # Extract values for all configured columns
            column_values = []
            for col_name in query_config.columns:
                if col_name not in columns:
                    raise QueryVizError(f"Column '{col_name}' not found in query results for '{query_config.name}'. Available columns: {columns}")
                
                col_index = columns.index(col_name)
                value = row[col_index]
                column_values.append(value)
            
            # Write data point to file
            data_file.write_data_point(column_values)
            rows_processed += 1
        
        return rows_processed
    
    def execute_once_queries_thread(self):
        """Execute all 'once' queries that haven't been run yet"""
        once_queries = [q for q in self.queries if q.interval == 'once']
        
        for query_config in once_queries:
            try:
                # Skip query if connection has failed
                connection = self.connections[query_config.connection_name]
                if connection.status == FAIL:
                    print(f"Skipping 'once' query '{query_config.name}': connection failed")
                    continue
                
                # Check if data file already exists
                data_file = DataFileSet.get(query_config.name)
                if data_file.exists():
                    print(f"Skipping 'once' query '{query_config.name}': already executed")
                    continue
                
                # Execute the query
                print(f"Executing 'once' query '{query_config.name}'...")
                columns, results = connection.execute_query(query_config.query)
                
                try:
                    data_file.open()
                    try:
                        self.process_query_results(query_config, columns, results, data_file)
                    except Exception as e:
                        print(f"Error processing results for 'once' query '{query_config.name}': {e}")
                    finally:
                        try:
                            data_file.close()
                        except:
                            pass
                except Exception as e:
                    print(f"Error opening data file for 'once' query '{query_config.name}': {e}")
                    
            except Exception as e:
                print(f"Error executing 'once' query '{query_config.name}': {e}")
        
        print("Finished executing 'once' queries")
    
    def execute_query_thread(self, query_config):
        """Execute a single query in a loop"""
        connection = self.connections[query_config.connection_name]
        data_file = DataFileSet.get(query_config.name)
        
        if (
                query_config.time_type == 'elapsed_seconds' and
                query_config.start_time is None
            ):
            query_config.start_time = int(time.time())
        
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
                
                # Extract values for all configured columns
                column_values = []
                for col_name in query_config.columns:
                    if col_name not in columns:
                        raise QueryVizError(f"Column '{col_name}' not found in query results for '{query_config.name}'. Available columns: {columns}")
                    
                    col_index = columns.index(col_name)
                    value = results[0][col_index]
                    column_values.append(value)
                
                # Store data point and write to file incrementally
                current_time = time.time()
                
                with self.data_lock:
                    # "time" is not a metric
                    if query_config.columns[0] == 'time':
                        metric_value = column_values[1]
                    else:
                        metric_value = column_values[0]
                    
                    # Convert to numeric and store
                    try:
                        numeric_value = float(metric_value)
                        self.data[query_config.name].append(numeric_value)
                    except (ValueError, TypeError):
                        raise QueryVizError(f"Metric value '{metric_value}' from query '{query_config.name}' is not numeric")
                    
                    # Update timestamps (shared across all queries)
                    if len(self.timestamps) == 0 or current_time > self.timestamps[-1]:
                        self.timestamps.append(current_time)
                    
                    # Write data point to file
                    data_file.write_data_point(column_values)
                
                print(f"Query '{query_config.name}': {column_values}")
                
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
            
            if chart_generator.generate_all_charts(chart_queries):
                # Get the output filename from the chart config
                chart_config = self.config['charts'][chart_index]
                chart_filenames.append(chart_config['output_file'])
        
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
            
            if not self.test_connections():
                self.exit(1)
            
            self.setup_queries()
            
            for query in self.queries:
                DataFileSet.set(query, self.output_dir)
            
            # Open data files for writing
            DataFileSet.open_recurring_queries()
            
            self.running = True
            
            # Start once queries thread (if any exist)
            once_queries = [q for q in self.queries if q.interval == 'once']
            if once_queries:
                once_thread = threading.Thread(target=self.execute_once_queries_thread)
                once_thread.daemon = False  # Non-daemon thread
                once_thread.start()
                self.threads.append(once_thread)
                print(f"Started 'once' queries thread for {len(once_queries)} queries")
            else:
                print("Not starting the 'once' thread")
            
            # Start query threads
            started_threads = 0
            for query in self.queries:
                if query.interval != 'once':
                    thread = threading.Thread(target=self.execute_query_thread, args=(query,))
                    thread.daemon = True
                    thread.start()
                    self.threads.append(thread)
                    started_threads = started_threads + 1
            print(f"Started {started_threads} query threads")
            
            # Start failed connection retry thread
            retry_thread = threading.Thread(target=self.retry_failed_connections)
            retry_thread.daemon = True
            retry_thread.start()
            self.threads.append(retry_thread)
            print("Started connection retry thread")
            
            # Main loop - generate plots periodically
            plot_interval = 30
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

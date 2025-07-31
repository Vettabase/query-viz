#!/usr/bin/env python3
"""
query-viz: A tool to generate real-time charts using GNU Plot
Copyright: Vettabase 2025
License: AGPLv3
"""

import sys
import time
import yaml
import mariadb
import subprocess
import threading
import signal
from datetime import datetime
from collections import defaultdict, deque
import re
import os

# Global constants for connection status
SUCCESS = "SUCCESS"
FAIL = "FAIL"

class QueryVizError(Exception):
    """Custom exception for query-viz errors"""
    pass

class DatabaseConnection:
    """Manages database connections"""
    
    def __init__(self, config):
        self.name = config['name']
        self.dbms = config['dbms']
        self.host = config['host']
        self.port = config['port']
        self.user = config['user']
        self.password = config['password']
        self.connection = None
        self.status = None
        
    def connect(self):
        """Establish database connection"""
        if self.dbms == 'mariadb':
            try:
                self.connection = mariadb.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password
                )
                print(f"Connected to {self.dbms} at {self.host}:{self.port}")
                self.status = SUCCESS
            except mariadb.Error as e:
                self.status = FAIL
                raise QueryVizError(f"Failed to connect to {self.host}: {e}")
        else:
            self.status = FAIL
            raise QueryVizError(f"Unsupported DBMS: {self.dbms}")
    
    def execute_query(self, query):
        """Execute a query and return results"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            results = cursor.fetchall()
            cursor.close()
            return columns, results
        except mariadb.Error as e:
            raise QueryVizError(f"Query execution failed on {self.name}: {e}")
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

class QueryConfig:
    """Represents a query configuration"""
    
    def __init__(self, config, default_connection, global_interval):
        self.name = config['name']
        self.query = config['query']
        self.connection_name = config.get('connection', default_connection)
        self.column = config.get('column')
        self.interval = config.get('interval', global_interval)
        self.description = config.get('description')
        self.color = config.get('color')

class QueryViz:
    """Main query-viz application"""
    
    def __init__(self, config_file='config.yaml'):
        self.config_file = config_file
        self.config = None
        self.connections = {}
        self.queries = []
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
    
    def _parse_interval(self, interval_str):
        """Parse interval string to seconds"""
        if isinstance(interval_str, (int, float)):
            return float(interval_str)
        
        pattern = r'^(\d+(?:\.\d+)?)\s*([smh]?)$'
        match = re.match(pattern, str(interval_str))
        if not match:
            raise QueryVizError(f"Invalid interval format: {interval_str}")
        
        value, unit = match.groups()
        value = float(value)
        
        if unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        else:  # 's' or no unit
            return value
    
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
        self.close_data_files()
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
        
        for i, query in enumerate(queries):
            required_fields = ['name', 'query']
            for field in required_fields:
                if field not in query:
                    raise QueryVizError(f"Query {i}: '{field}' is required")
        
        # Validate plot configuration
        if 'plot' not in self.config:
            raise QueryVizError("'plot' section is required")
        
        plot = self.config['plot']
        required_plot_fields = ['title', 'xlabel', 'ylabel', 'output_file', 'terminal', 
                               'grid', 'key_position', 'line_width', 'point_type']
        for field in required_plot_fields:
            if field not in plot:
                raise QueryVizError(f"Plot configuration: '{field}' is required")
        
        # Validate global interval
        if 'interval' not in self.config:
            raise QueryVizError("Global 'interval' is required")
        
        # Validate failed connections interval
        if 'failed_connections_interval' not in self.config:
            raise QueryVizError("'failed_connections_interval' is required")

        # Validate initial grace period
        if 'initial_grace_period' not in self.config:
            raise QueryVizError("'initial_grace_period' is required")
        
        # Intervals specified in the "10m" format can now be parsed
        self.config['interval'] = self._parse_interval(self.config['interval'])
        self.config['failed_connections_interval'] = self._parse_interval(self.config['failed_connections_interval'])
        self.config['initial_grace_period'] = self._parse_interval(self.config['initial_grace_period'])
    
    def setup_connections(self):
        """Setup database connections"""
        for conn_config in self.config['connections']:
            conn = DatabaseConnection(conn_config)
            self.connections[conn_config['name']] = conn
        
        # Set default connection
        self.default_connection = self.config['connections'][0]['name']
    
    def test_connections(self):
        """Test all database connections before starting main loop"""
        print("Testing connections...")
        
        failed_connections_interval = self.config['failed_connections_interval']
        initial_grace_period = self.config['initial_grace_period']
        
        start_time = time.time()
        
        while True:
            failed_connections = 0
            total_connections = len(self.connections)
            
            for conn_name, connection in self.connections.items():
                try:
                    connection.connect()
                    print(f"Connection '{conn_name}': Success")
                    # Keep connection open for reuse
                except QueryVizError as e:
                    print(f"Connection '{conn_name}': Fail")
                    failed_connections += 1
            
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
            time.sleep(failed_connections_interval)
    
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
            
            # Initialize data file for this query
            # Normalize query name for filename
            normalized_name = re.sub(r'[^a-zA-Z0-9\s_-]', '', query.name).lower().replace(' ', '-').replace('_', '-')
            data_file = os.path.join(self.output_dir, f"{normalized_name}.dat")
            self.data_files[query.name] = {
                'filename': data_file,
                'handle': None,
                'point_count': 0
            }
    
    def open_data_files(self):
        """Open data files for incremental writing"""
        for query_name, file_info in self.data_files.items():
            # Remove existing file and start fresh
            if os.path.exists(file_info['filename']):
                os.remove(file_info['filename'])
            file_info['handle'] = open(file_info['filename'], 'w')
            file_info['point_count'] = 0
    
    def close_data_files(self):
        """Close all data files"""
        for file_info in self.data_files.values():
            if file_info['handle']:
                file_info['handle'].close()
                file_info['handle'] = None
    
    def execute_query_thread(self, query_config):
        """Execute a single query in a loop"""
        connection = self.connections[query_config.connection_name]
        
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
                        raise QueryVizError(f"Column '{query_config.column}' not found in query results for '{query_config.name}'")
                    
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
                    
                    # Write data point to file incrementally
                    file_info = self.data_files[query_config.name]
                    if file_info['handle']:
                        relative_time = file_info['point_count'] * query_config.interval
                        file_info['handle'].write(f"{relative_time} {numeric_value}\n")
                        file_info['handle'].flush()  # Ensure data is written immediately
                        file_info['point_count'] += 1
                        
                        # Handle rolling window: if we exceed max points, rotate the file
                        if file_info['point_count'] > 1000:
                            self.rotate_data_file(query_config.name)
                
                print(f"Query '{query_config.name}': {numeric_value}")
                
                # Sleep for remaining interval time
                elapsed = time.time() - start_time
                sleep_time = max(0, query_config.interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"Error executing query '{query_config.name}': {e}")
                time.sleep(query_config.interval)
    
    def rotate_data_file(self, query_name):
        """Rotate data file when it gets too large (rolling window)"""
        file_info = self.data_files[query_name]
        
        # Close current file
        if file_info['handle']:
            file_info['handle'].close()
        
        # Rewrite file with only the recent data (last 1000 points)
        query_data = self.data[query_name]
        query = next(q for q in self.queries if q.name == query_name)
        
        with open(file_info['filename'], 'w') as f:
            for i, value in enumerate(query_data):
                relative_time = i * query.interval
                f.write(f"{relative_time} {value}\n")
        
        # Reopen file for appending
        file_info['handle'] = open(file_info['filename'], 'a')
        file_info['point_count'] = len(query_data)
    
    def generate_gnuplot_script(self):
        """Generate GNU Plot script from template"""
        try:
            with open('template.plt', 'r') as f:
                template = f.read()
        except FileNotFoundError:
            raise QueryVizError("template.plt not found")
        
        plot_config = self.config['plot']
        
        # Generate style lines
        style_lines = []
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        for i, query in enumerate(self.queries):
            color = query.color if query.color else colors[i % len(colors)]
            style_lines.append(f"set style line {i+1} linecolor rgb '{color}' linewidth {plot_config['line_width']} pointtype 7")
        
        # Generate plot lines using existing data files
        plot_lines = []
        
        for i, query in enumerate(self.queries):
            file_info = self.data_files[query.name]
            data_file = file_info['filename']
            
            title = query.description if query.description else query.name
            if i == 0:
                plot_lines.append(f"plot '{data_file}' using 1:2 with {plot_config['point_type']} linestyle {i+1} title '{title}'")
            else:
                plot_lines.append(f"     '{data_file}' using 1:2 with {plot_config['point_type']} linestyle {i+1} title '{title}'")
        
        # Replace template variables
        script_content = template.replace('{{TIMESTAMP}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        script_content = script_content.replace('{{TERMINAL}}', plot_config['terminal'])
        script_content = script_content.replace('{{OUTPUT_FILE}}', os.path.join(self.output_dir, plot_config['output_file']))
        script_content = script_content.replace('{{TITLE}}', plot_config['title'])
        script_content = script_content.replace('{{XLABEL}}', plot_config['xlabel'])
        script_content = script_content.replace('{{YLABEL}}', plot_config['ylabel'])
        script_content = script_content.replace('{{KEY_POSITION}}', plot_config['key_position'])
        script_content = script_content.replace('{{STYLE_LINES}}', '\n'.join(style_lines))
        script_content = script_content.replace('{{PLOT_LINES}}', ' \\\n'.join(plot_lines))
        
        # Write script file
        script_file = 'current_plot.plt'
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        return script_file
    
    def generate_plot(self):
        """Generate plot using GNU Plot"""
        script_file = self.generate_gnuplot_script()
        
        try:
            result = subprocess.run(['gnuplot', script_file], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"GNU Plot error: {result.stderr}")
            else:
                print(f"Plot generated: {os.path.join(self.output_dir, self.config['plot']['output_file'])}")
        except FileNotFoundError:
            print("Warning: gnuplot not found, script generated but plot not created")
        
        # Clean up only the script file (keep data files)
        try:
            os.remove(script_file)
        except OSError:
            pass
    
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
            
            # Open data files for writing
            self.open_data_files()
            
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
                    self.generate_plot()
                    last_plot_time = current_time
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error: {e}")
            self.exit(1)
        finally:
            self.running = False
            self.close_data_files()
            for conn in self.connections.values():
                conn.close()
        
        self.exit(0)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='query-viz: Generate real-time charts using GNU Plot')
    parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    args = parser.parse_args()
    
    app = QueryViz(args.config)
    return app.run()

if __name__ == '__main__':
    sys.exit(main())

"""
Data file handler.
Uses a keyd singleton to make sure that each data file matches no more than 1 handler.
A data file must contain data from one query.
"""

import os
import re
from collections import deque
from threading import Lock
from .temporal_column import TemporalColumnRegistry


class DataFile:
    """Manage data file operations for a single query"""
    
    # Instance dictionary. The key is query_name
    _instances = {}
    # Govern instance creation
    _lock = Lock()
    
    def __new__(cls, query_object, output_dir, max_points=1000):
        """
        Ensure only one DataFile instance per query_name.
        """
        key = query_object.name
        
        with cls._lock:
            if key not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[key] = instance
                instance._initialized = False
            return cls._instances[key]
    
    def __init__(self, query_object, output_dir, max_points=1000):
        """
        Initialize DataFile for a query.
        
        Args:
            query_object (str): From here we'll take all the query attributes we need.
                                A normalised version of the query name will be the file name.
            output_dir (str): Directory where data files are stored.
            max_points (int): Max number of data points before rotation. Data point = query row.
        """
        # Prevent re-initialization of existing instances
        if self._initialized:
            return
        
        self.query_name = query_object.name
        self.query_description = query_object.description or ""
        self.query_interval = query_object.interval
        self.columns = query_object.columns
        self.output_dir = output_dir
        self.max_points = max_points
        self.has_time_column = (self.columns[0] == 'time')
        
        # Create temporal column formatter based on query's time_type
        self.temporal_column = TemporalColumnRegistry.create(query_object.time_type)
        
        # Normalize query name for filename
        self.filename = self._generate_filename(query_object.name)
        self.filepath = os.path.join(output_dir, self.filename)
        
        # File handle and tracking
        self._file_handle = None
        self._point_count = 0
        self._is_open = False
        
        # In-memory data for rotation (no locks needed - single thread per instance)
        # File lines are stored as a list of strings
        self._data_lines = deque(maxlen=max_points)
        
        self._initialized = True
    
    def _generate_filename(self, query_name):
        """Generate normalized filename from query name"""
        # Remove special characters (keep only alphanumeric, spaces, underscores, and hyphens)
        normalized = re.sub(r'[^a-zA-Z0-9\s_-]', '', query_name)
        # Convert spaces and underscores to dashes
        normalized = re.sub(r'[\s_]+', '-', normalized)
        # Collapse consecutive dashes into one dash
        normalized = re.sub(r'-+', '-', normalized)
        # Remove leading/trailing dashes
        normalized = normalized.strip('-')
        # Make lowercase
        normalized = normalized.lower()
        # Add extension
        return f"{normalized}.dat"
    
    def _write_headers(self):
        """Write header comments to the data file"""
        if not self._file_handle:
            raise RuntimeError(f"DataFile for '{self.query_name}' is not open")
        
        # Build column list string
        if self.has_time_column:
            columns_str = ', '.join(self.columns)
        else:
            columns_str = 'time, ' + ', '.join(self.columns)
        
        header = f"""# Data file created by Query-Viz
# https://github.com/Vettabase/query-viz
#
# Query name: {self.query_name}
# Query description: {self.query_description}
# Columns: {columns_str}
#
"""
        self._file_handle.write(header)
    
    def _format_data_line(self, values):
        """
        Format a data line for writing to file.
        
        Args:
            values (list): List of values for all columns
        
        Returns:
            str: Formatted line ready for file writing
        """
        if self.has_time_column:
            # A Temporal Column is in the query results
            # We format it according to its type
            time_value = values[0]
            formatted_time = self.temporal_column.format_value(time_value)
            other_values = [str(val) for val in values[1:]]
            line_values = [formatted_time] + other_values
        else:
            # The query has no Temporal Column
            # Let's generate a Temporal Value artificially
            artificial_time = self.temporal_column.generate_artificial_time(self._point_count, self.query_interval)
            line_values = [artificial_time] + [str(val) for val in values]
        
        return ' '.join(line_values) + '\n'
    
    def open(self):
        """Open data file for writing, removing existing file if it exists"""
        if self._is_open:
            return
        
        # Remove existing file and start fresh
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
        
        self._file_handle = open(self.filepath, 'w')
        self._write_headers()
        self._point_count = 0
        self._data_lines.clear()
        self._is_open = True
    
    def close(self):
        """Close data file"""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        self._is_open = False
    
    def write_data_point(self, values):
        """
        Write a data point to the file.
        
        Args:
            values (list): List of values for all columns
            
        Returns:
            bool: True if rotation occurred, False otherwise
        """
        if not self._is_open or not self._file_handle:
            raise RuntimeError(f"DataFile for '{self.query_name}' is not open")
        
        # Format the line
        formatted_line = self._format_data_line(values)
        
        # Write to file
        self._file_handle.write(formatted_line)
        self._file_handle.flush()  # Ensure data is written immediately
        
        # Store in memory for rotation
        self._data_lines.append(formatted_line)
        self._point_count += 1
        
        # Check if rotation is needed
        if self._point_count > self.max_points:
            self._rotate_file()
            return True
        
        return False
    
    def _rotate_file(self):
        """Rotate data file when it gets too large (rolling window)"""
        # Close current file
        if self._file_handle:
            self._file_handle.close()
        
        # Rewrite file with only the recent data
        self._file_handle = open(self.filepath, 'w')
        
        # Write headers when file contents are replaced
        self._write_headers()
        
        # Flush to file
        for line in self._data_lines:
            self._file_handle.write(line)
        
        # Close and reopen file for appending
        self._file_handle.close()
        self._file_handle = open(self.filepath, 'a')
        self._point_count = len(self._data_lines)
    
    def get_filepath(self):
        """Get the full path to the data file"""
        return self.filepath
    
    def get_filename(self):
        """Get the filename (without path)"""
        return self.filename
    
    def get_point_count(self):
        """Get the current number of data points"""
        return self._point_count
    
    def is_open(self):
        """Check if the data file is currently open"""
        return self._is_open
    
    def get_data_copy(self):
        """Get a copy of the current in-memory data"""
        return list(self._data_lines)
    
    @classmethod
    def clear_instances(cls):
        """Clear all cached instances)"""
        with cls._lock:
            cls._instances.clear()
    
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

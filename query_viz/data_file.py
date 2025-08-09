"""
Data file handler.
Uses a keyd singleton to make sure that each data file matches no more than 1 handler.
A data file must contain data from one query.
"""

import os
import re
from collections import deque
from threading import Lock


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
        self.query_interval = query_object.interval
        self.columns = query_object.columns
        self.output_dir = output_dir
        self.max_points = max_points
        
        # Normalize query name for filename
        self.filename = self._generate_filename(query_object.name)
        self.filepath = os.path.join(output_dir, self.filename)
        
        # File handle and tracking
        self._file_handle = None
        self._point_count = 0
        self._is_open = False
        
        # In-memory data for rotation (no locks needed - single thread per instance)
        self._data = deque(maxlen=max_points)
        
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
    
    def open(self):
        """Open data file for writing, removing existing file if it exists"""
        if self._is_open:
            return
        
        # Remove existing file and start fresh
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
        
        self._file_handle = open(self.filepath, 'w')
        self._point_count = 0
        self._data.clear()
        self._is_open = True
    
    def close(self):
        """Close data file"""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        self._is_open = False
    
    def write_data_point(self, value):
        """
        Write a data point to the file.
        
        Args:
            value (float): The numeric value to write
            
        Returns:
            bool: True if rotation occurred, False otherwise
        """
        if not self._is_open or not self._file_handle:
            raise RuntimeError(f"DataFile for '{self.query_name}' is not open")
        
        # Calculate relative time
        relative_time = self._point_count * self.query_interval
        
        # Write to file
        self._file_handle.write(f"{relative_time} {value}\n")
        self._file_handle.flush()  # Ensure data is written immediately
        
        # Store in memory for potential rotation
        self._data.append(value)
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
        with open(self.filepath, 'w') as f:
            for i, value in enumerate(self._data):
                relative_time = i * self.query_interval
                f.write(f"{relative_time} {value}\n")
        
        # Reopen file for appending
        self._file_handle = open(self.filepath, 'a')
        self._point_count = len(self._data)
    
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
        return list(self._data)
    
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

"""
Data file set manager - centralized management of all DataFile instances
"""

from .data_file import DataFile


class DataFileSet:
    """Manages all DataFile instances. Only class methods - do not instantiate."""
    
    _data_files = {}

    def __new__(cls, *args, **kwargs):
        """Prevent instantiation of DataFileSet"""
        raise TypeError("DataFileSet cannot be instantiated")
    
    @classmethod
    def set(cls, query_object, output_dir):
        """Create a DataFile instance and cache it"""
        data_file = DataFile(query_object, output_dir)
        cls._data_files[query_object.name] = data_file
    
    @classmethod
    def get(cls, query_name):
        """Returns the DataFile instance for the specified query name, or None"""
        return cls._data_files.get(query_name)
    
    @classmethod
    def get_file_name(cls, query_name):
        """Returns the filename for the specified query name, or None"""
        return cls._data_files.get(query_name).get_filename()
    
    @classmethod
    def open_all(cls):
        """Open all data files"""
        for data_file in cls._data_files.values():
            data_file.open()
    
    @classmethod
    def open_recurring_queries(cls):
        """Open data files for queries with intervals (not 'once')"""
        for data_file in cls._data_files.values():
            if data_file.query_interval != 'once':
                data_file.open()
    
    @classmethod
    def close_all(cls):
        """Close all data files"""
        for data_file in cls._data_files.values():
            if data_file.is_open():
                data_file.close()
    
    @classmethod
    def clear_all(cls):
        """Clear all cached DataFile instances (for testing)"""
        cls._data_files.clear()

"""
Registry for Temporal Column formats.
It acts as a factory and implements validation.
"""

from .temporal_column import TemporalColumn
from .temporal_column_elapsed_time import TemporalColumnElapsedTime
from .temporal_column_timestamp import TemporalColumnTimestamp


class TemporalColumnRegistry:
    """Registry for creating and validating temporal column types"""
    
    _types = {
        'elapsed_seconds': TemporalColumnElapsedTime,
        'timestamp': TemporalColumnTimestamp
    }
    
    def __new__(cls, *args, **kwargs):
        """Prevent instantiation of TemporalColumnRegistry"""
        raise TypeError("Cannot instantiate TemporalColumnRegistry")
    
    @classmethod
    def create(cls, temporal_type: str) -> TemporalColumn:
        """
        Create a temporal column instance based on time type
        
        Args:
            temporal_type: The type of temporal column ('elapsed_seconds' or 'timestamp')
            
        Returns:
            TemporalColumn: Instance of the appropriate temporal column class
            
        Raises:
            KeyError: If temporal_type is not supported
        """
        if not self.validate(temporal_type):
            raise KeyError(f"Unsupported temporal_type: {temporal_type}")
        return cls._types[temporal_type]()
    
    @classmethod
    def validate(cls, temporal_type: str) -> bool:
        """
        Validate if a time type is supported
        
        Args:
            temporal_type: The time type to validate
            
        Returns:
            bool: True if temporal_type is valid, False otherwise
        """
        return temporal_type in cls._types

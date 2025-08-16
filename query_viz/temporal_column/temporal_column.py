"""
Abstract Base Class for Temporal Columns. Each subclass implements a format.
"""

from abc import ABC, abstractmethod


class TemporalColumn(ABC):
    """Abstract base class for temporal column formatting (equivalent to Java interface)"""
    
    def __new__(cls, *args, **kwargs):
        """Prevent direct instantiation of TemporalColumn"""
        if cls is TemporalColumn:
            raise TypeError("Cannot instantiate abstract class TemporalColumn")
        return super().__new__(cls)
    
    @abstractmethod
    def format_value(self, time_value) -> str:
        """
        Format a time value according to the specific temporal type
        
        Args:
            time_value: The time value to format
            
        Returns:
            str: Formatted time value
        """
        pass
    
    @abstractmethod
    def generate_artificial_time(self, point_count: int, interval: float) -> str:
        """
        Generate artificial time value when no time column exists
        
        Args:
            point_count: Number of data points collected so far
            interval: Time interval between data points
            
        Returns:
            str: Formatted artificial time value
        """
        pass

    def get_default_description(self) -> str:
        """
        Get default description for the temporal axis
        
        Returns:
            str: Default description for temporal axis label
            
        Raises:
            NotImplementedError: Always, as this must be implemented by subclasses
        """
        raise NotImplementedError("get_default_description() must be implemented by subclasses")

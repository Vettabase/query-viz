"""
TemporalColumn implementation in the ElapsedTime format.
In its current implementation, it is the number of seconds
elapsed from the beginning of data collection.
"""

import time
from .temporal_column import TemporalColumn


class TemporalColumnElapsedTime(TemporalColumn):
    """Handle temporal columns as elapsed seconds"""
    
    def __init__(self):
        self.start_time = None

    def format_value(self, time_value) -> str:
        """
        Format time value as elapsed seconds
        
        Args:
            time_value: The time value to format
            
        Returns:
            str: Time value as string
        """
        return str(time_value)
    
    def generate_artificial_time(self, point_count: int, interval: float) -> str:
        """
        Generate artificial elapsed time
        
        Args:
            point_count: Number of data points collected so far
            interval: Time interval between data points
            
        Returns:
            str: Elapsed time as string
        """
        if self.start_time is None:
            return '0'
        return str(int(time.time() - self.start_time))

    def get_default_description(self) -> str:
        """
        Get default description for the temporal axis
        
        Returns:
            str: Default description for temporal axis label
        """
        return "Elapsed Time"

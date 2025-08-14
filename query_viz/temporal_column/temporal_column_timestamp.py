"""
TemporalColumn implementation in the Timestamp format.
Values are shown in a human-readable format.
"""

import time
from datetime import datetime
from .temporal_column import TemporalColumn


class TemporalColumnTimestamp(TemporalColumn):
    """Handle temporal columns as formatted timestamps"""
    
    def format_value(self, time_value) -> str:
        """
        Format time value as YYYY-MM-DD hh-mm-ss timestamp
        
        Args:
            time_value: The time value to format (expected to be a timestamp)
            
        Returns:
            str: Formatted timestamp string
        """
        try:
            dt = datetime.fromtimestamp(float(time_value))
            return dt.strftime('%Y-%m-%d %H-%M-%S')
        except (ValueError, TypeError):
            # If conversion fails, return original value
            return str(time_value)
    
    def generate_artificial_time(self, point_count: int, interval: float) -> str:
        """
        Generate artificial timestamp based on current time and elapsed intervals
        
        Args:
            point_count: Number of data points collected so far
            interval: Time interval between data points
            
        Returns:
            str: Formatted timestamp string
        """
        relative_time = point_count * interval
        current_timestamp = time.time()
        point_timestamp = current_timestamp - (point_count * interval)
        return self.format_value(point_timestamp)

"""
Interval parsing and validation implementation
"""

import re
from ..exceptions import QueryVizError


class Interval:
    """Parse and validate time intervals with support for special values"""
    
    # Unit conversion factors to seconds
    UNITS = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800
    }

    # An interval type determines how the interval is validated.
    # min and max represent the range.
    # special_values is a list of admitted special string values.
    # When an interval type has no match in this dictionary,
    # the default type applies: positive, no maximum, no special
    # values.
    # This is a class property because the types dictionary must be
    # shared between all intervals, and must never be modified.
    INTERVAL_TYPES = {
        'default': {
            'min': 0,
            'max': None,
            'special_values': []
        },
        'query_interval': {
            'min': 1,
            'max': None,
            'special_values': ['once']
        }
    }
    
    def __init__(self, interval_type=None):
        """
        Initialize interval parser with optional special values
        
        Args:
            interval_type:         Type of interval, from INTERVAL_TYPES. Default: 'default'.
        """
        self._value = None
        self._is_special = None
        
        # interval_type refers to an existing type in INTERVAL_TYPES, and it's
        # an instance property.
        if interval_type is None or interval_type not in self.INTERVAL_TYPES:
            self.interval_type = 'default'
        else:
            self.interval_type = interval_type
    
    def validate(self, interval_str):
        """
        Validate and parse an interval string
        
        Args:
            interval_str:   String to validate (e.g., '1m', '30s', 'once')
            
        Returns:
            bool: True if valid, False otherwise
            
        Raises:
            QueryVizError: If the interval string is invalid
        """
        if interval_str is None:
            raise QueryVizError("Interval cannot be None")
        interval_str = str(interval_str).strip()
        if not interval_str:
            raise QueryVizError("Interval cannot be empty")
        
        # Get validation rules based on interval_type
        validation_rules = self.INTERVAL_TYPES[self.interval_type]
        min_seconds = validation_rules['min']
        max_seconds = validation_rules['max']
        special_values = validation_rules['special_values']
        
        # Check for special values first (case-insensitive)
        normalized_input = interval_str.lower()
        if normalized_input in special_values:
            self._value = normalized_input
            self._is_special = True
            return True
        
        # Parse numeric interval
        try:
            self._value = self._parse_numeric_interval(interval_str)
            self._is_special = False
        except QueryVizError:
            raise
        
        # Verify that value is in range
        if min_seconds is not None and self._value < min_seconds:
            raise QueryVizError(f"Interval is too low. Min: {min_seconds}")
        if max_seconds is not None and self._value > max_seconds:
            raise QueryVizError(f"Interval is too high. Max: {max_seconds}")
    
    def _parse_numeric_interval(self, interval_str):
        """
        Parse numeric interval string to seconds
        
        Args:
            interval_str: String like '1m', '30s', '2.5h'
            
        Returns:
            float: Interval in seconds
            
        Raises:
            QueryVizError: If format is invalid
        """
        # Remove all whitespace characters
        clean_str = re.sub(r'\s+', '', interval_str)
        
        # Check if it's just a number (default to seconds)
        try:
            return float(clean_str)
        except ValueError:
            pass
        
        # Extract numeric part and unit
        match = re.match(r'^([0-9]*\.?[0-9]+)([a-zA-Z]?)$', clean_str)
        if not match:
            raise QueryVizError(f"Invalid interval format: {interval_str}")
        
        value_str, unit = match.groups()
        value = float(value_str)
        if not unit:
            unit = 's'
        else:
            unit = unit.lower()
        if unit not in self.UNITS:
            raise QueryVizError(f"Invalid time unit '{unit}' in interval: {interval_str}")
        
        return value * self.UNITS[unit]
    
    def get_seconds(self):
        """
        Get interval value in seconds, as an integer
        
        Returns:
            float or str: Interval in seconds, or special value string if applicable
            
        Raises:
            RuntimeError: If validate() hasn't been called successfully
        """
        if self._is_special:
            return self._value
        return int(self._value)
    
    def get_time(self, unit='s'):
        """
        Get interval value in specified unit
        
        Args:
            unit (str): Target unit ('s', 'm', 'h', 'd', 'w')
            
        Returns:
            float or str: Interval in specified unit, or special value string if applicable
            
        Raises:
            RuntimeError: If validate() hasn't been called successfully
            ValueError: If unit is invalid
        """
        # Return special values as-is
        # Validate unit
        if unit not in self.UNITS:
            raise ValueError(f"Invalid time unit: {unit}")
        if self._is_special:
            return self._value
        return float(self._value / self.UNITS[unit])
    
    def is_special_value(self):
        """
        Check if the current value is a special value
        
        Returns:
            bool: True if current value is special, False if numeric
            
        Raises:
            RuntimeError: If validate() hasn't been called successfully
        """
        return self._is_special
        
    def setget(self, interval):
        """
        Validate an interval, set it internally, and return it as seconds.

        Args:
            interval_str:   String to validate (e.g., '1m', '30s', 'once')
        
        Returns:
            float or str: Interval in seconds, or special value string if applicable
            
        Raises:
            RuntimeError: If validate() hasn't been called successfully
        """
        self.validate(interval)
        return self.get_seconds()

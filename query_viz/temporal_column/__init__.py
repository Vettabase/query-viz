"""
Temporal column module.

This refers to a columns in the data files, which is the first column
of each line. It can be read from the database, or it can be generated
automatically.

Each format is implemented by a subclass of TemporalColumn:
- TemporalColumnElapsedTime: The time passed since the beginning of
  data collection;
- TemporalColumnTimestamp: Time and date.

Temporal values are used to identify a data point for the following goals:
- Joining different metrics, possibly from different queries;
- Data file rotation.
"""

from .temporal_column import TemporalColumn
from .temporal_column_elapsed_time import TemporalColumnElapsedTime
from .temporal_column_timestamp import TemporalColumnTimestamp
from .temporal_column_registry import TemporalColumnRegistry

__all__ = [
    'TemporalColumn',
    'TemporalColumnElapsedTime', 
    'TemporalColumnTimestamp',
    'TemporalColumnRegistry'
]

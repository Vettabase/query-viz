"""
query-viz: A tool to generate real-time charts using GNU Plot
Copyright: Vettabase 2025
License: AGPLv3
"""

from .core import QueryViz
from .query import QueryConfig
from .exceptions import QueryVizError

__version__ = "1.0.0"
__all__ = ['QueryViz', 'QueryConfig', 'QueryVizError']

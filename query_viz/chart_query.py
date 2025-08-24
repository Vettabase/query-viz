"""
Chart query configuration for selective column inclusion
"""

from .exceptions import QueryVizError


class ChartQuery:
    """Used by a chart generator to get metadata about the queries it should read."""
    
    def error(self, message):
        """
        Return a QueryVizError exception containing the query name plus the specified message.
        
        Args:
            message (str): Error message
        """
        query_name = self.query_name
        raise QueryVizError(f"Error in {query_name} columns configuration: {message}")
    
    def __init__(self, query_name, selected_columns=None):
        """
        Initialize chart query configuration
        
        Args:
            query_name (str): Name of the query to reference
            selected_columns (list): List of column specifications like ["column1:alias1", "column2"]
        """
        self.query_name = query_name
        self.selected_columns = selected_columns or []
        self.column_mappings = self._parse_column_mappings()
    
    def _parse_column_mappings(self):
        """
        Parse column specifications into mappings
        
        Returns:
            list: List of (column_name, alias) tuples
        """
        mappings = []
        
        for col_spec in self.selected_columns:
            if ':' in col_spec:
                # Format: "column:alias"
                parts = col_spec.split(':', 1)  # Split only on first ':'
                column_name = parts[0].strip()
                alias = parts[1].strip()
                
                if not column_name:
                    self.error(f"Invalid column specification '{col_spec}': column name not specified")
                if not alias:
                    alias = column_name
                
                mappings.append((column_name, alias))
            else:
                # Format: "column" (use column name as alias)
                column_name = col_spec.strip()
                if not column_name:
                    self.error(f"Invalid column specification '{col_spec}': column name not specified")
                
                mappings.append((column_name, column_name))
        
        return mappings
    
    def uses_all_columns(self):
        """
        Check if this query uses all available columns
        
        Returns:
            bool: True if no column selection specified (use all columns)
        """
        return len(self.selected_columns) == 0
    
    def get_data_file_column_specs(self, data_file):
        """
        Get data file column specifications for this query
        
        Args:
            data_file: DataFile instance
            
        Returns:
            list: List of (metric_col, title) tuples for chart generation
        """
        # Get column names from data file header
        column_names = data_file.get_column_names()
        
        if not column_names:
            self.error("No columns found in Data File")
        
        specs = []
        
        if self.uses_all_columns():
            # Use all metric columns (skip time column at index 0)
            for i, col_name in enumerate(column_names[1:], 2):  # Start from column 2
                title = f"{self.query_name}-{col_name}"
                specs.append((i, title))
        else:
            # Use selected columns only
            for column_name, alias in self.column_mappings:
                if column_name == 'time':
                    self.error("Cannot select 'time' column as a metric")
                
                if column_name not in column_names:
                    available_columns = ', '.join(column_names)
                    self.error(f"Column '{column_name}' not found. Available columns: {available_columns}")
                
                col_index = column_names.index(column_name) + 1  # Convert to 1-based indexing
                title = alias
                specs.append((col_index, title))
        
        return specs
    
    def __str__(self):
        """String representation for debugging"""
        if self.uses_all_columns():
            return f"ChartQuery(query='{self.query_name}', all_columns=True)"
        else:
            cols = [f"{col}:{alias}" if col != alias else col for col, alias in self.column_mappings]
            return f"ChartQuery(query='{self.query_name}', columns=[{', '.join(cols)}])"
    
    def __repr__(self):
        return self.__str__()

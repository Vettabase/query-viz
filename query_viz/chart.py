"""
Chart generation using Gnuplot
"""

import os
import subprocess
from datetime import datetime
from .exceptions import QueryVizError
from .data_file_set import DataFileSet


class ChartGenerator:
    """Handles Gnuplot chart generation"""
    
    # Chart type aliases
    CHART_TYPE_ALIASES = {
        'line_graph': 'line_chart'
    }
    
    def __init__(self, plot_config, output_dir, chart_type='line_chart'):
        self.plot_config = plot_config
        self.output_dir = output_dir
        
        # If an alias was used, resolve it
        self.chart_type = self.CHART_TYPE_ALIASES.get(chart_type, chart_type)
        self.template_file = f'chart_templates/{self.chart_type}.plt'
        
        # Validate chart type and template file
        if not os.path.exists(self.template_file):
            raise QueryVizError(f"Template file for chart type '{chart_type}' not found: {self.template_file}")
    
    def generate_all_charts(self, chart_queries):
        """Generate all charts using Gnuplot"""
        script_file = self._generate_gnuplot_script(chart_queries)
        # A falsey value is expected when there is no data to plot
        if script_file:
            return self._execute_gnuplot(script_file)
    
    def _generate_gnuplot_script(self, chart_queries):
        """Generate Gnuplot script from template"""
        try:
            with open(self.template_file, 'r') as f:
                template = f.read()
        except FileNotFoundError:
            raise QueryVizError(f"{self.template_file} not found")
        
        # Check if any query uses timestamp format
        has_timestamp = False
        for chart_query in chart_queries:
            if DataFileSet.has_started(chart_query.query_name):
                data_file = DataFileSet.is_ready(chart_query.query_name)
                if data_file and data_file.time_type == 'timestamp':
                    has_timestamp = True
                    break
        
        # Determine xlabel. If not specified, use default
        xlabel = self.plot_config.get('xlabel')
        if not xlabel and chart_queries:
            # Use the first query's temporal column to get default description
            first_data_file = DataFileSet.is_ready(chart_queries[0].query_name)
            if first_data_file and hasattr(first_data_file, 'time_type'):
                from .temporal_column import TemporalColumnRegistry
                temporal_column = TemporalColumnRegistry.create(first_data_file.time_type)
                xlabel = temporal_column.get_default_description()
        
        # Generate plot_lines and style_lines.
        # This distinctions allows to separate contents from presentation,
        # while keeping them clearly related (plot_lines[x] <=> style_lines[x]).
        plot_lines = []
        style_lines = []
        # TODO: Make the palette editable
        # TODO: Implement color aliases
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        line_index = 1
        
        for chart_query in chart_queries:
            data_file = DataFileSet.is_ready(chart_query.query_name)
            
            if not data_file:
                print(f"Warning: No Data File found for query '{chart_query.query_name}'")
                continue
            
            if data_file.get_point_count() == 0:
                print(f"Warning: Data file for query '{chart_query.query_name}' is empty. Skipping")
                continue
            
            # Get column specifications from Data File headers
            try:
                column_specs = chart_query.get_data_file_column_specs(data_file)
            except Exception as e:
                print(f"Warning: Could not get column specs for query '{chart_query.query_name}': {e}")
                continue
            
            for metric_col, title in column_specs:
                # Use default colors by looping over the palette
                color = colors[(line_index - 1) % len(colors)]
                style_lines.append(f"set style line {line_index} linecolor rgb '{color}' linewidth {self.plot_config['metrics_line_width']} pointtype 7")
                
                data_file_path = data_file.get_filepath()
                plot_lines.append(f"'{data_file_path}' using 1:{metric_col} with linespoints linestyle {line_index} title '{title}'")
                
                line_index += 1
        
        if not plot_lines:
            #raise QueryVizError("No plot lines generated")
            return ''
        
        if self.plot_config['grid']:
            grid_command = "set grid" 
        else:
            grid_command = "unset grid"
        
        # Replace template variables
        script_content = template
        script_content = script_content.replace('{{CHART_WIDTH}}', str(self.plot_config['chart_width']))
        script_content = script_content.replace('{{CHART_HEIGHT}}', str(self.plot_config['chart_height']))
        script_content = script_content.replace('{{OUTPUT_FILE}}', os.path.join(self.output_dir, self.plot_config['output_file']))
        script_content = script_content.replace('{{TITLE}}', self.plot_config['title'])
        script_content = script_content.replace('{{XLABEL}}', xlabel)
        script_content = script_content.replace('{{YLABEL}}', self.plot_config['ylabel'])
        script_content = script_content.replace('{{GRID}}', grid_command)
        script_content = script_content.replace('{{KEY_POSITION}}', self.plot_config['key_position'])
        script_content = script_content.replace('{{STYLE_LINES}}', '\n'.join(style_lines))
        script_content = script_content.replace('{{PLOT_LINES}}', 'plot ' + ', \\\n     '.join(plot_lines))
        
        # Add timestamp formatting if needed
        if has_timestamp:
            # Insert timestamp formatting commands before the plot command
            plot_command_pos = script_content.find('plot ')
            timestamp_commands = '''
# Format X axis for timestamps
set xdata time
set timefmt "%s"
set format x "%Y-%m-%d %H:%M:%S"
set xtics rotate by -45

'''
            script_content = script_content[:plot_command_pos] + timestamp_commands + script_content[plot_command_pos:]
        
        # Write script file
        script_file = 'current_plot.plt'
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        return script_file
    
    def _execute_gnuplot(self, script_file):
        """Execute Gnuplot script"""
        try:
            result = subprocess.run(['gnuplot', script_file], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Gnuplot error: {result.stderr}")
                return False
            else:
                print(f"Plot generated: {os.path.join(self.output_dir, self.plot_config['output_file'])}")
                return True
        except FileNotFoundError:
            print("Warning: gnuplot not found, script generated but plot not created")
            return False
        finally:
            # Clean up script file
            try:
                os.remove(script_file)
            except OSError:
                pass

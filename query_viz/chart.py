"""
Chart generation using Gnuplot
"""

import os
import subprocess
from datetime import datetime
from .exceptions import QueryVizError


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
    
    def generate_chart(self, queries, data_files):
        """Generate chart using Gnuplot"""
        script_file = self._generate_gnuplot_script(queries, data_files)
        return self._execute_gnuplot(script_file)
    
    def _generate_gnuplot_script(self, queries, data_files):
        """Generate Gnuplot script from template"""
        try:
            with open(self.template_file, 'r') as f:
                template = f.read()
        except FileNotFoundError:
            raise QueryVizError(f"{self.template_file} not found")
        
        # Generate style lines
        style_lines = []
        # TODO: Make the palette editable
        # TODO: Implement color aliases
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        for i, query in enumerate(queries):
            color = query.color if query.color else colors[i % len(colors)]
            style_lines.append(f"set style line {i+1} linecolor rgb '{color}' linewidth {self.plot_config['line_width']} pointtype 7")
        
        # Generate plot lines using existing data files
        plot_lines = []
        
        
        # Determine which column to use (from the data file)
        # for X axis based on xcontents
        xcontents = self.plot_config.get('xcontents')
        if xcontents == 'row_numbers':
            # Only specify Y column, X will use Gnuplot's default: row numbers
            using_clause = '2'
        else:
            # elapsed_seconds (our default)
            # X = column 1 (elapsed seconds) : Y = column 2 (metric)
            using_clause = '1:2'

        for i, query in enumerate(queries):
            file_info = data_files[query.name]
            data_file = file_info['filename']
            
            title = query.description if query.description else query.name
            plot_lines.append(f"'{data_file}' using {using_clause} with {self.plot_config['point_type']} linestyle {i+1} title '{title}'")

        # Replace template variables
        script_content = template
        script_content = script_content.replace('{{TERMINAL}}', self.plot_config['terminal'])
        script_content = script_content.replace('{{OUTPUT_FILE}}', os.path.join(self.output_dir, self.plot_config['output_file']))
        script_content = script_content.replace('{{TITLE}}', self.plot_config['title'])
        script_content = script_content.replace('{{XLABEL}}', self.plot_config['xlabel'])
        script_content = script_content.replace('{{YLABEL}}', self.plot_config['ylabel'])
        script_content = script_content.replace('{{KEY_POSITION}}', self.plot_config['key_position'])
        script_content = script_content.replace('{{STYLE_LINES}}', '\n'.join(style_lines))
        script_content = script_content.replace('{{PLOT_LINES}}', 'plot ' + ', \\\n     '.join(plot_lines))
        
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

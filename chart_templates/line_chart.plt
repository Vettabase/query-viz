#!/usr/bin/gnuplot
# MariaDB Query Statistics Plot Template
# Generated on {{TIMESTAMP}}

set terminal {{TERMINAL}}
set output '{{OUTPUT_FILE}}'

set title '{{TITLE}}'
set xlabel '{{XLABEL}}'
set ylabel '{{YLABEL}}'

set grid
set key {{KEY_POSITION}}

# Set colors and styles for different query types
{{STYLE_LINES}}

{{PLOT_LINES}}

# Also create a terminal version for viewing
set terminal dumb 120 30
set output
replot

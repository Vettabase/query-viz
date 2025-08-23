#!/usr/bin/env python3
"""
query-viz: A tool to generate real-time charts using GNU Plot
Copyright: Vettabase 2025
License: AGPLv3
"""

import sys
import argparse
from query_viz import QueryViz


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='query-viz: Generate real-time charts using GNU Plot')
    parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    parser.add_argument('-v', action='count', default=0, 
                       help='Verbosity. Can be used multiple times: -v, -vv...')
    args = parser.parse_args()

    verbosity_level = args.v
    print(f"Verbosity level: {verbosity_level}")
    
    app = QueryViz(args.config, verbosity_level)
    return app.run()


if __name__ == '__main__':
    sys.exit(main())

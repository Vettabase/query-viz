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
    args = parser.parse_args()
    
    app = QueryViz(args.config)
    return app.run()


if __name__ == '__main__':
    sys.exit(main())

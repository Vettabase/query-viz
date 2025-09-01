#!/usr/bin/env python3
"""
query-viz: A tool to generate real-time charts using GNU Plot
Copyright: Vettabase 2025
License: AGPLv3
"""

import sys
import argparse
from query_viz import QueryViz


def list_available_dbms():
    """
    List all available DBMS types and print them in a human-readable format
    """
    try:
        from query_viz import ConnectionManager
        connection_manager = ConnectionManager()
        dbms_list = connection_manager.list_dbms()
        
        print("Available DBMS connectors:")
        for dbms in dbms_list:
            print(f"  - {dbms}")
    
    except Exception as e:
        print(f"Error: Could not list DBMS types: {e}", file=sys.stderr)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='query-viz: Generate real-time charts using GNU Plot')
    parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    parser.add_argument('-v', action='count', default=0, 
                       help='Verbosity. Can be used multiple times: -v, -vv...')
    parser.add_argument('--list-dbms', action='store_true',
                       help='List available DBMS types and exit')
    args = parser.parse_args()
    
    if args.list_dbms:
        list_available_dbms()
        sys.exit(0)
    
    verbosity_level = args.v
    print(f"Verbosity level: {verbosity_level}")
    
    app = QueryViz(verbosity_level, args.config)
    return app.run()


if __name__ == '__main__':
    sys.exit(main())

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


def show_dbms_info(connector_name):
    """
    Show detailed information about a specific DBMS connector
    
    Args:
        connector_name (str): Name of the connector to show info for
    """
    try:
        from query_viz import ConnectionManager
        connection_manager = ConnectionManager()
        
        # Get connector information through ConnectionManager
        info = connection_manager.get_dbms_info(connector_name)
        
        print(f"DBMS Connector: {connector_name}")
        print("=" * (len(f"DBMS Connector: {connector_name}")))
        
        # Display connector information
        if 'connector-name' in info:
            print(f"Name: {info['connector-name']}")
        
        if 'version' in info:
            print(f"Version: {info['version']}")
        
        if 'maturity' in info:
            print(f"Maturity: {info['maturity']}")
        
        if 'license' in info:
            print(f"License: {info['license']}")
        
        if 'copyright' in info:
            print(f"Copyright: {info['copyright']}")
        
        if 'connector-url' in info:
            print(f"Project URL: {info['connector-url']}")
        
        if 'authors' in info and isinstance(info['authors'], list):
            print("Authors:")
            for author in info['authors']:
                if isinstance(author, dict):
                    author_line = f"  - {author.get('name', 'Unknown')}"
                    if 'url' in author:
                        author_line += f" ({author['url']})"
                    print(author_line)
                else:
                    print(f"  - {author}")
    
    except Exception as e:
        print(f"Error: Could not show information for DBMS '{connector_name}': {e}", file=sys.stderr)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='query-viz: Generate real-time charts using GNU Plot')
    parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    parser.add_argument('-v', action='count', default=0, 
                       help='Verbosity. Can be used multiple times: -v, -vv...')
    parser.add_argument('--list-dbms', action='store_true',
                       help='List available DBMS types and exit')
    parser.add_argument('--show-dbms', metavar='CONNECTOR_NAME',
                       help='Show detailed information about a specific DBMS connector and exit')
    args = parser.parse_args()
    
    if args.list_dbms:
        list_available_dbms()
        sys.exit(0)
    
    if args.show_dbms:
        show_dbms_info(args.show_dbms)
        sys.exit(0)
    
    verbosity_level = args.v
    print(f"Verbosity level: {verbosity_level}")
    
    app = QueryViz(verbosity_level, args.config)
    return app.run()


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
VisuaLex API Runner

This script runs the VisuaLex API standalone server.
"""

import os
import sys
import argparse

# Add the project root directory to the Python path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from merl_t.core.visualex.api.app import NormaController

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run VisuaLex API server")
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind the server to"
    )
    
    args = parser.parse_args()
    
    controller = NormaController()
    app = controller.app
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main() 
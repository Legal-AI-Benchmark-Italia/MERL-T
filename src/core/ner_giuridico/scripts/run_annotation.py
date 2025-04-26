#!/usr/bin/env python3
"""
Script to run the annotation interface.
"""

import os
import sys
from pathlib import Path

def main():
    """Main function to run the annotation interface."""
    try:
        # Import the app
        from ner_giuridico.annotation.app import app
        
        # Run the app
        app.run(host='0.0.0.0', port=8080, debug=True)
        return 0
    except Exception as e:
        print(f"Error running annotation interface: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
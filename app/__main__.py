#!/usr/bin/env python3
"""
Main entry point for the Wellona Pharm SMART API application.
Run with: python -m app
"""

import os
import sys

# Add the parent directory to the path so we can import from the root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Now import and run the app
from app.app_v2 import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("APP_PORT", "8055")), debug=False, use_reloader=False)
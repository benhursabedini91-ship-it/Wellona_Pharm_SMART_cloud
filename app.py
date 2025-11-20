"""
Main entry point for Wellona Pharm SMART Cloud Flask API.

This script starts the Flask development server with configuration
loaded from environment variables.

Usage:
    python app.py
"""
import os
from dotenv import load_dotenv
from app import create_app

# Load environment variables
load_dotenv()

# Create Flask application
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', '8055'))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    print(f"Starting Wellona Pharm SMART Cloud API")
    print(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print("")
    print("Available endpoints:")
    print("  GET  /health                      - Health check (no auth)")
    print("  GET  /api/orders                  - Get orders (requires X-API-Key)")
    print("  GET  /api/orders/export           - Export orders (requires X-API-Key)")
    print("  POST /api/orders/approve          - Approve orders (requires X-API-Key)")
    print("  POST /faktura-ai/import-csv       - Import CSV invoices (requires X-API-Key)")
    print("  POST /faktura-ai/import-xml/parse - Parse XML invoice (requires X-API-Key)")
    print("  POST /faktura-ai/import-xml/commit- Commit XML invoice (requires X-API-Key)")
    print("")
    
    # Run the application
    app.run(host=host, port=port, debug=debug)

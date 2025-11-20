"""
Flask application factory for Wellona Pharm SMART Cloud.

This module creates and configures the Flask application with:
- CORS support
- API authentication middleware
- Health check endpoint
- Orders API (Porosi AI)
- Faktura AI API
"""
import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name=None):
    """
    Create and configure the Flask application.
    
    Args:
        config_name: Optional configuration name (development, production, testing)
    
    Returns:
        Configured Flask application instance
    """
    # Load environment variables
    load_dotenv()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration from environment
    app.config['FLASK_ENV'] = os.getenv('FLASK_ENV', 'development')
    app.config['DEBUG'] = app.config['FLASK_ENV'] == 'development'
    
    # Configure CORS
    allowed_origins = []
    
    if app.config['FLASK_ENV'] == 'development':
        dev_origin = os.getenv('CORS_ORIGIN_DEV', 'http://localhost:3000')
        allowed_origins.append(dev_origin)
    
    if app.config['FLASK_ENV'] == 'production':
        prod_origin = os.getenv('CORS_ORIGIN_PROD', 'https://ai.wellonapharm.com')
        allowed_origins.append(prod_origin)
    
    # If no specific origins configured, allow based on environment
    if not allowed_origins:
        allowed_origins = [
            'http://localhost:3000',  # Dev
            'https://ai.wellonapharm.com'  # Prod
        ]
    
    CORS(app, origins=allowed_origins)
    logger.info(f"CORS enabled for origins: {allowed_origins}")
    
    # Health check endpoint (no authentication required)
    @app.route('/health', methods=['GET'])
    def health():
        """
        Health check endpoint.
        
        Returns basic status information without requiring authentication.
        """
        return jsonify({
            'status': 'ok',
            'message': 'Wellona Pharm SMART Cloud API is running',
            'environment': app.config['FLASK_ENV']
        })
    
    # Register blueprints
    from app.routes import orders_bp, faktura_bp
    
    app.register_blueprint(orders_bp)
    app.register_blueprint(faktura_bp)
    
    logger.info("Registered blueprints: orders_api (/api), faktura_api (/faktura-ai)")
    
    # Log startup
    logger.info(f"Flask app created in {app.config['FLASK_ENV']} mode")
    
    return app

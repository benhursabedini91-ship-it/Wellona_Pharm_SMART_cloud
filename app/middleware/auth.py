"""Authentication middleware for API endpoints."""
import os
from functools import wraps
from flask import request, jsonify


def require_api_key(f):
    """
    Decorator to require API key authentication.
    
    Reads the X-API-Key header and compares it to the API_KEY environment variable.
    Returns 401 Unauthorized if the key is missing or invalid.
    
    Usage:
        @app.route('/api/endpoint')
        @require_api_key
        def protected_endpoint():
            return jsonify({"data": "secret"})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        expected_key = os.getenv('API_KEY')
        
        if not api_key:
            return jsonify({
                "status": "error",
                "message": "Unauthorized",
                "code": "INVALID_API_KEY"
            }), 401
        
        if api_key != expected_key:
            return jsonify({
                "status": "error",
                "message": "Unauthorized",
                "code": "INVALID_API_KEY"
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

"""Standard response helpers for API endpoints."""
from flask import jsonify


def success_response(data=None, message="Success", status_code=200):
    """
    Create a standardized success response.
    
    Args:
        data: Optional data to include in response
        message: Success message (default: "Success")
        status_code: HTTP status code (default: 200)
    
    Returns:
        Tuple of (json_response, status_code)
    """
    response = {
        "status": "ok",
        "message": message
    }
    
    if data is not None:
        response["data"] = data
    
    return jsonify(response), status_code


def error_response(message="Error", code="UNKNOWN_ERROR", status_code=400):
    """
    Create a standardized error response.
    
    Args:
        message: Error message (default: "Error")
        code: Error code for client-side handling (default: "UNKNOWN_ERROR")
        status_code: HTTP status code (default: 400)
    
    Returns:
        Tuple of (json_response, status_code)
    """
    response = {
        "status": "error",
        "message": message,
        "code": code
    }
    
    return jsonify(response), status_code

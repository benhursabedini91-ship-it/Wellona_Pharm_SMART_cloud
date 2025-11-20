"""
Orders API routes (Porosi AI).

All endpoints require X-API-Key header for authentication.
"""
from flask import Blueprint, request, send_file
from app.middleware.auth import require_api_key
from app.utils.response import success_response, error_response
from app.services.orders_service import OrdersService
import logging
import io

logger = logging.getLogger(__name__)

# Create blueprint with /api prefix
orders_bp = Blueprint('orders_api', __name__, url_prefix='/api')

# Initialize service
orders_service = OrdersService()


@orders_bp.route('/orders', methods=['GET'])
@require_api_key
def get_orders():
    """
    Get orders with optional filtering.
    
    Query parameters:
        - limit: Maximum number of orders (default: 100, max: 5000)
        - offset: Number of orders to skip (default: 0)
        - urgent_only: Filter for urgent orders only (default: false)
    
    Returns:
        JSON with orders list and totals
    """
    try:
        # Parse query parameters
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        urgent_only = request.args.get('urgent_only', 'false').lower() == 'true'
        
        # Validate limits
        limit = max(1, min(limit, 5000))
        offset = max(0, offset)
        
        # Build params
        params = {
            'limit': limit,
            'offset': offset,
            'urgent_only': urgent_only
        }
        
        # Get orders
        result = orders_service.get_orders(params)
        
        logger.info(f"GET /api/orders: returned {len(result['items'])} orders")
        return success_response(data=result, message="Orders retrieved successfully")
        
    except Exception as e:
        logger.error(f"Error getting orders: {str(e)}")
        return error_response(
            message=f"Failed to retrieve orders: {str(e)}",
            code="ORDERS_RETRIEVAL_ERROR",
            status_code=500
        )


@orders_bp.route('/orders/export', methods=['GET'])
@require_api_key
def export_orders():
    """
    Export orders to a file.
    
    Query parameters:
        - format: Export format (csv, xlsx) - default: csv
        - limit: Maximum number of orders (default: 100, max: 5000)
        - urgent_only: Filter for urgent orders only (default: false)
    
    Returns:
        File download
    """
    try:
        # Parse query parameters
        format_type = request.args.get('format', 'csv').lower()
        limit = request.args.get('limit', 100, type=int)
        urgent_only = request.args.get('urgent_only', 'false').lower() == 'true'
        
        # Validate format
        if format_type not in ['csv', 'xlsx']:
            return error_response(
                message="Invalid format. Supported formats: csv, xlsx",
                code="INVALID_FORMAT",
                status_code=400
            )
        
        # Validate limits
        limit = max(1, min(limit, 5000))
        
        # Build params
        params = {
            'limit': limit,
            'offset': 0,
            'urgent_only': urgent_only
        }
        
        # Export orders
        file_content = orders_service.export_orders(params, format_type)
        
        # Create file-like object
        file_io = io.BytesIO(file_content)
        file_io.seek(0)
        
        # Generate filename
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"orders_export_{timestamp}.{format_type}"
        
        logger.info(f"GET /api/orders/export: exported {format_type} file")
        
        return send_file(
            file_io,
            mimetype='text/csv' if format_type == 'csv' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error exporting orders: {str(e)}")
        return error_response(
            message=f"Failed to export orders: {str(e)}",
            code="ORDERS_EXPORT_ERROR",
            status_code=500
        )


@orders_bp.route('/orders/approve', methods=['POST'])
@require_api_key
def approve_orders():
    """
    Approve a list of orders.
    
    Request body (JSON):
        {
            "order_ids": ["id1", "id2", ...]
        }
    
    Returns:
        JSON with approval results
    """
    try:
        # Parse request body
        data = request.get_json()
        
        if not data or 'order_ids' not in data:
            return error_response(
                message="Missing required field: order_ids",
                code="MISSING_ORDER_IDS",
                status_code=400
            )
        
        order_ids = data['order_ids']
        
        if not isinstance(order_ids, list):
            return error_response(
                message="order_ids must be a list",
                code="INVALID_ORDER_IDS",
                status_code=400
            )
        
        if len(order_ids) == 0:
            return error_response(
                message="order_ids cannot be empty",
                code="EMPTY_ORDER_IDS",
                status_code=400
            )
        
        # Approve orders
        result = orders_service.approve_orders(order_ids)
        
        logger.info(f"POST /api/orders/approve: approved {result['approved']} orders")
        return success_response(data=result, message="Orders approval completed")
        
    except Exception as e:
        logger.error(f"Error approving orders: {str(e)}")
        return error_response(
            message=f"Failed to approve orders: {str(e)}",
            code="ORDERS_APPROVAL_ERROR",
            status_code=500
        )

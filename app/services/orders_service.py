"""
OrdersService - Business logic for Porosi AI (Orders).

This service will eventually connect to the wph_ai database and use the 
logic from wphAI/web_modern for order management.
For now, it returns mock data with the correct structure.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class OrdersService:
    """Service for managing orders (Porosi AI)."""
    
    def __init__(self):
        """Initialize the OrdersService."""
        logger.info("OrdersService initialized")
    
    def get_orders(self, params: dict) -> dict:
        """
        Get orders with optional filtering.
        
        Args:
            params: Dictionary with optional filters:
                - limit: Maximum number of orders to return
                - offset: Number of orders to skip
                - urgent_only: Boolean to filter urgent orders
        
        Returns:
            Dictionary with:
                - items: List of order items
                - total: Total count
                - filters: Applied filters
        """
        logger.info(f"Getting orders with params: {params}")
        
        limit = params.get('limit', 100)
        offset = params.get('offset', 0)
        urgent_only = params.get('urgent_only', False)
        
        # Mock data - structure matches wphAI database schema
        mock_items = [
            {
                'sifra': 'ART001',
                'name': 'Aspirin 100mg',
                'stock': 50,
                'avg_daily': 10.5,
                'cover_days': 4.76,
                'min_zaliha': 100,
                'qty_to_order': 150,
                'urgent_flag': True
            },
            {
                'sifra': 'ART002',
                'name': 'Paracetamol 500mg',
                'stock': 200,
                'avg_daily': 25.3,
                'cover_days': 7.91,
                'min_zaliha': 300,
                'qty_to_order': 200,
                'urgent_flag': False
            },
            {
                'sifra': 'ART003',
                'name': 'Ibuprofen 400mg',
                'stock': 30,
                'avg_daily': 15.2,
                'cover_days': 1.97,
                'min_zaliha': 150,
                'qty_to_order': 250,
                'urgent_flag': True
            }
        ]
        
        # Apply filters
        if urgent_only:
            mock_items = [item for item in mock_items if item.get('urgent_flag')]
        
        # Apply pagination
        paginated_items = mock_items[offset:offset + limit]
        
        result = {
            'items': paginated_items,
            'total': len(mock_items),
            'limit': limit,
            'offset': offset,
            'filters': {
                'urgent_only': urgent_only
            }
        }
        
        logger.info(f"Returning {len(paginated_items)} orders out of {len(mock_items)} total")
        return result
    
    def export_orders(self, params: dict, format_type: str) -> bytes:
        """
        Export orders to a file format.
        
        Args:
            params: Dictionary with optional filters (same as get_orders)
            format_type: Export format ('csv', 'xlsx')
        
        Returns:
            Bytes of the exported file
        """
        logger.info(f"Exporting orders with params: {params}, format: {format_type}")
        
        # Get orders
        orders_data = self.get_orders(params)
        
        # Generate CSV (mock)
        if format_type == 'csv':
            csv_lines = ['Sifra;Kolicina']
            for item in orders_data['items']:
                csv_lines.append(f"{item['sifra']};{int(item['qty_to_order'])}")
            
            content = '\n'.join(csv_lines)
            logger.info(f"Generated CSV export with {len(orders_data['items'])} items")
            return content.encode('utf-8')
        
        # For other formats, return a placeholder
        logger.warning(f"Format {format_type} not yet implemented, returning CSV")
        return self.export_orders(params, 'csv')
    
    def approve_orders(self, order_ids: list) -> dict:
        """
        Approve a list of orders.
        
        Args:
            order_ids: List of order IDs to approve
        
        Returns:
            Dictionary with:
                - approved: Number of approved orders
                - failed: Number of failed approvals
                - order_ids: List of successfully approved order IDs
        """
        logger.info(f"Approving orders: {order_ids}")
        
        # Mock approval logic
        approved = []
        failed = []
        
        for order_id in order_ids:
            # In real implementation, update database
            # For now, simulate success
            if order_id:
                approved.append(order_id)
            else:
                failed.append(order_id)
        
        result = {
            'approved': len(approved),
            'failed': len(failed),
            'order_ids': approved,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Approval complete: {len(approved)} approved, {len(failed)} failed")
        return result

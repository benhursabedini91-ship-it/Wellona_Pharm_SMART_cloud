"""API routes for the application."""
from .orders_api import orders_bp
from .faktura_api import faktura_bp

__all__ = ['orders_bp', 'faktura_bp']

# This file makes the 'faktura_ai' directory a Python package
from flask import Blueprint

faktura_ai_bp = Blueprint('faktura_ai', __name__, template_folder='templates')

from . import routes

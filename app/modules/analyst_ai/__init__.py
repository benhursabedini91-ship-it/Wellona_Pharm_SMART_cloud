# This file makes the 'analyst_ai' directory a Python package
from flask import Blueprint

analyst_ai_bp = Blueprint('analyst_ai', __name__, template_folder='templates')

from . import routes

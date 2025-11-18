# This file makes the 'banka_ai' directory a Python package
from flask import Blueprint

banka_ai_bp = Blueprint('banka_ai', __name__, template_folder='templates')

from . import routes

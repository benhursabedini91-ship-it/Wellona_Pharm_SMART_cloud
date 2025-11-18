# This file makes the 'loyalty_card' directory a Python package
from flask import Blueprint

loyalty_card_bp = Blueprint('loyalty_card', __name__, template_folder='templates')

from . import routes

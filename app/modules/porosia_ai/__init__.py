# This file makes the 'porosia_ai' directory a Python package
from flask import Blueprint

porosia_ai_bp = Blueprint('porosia_ai', __name__, template_folder='templates')

from . import routes

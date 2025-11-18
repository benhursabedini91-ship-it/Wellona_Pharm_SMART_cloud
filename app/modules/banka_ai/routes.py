# Routes for the Banka AI module
from . import banka_ai_bp

@banka_ai_bp.route('/banka')
def index():
    return "<h1>Banka AI Module</h1>"

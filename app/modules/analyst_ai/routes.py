# Routes for the Analyst AI module
from . import analyst_ai_bp

@analyst_ai_bp.route('/analyst')
def index():
    return "<h1>Analyst AI Module</h1>"

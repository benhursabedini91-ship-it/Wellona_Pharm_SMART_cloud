# Routes for the Porosia AI module
from . import porosia_ai_bp

@porosia_ai_bp.route('/porosia')
def index():
    return "<h1>Porosia AI Module</h1>"

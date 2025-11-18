# Routes for the Loyalty Card module
from . import loyalty_card_bp

@loyalty_card_bp.route('/loyalty')
def index():
    return "<h1>Loyalty Card Module</h1>"

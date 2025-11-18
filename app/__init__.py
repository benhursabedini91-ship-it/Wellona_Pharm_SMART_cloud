from flask import Flask, render_template

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    
    # Load the default configuration
    app.config.from_object('app.config.Config')

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/console')
    def console():
        """UI konsola unifikuar (Orders Pro+ & Faktura import)."""
        return render_template('orders_pro_plus.html')

    # Register blueprints for each module
    from .modules.analyst_ai import analyst_ai_bp
    app.register_blueprint(analyst_ai_bp)

    from .modules.banka_ai import banka_ai_bp
    app.register_blueprint(banka_ai_bp)

    from .modules.faktura_ai import faktura_ai_bp
    app.register_blueprint(faktura_ai_bp)

    from .modules.loyalty_card import loyalty_card_bp
    app.register_blueprint(loyalty_card_bp)

    from .modules.porosia_ai import porosia_ai_bp
    app.register_blueprint(porosia_ai_bp)

    return app

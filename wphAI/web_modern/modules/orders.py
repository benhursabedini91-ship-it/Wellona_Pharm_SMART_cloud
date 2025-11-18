from flask import Blueprint, render_template_string
bp = Blueprint('orders', __name__)
@bp.route('/orders')
def page():
    return render_template_string('<h2 style="margin:24px 0">Auto Order</h2><p>Placeholder – këtu vjen paneli i porosive (CSV approve → gjenerim).</p>')

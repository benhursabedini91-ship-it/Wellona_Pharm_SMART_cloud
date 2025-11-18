from flask import Blueprint, render_template_string
bp = Blueprint('admin', __name__)
@bp.route('/admin')
def page():
    return render_template_string('<h2 style="margin:24px 0">Admin</h2><p>Placeholder – konfigurime, environment, logs.</p>')

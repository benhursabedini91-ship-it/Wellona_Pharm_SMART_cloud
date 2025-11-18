from flask import Blueprint, render_template_string
bp = Blueprint('finance', __name__)
@bp.route('/finance')
def page():
    return render_template_string('<h2 style="margin:24px 0">Finance</h2><p>Placeholder – faturat, pagesat, limiti furnitorëve.</p>')

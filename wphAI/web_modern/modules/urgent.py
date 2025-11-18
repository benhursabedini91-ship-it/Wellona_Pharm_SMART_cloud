from flask import Blueprint, render_template_string
bp = Blueprint('urgent', __name__)
@bp.route('/urgent')
def page():
    return render_template_string('<h2 style="margin:24px 0">Urgjencë &lt;3 ditë</h2><p>Placeholder – listë artikujsh nga ops.article_urgency.</p>')

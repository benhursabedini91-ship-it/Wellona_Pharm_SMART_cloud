"""Rrugët për modulin Faktura AI (CSV + XML import)."""
from flask import render_template, request, jsonify, send_from_directory
from . import faktura_ai_bp
from .services import parse_invoices_csv, send_invoices_to_erp
from .sopharma_to_erp import parse_sopharma_xml, insert_kalkulacija, MP_CONFIG, DB_DEFAULTS
import os
import json
import datetime
import psycopg2


def _env_or(name, default=None):
    v = os.getenv(name)
    return v if v not in (None, "") else default

DB_CFG = {
    'dbname': _env_or('WPH_DB_NAME', 'wph_ai'),
    'user': _env_or('WPH_DB_USER', 'postgres'),
    'password': _env_or('WPH_DB_PASS', ''),
    'host': _env_or('WPH_DB_HOST', '127.0.0.1'),
    'port': int(_env_or('WPH_DB_PORT', '5432')),
    'application_name': _env_or('WPH_DB_APP', 'wphAI_faktura_api'),
}

def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)
    return p

def dtstamp():
    return datetime.datetime.now  fr().strftime('%Y%m%d_%H%M%S')

def to_number(val, default=0):
    """Convert string to number, return default if conversion fails."""
    if val is None or val == '':
        return default
    try:
        # Handle comma as decimal separator
        val_str = str(val).replace(',', '.')
        return float(val_str)
    except (ValueError, TypeError):
        return default


@faktura_ai_bp.route('/faktura')
def index():
    return "<h1>Faktura AI Module</h1>"


@faktura_ai_bp.route('/faktura/import', methods=['GET', 'POST'])
def import_invoices():
    message = None
    result = None
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            message = 'Ju lutem zgjidhni një skedar CSV.'
        elif not file.filename.lower().endswith('.csv'):
            message = 'Formati i mbështetur aktualisht: CSV.'
        else:
            try:
                invoices = parse_invoices_csv(file.stream)
                result = send_invoices_to_erp(invoices)
                message = f"U përpunuan {result['processed']} rreshta, {result['invoices']} fatura (me {result['errors']} gabime)."
            except Exception as e:
                message = f"Gabim gjatë përpunimit: {e}"
    return render_template('import.html', module_title='Import i Faturave', message=message, result=result)


@faktura_ai_bp.route('/api/faktura/import', methods=['POST'])
def api_import_invoices():
    file = request.files.get('file')
    dry_run = request.args.get('dry_run', '1') == '1'
    if not file or file.filename == '':
        return jsonify({'ok': False, 'error': 'Ju lutem ngarkoni një skedar CSV me emër.'}), 400
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'ok': False, 'error': 'Formati i mbështetur: CSV.'}), 400
    try:
        invoices = parse_invoices_csv(file.stream)
        summary = send_invoices_to_erp(invoices, dry_run=dry_run)
        return jsonify({'ok': True, 'summary': summary})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@faktura_ai_bp.route('/api/faktura/xml/dry-run', methods=['POST'])
def api_xml_dry_run():
    """Bën parse të XML (Sopharma / UBL) dhe kthen përmbledhje pa shkruar në DB."""
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'ok': False, 'error': 'Ngarko skedarin XML.'}), 400
    if not file.filename.lower().endswith('.xml'):
        return jsonify({'ok': False, 'error': 'Kërkohet format XML.'}), 400
    try:
        # Lexo stream-in në memorie për parse
        content = file.read()
        import io
        tmp = io.BytesIO(content)
        header, items = parse_sopharma_xml(tmp)
        resp = {
            'ok': True,
            'header': {
                'broj_faktura': header.get('broj_faktura'),
                'dobavljac': header.get('dobavljac'),
                'datum': header.get('datum').strftime('%Y-%m-%d') if header.get('datum') else None,
                'total_neto': float(header.get('total_neto', 0)),
                'cash_discount': float(header.get('cash_discount', 0)),
                'payable_amount': float(header.get('payable_amount', 0)),
                'valuta_datum': header.get('valuta_datum').strftime('%Y-%m-%d') if header.get('valuta_datum') else None,
            },
            'counts': {
                'items': len(items)
            }
        }
        return jsonify(resp)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@faktura_ai_bp.route('/api/faktura/list', methods=['GET'])
def api_faktura_list():
    """
    📋 List processed invoices
    
    Query params:
      - date: YYYYMMDD (default: today)
    
    Returns: [{invoice_no, supplier, items, status, files}, ...]
    """
    try:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'wphAI', 'out', 'faktura')
        date_str = request.args.get('date', datetime.datetime.now().strftime('%Y%m%d'))
        out_day = os.path.join(base, date_str)
        
        if not os.path.isdir(out_day):
            return jsonify({"invoices": []})
        
        # Group files by invoice_no prefix
        invoices = {}
        for fn in os.listdir(out_day):
            if fn.endswith('_header.csv'):
                inv_id = fn.replace('_header.csv', '')
                invoices[inv_id] = {
                    'invoice_no': inv_id,
                    'files': {
                        'header': os.path.join(out_day, fn),
                        'items': os.path.join(out_day, f'{inv_id}_items.csv')
                    }
                }
                
                # Read header to get supplier
                try:
                    with open(os.path.join(out_day, fn), 'r', encoding='utf-8') as f:
                        import csv
                        reader = csv.DictReader(f)
                        row = next(reader, {})
                        invoices[inv_id]['supplier'] = row.get('supplier', '')
                        invoices[inv_id]['invoice_date'] = row.get('invoice_date', '')
                except Exception:
                    pass
                
                # Count items
                try:
                    with open(os.path.join(out_day, f'{inv_id}_items.csv'), 'r', encoding='utf-8') as f:
                        invoices[inv_id]['items'] = sum(1 for _ in f) - 1  # exclude header
                except Exception:
                    invoices[inv_id]['items'] = 0
        
        return jsonify({"invoices": list(invoices.values())})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

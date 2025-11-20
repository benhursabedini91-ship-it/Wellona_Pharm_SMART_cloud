"""
Fiscal Bills Web UI - Test & Monitor Interface
Flask web app për të testuar dhe monitoruar faturat fiskale.
"""
import os
import sys
import json
import datetime as dt
import glob
from flask import Flask, render_template, request, jsonify, send_file
from waitress import serve

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from efaktura_client import make_session, list_fiscal_bills_for_date, get_fiscal_bill
from check_fiscal_alarm import check_recent_days, find_consecutive_zeros

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

STAGING_DIR = os.path.join(os.path.dirname(__file__), 'staging', 'fiscal_bills')
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')


@app.route('/')
def index():
    return render_template('fiscal_dashboard.html')


@app.route('/api/fetch-by-date', methods=['POST'])
def fetch_by_date():
    """Fetch fiscal bills për një datë specifike."""
    try:
        data = request.get_json()
        date_str = data.get('date')
        if not date_str:
            return jsonify({'error': 'Date required'}), 400
        
        date_obj = dt.date.fromisoformat(date_str)
        s = make_session()
        bills = list_fiscal_bills_for_date(s, date_obj)
        
        count = len(bills)
        saved = []
        
        os.makedirs(STAGING_DIR, exist_ok=True)
        
        for bill in bills:
            bill_num = bill.get('fiscalBillNumber') or bill.get('number', 'UNKNOWN')
            try:
                full = get_fiscal_bill(s, bill_num)
                fpath = os.path.join(STAGING_DIR, f"FB_{bill_num}.json")
                with open(fpath, 'w', encoding='utf-8') as f:
                    json.dump(full, f, ensure_ascii=False, indent=2)
                saved.append(bill_num)
            except Exception as e:
                saved.append(f"ERROR:{bill_num}")
        
        return jsonify({
            'success': True,
            'date': date_str,
            'count': count,
            'saved': len([s for s in saved if not s.startswith('ERROR:')]),
            'bills': saved
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fetch-by-number', methods=['POST'])
def fetch_by_number():
    """Fetch një faturë specifike me numër."""
    try:
        data = request.get_json()
        number = data.get('number')
        if not number:
            return jsonify({'error': 'Fiscal bill number required'}), 400
        
        s = make_session()
        bill_data = get_fiscal_bill(s, number)
        
        os.makedirs(STAGING_DIR, exist_ok=True)
        fpath = os.path.join(STAGING_DIR, f"FB_{number}.json")
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(bill_data, f, ensure_ascii=False, indent=2)
        
        total = bill_data.get('totalAmount') or bill_data.get('TotalAmount')
        issue_dt = bill_data.get('issueDate') or bill_data.get('IssueDate')
        
        return jsonify({
            'success': True,
            'number': number,
            'total': total,
            'issueDate': issue_dt,
            'saved': fpath
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/check-alarm', methods=['GET'])
def check_alarm():
    """Kontrollon historikun për zero bills alarm."""
    try:
        history = check_recent_days(days_back=7)
        consecutive = find_consecutive_zeros(history)
        
        return jsonify({
            'success': True,
            'consecutive_zeros': consecutive,
            'threshold': 2,
            'alarm_active': consecutive >= 2,
            'history': [
                {
                    'date': d.isoformat(),
                    'count': c,
                    'status': 'OK' if c > 0 else ('API_ERROR' if c == -1 else 'ZERO')
                }
                for d, c in history
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/list-files', methods=['GET'])
def list_files():
    """Liston të gjitha FB_*.json files në staging."""
    try:
        pattern = os.path.join(STAGING_DIR, 'FB_*.json')
        files = glob.glob(pattern)
        
        result = []
        for fpath in files:
            fname = os.path.basename(fpath)
            size = os.path.getsize(fpath)
            mtime = dt.datetime.fromtimestamp(os.path.getmtime(fpath))
            result.append({
                'name': fname,
                'size': size,
                'modified': mtime.isoformat()
            })
        
        return jsonify({
            'success': True,
            'count': len(result),
            'files': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/parse-lines', methods=['POST'])
def parse_lines():
    """Ekzekuton parse_fiscal_lines.py dhe kthen CSV path."""
    try:
        import subprocess
        script = os.path.join(os.path.dirname(__file__), 'parse_fiscal_lines.py')
        result = subprocess.run(
            ['python', script],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        output = result.stdout + result.stderr
        
        # Gjej CSV path nga output
        csv_path = None
        for line in output.split('\n'):
            if 'fiscal_lines_' in line and '.csv' in line:
                csv_path = line.split('Output:')[-1].strip()
                break
        
        return jsonify({
            'success': result.returncode == 0,
            'output': output,
            'csv_path': csv_path
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/guard-status', methods=['GET'])
def guard_status():
    """Kthen statusin e guard files."""
    guards_dir = os.path.join(os.path.dirname(__file__), 'guards')
    allow_file = os.path.join(guards_dir, 'ALLOW_DB_WRITE.flag')
    confirm_file = os.path.join(guards_dir, 'REQUIRE_MANUAL_CONFIRM.flag')
    
    return jsonify({
        'allow_db_write': os.path.exists(allow_file),
        'require_confirm': os.path.exists(confirm_file),
        'status': 'DB writes blocked' if not os.path.exists(allow_file) else (
            'DB writes require manual confirm' if os.path.exists(confirm_file) else
            'DB writes enabled (no confirm)'
        )
    })


@app.route('/health')
def health():
    return jsonify({'status': 'OK', 'timestamp': dt.datetime.now().isoformat()})


if __name__ == '__main__':
    port = int(os.getenv('FISCAL_WEB_PORT', '5556'))
    print(f"Starting Fiscal Bills Web UI on http://localhost:{port}")
    serve(app, host='0.0.0.0', port=port)

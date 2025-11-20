from pathlib import Path

p = r"C:\\Wellona\\wphAI\\web_modern\\app_v2.py"
s = Path(p).read_text(encoding="utf-8")
marker = "\nif __name__ == \"__main__\":"
ins = (
    "\n\n@app.errorhandler(500)\n"
    "def handle_500(e):\n"
    "    # Graceful fallback when eb_inventory_current is missing: return empty list for /api/orders\n"
    "    try:\n"
    "        path = request.path\n"
    "        text = str(e)\n"
    "    except Exception:\n"
    "        path = ''\n"
    "        text = ''\n"
    "    if path.startswith('/api/orders') and 'eb_inventory_current' in text:\n"
    "        return jsonify([]), 200\n"
    "    return jsonify({ 'error': text or 'internal error' }), 500\n"
)
idx = s.find(marker)
if idx == -1:
    raise SystemExit('marker not found')
Path(p).write_text(s[:idx] + ins + s[idx:], encoding='utf-8')
print('Injected 500 error handler with fallback for /api/orders')

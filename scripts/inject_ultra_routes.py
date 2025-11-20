from pathlib import Path
import os

p = r"C:\\Wellona\\wphAI\\web_modern\\app_v2.py"
s = Path(p).read_text(encoding="utf-8")
marker = "\nif __name__ == \"__main__\":"
ins = (
    "\n\n@app.get(\"/ui/ultra\")\n"
    "def ui_ultra():\n"
    "    return send_from_directory(os.path.join(os.path.dirname(__file__), \"public\"), \"orders_master_ultra.html\")\n"
    "\n"
    "@app.get(\"/orders/download\")\n"
    "def orders_download():\n"
    "    try:\n"
    "        latest=None\n"
    "        latest_mtime=0.0\n"
    "        for root, dirs, files in os.walk(OUT_DIR):\n"
    "            for fn in files:\n"
    "                if fn.lower().endswith(\".csv\"):\n"
    "                    pth=os.path.join(root, fn)\n"
    "                    m=os.path.getmtime(pth)\n"
    "                    if m>latest_mtime:\n"
    "                        latest_mtime=m\n"
    "                        latest=pth\n"
    "        if not latest:\n"
    "            return jsonify({\"error\":\"no csv found\"}),404\n"
    "        return send_from_directory(os.path.dirname(latest), os.path.basename(latest), as_attachment=True)\n"
    "    except Exception as e:\n"
    "        return jsonify({\"error\": str(e)}),500\n"
)

idx = s.find(marker)
if idx == -1:
    raise SystemExit("marker not found; aborting")

s2 = s[:idx] + ins + s[idx:]
Path(p).write_text(s2, encoding="utf-8")
print("Injected /ui/ultra and /orders/download routes before app.run")

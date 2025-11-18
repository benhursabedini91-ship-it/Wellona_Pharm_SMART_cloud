import os
from flask import Flask, jsonify, send_file
from dotenv import load_dotenv
from datetime import datetime
from db import fetch_all

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

app = Flask(__name__)

@app.get("/health")
def health():
    return jsonify({
        "status": "OK",
        "db_host": os.getenv("WPH_DB_HOST",""),
        "db_name": os.getenv("WPH_DB_NAME",""),
        "app_port": int(os.getenv("APP_PORT","8055"))
    })

@app.get("/")
def home():
    return jsonify({"routes": ["/health","/urgent","/orders","/orders/generate"]})

@app.get("/urgent")
def urgent():
    rows = fetch_all("SELECT sifra, name, stock, avg_daily, cover_days, urgent_flag FROM ops.article_urgency WHERE urgent_flag = TRUE ORDER BY cover_days ASC LIMIT 200")
    return jsonify({"count": len(rows), "items": rows})

@app.get("/orders")
def orders():
    rows = fetch_all("SELECT sifra, name, stock, avg_daily, cover_days, min_zaliha, qty_to_order FROM ops.article_status WHERE qty_to_order > 0 ORDER BY qty_to_order DESC LIMIT 500")
    return jsonify({"count": len(rows), "items": rows})

@app.post("/orders/generate")
def generate_order():
    out_dir = os.getenv("WPH_OUT_DIR", r"C:\\Wellona\\wphAI\\out\\orders")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    path = os.path.join(out_dir, f"ORDER_PHOENIX_{ts}.csv")

    rows = fetch_all("SELECT sifra, qty_to_order FROM ops.article_status WHERE qty_to_order > 0 ORDER BY qty_to_order DESC")
    # Phoenix CSV minimal: Sifra;Kolicina
    with open(path, "w", encoding="utf-8") as f:
        f.write("Sifra;Kolicina\n")
        for r in rows:
            f.write(f"{r['sifra']};{int(r['qty_to_order'])}\n")

    return jsonify({"status": "OK", "file": path, "rows": len(rows)})

@app.get("/orders/download")
def download_last():
    out_dir = os.getenv("WPH_OUT_DIR", r"C:\\Wellona\\wphAI\\out\\orders")
    if not os.path.isdir(out_dir):
        return jsonify({"error":"out dir missing"}), 404
    files = sorted([os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.startswith("ORDER_PHOENIX_") and f.endswith(".csv")], reverse=True)
    if not files:
        return jsonify({"error":"no orders found"}), 404
    return send_file(files[0], as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("APP_PORT","8055")), debug=False)

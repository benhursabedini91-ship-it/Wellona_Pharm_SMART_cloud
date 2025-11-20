# Mock server pa DB për zhvillim UI
# Përdor Flask (built-in dev server). Për prodhim përdorni app_v2.py + Waitress.

from flask import Flask, request, jsonify, Response
from pathlib import Path
import csv
import io
import json

app = Flask(__name__)
BASE = Path(__file__).resolve().parent
SAMPLES = BASE / "samples"

# Helper për të lexuar sample JSON

def load_sample(name: str):
    p = SAMPLES / name
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

# /api/orders – kthen JSON ose CSV bazuar në parametrat
@app.get("/api/orders")
def get_orders():
    sales_window = int(request.args.get("sales_window", "30"))
    target_days = int(request.args.get("target_days", "28"))
    include_zero = request.args.get("include_zero", "0")  # "0"/"1"
    q = request.args.get("q", "").strip().lower()
    suppliers = request.args.getlist("supplier")
    download = request.args.get("download")  # csv | xlsx

    # Zgjedh sample sipas filtrave më të zakonshëm
    data = load_sample("api_orders_sample.json")

    # Nëse filtrohet sipas furnitorit (p.sh. PHOENIX) – përdor skedarin specifik
    if suppliers and all(s.upper() == "PHOENIX" for s in suppliers):
        phoenix = SAMPLES / "api_orders_phoenix.json"
        if phoenix.exists():
            data = load_sample("api_orders_phoenix.json")

    # Nëse kërkohet q ~ "para" – përdor sample search
    if q and "para" in q:
        search = SAMPLES / "api_orders_search_para.json"
        if search.exists():
            data = load_sample("api_orders_search_para.json")

    # Simulo filtrimin include_zero (nëse 0 – hiq rreshtat me avg_daily_sales==0)
    if include_zero == "0":
        data = [r for r in data if float(r.get("avg_daily_sales", 0) or 0) > 0]

    # Simulo efektin e sales_window duke shtuar fusha të llogaritura në UI
    # (UI tashmë llogarit AVG/30D dhe AVG/WINDOW në klient)

    if download == "csv":
        # Shkarko si CSV
        if not data:
            return Response("", mimetype="text/csv")
        headers = list(data[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers, delimiter=',')
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        resp = Response(buf.getvalue(), mimetype="text/csv")
        resp.headers["Content-Disposition"] = "attachment; filename=orders.csv"
        return resp

    if download == "xlsx":
        # Nuk implementohet në mock – jep 501
        return jsonify({"error":"XLSX download not implemented in mock"}), 501

    return jsonify(data)


if __name__ == "__main__":
    # Nis serverin në portin 8055 që të përputhet me UI-në
    app.run(host="127.0.0.1", port=8055, debug=True)

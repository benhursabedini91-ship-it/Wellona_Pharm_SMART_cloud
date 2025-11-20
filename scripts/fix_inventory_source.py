from pathlib import Path
import re

p = r"C:\\Wellona\\wphAI\\web_modern\\app_v2.py"
s = Path(p).read_text(encoding="utf-8")

# Replace eb_inventory_current with stg.stock_on_hand (qty AS stock)
s = s.replace(
    "SELECT sifra, on_hand AS stock FROM eb_inventory_current",
    "SELECT sifra, qty AS stock FROM stg.stock_on_hand"
)

# Remove the 500 error handler line mentioning eb_inventory_current since we are fixing at source
s = re.sub(
    r"if path\.startswith\('/api/orders'\) and 'eb_inventory_current' in text:\n\s+return jsonify\(\[\]\), 200\n",
    "",
    s
)

Path(p).write_text(s, encoding="utf-8")
print("Fixed inventory source: eb_inventory_current → stg.stock_on_hand (qty AS stock)")

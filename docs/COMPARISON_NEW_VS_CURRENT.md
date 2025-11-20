# KRAHASIM: Skrip i Ri vs. Sistemi Aktual

**Data:** 2025-11-05  
**Qëllimi:** Vlerësim i plotësisë dhe krahasim parametrash

---

## 📊 PËRMBLEDHJE E SHPEJTË

| Aspekt | Sistemi Aktual (web_modern) | Skrip i Ri (webapp_final) | Fitues |
|--------|------------------------------|---------------------------|---------|
| **Parametra API** | ✅ 4 (target_days, sales_window, include_zero, q) | ✅ 5 (+ suppliers[]) | **I RI** 🏆 |
| **Export Format** | ❌ Vetëm JSON | ✅ JSON + CSV + XLSX | **I RI** 🏆 |
| **Healthcheck** | ⚠️ Basic | ✅ Advanced (/api/health/db) | **I RI** 🏆 |
| **UI** | ✅ Complex (Tailwind, features) | ⚠️ Simple (dark, minimal) | **AKTUAL** |
| **DB Filtering** | ❌ Client-side | ✅ Server-side (suppliers IN DB) | **I RI** 🏆 |
| **Migration Tool** | ❌ Manual SQL | ✅ db_migrate.py | **I RI** 🏆 |
| **Deployment** | ⚠️ Manual | ✅ bootstrap.sh/ps1 + Makefile | **I RI** 🏆 |
| **Connection Pooling** | ❌ Naïve | ✅ Thread-local (_thread.conn) | **I RI** 🏆 |
| **Error Handling** | ⚠️ Basic | ✅ Better (500 responses) | **I RI** 🏆 |

**REZULTAT:** Skripi i ri është **më i plotë** në backend/infrastrukturë, por UI-ja aktuale është **më e pasur**.

---

## 1️⃣ PARAMETRAT API

### Sistemi Aktual (`web_modern/app_v2.py`)

```python
@app.get("/api/orders")
def api_orders():
    target_days = int(request.args.get("target_days", 28))
    sales_window = int(request.args.get("sales_window", 60))
    include_zero = (request.args.get("include_zero", "0") == "1")
    search_query = request.args.get("q", "").strip() or None
    
    rows = fetch_all(
        "SELECT * FROM wph_core.get_orders(%s, %s, %s, %s)",
        [target_days, sales_window, include_zero, search_query]
    )
    return jsonify(rows)
```

**Parametrat:**
- ✅ `target_days`: 28 (default)
- ✅ `sales_window`: 60 (default)
- ✅ `include_zero`: FALSE (default)
- ✅ `q`: NULL (search query)

**Mungon:**
- ❌ `suppliers`: Filtrim për furnitorë (bëhet client-side në UI)

---

### Skripi i Ri (`webapp_final/app.py`)

```python
def _parse_query():
    target_days = int(request.args.get("target_days", 28))
    sales_window = int(request.args.get("sales_window", 30))
    include_zero = (request.args.get("include_zero", "0") == "1")
    q = (request.args.get("q", "") or "").strip() or None
    suppliers = request.args.getlist("supplier") or None  # 🆕 MULTI-SELECT
    
    if sales_window not in (7, 30, 60, 180):
        raise ValueError("sales_window duhet të jetë një nga: 7,30,60,180")
    if target_days <= 0 or target_days > 180:
        raise ValueError("target_days duhet të jetë 1..180")
    return target_days, sales_window, include_zero, q, suppliers

@app.get("/api/orders")
def api_orders():
    target_days, sales_window, include_zero, q, suppliers = _parse_query()
    
    rows = fetch_all(
        "SELECT * FROM wph_core.get_orders_v2(%s, %s, %s, %s, %s)",
        [target_days, sales_window, include_zero, q, suppliers],
    )
    # ... CSV/XLSX export logic
```

**Parametrat:**
- ✅ `target_days`: 28 (default, validated 1-180)
- ✅ `sales_window`: 30 (default, validated 7/30/60/180)
- ✅ `include_zero`: FALSE (default)
- ✅ `q`: NULL (search query)
- ✅ `suppliers`: NULL (array, e.g., `?supplier=PHOENIX&supplier=VEGA`) **🆕**

**Përmirësime:**
- ✅ **Validation** (sales_window dhe target_days)
- ✅ **Multi-supplier filtering** (në DB, jo client-side!)
- ✅ **Export formats** (CSV, XLSX)

---

## 2️⃣ EXPORT FORMATS

### Sistemi Aktual

```python
@app.get("/api/orders")
def api_orders():
    # ...
    return jsonify(rows)  # ❌ Vetëm JSON
```

**Mungon:**
- ❌ CSV export
- ❌ XLSX export

**Workaround aktual:** User kopjon nga browser dhe ngjit në Excel (manual!)

---

### Skripi i Ri

```python
@app.get("/api/orders")
def api_orders():
    # ...
    dl = (request.args.get("download") or "").lower()
    
    if dl == "csv":
        # CSV response (UTF-8, headers)
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
        return Response(buf.getvalue(), mimetype="text/csv", ...)
    
    if dl == "xlsx":
        # XLSX response (openpyxl, styled)
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        # ... styling (bold headers, borders, auto-width)
        for r in rows:
            ws.append([r.get(k) for k in headers])
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        return Response(buf.getvalue(), mimetype="...", ...)
    
    return jsonify(rows)  # Default: JSON
```

**URL Examples:**
- JSON: `/api/orders?sales_window=30&target_days=28`
- CSV: `/api/orders?sales_window=30&target_days=28&download=csv`
- XLSX: `/api/orders?sales_window=30&target_days=28&download=xlsx`

**Styling në XLSX:**
- ✅ Bold headers
- ✅ Dark background (#1f2937)
- ✅ White font
- ✅ Auto column width
- ✅ Borders

**Avantazhe:**
- ✅ **1-click download** direkt nga UI
- ✅ **No manual copy-paste**
- ✅ **Professional formatting**

---

## 3️⃣ HEALTHCHECK API

### Sistemi Aktual

```python
# ❌ Nuk ka /api/health endpoint!
# Duhet të kontrollojmë manual me psql ose logs
```

---

### Skripi i Ri

```python
@app.get("/api/health")
def api_health():
    return jsonify({"status": "ok"})

@app.get("/api/health/db")
def api_health_db():
    # 1. Ping DB
    ok = fetch_all("SELECT 1 AS ok")[0]["ok"] == 1
    
    # 2. Check nëse ekziston funksioni
    has_fn = fetch_all(
        "SELECT to_regprocedure('wph_core.get_orders_v2(...)') IS NOT NULL"
    )[0]["exists"]
    
    # 3. Check nëse ekziston mappers table
    has_map = fetch_all(
        "SELECT to_regclass('wph_core.mappers') IS NOT NULL"
    )[0]["exists"]
    
    # 4. Test sample query
    if has_fn:
        try:
            _ = fetch_all("SELECT * FROM wph_core.get_orders_v2(...) LIMIT 1")
            sample_ok = True
        except Exception as e:
            sample_err = str(e)
    
    return jsonify({
        "ok": bool(ok and has_fn),
        "ping": bool(ok),
        "has_function": bool(has_fn),
        "has_mappers": bool(has_map),
        "sample_ok": sample_ok,
        "sample_error": sample_err,
    })
```

**Response Example:**
```json
{
  "ok": true,
  "ping": true,
  "has_function": true,
  "has_mappers": true,
  "sample_ok": true,
  "sample_error": null
}
```

**Use Cases:**
- ✅ CI/CD healthcheck
- ✅ Monitoring (Uptime Robot, DataDog, etc.)
- ✅ Debugging (quick check nëse DB është OK)
- ✅ Migration validation

---

## 4️⃣ DB FILTERING (Suppliers)

### Sistemi Aktual

**Backend:**
```python
# app_v2.py → /api/orders
rows = fetch_all(
    "SELECT * FROM wph_core.get_orders(%s, %s, %s, %s)",
    [target_days, sales_window, include_zero, search_query]
)
return jsonify(rows)  # ❌ Kthen të gjithë furnitorët
```

**Frontend:**
```javascript
// orders_ai.html → filtering happens HERE (client-side)
const filteredRows = st.rows.filter(r => {
  // Nëse user ka zgjedhur supplier, filtro
  if (selectedSuppliers.length > 0) {
    return selectedSuppliers.includes(r.supplier_name);
  }
  return true;
});
renderRows(filteredRows);
```

**Problem:**
- ❌ DB kthen 5000 rows, por user dëshiron vetëm 200 (PHOENIX)
- ❌ Waste of bandwidth
- ❌ Slow rendering nëse dataset është i madh

---

### Skripi i Ri

**Backend:**
```python
# app.py → /api/orders
rows = fetch_all(
    "SELECT * FROM wph_core.get_orders_v2(%s, %s, %s, %s, %s)",
    [target_days, sales_window, include_zero, q, suppliers]  # ✅ suppliers[]
)
return jsonify(rows)  # ✅ Vetëm rows që përputhen me suppliers
```

**DB Function:**
```sql
-- db_migrate.py → get_orders_v2
CREATE OR REPLACE FUNCTION wph_core.get_orders_v2(
    p_target_days   INTEGER,
    p_sales_window  INTEGER,
    p_include_zero  BOOLEAN,
    p_search_query  TEXT,
    p_suppliers     TEXT[]  -- 🆕 Array of suppliers
)
RETURNS TABLE (..., supplier_name TEXT)
AS $$
BEGIN
    -- LEFT JOIN me wph_core.mappers
    SELECT ..., m.supplier_name
    FROM wph_core.get_orders(...) b
    LEFT JOIN wph_core.mappers m ON m.sifra = b.sifra
    WHERE ($5 IS NULL OR upper(m.supplier_name) = ANY (
             SELECT upper(x) FROM unnest($5) AS t(x)  -- 🆕 IN clause
          ));
END;
$$;
```

**Frontend:**
```javascript
// orders.html → multi-select
<select id="supplier" multiple>
  <option>PHOENIX</option>
  <option>VEGA</option>
  <option>SOPHARMA</option>
</select>

// JavaScript
const params = new URLSearchParams({...});
for (const s of getSelectedSuppliers()) {
  params.append("supplier", s);  // ?supplier=PHOENIX&supplier=VEGA
}
fetch(`/api/orders?${params.toString()}`);
```

**Avantazhe:**
- ✅ **Filtering në DB** (më shpejt, më pak bandwidth)
- ✅ **Multi-supplier support** (zgjedh PHOENIX + VEGA njëkohësisht)
- ✅ **Case-insensitive** (upper() në WHERE clause)
- ✅ **NULL-safe** (nëse p_suppliers IS NULL, kthen të gjithë)

---

## 5️⃣ MIGRATION & DEPLOYMENT

### Sistemi Aktual

**Setup:**
1. Ekzekuto manualisht `setup_wphAI.ps1` (krep DB, schemas, seed data)
2. Apliko patches: `baseline_erp_identik_2025-11-01.sql`, `sales_windows_7d_30d.sql`, etc.
3. Refresh MVs: `REFRESH MATERIALIZED VIEW ...`
4. Ekzekuto `sql/query_get_orders_ready_v2.sql` për të krijuar funksionin
5. Nise Flask: `cd web_modern && python app_v2.py`

**Problems:**
- ❌ **Multi-step manual process**
- ❌ **No idempotent migration script**
- ❌ **No dependency tracking** (cili patch duhet të ekzekutohet para cilit)

---

### Skripi i Ri

**Setup:**

**Linux/macOS:**
```bash
cd webapp_final
bash bootstrap.sh  # ✅ Automated!
```

**Windows:**
```powershell
cd webapp_final
./bootstrap.ps1  # ✅ Automated!
```

**bootstrap.sh/ps1:**
```bash
#!/usr/bin/env bash
set -e
python3 -m venv .venv           # 1. Krijo virtual env
. .venv/bin/activate            # 2. Activate
pip install -r requirements.txt # 3. Install dependencies
python db_migrate.py            # 4. Run DB migration ✅
python app.py                   # 5. Nise app
```

**db_migrate.py:**
```python
# Idempotent migration script
SQL_MIGRATION = dedent("""
    CREATE SCHEMA IF NOT EXISTS wph_core;
    CREATE TABLE IF NOT EXISTS wph_core.mappers (...);
    CREATE INDEX IF NOT EXISTS idx_mappers_sifra ON ...;
    CREATE OR REPLACE FUNCTION wph_core.get_orders_v2(...) ...;
""")

def main():
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_MIGRATION)
        conn.commit()
    print("[OK] Migration done.")
```

**Makefile:**
```makefile
venv:
    python -m venv .venv

install: venv
    .venv/bin/pip install -r requirements.txt

run:
    .venv/bin/python app.py

prod:
    .venv/bin/waitress-serve --host=0.0.0.0 --port=8055 app:app

migrate:
    .venv/bin/python db_migrate.py

health:
    curl -s http://127.0.0.1:8055/api/health/db | jq .
```

**Avantazhe:**
- ✅ **1-command setup** (`bash bootstrap.sh`)
- ✅ **Idempotent migrations** (CREATE IF NOT EXISTS, CREATE OR REPLACE)
- ✅ **Automated** (no manual SQL execution)
- ✅ **Production-ready** (`make prod` → Waitress server)
- ✅ **Healthcheck** (`make health`)

---

## 6️⃣ CONNECTION POOLING

### Sistemi Aktual

```python
# web_modern/db.py
def get_conn():
    # ❌ Krijon lidhje të re për çdo request
    return psycopg2.connect(
        host=host, port=port, dbname=dbname, user=user, password=password
    )

def fetch_all(sql, params=None):
    with get_conn() as conn:  # ❌ New connection per call
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [dict(zip(cols, r)) for r in cur.fetchall()]
```

**Problem:**
- ❌ **No connection pooling** → slow (TCP handshake + auth për çdo query)
- ❌ **Resource leak** nëse connection nuk mbyllet siç duhet

---

### Skripi i Ri

```python
# webapp_final/db.py
import threading

_thread = threading.local()  # ✅ Thread-local storage

def _conn():
    c = getattr(_thread, "conn", None)
    if c is None or c.closed:
        c = psycopg2.connect(_dsn())
        c.autocommit = True  # ✅ No manual commit needed
        _thread.conn = c  # ✅ Reuse në të njëjtin thread
    return c

def fetch_all(sql, params=None):
    with _conn().cursor(cursor_factory=factory) as c:  # ✅ Reused connection
        c.execute(sql, params or [])
        return [dict(r) for r in c.fetchall()]
```

**Avantazhe:**
- ✅ **Connection reuse** në të njëjtin thread (1 connection per Flask worker)
- ✅ **Autocommit** (no manual `conn.commit()`)
- ✅ **Thread-safe** (çdo thread ka connection-in e vet)
- ✅ **Lazy connection** (krijohet vetëm kur duhet)

**Note:** Për production me Waitress/Gunicorn, çdo worker ka thread pool → çdo thread ka 1 connection.

---

## 7️⃣ UI COMPARISON

### Sistemi Aktual (`web_modern/public/orders_ai.html`)

**Features:**
- ✅ **Tailwind CSS** (modern design)
- ✅ **Lucide icons**
- ✅ **Dark mode toggle** (button + localStorage)
- ✅ **Skeleton loader** (shimmer effect)
- ✅ **Toast notifications** (success/error messages)
- ✅ **KPI dashboard** (items count, total qty, total value)
- ✅ **Editable qty/pack** (inline input fields)
- ✅ **Checkbox selection** (select rows për order)
- ✅ **POST order** endpoint (approved_by, CSV generation)
- ✅ **Download orders** (nga `/download` endpoint)
- ✅ **Responsive** (mobile-friendly)

**Code size:** ~359 lines

---

### Skripi i Ri (`webapp_final/static/orders.html`)

**Features:**
- ✅ **Dark theme** (hardcoded, no toggle)
- ✅ **Multi-supplier filter** (select multiple)
- ✅ **CSV/XLSX download buttons** (direct links)
- ✅ **KPI dashboard** (items count, total qty)
- ✅ **Error display** (red text)
- ✅ **Fetch button**

**Missing:**
- ❌ No skeleton loader
- ❌ No toast notifications
- ❌ No editable fields
- ❌ No checkbox selection
- ❌ No POST order
- ❌ No dark mode toggle
- ❌ No icons
- ❌ Not responsive

**Code size:** ~130 lines (më i thjeshtë, por më pak features)

---

## 8️⃣ ERROR HANDLING

### Sistemi Aktual

```python
@app.get("/api/orders")
def api_orders():
    # ❌ No try-catch
    # ❌ No parameter validation
    # ❌ 500 error on any exception (Flask default)
    
    target_days = int(request.args.get("target_days", 28))  # ❌ ValueError if not int
    sales_window = int(request.args.get("sales_window", 60))
    # ...
    return jsonify(rows)
```

---

### Skripi i Ri

```python
def _parse_query():
    # ✅ Try-catch në caller
    target_days = int(request.args.get("target_days", 28))
    sales_window = int(request.args.get("sales_window", 30))
    
    # ✅ Validation with clear error messages
    if sales_window not in (7, 30, 60, 180):
        raise ValueError("sales_window duhet të jetë një nga: 7,30,60,180")
    if target_days <= 0 or target_days > 180:
        raise ValueError("target_days duhet të jetë 1..180")
    
    return target_days, sales_window, include_zero, q, suppliers

@app.get("/api/orders")
def api_orders():
    try:
        params = _parse_query()  # ✅ Validation
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400  # ✅ 400 Bad Request
    
    # ✅ DB errors are caught by Flask (500 response)
    rows = fetch_all(...)
    return jsonify(rows)
```

**Avantazhe:**
- ✅ **400 Bad Request** për invalid input (jo 500)
- ✅ **Clear error messages** (`"sales_window duhet të jetë një nga: 7,30,60,180"`)
- ✅ **Validation before DB call** (no wasted DB queries)

---

## 9️⃣ DATABASE FUNCTION COMPARISON

### Sistemi Aktual (`wph_core.get_orders`)

```sql
CREATE OR REPLACE FUNCTION wph_core.get_orders(
    p_target_days   INTEGER DEFAULT 28,
    p_sales_window  INTEGER DEFAULT 30,
    p_include_zero  BOOLEAN DEFAULT FALSE,
    p_search_query  TEXT    DEFAULT NULL
)
RETURNS TABLE (
    sifra, emri, barkod, current_stock, avg_daily_sales,
    days_cover, min_zaliha, qty_to_order
)
-- ❌ NO supplier filtering
```

**Output:** 8 columns

---

### Skripi i Ri (`wph_core.get_orders_v2`)

```sql
CREATE OR REPLACE FUNCTION wph_core.get_orders_v2(
    p_target_days   INTEGER DEFAULT 28,
    p_sales_window  INTEGER DEFAULT 30,
    p_include_zero  BOOLEAN DEFAULT FALSE,
    p_search_query  TEXT    DEFAULT NULL,
    p_suppliers     TEXT[]  DEFAULT NULL  -- 🆕
)
RETURNS TABLE (
    sifra, emri, barkod, current_stock, avg_daily_sales,
    days_cover, min_zaliha, qty_to_order,
    supplier_name TEXT  -- 🆕
)
AS $$
DECLARE
    v_has_map BOOLEAN;
BEGIN
    -- Check nëse ekziston mappers table
    v_has_map := to_regclass('wph_core.mappers') IS NOT NULL;
    
    IF v_has_map THEN
        -- JOIN me mappers dhe filtro sipas suppliers
        RETURN QUERY
        SELECT b.*, m.supplier_name
        FROM wph_core.get_orders(...) b
        LEFT JOIN wph_core.mappers m ON m.sifra = b.sifra
        WHERE ($5 IS NULL OR upper(m.supplier_name) = ANY (
                 SELECT upper(x) FROM unnest($5) AS t(x)
              ));
    ELSE
        -- Fallback: kthen pa supplier_name
        RETURN QUERY
        SELECT b.*, NULL::TEXT AS supplier_name
        FROM wph_core.get_orders(...) b;
    END IF;
END;
$$;
```

**Output:** 9 columns (+ supplier_name)

**Avantazhe:**
- ✅ **Backward compatible** (nëse mappers nuk ekziston, funksionon prapë)
- ✅ **Supplier filtering në DB** (WHERE clause me ANY)
- ✅ **Case-insensitive** (upper())
- ✅ **NULL-safe** (nëse p_suppliers IS NULL, kthen të gjithë)
- ✅ **Reuses existing function** (`wph_core.get_orders`)

---

## 🔟 REQUIREMENTS & DEPENDENCIES

### Sistemi Aktual

```txt
# web_modern/requirements.txt (partial)
Flask>=3.0
python-dotenv>=1.0
psycopg2-binary>=2.9
waitress>=3.0
# ❌ No openpyxl (no XLSX export)
```

---

### Skripi i Ri

```txt
# webapp_final/requirements.txt
Flask>=3.0
python-dotenv>=1.0
psycopg2-binary>=2.9
waitress>=3.0
openpyxl>=3.1  # 🆕 For XLSX export
```

---

## 📋 REKOMANDIME

### Çfarë të mbajmë nga sistemi aktual:

1. ✅ **UI-ja e pasur** (`orders_ai.html`)
   - Tailwind CSS
   - Dark mode toggle
   - Skeleton loader
   - Toast notifications
   - Editable fields
   - POST order functionality

2. ✅ **Funksioni bazë** (`wph_core.get_orders`)
   - Dynamic MV selection
   - Min zaliha lookup
   - Formula e porosisë

3. ✅ **MVs dhe patches** (janë stabile dhe të verifikuara)

---

### Çfarë të integrojmë nga skripi i ri:

1. ✅ **`wph_core.get_orders_v2`** (supplier filtering në DB)
   ```sql
   -- Shto këtë në sql/query_get_orders_ready_v3.sql
   CREATE OR REPLACE FUNCTION wph_core.get_orders_v2(...)
   ```

2. ✅ **CSV/XLSX export** (shto në `web_modern/app_v2.py`)
   ```python
   def _xlsx_response(rows):
       wb = Workbook()
       # ... styling logic
   
   @app.get("/api/orders")
   def api_orders():
       # ...
       dl = request.args.get("download")
       if dl == "csv": return _csv_response(rows)
       if dl == "xlsx": return _xlsx_response(rows)
       return jsonify(rows)
   ```

3. ✅ **Healthcheck** (`/api/health/db`)
   ```python
   @app.get("/api/health/db")
   def api_health_db():
       ok = fetch_all("SELECT 1")[0]["ok"] == 1
       has_fn = fetch_all("SELECT to_regprocedure(...)")
       # ...
   ```

4. ✅ **Parameter validation**
   ```python
   def _parse_query():
       # ... validation logic
       if sales_window not in (7,30,60,180):
           raise ValueError("...")
   ```

5. ✅ **Thread-local connection** (në `web_modern/db.py`)
   ```python
   import threading
   _thread = threading.local()
   
   def _conn():
       c = getattr(_thread, "conn", None)
       if c is None or c.closed:
           c = psycopg2.connect(...)
           _thread.conn = c
       return c
   ```

6. ✅ **`wph_core.mappers` table**
   ```sql
   -- Shto në sql/010_wph_core.sql
   CREATE TABLE IF NOT EXISTS wph_core.mappers (
       sifra TEXT,
       supplier_name TEXT
   );
   CREATE INDEX idx_mappers_sifra ON wph_core.mappers(sifra);
   ```

7. ✅ **db_migrate.py** (idempotent migration tool)
   ```python
   # Krep bin/db_migrate.py
   def main():
       with psycopg2.connect(dsn) as conn:
           cur.execute(SQL_MIGRATION)
           conn.commit()
   ```

8. ✅ **bootstrap.ps1** (automated setup për Windows)
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python bin/db_migrate.py
   cd web_modern && python app_v2.py
   ```

9. ✅ **Makefile** (Linux/macOS convenience)
   ```makefile
   venv:
       python3 -m venv .venv
   
   install: venv
       .venv/bin/pip install -r requirements.txt
   
   migrate:
       .venv/bin/python bin/db_migrate.py
   
   run:
       cd web_modern && ../.venv/bin/python app_v2.py
   ```

---

### Çfarë të hedhim:

1. ❌ **UI e re (orders.html)** nga webapp_final
   - Më e thjeshtë, por më pak features
   - Sistemi aktual është më i mirë

2. ❌ **db.py i ri** (mund të integrojmë vetëm thread-local logic)

3. ❌ **app.py i ri** (mbajmë app_v2.py dhe i shtojmë features)

---

## 🎯 PLANI I INTEGRIMIT (HYBRID APPROACH)

### Faza 1: Backend Enhancements (Low Risk)

**Files to update:**

1. **`sql/query_get_orders_ready_v3.sql`** (NEW)
   - Copy `wph_core.get_orders_v2` nga webapp_final
   - Wrapper around existing `wph_core.get_orders`

2. **`sql/010_wph_core.sql`**
   - Shto `wph_core.mappers` table
   - Indexes: `idx_mappers_sifra`, `idx_mappers_supplier_upper`

3. **`bin/db_migrate.py`** (NEW)
   - Idempotent migration script
   - Run before app startup

4. **`web_modern/db.py`**
   - Replace `get_conn()` me thread-local version
   - Keep existing `fetch_all()` signature

5. **`web_modern/app_v2.py`**
   - Add `_parse_query()` with validation
   - Add `_csv_response()` and `_xlsx_response()`
   - Add `/api/health/db` endpoint
   - Update `/api/orders` to support `suppliers[]` and `download`

6. **`requirements.txt`**
   - Add `openpyxl>=3.1`

7. **`bootstrap.ps1`** (NEW)
   - Automated setup për Windows

8. **`Makefile`** (NEW)
   - Convenience commands për dev

---

### Faza 2: UI Enhancements (Medium Risk)

**Files to update:**

1. **`web_modern/public/orders_ai.html`**
   - Add multi-supplier filter (select multiple)
   - Add CSV/XLSX download buttons
   - Update `fetchOrders()` to pass `suppliers[]`
   - Update render logic to show `supplier_name` column

---

### Faza 3: Testing & Validation

1. ✅ Run `python bin/db_migrate.py` (verify tables/functions)
2. ✅ Test `/api/health/db` (verify all checks pass)
3. ✅ Test `/api/orders?supplier=PHOENIX&supplier=VEGA` (verify filtering)
4. ✅ Test `/api/orders?...&download=csv` (verify CSV format)
5. ✅ Test `/api/orders?...&download=xlsx` (verify XLSX styling)
6. ✅ Manual QA në UI (select suppliers, download buttons)

---

## ✅ PËRFUNDIM

**Skripi i ri (webapp_final) është më i plotë në:**
- ✅ Backend architecture (validation, exports, healthcheck)
- ✅ Deployment automation (bootstrap, Makefile, migrations)
- ✅ DB filtering (suppliers në DB, jo client-side)
- ✅ Connection handling (thread-local pooling)

**Sistemi aktual (web_modern) është më i mirë në:**
- ✅ UI/UX (Tailwind, dark mode, toast, skeleton)
- ✅ Feature richness (editable fields, POST orders, responsive)

**Qasja optimale:**
Integrimi hybrid - **marrim backend features nga webapp_final dhe i shtojmë te web_modern UI.**

---

**REKOMANDIM FINAL:** Integrimi duhet bërë në 3 faza:
1. **Backend first** (low risk, no UI changes)
2. **UI enhancements** (add supplier filter + download buttons)
3. **Testing & rollout** (verify në dev, pastaj production)

---

**END OF COMPARISON**

# WPH_AI - Web App Execution Flow

**Data:** 2025-11-05  
**Purpose:** Dokumentim i plotë i ekzekutimit nga UI → Backend → Database

---

## 🔄 FLOW DIAGRAM (UI → DB)

```
┌──────────────────────────────────────────────────────────────┐
│  1. USER INTERACTION (Browser)                               │
├──────────────────────────────────────────────────────────────┤
│  File: web_modern/public/orders_ai.html                      │
│                                                                │
│  User actions:                                                │
│  • Zgjedh sales_window: 7/30/60/180 ditë                     │
│  • Zgjedh target_days: 6-100 ditë                            │
│  • Toggle include_zero: 0/1                                   │
│  • Shkruan query në search box (optional)                    │
│  • Click "RUN Analiza"                                        │
│                                                                │
│  JavaScript function:                                         │
│  ┌────────────────────────────────────────────────┐          │
│  │ async function fetchOrders() {                 │          │
│  │   const params = new URLSearchParams({        │          │
│  │     sales_window: 30,                          │          │
│  │     target_days: 28,                           │          │
│  │     include_zero: 0,                           │          │
│  │     q: 'aspirin'                               │          │
│  │   });                                          │          │
│  │   const res = await fetch(                     │          │
│  │     `/api/orders?${params.toString()}`        │          │
│  │   );                                           │          │
│  │   const data = await res.json();              │          │
│  │   renderRows(data);                            │          │
│  │ }                                              │          │
│  └────────────────────────────────────────────────┘          │
│                                                                │
│  HTTP GET Request:                                            │
│  → GET /api/orders?sales_window=30&target_days=28&           │
│         include_zero=0&q=aspirin                              │
│                                                                │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  2. FLASK WEB SERVER (Python)                                │
├──────────────────────────────────────────────────────────────┤
│  File: web_modern/app_v2.py                                   │
│                                                                │
│  Flask route handler:                                         │
│  ┌────────────────────────────────────────────────┐          │
│  │ @app.get("/api/orders")                        │          │
│  │ def api_orders():                              │          │
│  │     # Parse query parameters                   │          │
│  │     target_days = int(request.args.get(        │          │
│  │         "target_days", 28))                    │          │
│  │     sales_window = int(request.args.get(       │          │
│  │         "sales_window", 60))                   │          │
│  │     include_zero = (request.args.get(          │          │
│  │         "include_zero", "0") == "1")           │          │
│  │     search_query = request.args.get(           │          │
│  │         "q", "").strip() or None               │          │
│  │                                                 │          │
│  │     # Call DB helper                           │          │
│  │     rows = fetch_all(                          │          │
│  │         "SELECT * FROM wph_core.get_orders(    │          │
│  │             %s, %s, %s, %s)",                  │          │
│  │         [target_days, sales_window,            │          │
│  │          include_zero, search_query]           │          │
│  │     )                                          │          │
│  │     return jsonify(rows)                       │          │
│  └────────────────────────────────────────────────┘          │
│                                                                │
│  Parameters passed to DB:                                     │
│  • target_days: 28 (INTEGER)                                 │
│  • sales_window: 30 (INTEGER)                                │
│  • include_zero: FALSE (BOOLEAN)                             │
│  • search_query: 'aspirin' (TEXT)                            │
│                                                                │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  3. DATABASE HELPER (Python)                                  │
├──────────────────────────────────────────────────────────────┤
│  File: web_modern/db.py                                       │
│                                                                │
│  Connection & execution:                                      │
│  ┌────────────────────────────────────────────────┐          │
│  │ def fetch_all(sql, params=None):              │          │
│  │     with get_conn() as conn:                   │          │
│  │         with conn.cursor() as cur:             │          │
│  │             cur.execute(sql, params)           │          │
│  │             cols = [d[0] for d in              │          │
│  │                     cur.description]           │          │
│  │             return [dict(zip(cols, r))         │          │
│  │                     for r in cur.fetchall()]   │          │
│  └────────────────────────────────────────────────┘          │
│                                                                │
│  Connection config (from .env):                               │
│  • WPH_DB_HOST=127.0.0.1                                     │
│  • WPH_DB_PORT=5432                                          │
│  • WPH_DB_NAME=wph_ai                                        │
│  • WPH_DB_USER=postgres                                      │
│  • WPH_DB_PASS=<secret>                                      │
│                                                                │
│  SQL executed:                                                │
│  → SELECT * FROM wph_core.get_orders(28, 30, FALSE,          │
│         'aspirin')                                            │
│                                                                │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  4. POSTGRESQL FUNCTION (SQL)                                 │
├──────────────────────────────────────────────────────────────┤
│  File: sql/query_get_orders_ready_v2.sql                     │
│                                                                │
│  Function signature:                                          │
│  ┌────────────────────────────────────────────────┐          │
│  │ CREATE OR REPLACE FUNCTION                     │          │
│  │   wph_core.get_orders(                         │          │
│  │     p_target_days   INTEGER DEFAULT 28,        │          │
│  │     p_sales_window  INTEGER DEFAULT 30,        │          │
│  │     p_include_zero  BOOLEAN DEFAULT FALSE,     │          │
│  │     p_search_query  TEXT    DEFAULT NULL       │          │
│  │   )                                            │          │
│  │ RETURNS TABLE (                                │          │
│  │   sifra            TEXT,                       │          │
│  │   emri             TEXT,                       │          │
│  │   barkod           TEXT,                       │          │
│  │   current_stock    NUMERIC,                    │          │
│  │   avg_daily_sales  NUMERIC,                    │          │
│  │   days_cover       NUMERIC,                    │          │
│  │   min_zaliha       NUMERIC,                    │          │
│  │   qty_to_order     NUMERIC                     │          │
│  │ )                                              │          │
│  └────────────────────────────────────────────────┘          │
│                                                                │
│  STEP 1: Resolve MV name based on sales_window               │
│  ┌────────────────────────────────────────────────┐          │
│  │ IF p_sales_window = 7 THEN                     │          │
│  │   v_mv_name := 'ops._sales_7d'                 │          │
│  │ ELSIF p_sales_window = 30 THEN                 │          │
│  │   v_mv_name := 'ops._sales_30d'                │          │
│  │ ELSIF p_sales_window = 180 THEN                │          │
│  │   v_mv_name := 'ops._sales_180d'               │          │
│  │ ELSE                                           │          │
│  │   v_mv_name := 'ops._sales_30d'  -- default    │          │
│  │ END IF;                                        │          │
│  └────────────────────────────────────────────────┘          │
│  Result: v_mv_name = 'ops._sales_30d'                        │
│                                                                │
│  STEP 2: Build WHERE clause for include_zero                 │
│  ┌────────────────────────────────────────────────┐          │
│  │ IF NOT p_include_zero THEN                     │          │
│  │   v_where_clause := 'AND COALESCE(             │          │
│  │       c.current_stock,0) > 0'                  │          │
│  │ END IF;                                        │          │
│  └────────────────────────────────────────────────┘          │
│  Result: v_where_clause = 'AND COALESCE(...) > 0'            │
│                                                                │
│  STEP 3: Build search pattern for p_search_query             │
│  ┌────────────────────────────────────────────────┐          │
│  │ IF p_search_query IS NOT NULL THEN             │          │
│  │   v_search_sql := 'AND (                       │          │
│  │     LOWER(ar.naziv)  LIKE LOWER($1)            │          │
│  │  OR LOWER(c.sifra)   LIKE LOWER($1)            │          │
│  │  OR LOWER(ar.barkod) LIKE LOWER($1)            │          │
│  │   )'                                           │          │
│  │   v_pattern := '%' || p_search_query || '%'    │          │
│  │ END IF;                                        │          │
│  └────────────────────────────────────────────────┘          │
│  Result: v_pattern = '%aspirin%'                             │
│                                                                │
│  STEP 4: Build & execute dynamic SQL                         │
│  ┌────────────────────────────────────────────────┐          │
│  │ v_sql := format($query$                        │          │
│  │   WITH demand AS (                             │          │
│  │     SELECT sifra, avg_daily, last_sale_date,   │          │
│  │            has_recent_sales, monthly_units     │          │
│  │     FROM %1$I  -- ops._sales_30d               │          │
│  │   ),                                           │          │
│  │   inventory AS (                               │          │
│  │     SELECT sifra, qty AS stock                 │          │
│  │     FROM stg.stock_on_hand                     │          │
│  │   ),                                           │          │
│  │   calc AS (                                    │          │
│  │     SELECT ..., (                              │          │
│  │       SELECT p.min_zaliha                      │          │
│  │       FROM ref.min_zaliha_policy_v2 p          │          │
│  │       WHERE monthly_units >= p.range_from      │          │
│  │         AND (p.range_to IS NULL OR             │          │
│  │              monthly_units <= p.range_to)      │          │
│  │       ORDER BY p.range_from DESC LIMIT 1       │          │
│  │     ) AS min_zaliha                            │          │
│  │     FROM demand d                              │          │
│  │     FULL OUTER JOIN inventory i                │          │
│  │       ON d.sifra = i.sifra                     │          │
│  │   )                                            │          │
│  │   SELECT c.sifra, ar.naziv AS emri,            │          │
│  │          ar.barkod, c.current_stock,           │          │
│  │          c.avg_daily_sales,                    │          │
│  │          ROUND(c.current_stock /               │          │
│  │            NULLIF(c.avg_daily_sales,0), 1)     │          │
│  │            AS days_cover,                      │          │
│  │          COALESCE(c.min_zaliha,0),             │          │
│  │          CEIL(GREATEST(0, GREATEST(            │          │
│  │            COALESCE(c.min_zaliha, 0),          │          │
│  │            CEIL(%2$s * c.avg_daily_sales)      │          │
│  │          ) - c.current_stock))                 │          │
│  │            AS qty_to_order                     │          │
│  │   FROM calc c                                  │          │
│  │   JOIN eb_fdw.artikli ar ON c.sifra=ar.sifra   │          │
│  │   WHERE 1=1 %3$s %4$s                          │          │
│  │   ORDER BY qty_to_order DESC,                  │          │
│  │            days_cover ASC NULLS FIRST          │          │
│  │   LIMIT 5000                                   │          │
│  │ $query$, v_mv_name, p_target_days,             │          │
│  │         v_search_sql, v_where_clause);         │          │
│  │                                                │          │
│  │ IF v_search_sql <> '' THEN                     │          │
│  │   RETURN QUERY EXECUTE v_sql USING v_pattern;  │          │
│  │ ELSE                                           │          │
│  │   RETURN QUERY EXECUTE v_sql;                  │          │
│  │ END IF;                                        │          │
│  └────────────────────────────────────────────────┘          │
│                                                                │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  5. DATABASE VIEWS & TABLES (Read Sources)                   │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  A. ops._sales_30d (Materialized View)                       │
│  ┌────────────────────────────────────────────────┐          │
│  │ SELECT TRIM(artikal) AS sifra,                 │          │
│  │   ROUND(SUM(GREATEST(izlaz,0))/30.0, 6)        │          │
│  │     AS avg_daily,                              │          │
│  │   MAX(CASE WHEN izlaz>0 THEN DATE(datum)       │          │
│  │       END) AS last_sale_date                   │          │
│  │ FROM eb_fdw.artiklikartica                     │          │
│  │ WHERE datum >= CURRENT_DATE - INTERVAL '30d'   │          │
│  │   AND magacin = '101'                          │          │
│  │ GROUP BY TRIM(artikal);                        │          │
│  └────────────────────────────────────────────────┘          │
│  → Returns: sifra, avg_daily, last_sale_date                 │
│  → Refreshed: Nightly @ 02:00                                │
│                                                                │
│  B. stg.stock_on_hand (Materialized View)                    │
│  ┌────────────────────────────────────────────────┐          │
│  │ SELECT TRIM(artikal) AS sifra,                 │          │
│  │   COALESCE(SUM(ulaz - izlaz), 0) AS qty        │          │
│  │ FROM eb_fdw.artiklikartica                     │          │
│  │ WHERE magacin = '101'                          │          │
│  │   AND EXTRACT(YEAR FROM datum)                 │          │
│  │     = EXTRACT(YEAR FROM CURRENT_DATE)          │          │
│  │ GROUP BY TRIM(artikal);                        │          │
│  └────────────────────────────────────────────────┘          │
│  → Returns: sifra, qty (current stock)                       │
│  → Refreshed: Nightly @ 02:00                                │
│                                                                │
│  C. ref.min_zaliha_policy_v2 (Table)                         │
│  ┌────────────────────────────────────────────────┐          │
│  │ range_from │ range_to │ min_zaliha │ note      │          │
│  │────────────┼──────────┼────────────┼───────────│          │
│  │ 0          │ 0        │ 0          │ no move   │          │
│  │ 1          │ 5        │ 2          │ presence  │          │
│  │ 5          │ 10       │ 3          │           │          │
│  │ 10         │ 15       │ 4          │           │          │
│  │ 15         │ 20       │ 5          │           │          │
│  │ 20         │ 30       │ 7          │           │          │
│  │ 30         │ 40       │ 9          │           │          │
│  │ 40         │ 50       │ 11         │           │          │
│  │ 50         │ NULL     │ 14         │ critical  │          │
│  └────────────────────────────────────────────────┘          │
│  → Lookup: monthly_units >= range_from AND                   │
│            (range_to IS NULL OR monthly_units <= range_to)   │
│  → Static table (manual updates only)                        │
│                                                                │
│  D. eb_fdw.artikli (Foreign Table → ERP)                     │
│  ┌────────────────────────────────────────────────┐          │
│  │ Source: ebdata@100.69.251.92:5432              │          │
│  │ SELECT sifra, barkod, naziv, jmj, stanje       │          │
│  │ FROM public.artikli;                           │          │
│  └────────────────────────────────────────────────┘          │
│  → Live read from ERP (PostgreSQL 9.3)                       │
│  → Used for: naziv, barkod lookup                            │
│                                                                │
│  E. eb_fdw.artiklikartica (Foreign Table → ERP)              │
│  ┌────────────────────────────────────────────────┐          │
│  │ Source: ebdata@100.69.251.92:5432              │          │
│  │ SELECT artikal, datum, magacin,                │          │
│  │        ulaz, izlaz                             │          │
│  │ FROM public.artiklikartica;                    │          │
│  └────────────────────────────────────────────────┘          │
│  → Live read from ERP                                        │
│  → Used for: sales & stock calculations (via MVs)            │
│                                                                │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  6. RESULT TRANSFORMATION (SQL → Python → JSON)              │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  PostgreSQL returns rows:                                     │
│  ┌────────────────────────────────────────────────┐          │
│  │ sifra      │ emri           │ barkod  │ ...    │          │
│  │────────────┼────────────────┼─────────┼────────│          │
│  │ '10011005' │ 'ASPIRIN 500'  │ '8601..'│ ...    │          │
│  │ '10011006' │ 'ASPIRIN PLUS' │ '8602..'│ ...    │          │
│  └────────────────────────────────────────────────┘          │
│                                                                │
│  db.py transforms to list of dicts:                           │
│  ┌────────────────────────────────────────────────┐          │
│  │ [                                              │          │
│  │   {                                            │          │
│  │     "sifra": "10011005",                       │          │
│  │     "emri": "ASPIRIN 500",                     │          │
│  │     "barkod": "8601...",                       │          │
│  │     "current_stock": 152.0,                    │          │
│  │     "avg_daily_sales": 6.24,                   │          │
│  │     "days_cover": 24.4,                        │          │
│  │     "min_zaliha": 5,                           │          │
│  │     "qty_to_order": 23                         │          │
│  │   },                                           │          │
│  │   ...                                          │          │
│  │ ]                                              │          │
│  └────────────────────────────────────────────────┘          │
│                                                                │
│  app_v2.py wraps in Flask jsonify():                          │
│  ┌────────────────────────────────────────────────┐          │
│  │ return jsonify(rows)                           │          │
│  └────────────────────────────────────────────────┘          │
│                                                                │
│  HTTP Response:                                               │
│  ┌────────────────────────────────────────────────┐          │
│  │ HTTP/1.1 200 OK                                │          │
│  │ Content-Type: application/json                 │          │
│  │                                                │          │
│  │ [{"sifra":"10011005","emri":"ASPIRIN 500",...}]│          │
│  └────────────────────────────────────────────────┘          │
│                                                                │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  7. UI RENDERING (JavaScript)                                 │
├──────────────────────────────────────────────────────────────┤
│  File: web_modern/public/orders_ai.html                      │
│                                                                │
│  JavaScript processes response:                               │
│  ┌────────────────────────────────────────────────┐          │
│  │ const data = await res.json();                 │          │
│  │ st.rows = data.map(r => ({                     │          │
│  │   sifra: r.sifra,                              │          │
│  │   emri: r.emri || r.name || '',                │          │
│  │   barkod: r.barkod || '',                      │          │
│  │   current_stock: r.current_stock ?? 0,         │          │
│  │   avg_daily_sales: r.avg_daily_sales ?? 0,     │          │
│  │   min_zaliha: r.min_zaliha ?? 0,               │          │
│  │   days_cover: r.days_cover ?? 0,               │          │
│  │   qty_to_order: Math.max(0,                    │          │
│  │     Math.round(r.qty_to_order || 0)),          │          │
│  │   pack_size: Math.max(1,                       │          │
│  │     Math.round(r.pack_size || 1))              │          │
│  │ }));                                           │          │
│  │ renderRows();                                  │          │
│  └────────────────────────────────────────────────┘          │
│                                                                │
│  Renders HTML table:                                          │
│  ┌────────────────────────────────────────────────┐          │
│  │ <table>                                        │          │
│  │   <tr>                                         │          │
│  │     <td>10011005</td>                          │          │
│  │     <td>ASPIRIN 500</td>                       │          │
│  │     <td>152</td>                               │          │
│  │     <td>6.24</td>                              │          │
│  │     <td>24.4</td>                              │          │
│  │     <td>5</td>                                 │          │
│  │     <td>23</td>                                │          │
│  │   </tr>                                        │          │
│  │   ...                                          │          │
│  │ </table>                                       │          │
│  └────────────────────────────────────────────────┘          │
│                                                                │
│  User sees table with:                                        │
│  • Sifra, Emri, Barkod                                        │
│  • Stock aktual                                               │
│  • Shitje ditore                                              │
│  • Cover (ditë)                                               │
│  • Min zaliha                                                 │
│  • Sasi për porosi                                            │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 📁 FILES INVOLVED (në rend ekzekutimi)

| # | File | Role | Language |
|---|------|------|----------|
| 1 | `web_modern/public/orders_ai.html` | UI (Frontend) | HTML/JS |
| 2 | `web_modern/app_v2.py` | Web Server | Python/Flask |
| 3 | `web_modern/db.py` | DB Helper | Python/psycopg2 |
| 4 | `sql/query_get_orders_ready_v2.sql` | Business Logic | SQL/PL/pgSQL |
| 5 | `patches/sales_windows_7d_30d.sql` | Sales MVs | SQL |
| 6 | `patches/baseline_erp_identik_2025-11-01.sql` | Stock MV | SQL |
| 7 | `sql/patch3_min_zaliha_policy_v2.sql` | Policy Table | SQL |
| 8 | `sql/01_fdw_setup.sql` | FDW Setup | SQL |

---

## 🔍 PARAMETRAT (Request → Response)

### Request Parameters (nga UI)
```javascript
// orders_ai.html → line ~294
const params = new URLSearchParams({
  sales_window: 30,      // 7, 30, 60, 180 (zgjedh MV)
  target_days: 28,       // 6-100 (për formula porosie)
  include_zero: 0,       // 0=false, 1=true (filton stock=0)
  q: 'aspirin'          // search query (optional)
});

fetch(`/api/orders?${params.toString()}`);
```

### Flask Route Handler (app_v2.py)
```python
# app_v2.py → line ~135
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

### PostgreSQL Function (query_get_orders_ready_v2.sql)
```sql
-- sql/query_get_orders_ready_v2.sql → line ~12
CREATE OR REPLACE FUNCTION wph_core.get_orders(
    p_target_days   INTEGER DEFAULT 28,
    p_sales_window  INTEGER DEFAULT 30,
    p_include_zero  BOOLEAN DEFAULT FALSE,
    p_search_query  TEXT DEFAULT NULL
)
RETURNS TABLE (
    sifra            TEXT,
    emri             TEXT,
    barkod           TEXT,
    current_stock    NUMERIC,
    avg_daily_sales  NUMERIC,
    days_cover       NUMERIC,
    min_zaliha       NUMERIC,
    qty_to_order     NUMERIC
)
```

### Response Format (JSON)
```json
[
  {
    "sifra": "10011005",
    "emri": "ASPIRIN 500MG",
    "barkod": "8601234567890",
    "current_stock": 152.00,
    "avg_daily_sales": 6.24,
    "days_cover": 24.4,
    "min_zaliha": 5.00,
    "qty_to_order": 23.00
  }
]
```

---

## ⚙️ BUSINESS LOGIC (Formula e porosisë)

### 1. Dynamic MV Selection (në funksion)
```sql
-- Zgjedh MV bazuar në sales_window
IF p_sales_window = 7 THEN
    v_mv_name := 'ops._sales_7d';
ELSIF p_sales_window = 30 THEN
    v_mv_name := 'ops._sales_30d';
ELSIF p_sales_window = 180 THEN
    v_mv_name := 'ops._sales_180d';
ELSE
    v_mv_name := 'ops._sales_30d';  -- default
END IF;
```

### 2. Min Zaliha Lookup
```sql
-- Gjen min_zaliha bazuar në monthly_units (avg_daily*30)
SELECT p.min_zaliha
FROM ref.min_zaliha_policy_v2 p
WHERE monthly_units >= p.range_from
  AND (p.range_to IS NULL OR monthly_units <= p.range_to)
ORDER BY p.range_from DESC
LIMIT 1
```

### 3. Qty To Order Calculation
```sql
-- Formula finale
qty_to_order = CEIL(
  GREATEST(0, 
    GREATEST(
      min_zaliha,
      CEIL(target_days * avg_daily_sales)
    ) - current_stock
  )
)

-- Shembull:
-- min_zaliha = 5
-- target_days = 28
-- avg_daily_sales = 6.24
-- current_stock = 152
-- 
-- qty_to_order = CEIL(GREATEST(0, GREATEST(5, CEIL(28*6.24)) - 152))
--              = CEIL(GREATEST(0, GREATEST(5, 175) - 152))
--              = CEIL(GREATEST(0, 175 - 152))
--              = CEIL(23)
--              = 23
```

---

## 🔄 REFRESH CYCLE (Nightly ETL)

### Schedule
```powershell
# run_nightly_etl.ps1 → runs @ 02:00 daily
REFRESH MATERIALIZED VIEW stg.stock_on_hand;
REFRESH MATERIALIZED VIEW ops._sales_7d;
REFRESH MATERIALIZED VIEW ops._sales_30d;
REFRESH MATERIALIZED VIEW ops._sales_180d;
REFRESH MATERIALIZED VIEW ops.article_status;
```

### Manual Refresh
```powershell
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
& $psql -h 127.0.0.1 -U postgres -d wph_ai -c "
  REFRESH MATERIALIZED VIEW stg.stock_on_hand;
  REFRESH MATERIALIZED VIEW ops._sales_30d;
"
```

---

## 🐛 DEBUGGING TIPS

### 1. Test SQL Function Directly
```sql
-- psql prompt
SELECT * FROM wph_core.get_orders(
    p_target_days := 28,
    p_sales_window := 30,
    p_include_zero := FALSE,
    p_search_query := 'aspirin'
)
LIMIT 10;
```

### 2. Check MV Freshness
```sql
-- Shiko kur u refresh-ua last time
SELECT schemaname, matviewname, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname))
FROM pg_matviews
WHERE schemaname IN ('stg', 'ops')
ORDER BY schemaname, matviewname;
```

### 3. Test API Endpoint
```bash
# curl test (Windows PowerShell)
curl "http://localhost:5000/api/orders?sales_window=30&target_days=28&include_zero=0&q=aspirin"
```

### 4. Flask Logs
```python
# app_v2.py → check terminal output
# Log level set in db.py:
logger.debug("SQL: %s params=%s", sql, params)
```

### 5. Browser DevTools
```javascript
// Console → Network tab
// Check request URL and response
fetch('/api/orders?sales_window=30&target_days=28')
  .then(r => r.json())
  .then(console.log);
```

---

## 📊 PERFORMANCE NOTES

### Query Performance
- **MVs are indexed** on `sifra` (UNIQUE)
- **Foreign tables** (eb_fdw) are NOT indexed locally → use MVs for heavy queries
- **LIMIT 5000** në funksion për të shmangur OOM
- **JOIN on sifra** është i shpejtë (indexed)

### Bottlenecks
1. **FDW queries** (eb_fdw.artiklikartica) → shmang live queries, përdor MVs
2. **Policy lookup** (ref.min_zaliha_policy_v2) → shpejt (9 rows only)
3. **Dynamic SQL** (format + EXECUTE) → minimal overhead

### Optimization Ideas
```sql
-- Krijo indexes për search
CREATE INDEX CONCURRENTLY idx_artikli_naziv_gin 
  ON eb_fdw.artikli USING gin(to_tsvector('simple', naziv));

-- Partial index për active items
CREATE INDEX CONCURRENTLY idx_stock_positive 
  ON stg.stock_on_hand(sifra) WHERE qty > 0;
```

---

## 🚀 DEPLOYMENT CHECKLIST

### Production Readiness
- [ ] Environment variables set në `.env` (WPH_DB_*)
- [ ] PostgreSQL accessible (firewall rules)
- [ ] FDW connection tested (eb_fdw → ebdata)
- [ ] MVs refreshed at least once
- [ ] Indexes created (see patches)
- [ ] Flask app running (Waitress/Gunicorn)
- [ ] Nightly ETL scheduled (Task Scheduler)
- [ ] Logs directory writable (`logs/`)
- [ ] Backup strategy (pg_dump daily)

### Health Check
```bash
# Test DB connection
psql -h 127.0.0.1 -U postgres -d wph_ai -c "SELECT version();"

# Test FDW
psql -h 127.0.0.1 -U postgres -d wph_ai -c "SELECT COUNT(*) FROM eb_fdw.artikli;"

# Test function
psql -h 127.0.0.1 -U postgres -d wph_ai -c "SELECT COUNT(*) FROM wph_core.get_orders(28,30,FALSE,NULL);"

# Test Flask endpoint
curl http://localhost:5000/api/health
```

---

## 📚 RELATED DOCS

- `docs/DATABASE_CONFIGURATION.md` - Full DB schema documentation
- `BASELINE_GUIDE.md` - Baseline setup & MVs
- `docs/ORDER_DECISION_GUIDE.md` - Order formula explained
- `sql/query_get_orders_ready_v2.sql` - Function source code
- `web_modern/README.md` - Web app setup guide

---

**END OF DOCUMENT**

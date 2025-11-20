$env:PGPASSWORD='0262000'; & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -p 5432 -d wph_ai -c "SELECT sifra, supplier_name, price FROM stg.pricefeed WHERE sifra = '10049015' ORDER BY price;"$env:PGPASSWORD='supersqlpedja'; & C:\psql\bin\psql.exe -h 100.69.251.92 -p 5432 -U postgresPedja -d ebdata -c "\dt *stanje* *stock* *zaliha*"$env:PGPASSWORD='supersqlpedja'; & C:\psql\bin\psql.exe -h 100.69.251.92 -p 5432 -U postgresPedja -d ebdata -c "SELECT SUM(CASE WHEN vrstadok IN ('PR','UL') THEN kolicina WHEN vrstadok IN ('IZ','OT') THEN -kolicina ELSE 0 END) as calculated_stock FROM kalkstavke WHERE sifra = '10049015';"$env:PGPASSWORD='supersqlpedja'; & C:\psql\bin\psql.exe -h 100.69.251.92 -p 5432 -U postgresPedja -d ebdata -c "SELECT COUNT(*), SUM(kolicina) FROM kalkstavke WHERE artikal = '10049015' LIMIT 5;"# WPH_AI - Konfigurimi i Databazës

**Data:** 2025-11-05  
**Status:** Dokumentacion i plotë i arkitekturës së databazës

---

## 1. PËRMBLEDHJE E SHKURTËR

WPH_AI përdor **PostgreSQL** si databazë qendrore për të gjitha operacionet:
- **Databaza kryesore:** `wph_ai` (localhost:5432 ose remote)
- **ERP (legacy):** `ebdata` (PG 9.3 @ `100.69.251.92:5432`) - **READ-ONLY** përmes FDW
- **Encoding:** UTF-8, ICU locale `en-US`
- **Skemat:** `stg`, `ref`, `wph_core`, `ops`, `audit`, `eb_fdw`

---

## 2. KONFIGURIMI I LIDHJES

### Environment Variables
```bash
WPH_DB_HOST=127.0.0.1           # ose IP remote
WPH_DB_PORT=5432
WPH_DB_NAME=wph_ai
WPH_DB_USER=postgres
WPH_DB_PASS=<sekret>            # KURRË mos e hardcode-o!
```

### Connection String (Flask/Psycopg2)
```python
# .env file në root:
PGAPP_DSN=postgresql://postgres:<pass>@127.0.0.1:5432/wph_ai

# Në kod:
import psycopg2
conn = psycopg2.connect(os.getenv("PGAPP_DSN"))
```

### psql CLI
```powershell
# Auto-detect psql.exe (nga setup_wphAI.ps1)
$psql = Get-ChildItem "C:\Program Files\PostgreSQL" -Recurse -Filter psql.exe | 
        Select-Object -First 1 | Select-Object -ExpandProperty FullName

& $psql -h 127.0.0.1 -p 5432 -U postgres -d wph_ai
```

---

## 3. ARKITEKTURA E SKEMAVE

### 3.1 `eb_fdw` - Foreign Data Wrapper (ERP Legacy)
**Purpose:** Lexim READ-ONLY nga ERP (EasyBusiness) në `ebdata@100.69.251.92`

**Foreign Tables:**
| Tabela | Përdorimi | Kolonat kryesore |
|--------|-----------|------------------|
| `eb_fdw.artikli` | Katalog i artikujve | `sifra`, `barkod`, `naziv`, `jmj`, `stanje` |
| `eb_fdw.artiklikartica` | Lëvizjet e stokut | `artikal`, `datum`, `magacin`, `ulaz`, `izlaz` |
| `eb_fdw.promet_artikala` | Shitjet historike | `sifra`, `datum`, `kolicina` |
| `eb_fdw.pos` | Transaksionet POS | `id`, `sifra`, `qty`, `cena` |

**Setup Script:** `sql/01_fdw_setup.sql`

**Konfigurim FDW:**
```sql
CREATE SERVER eb_fdw FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host '100.69.251.92', port '5432', dbname 'ebdata');

CREATE USER MAPPING FOR postgres SERVER eb_fdw
  OPTIONS (user 'smart_pedja', password 'wellona-server');

IMPORT FOREIGN SCHEMA public
  LIMIT TO (artikli, artiklikartica, promet_artikala, pos)
  FROM SERVER eb_fdw INTO eb_fdw;
```

---

### 3.2 `stg` - Staging (ETL & Cache)
**Purpose:** Data e përkohshme nga import/export dhe cache të llogaritura

**Materialized Views:**
| View | Refresh | Përdorimi | Kolonat |
|------|---------|-----------|---------|
| `stg.stock_on_hand` | Nightly | Stock aktual (FY current, mag=101) | `sifra`, `datum`, `qty` |

**Tabelat:**
| Tabela | Përdorimi |
|--------|-----------|
| `stg.phoenix` | Import pricefeed Phoenix |
| `stg.sopharma` | Import pricefeed Sopharma |
| `stg.vega` | Import pricefeed Vega |
| `stg_pricefeed` | Unified pricefeed (nga orchestrator) |

**Formula `stock_on_hand`:**
```sql
-- Stock = Σ(ulaz - izlaz) për vitin fiskal aktual dhe magacin 101
SELECT TRIM(artikal)::text AS sifra,
       COALESCE(SUM(ulaz - izlaz), 0)::numeric AS qty
FROM eb_fdw.artiklikartica
WHERE magacin = '101'
  AND EXTRACT(YEAR FROM datum) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY TRIM(artikal);
```

---

### 3.3 `ops` - Operational Metrics
**Purpose:** Metrika operative (shitje, demand, status)

**Materialized Views:**
| View | Window | Refresh | Formula | Kolonat |
|------|--------|---------|---------|---------|
| `ops._sales_7d` | 7 ditë | Nightly | `SUM(izlaz) / 7` | `sifra`, `avg_daily`, `last_sale_date` |
| `ops._sales_30d` | 30 ditë | Nightly | `SUM(izlaz) / 30` | `sifra`, `avg_daily`, `last_sale_date` |
| `ops._sales_180d` | 180 ditë | Nightly | `SUM(izlaz) / 180` | `sifra`, `avg_daily`, `last_sale_date` |
| `ops.article_status` | - | Nightly | Demand + Stock + Policy | `sifra`, `current_stock`, `avg_daily_sales`, `monthly_units`, `min_zaliha`, `qty_to_order`, `has_recent_sales` |

**Formula shitjesh (calendar-day average):**
```sql
-- Përfshin edhe ditët pa shitje për të dhënë avg real ditor
SELECT TRIM(artikal)::text AS sifra,
       ROUND(COALESCE(SUM(GREATEST(izlaz,0)),0) / 30.0, 6) AS avg_daily,
       MAX(CASE WHEN GREATEST(izlaz,0) > 0 THEN DATE(datum) END) AS last_sale_date
FROM eb_fdw.artiklikartica
WHERE datum >= CURRENT_DATE - INTERVAL '30 days'
  AND magacin = '101'
GROUP BY TRIM(artikal);
```

**Formula `article_status`:**
```sql
-- Bashkon demand (nga sales MV) me inventory (stock_on_hand)
-- dhe aplikon policy (min_zaliha_policy_v2) për të llogaritur qty_to_order
WITH demand AS (...),
     inventory AS (SELECT sifra, qty AS stock FROM stg.stock_on_hand),
     calc AS (
       SELECT ...,
              (SELECT p.min_zaliha FROM ref.min_zaliha_policy_v2 p
               WHERE monthly_units >= p.range_from
                 AND (p.range_to IS NULL OR monthly_units <= p.range_to)
               ORDER BY p.range_from DESC LIMIT 1
              ) AS min_zaliha
       FROM demand d FULL OUTER JOIN inventory i ON d.sifra = i.sifra
     )
SELECT ...,
       CASE 
         WHEN NOT has_recent_sales THEN 
           CASE WHEN current_stock=0 AND avg_daily_sales>0 THEN 2 ELSE 0 END
         ELSE 
           GREATEST(0, GREATEST(min_zaliha, CEIL(target_days*avg_daily_sales)) - current_stock)
       END AS qty_to_order
FROM calc;
```

---

### 3.4 `ref` - Reference Data
**Purpose:** Tabela referuese (suppliers, policies, aliases)

**Tabelat:**
| Tabela | Përmbajtja | Kolonat |
|--------|------------|---------|
| `ref.suppliers` | Lista e furnitorëve | `supplier_id`, `code`, `name`, `is_active` |
| `ref.min_zaliha_policy_v2` | Politika e stokut minimal (9 shkallë) | `range_from`, `range_to`, `min_zaliha`, `note` |
| `ref.ref_supplier_terms` | Termat e furnitorëve | `supplier_code`, `moq`, `lead_time_days`, `rabat_pct` |

**Policy Ranges (`ref.min_zaliha_policy_v2`):**
| `range_from` | `range_to` | `min_zaliha` | Note |
|--------------|------------|--------------|------|
| 0 | 0 | 0 | no movement |
| 1 | 5 | 2 | presence |
| 5 | 10 | 3 | - |
| 10 | 15 | 4 | - |
| 15 | 20 | 5 | - |
| 20 | 30 | 7 | - |
| 30 | 40 | 9 | - |
| 40 | 50 | 11 | - |
| 50 | NULL | 14 | critical |

**Lookup Logic:**
```sql
-- Gjen min_zaliha bazuar në monthly_units (avg_daily * 30)
SELECT p.min_zaliha
FROM ref.min_zaliha_policy_v2 p
WHERE monthly_units >= p.range_from
  AND (p.range_to IS NULL OR monthly_units <= p.range_to)
ORDER BY p.range_from DESC
LIMIT 1;
```

---

### 3.5 `wph_core` - Core Business Logic
**Purpose:** Funksionet dhe tabelat qendrore të logjikës së biznesit

**Functions:**
| Funksioni | Parametrat | Return | Përdorimi |
|-----------|-----------|---------|-----------|
| `wph_core.get_orders()` | `p_target_days`, `p_sales_window`, `p_include_zero`, `p_search_query` | TABLE | API endpoint `/api/orders` |
| `wph_core.run_pipeline()` | `pipeline_code` | void | Ekzekuton ETL pipeline (nightly_etl) |

**Tabelat:**
| Tabela | Përdorimi |
|--------|-----------|
| `wph_core.mappers` | Konfigurime mapper (Phoenix, Sopharma, ...) |
| `wph_core.pipelines` | Pipeline specs (nightly_etl.json) |

**Shembull `get_orders()`:**
```sql
-- Dynamic SQL që zgjedh MV bazuar në sales_window
SELECT * FROM wph_core.get_orders(
    p_target_days := 28,      -- Ditë për të cilat dëshirojmë të mbulojmë stokun
    p_sales_window := 30,     -- Window i shitjeve (7/30/180)
    p_include_zero := FALSE,  -- Përfshi artikuj me stock=0
    p_search_query := 'aspirin' -- Kërkim në emër/sifra/barkod
);
```

---

### 3.6 `audit` - Audit Trail
**Purpose:** Logging i event-eve sistemit

**Tabelat:**
| Tabela | Kolonat | Përdorimi |
|--------|---------|-----------|
| `audit.events` | `event_id`, `event_time`, `actor`, `action`, `payload` | Log i të gjitha veprimeve (order, refresh, import) |

---

## 4. VIEWS & MATERIALIZED VIEWS - PËRMBLEDHJE

### Read Source (nga ku lexojmë)
| Për çfarë | Source | Type |
|-----------|--------|------|
| Stock aktual | `stg.stock_on_hand` | MV (refresh nightly) |
| Shitje 7d | `ops._sales_7d` | MV (refresh nightly) |
| Shitje 30d | `ops._sales_30d` | MV (refresh nightly) |
| Shitje 180d | `ops._sales_180d` | MV (refresh nightly) |
| Status artikulli | `ops.article_status` | MV (refresh nightly) |
| Katalog ERP | `eb_fdw.artikli` | Foreign Table (live) |
| Lëvizjet ERP | `eb_fdw.artiklikartica` | Foreign Table (live) |
| Policy stoku | `ref.min_zaliha_policy_v2` | Table (static/manual) |

### Refresh Schedule
```sql
-- Nightly refresh (run_nightly_etl.ps1 @ 02:00)
REFRESH MATERIALIZED VIEW stg.stock_on_hand;
REFRESH MATERIALIZED VIEW ops._sales_7d;
REFRESH MATERIALIZED VIEW ops._sales_30d;
REFRESH MATERIALIZED VIEW ops._sales_180d;
REFRESH MATERIALIZED VIEW ops.article_status;
```

**PowerShell command:**
```powershell
& $psql -h 127.0.0.1 -U postgres -d wph_ai -c "
  REFRESH MATERIALIZED VIEW stg.stock_on_hand;
  REFRESH MATERIALIZED VIEW ops._sales_7d;
  REFRESH MATERIALIZED VIEW ops._sales_30d;
  REFRESH MATERIALIZED VIEW ops._sales_180d;
  REFRESH MATERIALIZED VIEW ops.article_status;
"
```

---

## 5. ENTRY POINTS - KU PËRDORET SECILA VIEW/TABELË

### 5.1 Web App (`web_modern/app_v2.py`)
**Endpoint:** `GET /api/orders`

```python
# Thirrje në DB function
rows = fetch_all(
    "SELECT * FROM wph_core.get_orders(%s, %s, %s, %s)",
    [target_days, sales_window, include_zero, search_query]
)
```

**Funksioni lexon:**
- `ops._sales_<window>d` (dinamik bazuar në `sales_window`)
- `stg.stock_on_hand` (për stock aktual)
- `ref.min_zaliha_policy_v2` (për min_zaliha)
- `eb_fdw.artikli` (për naziv/barkod)

---

### 5.2 Orchestrator (`bin/wph_ai_orchestrator.py`)
**Purpose:** Order Brain pa Excel, lexim direkt nga DB

```python
# SQL Queries
SQL_INVENTORY = """
SELECT sifra, barkod, naziv, on_hand, on_order, moq, pack, lead_time_days
FROM eb_inventory_current;
"""

SQL_SALES = """
SELECT sifra, barkod, avgd_7, avgd_14, avgd_30, avgd_90
FROM eb_sales_rolling;
"""

SQL_PRICEFEED = """
SELECT supplier, sifra, barkod, vpc, kasa
FROM stg_pricefeed
WHERE supplier = '{supplier}' AND active = true;
"""
```

**Viewsa që duhen ekzistuar (ose krijohen si alias):**
- `eb_inventory_current` → alias për `stg.stock_on_hand` + join me `eb_fdw.artikli`
- `eb_sales_rolling` → alias për `ops._sales_180d` (ose CTE që bashkon 7d/30d/90d)
- `stg_pricefeed` → tabela që popullojmë nga ETL

---

### 5.3 Order Brain (`app/order_brain.py`)
**Purpose:** Excel-centric decision engine (legacy)

**Inputs:**
- `PROMET ARTIKLA.xlsx` (lexon nga disk)
- `FURNITORET.xlsx` (lexon nga disk)

**Matching Logic:**
- BARKOD → SIFRA → SIGNATURE → API_DOSE → ...

**Nuk lexon direkt nga DB, por mund të shkruajë output në `out/orders/`**

---

## 6. SETUP & BOOTSTRAPPING

### 6.1 Fillimtare - Krijo DB & Schemas
```powershell
# Run once
.\setup_wphAI.ps1
```

**Çfarë bën:**
1. Krijon databazë `wph_ai` (nëse mungon)
2. Krijon skemat: `stg`, `ref`, `wph_core`, `ops`, `audit`, `eb_fdw`
3. Setup FDW për ERP (`eb_fdw`)
4. Krijon tabela bazë (`ref.suppliers`, `wph_core.mappers`, `wph_core.pipelines`)
5. Seed data (4 furnitorë: Phoenix, Sopharma, Vega, Farmalogist)
6. Upsert mapper & pipeline configs nga JSON files

---

### 6.2 Apliko Baseline Patches
```powershell
# Apliko MVs dhe policy
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"

& $psql -h 127.0.0.1 -U postgres -d wph_ai `
  -f patches/baseline_erp_identik_2025-11-01.sql

& $psql -h 127.0.0.1 -U postgres -d wph_ai `
  -f patches/sales_windows_7d_30d.sql

& $psql -h 127.0.0.1 -U postgres -d wph_ai `
  -f sql/patch3_min_zaliha_policy_v2.sql

# Refresh MVs
& $psql -h 127.0.0.1 -U postgres -d wph_ai -c "
  REFRESH MATERIALIZED VIEW stg.stock_on_hand;
  REFRESH MATERIALIZED VIEW ops._sales_7d;
  REFRESH MATERIALIZED VIEW ops._sales_30d;
  REFRESH MATERIALIZED VIEW ops._sales_180d;
  REFRESH MATERIALIZED VIEW ops.article_status;
"
```

---

### 6.3 Nightly Refresh (Scheduled Task)
```powershell
# run_nightly_etl.ps1 (ekzekuton çdo natë @ 02:00)
.\run_nightly_etl.ps1
```

**Çfarë bën:**
1. REFRESH të gjitha MVs
2. Run `wph_core.run_pipeline('nightly_etl')`
3. Parse Phoenix pricelists nga `in/phoenix/`
4. Emit provisional orders në `out/orders/`
5. Log në `logs/nightly_<TS>.log`

---

## 7. TROUBLESHOOTING

### 7.1 Error: "relation does not exist"
**Problem:** MV ose tabela nuk është krijuar ende.

**Solution:**
```powershell
# Check nëse ekziston
& $psql -h 127.0.0.1 -U postgres -d wph_ai -c "\
SELECT schemaname, matviewname FROM pg_matviews WHERE schemaname IN ('stg','ops');
"

# Nëse mungon, apliko patch-in
& $psql -h 127.0.0.1 -U postgres -d wph_ai -f patches/baseline_erp_identik_2025-11-01.sql
```

---

### 7.2 Error: FDW connection failed
**Problem:** ERP server `100.69.251.92` nuk është i arritshëm ose kredencialet gabojnë.

**Solution:**
```powershell
# Test ping
ping 100.69.251.92

# Test psql direkt në ERP
& $psql -h 100.69.251.92 -U smart_pedja -d ebdata -c "SELECT version();"

# Check FDW mapping
& $psql -h 127.0.0.1 -U postgres -d wph_ai -c "
SELECT * FROM pg_user_mappings WHERE srvname='eb_fdw';
"
```

---

### 7.3 Error: Slow queries / missing indexes
**Problem:** Query të ngadalshme për shkak të mungesës së index-eve.

**Solution:**
```sql
-- Krijo indexes për MVs
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_stock_on_hand_sifra 
  ON stg.stock_on_hand(sifra);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sales_7d_sifra 
  ON ops._sales_7d(sifra);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sales_30d_sifra 
  ON ops._sales_30d(sifra);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sales_180d_sifra 
  ON ops._sales_180d(sifra);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_article_status_sifra 
  ON ops.article_status(sifra);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_article_status_order 
  ON ops.article_status(qty_to_order) WHERE qty_to_order > 0;

-- Krijo indexes për ref policy
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_policy_range 
  ON ref.min_zaliha_policy_v2(range_from, range_to);

-- Analyze tables
ANALYZE stg.stock_on_hand;
ANALYZE ops._sales_7d;
ANALYZE ops._sales_30d;
ANALYZE ops._sales_180d;
ANALYZE ops.article_status;
ANALYZE ref.min_zaliha_policy_v2;
```

---

## 8. BACKUPS & SNAPSHOTS

### 8.1 Schema Backup (pg_dump)
```powershell
# Backup full schema
$ts = Get-Date -Format "yyyyMMdd_HHmm"
$snapdir = "C:\Wellona\wphAI\snapshots\baseline_$ts"
New-Item -ItemType Directory -Force -Path $snapdir

& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" `
  -h 127.0.0.1 -U postgres -d wph_ai `
  --schema-only --no-owner --no-privileges `
  -f "$snapdir\wph_ai_schema.sql"

# Backup data only (excluding FDW)
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" `
  -h 127.0.0.1 -U postgres -d wph_ai `
  --data-only --exclude-schema=eb_fdw `
  -f "$snapdir\wph_ai_data.sql"
```

---

### 8.2 Restore nga Snapshot
```powershell
# Drop & recreate DB (DANGEROUS!)
& $psql -h 127.0.0.1 -U postgres -c "DROP DATABASE IF EXISTS wph_ai;"
& $psql -h 127.0.0.1 -U postgres -c "
  CREATE DATABASE wph_ai WITH OWNER=postgres TEMPLATE=template0 
  ENCODING='UTF8' LOCALE_PROVIDER='icu' ICU_LOCALE='en-US';
"

# Restore schema
& $psql -h 127.0.0.1 -U postgres -d wph_ai `
  -f "C:\Wellona\wphAI\snapshots\baseline_20251102_0005\wph_ai_schema.sql"

# Restore data
& $psql -h 127.0.0.1 -U postgres -d wph_ai `
  -f "C:\Wellona\wphAI\snapshots\baseline_20251102_0005\wph_ai_data.sql"

# Refresh MVs
& $psql -h 127.0.0.1 -U postgres -d wph_ai -c "
  REFRESH MATERIALIZED VIEW stg.stock_on_hand;
  REFRESH MATERIALIZED VIEW ops._sales_7d;
  REFRESH MATERIALIZED VIEW ops._sales_30d;
  REFRESH MATERIALIZED VIEW ops._sales_180d;
  REFRESH MATERIALIZED VIEW ops.article_status;
"
```

---

## 9. SUMMARY DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                    WPH_AI DATABASE (wph_ai)                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐         ┌─────────────┐                    │
│  │   eb_fdw    │ ──FDW─> │   ebdata    │ (ERP @ 100.69...) │
│  │ (read-only) │         │   PG 9.3    │                    │
│  └─────────────┘         └─────────────┘                    │
│         │                                                     │
│         ├─> artikli (katalog)                               │
│         ├─> artiklikartica (lëvizjet)                       │
│         ├─> promet_artikala (shitje)                        │
│         └─> pos (POS transactions)                          │
│                                                               │
│  ┌─────────────┐                                             │
│  │     stg     │  (Staging & Cache)                         │
│  ├─────────────┤                                             │
│  │ • stock_on_hand (MV) ← artiklikartica (FY, mag=101)     │
│  │ • phoenix, sopharma, vega (tables)                       │
│  └─────────────┘                                             │
│         │                                                     │
│         v                                                     │
│  ┌─────────────┐                                             │
│  │     ops     │  (Operational Metrics)                     │
│  ├─────────────┤                                             │
│  │ • _sales_7d (MV)                                         │
│  │ • _sales_30d (MV)                                        │
│  │ • _sales_180d (MV)                                       │
│  │ • article_status (MV) ← demand + stock + policy         │
│  └─────────────┘                                             │
│         │                                                     │
│         v                                                     │
│  ┌─────────────┐                                             │
│  │     ref     │  (Reference Data)                          │
│  ├─────────────┤                                             │
│  │ • suppliers (table)                                      │
│  │ • min_zaliha_policy_v2 (table) - 9 shkallë              │
│  │ • ref_supplier_terms (table)                             │
│  └─────────────┘                                             │
│         │                                                     │
│         v                                                     │
│  ┌─────────────┐                                             │
│  │  wph_core   │  (Business Logic)                          │
│  ├─────────────┤                                             │
│  │ • get_orders(target_days, sales_window, ...) FUNCTION   │
│  │ • run_pipeline(pipeline_code) FUNCTION                   │
│  │ • mappers (table)                                        │
│  │ • pipelines (table)                                      │
│  └─────────────┘                                             │
│         │                                                     │
│         v                                                     │
│  ┌─────────────┐                                             │
│  │    audit    │  (Audit Trail)                             │
│  ├─────────────┤                                             │
│  │ • events (table) - log i të gjitha veprimeve            │
│  └─────────────┘                                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
              │
              v
     ┌────────────────────┐
     │   Web App (Flask)  │ → /api/orders
     │   Orchestrator     │ → ORDER_<SUPPLIER>.csv
     │   Order Brain      │ → POROSIT_FULL.xlsx
     └────────────────────┘
```

---

## 10. REFERENCES

### SQL Files
- `sql/01_fdw_setup.sql` - FDW setup për ERP
- `sql/patch3_min_zaliha_policy_v2.sql` - Policy table & article_status MV
- `patches/baseline_erp_identik_2025-11-01.sql` - Baseline MVs (stock, sales_180d)
- `patches/sales_windows_7d_30d.sql` - Sales windows (7d, 30d)
- `sql/query_get_orders_ready_v2.sql` - Funksioni `wph_core.get_orders()`

### PowerShell Scripts
- `setup_wphAI.ps1` - Initial DB bootstrap
- `run.ps1` - Main runner
- `run_nightly_etl.ps1` - Nightly refresh scheduler

### Python Apps
- `web_modern/app_v2.py` - Flask API
- `bin/wph_ai_orchestrator.py` - DB orchestrator
- `app/order_brain.py` - Excel-centric decision engine

### Docs
- `BASELINE_GUIDE.md` - Baseline ERP-identik (2025-11-01)
- `docs/ORDER_DECISION_GUIDE.md` - Order formula guide

---

**END OF DOCUMENT**

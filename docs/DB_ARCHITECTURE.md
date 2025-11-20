# ═══════════════════════════════════════════════════════════════════════════════
# ARKITEKTURA E PLOTË E LIDHJEVE DB - WPH_AI ORDERS SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
# Data: 2025-11-04
# Qëllimi: Dokumentim i plotë i rrugës së të dhënave nga ERP → Postgres → API
# ═══════════════════════════════════════════════════════════════════════════════

## 🔗 SHTRESA 1: LIDHJA ME ERP (Foreign Data Wrapper)
## ─────────────────────────────────────────────────────────────────────────────

# SCHEMA: eb_fdw (Foreign Data Wrapper - live read nga ERP EvidentaBaze)
# SERVER: eb_server → TCP connection me SQL Server ERP database

eb_fdw.artikli                # Master table artikujsh
├── sifra         PK          # Kodi unik i artikullit
├── naziv                     # Emri
├── barkod                    # Barkodi EAN/UPC
├── pakovanje                 # Madhësia e paketës (default 1)
├── stanje                    # Stock aktual (live nga ERP)
├── vpc                       # Çmimi blerje
├── cena                      # Çmimi shitje
└── aktivan                   # Flag aktiv/pasiv

eb_fdw.kalkulacije            # Historiku i faturave
├── id_kalkulacija  PK        
├── sifra           FK        # → eb_fdw.artikli.sifra
├── kolicina                  # Sasia e shitur/blerë
├── datum                     # Data e transaksionit
├── vrsta                     # Lloji (MP=shitje, FAKTURE=blerje)
└── iznos_promet              # Vlera totale

eb_fdw.kasa_promet            # Transaksionet e arkës
├── id               PK
├── sifra           FK        # → eb_fdw.artikli.sifra
├── kolicina
├── datum
└── cena

## 🔄 SHTRESA 2: STAGING (Snapshot & Cache Layer)
## ─────────────────────────────────────────────────────────────────────────────

# SCHEMA: stg (Staging - snapshots të përkohshëm për performance)

stg.stock_on_hand             # VIEW/TABLE (fallback nga eb_fdw.artikli)
├── sifra          PK
└── qty                       # ≡ eb_fdw.artikli.stanje

stg.sales_raw                 # Snapshot ditor i shitjeve
├── sifra          FK
├── sale_date
├── qty_sold
└── revenue

stg.phoenix_latest            # Pricefeed i fundit nga Phoenix
├── sifra          FK
├── barkod
├── price
├── rabat_pct
├── pack_size
└── fetched_at

stg.sopharma_latest           # Pricefeed Sopharma
stg.vega_latest               # Pricefeed Vega

## 📊 SHTRESA 3: OPERATIONS (Business Logic & Aggregations)
## ─────────────────────────────────────────────────────────────────────────────

# SCHEMA: ops (Operational views & materialized views)

ops._sales_7d       MV        # Mesatarja ditore 7 ditë
├── sifra          PK
├── avg_daily               # AVG(qty_sold)
├── total_qty               # SUM(qty_sold)
├── last_sale_date
└── refreshed_at

ops._sales_15d      MV        # Mesatarja 15 ditë
ops._sales_30d      MV        # Mesatarja 30 ditë (default)
ops._sales_60d      MV        # Mesatarja 60 ditë
ops._sales_180d     MV        # Mesatarja 180 ditë

-- Refresh command (nightly ETL):
-- REFRESH MATERIALIZED VIEW CONCURRENTLY ops._sales_Xd;

ops.article_status   VIEW     # View real-time për dashboard
├── sifra
├── naziv
├── stock              ← stg.stock_on_hand
├── avg_daily_7d       ← ops._sales_7d
├── avg_daily_30d      ← ops._sales_30d
├── days_cover         # stock / avg_daily
├── min_zaliha         ← ref.min_zaliha_policy_v2
├── qty_to_order       # Calculated
└── urgent_flag        # days_cover < 7

## 📋 SHTRESA 4: REFERENCE DATA (Static/Slow-Changing)
## ─────────────────────────────────────────────────────────────────────────────

# SCHEMA: ref (Reference data - politikat dhe metadata)

ref.min_zaliha_policy_v2      # Politika dinamike e min-stock
├── id             PK
├── sifra          FK         # NULL = default rule për të gjithë
├── range_from               # Threshold i ulët i monthly_units
├── range_to                 # Threshold i lartë (NULL = pa kufizim)
├── min_zaliha               # Sasia minimale për këtë range
├── active                   # Flag aktiv
└── created_at

-- Shembull:
-- range_from=0,    range_to=10,   min_zaliha=5    → artikuj me shitje të ulët
-- range_from=10,   range_to=50,   min_zaliha=15   → artikuj medium
-- range_from=50,   range_to=NULL, min_zaliha=30   → artikuj të lartë

ref.suppliers                 # Lista e furnitorëve
├── id             PK
├── name                     # PHOENIX, SOPHARMA, VEGA
├── contact_email
├── ftp_config      JSON     # Credentials për FTP/IMAP
└── active

ref.banned_words              # Fjalët e ndaluara për filtrimin e porosisë
├── id             PK
├── word                     # igla, spric, maska, etj.
└── active

ref.drug_aliases              # Mapping i emrave alternativë të barnave
├── id             PK
├── sifra_primary  FK
├── sifra_alias    FK
└── match_type               # EXACT, FUZZY, API_DOSE

## 💾 SHTRESA 5: APPLICATION DATA (Order History & Logs)
## ─────────────────────────────────────────────────────────────────────────────

# SCHEMA: app (Application tables - nga web_modern/app_v2.py)

app.orders                    # Header i porosive
├── id              PK        # SERIAL
├── supplier                  # PHOENIX, SOPHARMA, etc.
├── status                    # draft, approved, sent, received
├── target_days              # Parametri i përdorur
├── sales_window             # 7/15/30/60/180
├── created_by               # webapp, orchestrator, etc.
├── approved_by              # Username
├── approved_at              # Timestamp
├── csv_path                 # C:\Wellona\wphAI\out\orders\2025-11-04\ORDER_PHOENIX_20251104_083215.csv
├── note                     # Shënime opsionale
├── meta           JSON      # {"items": 42, "total_rsd": 125000}
├── created_at               # NOW()
└── updated_at

app.order_items               # Detajet e porosisë (line items)
├── id              PK
├── order_id        FK       # → app.orders.id
├── sifra           FK       # → eb_fdw.artikli.sifra
├── barkod
├── naziv
├── qty                      # Sasia e porositur
├── unit_cost                # Çmimi për njësi
├── line_total               # qty × unit_cost
├── meta           JSON      # {"pakovanje": 6, "rabat": 10}
└── created_at

## 📈 SHTRESA 6: AUDIT & MONITORING
## ─────────────────────────────────────────────────────────────────────────────

# SCHEMA: audit (Logging dhe gjurmimi)

audit.etl_runs                # Log i ETL pipeline executions
├── id              PK
├── pipeline_name            # nightly_etl, load_phoenix, etc.
├── status                   # running, success, failed
├── started_at
├── completed_at
├── rows_processed
├── error_msg       TEXT
└── meta           JSON

audit.api_requests            # Log i API calls (opsional)
├── id              PK
├── endpoint                 # /api/orders, /api/orders/phoenix
├── method                   # GET, POST
├── params         JSON
├── status_code
├── response_time_ms
├── user_agent
└── timestamp

## 🔐 SHTRESA 7: SECURITY & ACCESS
## ─────────────────────────────────────────────────────────────────────────────

# ROLES:
wph_app_read       # SELECT në të gjitha schemat
wph_app_write      # INSERT/UPDATE në app.*, audit.*
wph_etl            # Refresh MVs, INSERT/UPDATE në stg.*, ops.*
wph_admin          # DDL, gjithçka

# GRANTS:
GRANT USAGE ON SCHEMA eb_fdw, stg, ops, ref, app, audit TO wph_app_read;
GRANT SELECT ON ALL TABLES IN SCHEMA eb_fdw, stg, ops, ref TO wph_app_read;
GRANT SELECT, INSERT, UPDATE ON app.orders, app.order_items TO wph_app_write;
GRANT SELECT, INSERT ON audit.api_requests TO wph_app_write;

## 🔄 FLOW I TË DHËNAVE (Data Pipeline)
## ─────────────────────────────────────────────────────────────────────────────

1. ERP (SQL Server) → eb_fdw.artikli, eb_fdw.kalkulacije  [FDW real-time]
2. Nightly ETL:
   - Extract: eb_fdw.kalkulacije → stg.sales_raw
   - Aggregate: stg.sales_raw → ops._sales_Xd (REFRESH MV)
   - Cleanup: DELETE old staging rows (> 180d)
3. Web API (/api/orders):
   - Read: ops._sales_30d + stg.stock_on_hand + ref.min_zaliha_policy_v2 + eb_fdw.artikli
   - Calculate: qty_to_order
   - Filter: include_zero, search query
4. Web API (/api/orders/<supplier> POST):
   - Validate: banned words, budget cap
   - Round: ceil_to_pack(pakovanje)
   - Write: app.orders + app.order_items
   - Export: CSV → C:\Wellona\wphAI\out\orders\YYYY-MM-DD\
5. Orchestrator (bin/wph_ai_orchestrator.py):
   - Cron: 02:00 daily
   - Execute: nightly ETL pipeline
   - Alert: email/SMS nëse ka failure

## 📦 DEPENDENCIES EXTERNE
## ─────────────────────────────────────────────────────────────────────────────

psycopg2           # Postgres driver
python-dotenv      # .env loader
flask              # Web framework
pandas             # CSV export (order_brain.py)
openpyxl           # Excel input (order_brain.py)
requests           # API calls (Phoenix API)
paramiko           # SFTP (për vendor pricefeeds)
imaplib            # Email fetch (app/imap_fetch.py)

## 🗂️ FILE STRUCTURE
## ─────────────────────────────────────────────────────────────────────────────

C:\Wellona\wphAI\
├── web_modern\
│   ├── app_v2.py              # Flask API (GET/POST /api/orders)
│   ├── db.py                  # DB connection helper
│   ├── logger_setup.py        # Logging config
│   └── public\
│       ├── orders_ai.html     # Ultra UI (Tailwind)
│       └── orders_master_ultra.html
├── bin\
│   └── wph_ai_orchestrator.py # CLI orchestrator
├── app\
│   ├── order_brain.py         # Excel-based legacy processor
│   ├── imap_fetch.py          # Email attachment fetcher
│   └── etl_run.ps1            # PowerShell ETL runner
├── sql\
│   ├── 01_fdw_setup.sql       # FDW creation
│   ├── 02_create_mvs.sql      # Create ops._sales_Xd
│   └── 03_refresh_mvs.sql     # Refresh logic
├── configs\
│   ├── core.json              # DB connection strings
│   ├── pipelines\
│   │   └── nightly_etl.json   # Pipeline definition
│   └── suppliers\
│       ├── phoenix.v1.json    # Phoenix mapping
│       ├── sopharma.v1.json
│       └── vega.v1.json
├── in\                        # Input folder (vendor data)
├── out\                       # Output folder (CSV exports)
├── logs\                      # ETL & API logs
└── .env                       # Secrets (DB credentials)

## 🚀 DEPLOYMENT SEQUENCE (Setup i ri)
## ─────────────────────────────────────────────────────────────────────────────

1. run.ps1                     # Bootstrap DB schemas & tables
2. setup_wphAI.ps1             # Create roles, grants, FDW
3. sql/01_fdw_setup.sql        # Link ERP database
4. sql/02_create_mvs.sql       # Create all MVs
5. app/etl_run.ps1             # First data load
6. web_modern/run_web.ps1      # Start Flask server
7. Test: http://127.0.0.1:8055/ui


`# 🔍 ANALIZË INTEGRIMI: wellona-order-brain → wphAI

**Data:** 2025-11-06  
**Qëllimi:** Krahasim i detajuar i folder `wellona-order-brain-WellonaVSCODE-main` me infrastrukturën tonë aktuale

---

## 📋 PËRMBLEDHJE EXECUTIVE

| Kategoria | Gjendja | Detaje |
|-----------|---------|--------|
| **Tabela bazë** | ✅ 100% Compatible | artikli, artiklikartica, artikliuslovi ekzistojnë në eb_fdw |
| **Schemas** | ✅ Ekzistojnë | stg, ref, ops ekzistojnë në wph_ai |
| **Views** | ❌ NUK ekzistojnë | stg.order_proposal duhet krijuar |
| **Functions** | ⚠️ Pjesërisht | wph_core.get_orders() ekziston, por kolonat ndryshojnë |
| **Reference tables** | ❌ NUK ekziston | ref.ref_supplier_terms mungon |

**VERDICT:** 
- ✅ **Infrastruktura bazë është e gatshme**
- ⚠️ **Nevojiten modifikime në kolonat dhe views**
- ❌ **Duhen krijuar tabela reference të reja**

---

## 1️⃣ TABELA BAZË (Source Data)

### Çfarë përdor `wellona-order-brain`:

```sql
-- order_proposal_view.sql dhe Wellona_Order_Brain_v11.sql
FROM artiklikartica ak          -- Sales history (izlaz/ulaz per magacin)
FROM artikli a                  -- Master artikli (sifra, naziv, barkod, stanje)
FROM artikliuslovi u           -- Supplier prices (dobavljac, vpcena, kasa1)
```

### Çfarë KEMI në wph_ai:

| Tabela | Schema | Lloji | Burimi | Status |
|--------|--------|-------|--------|--------|
| `artikli` | eb_fdw | Foreign Table | ebdata@PG9.3 | ✅ **EKZISTON** |
| `artiklikartica` | eb_fdw | Foreign Table | ebdata@PG9.3 | ✅ **EKZISTON** |
| `artikliuslovi` | eb_fdw | Foreign Table | ebdata@PG9.3 | ✅ **EKZISTON** |

**✅ REZULTAT:** Të gjitha tabelat e nevojshme janë të disponueshme!

---

## 2️⃣ KOLONAT (Column Mapping)

### `wellona-order-brain` OUTPUT Columns:

```sql
-- order_proposal_view.sql (SELECT final)
sifra                   text        -- Kodi i artikullit
barcode                 text        -- EAN/UPC barcode
emri_artikullit         text        -- Emri i produktit
magacin_id              text        -- '101' (fixed)
current_stock           numeric     -- Stock aktual
avg_daily_sales_28d     numeric     -- Mesatarja ditore 28 ditë
days_cover              numeric     -- Sa ditë mbulon stock-u
target_days             numeric     -- 15 (ose 28 për Wellona)
needed_qty_raw          numeric     -- Raw calculation (me decimal)
needed_qty_rounded      numeric     -- CEIL(needed_qty_raw)
pack_size               numeric     -- 1 (placeholder)
final_order_qty         numeric     -- Final qty to order
best_supplier           text        -- PHOENIX, SOPHARMA, etc.
supplier_price          numeric     -- VPCena
supplier_discount       numeric     -- kasa1 (rabat%)
final_price             numeric     -- vpc × (1 - rabat/100)
cash_impact             numeric     -- final_order_qty × final_price
priority_class          text        -- HIGH/MID/LOW
```

### `wph_core.get_orders()` OUTPUT Columns (AKTUAL):

```sql
-- wph_core.get_orders() return type
sifra               character varying
emri                character varying
barkod              character varying
current_stock       numeric
avg_daily_sales     numeric         -- ❌ Jo avg_daily_sales_28d!
days_cover          numeric
min_zaliha          numeric         -- ✅ EKZISTON (jo në wellona!)
qty_to_order        numeric         -- ❌ Jo final_order_qty!
supplier_name       text            -- ❌ Jo best_supplier!
```

### ⚠️ KONFLIKTET:

| wellona-order-brain | wph_core.get_orders() | Ndryshimi |
|---------------------|----------------------|-----------|
| `avg_daily_sales_28d` | `avg_daily_sales` | ✅ Vetëm emër |
| `final_order_qty` | `qty_to_order` | ✅ Vetëm emër |
| `best_supplier` | `supplier_name` | ✅ Vetëm emër |
| `barcode` | `barkod` | ✅ Vetëm emër |
| `emri_artikullit` | `emri` | ✅ Vetëm emër |
| **MUNGON:** `target_days` | ❌ | ⚠️ Static në function |
| **MUNGON:** `needed_qty_raw` | ❌ | ⚠️ Jo në output |
| **MUNGON:** `needed_qty_rounded` | ❌ | ⚠️ Jo në output |
| **MUNGON:** `pack_size` | ❌ | ⚠️ Jo në output |
| **MUNGON:** `supplier_price` | ❌ | ⚠️ Jo në output |
| **MUNGON:** `supplier_discount` | ❌ | ⚠️ Jo në output |
| **MUNGON:** `final_price` | ❌ | ⚠️ Jo në output |
| **MUNGON:** `cash_impact` | ❌ | ⚠️ Jo në output |
| **MUNGON:** `priority_class` | ❌ | ⚠️ Jo në output |
| **EKSTRA:** `min_zaliha` | ✅ | ✅ Bonus kolona! |

---

## 3️⃣ VIEWS & MATERIALIZED VIEWS

### Çfarë nevojitet nga `wellona-order-brain`:

```sql
-- Wellona_Order_Brain_v11.sql
CREATE OR REPLACE VIEW stg.order_proposal AS
WITH
  blocked AS (...),           -- Banned words (igla, spric, etc.)
  sales_28d AS (...),         -- Sales aggregation FROM artiklikartica
  stock_now AS (...),         -- Stock FROM artikli
  coverage AS (...),          -- Days cover calculation
  demand_calc AS (...),       -- Qty needed calculation
  qty_final AS (...),         -- Rounding to pack_size
  best_supplier AS (...),     -- Cheapest supplier FROM artikliuslovi
  joined AS (...),            -- Join everything + priority_class
  filtered AS (...)           -- Filter banned words
SELECT ...
FROM filtered
WHERE final_order_qty > 0;
```

### Çfarë KEMI në wph_ai:

| View | Schema | Status |
|------|--------|--------|
| `stg.order_proposal` | stg | ❌ **NUK EKZISTON** |
| `stg.stock_on_hand` | stg | ✅ **EKZISTON** (view mbi eb_fdw.artikli) |
| `ops._sales_7d` | ops | ❌ **NUK EKZISTON** (nuk ka REFRESH) |
| `ops._sales_30d` | ops | ❌ **NUK EKZISTON** (nuk ka REFRESH) |
| `ops._sales_180d` | ops | ❌ **NUK EKZISTON** (nuk ka REFRESH) |

**⚠️ PROBLEMI:** Materialized Views për sales analytics **NUK JANË REFRESH-UER**!

---

## 4️⃣ REFERENCE TABLES

### Çfarë nevojitet nga `wellona-order-brain`:

```sql
-- Wellona_Order_Brain_v11.sql
CREATE TABLE IF NOT EXISTS ref.ref_supplier_terms (
    supplier_name       text PRIMARY KEY,
    payment_days        integer NOT NULL DEFAULT 30,
    credit_limit_rsd    numeric(18,2),
    credit_used_rsd     numeric(18,2),
    updated_at          timestamp DEFAULT now()
);
```

### Çfarë KEMI në wph_ai:

```sql
-- sql/020_refs.sql
CREATE TABLE IF NOT EXISTS ref.supplier_terms (
    supplier_name    text PRIMARY KEY,
    payment_days     integer DEFAULT 30,
    active           boolean DEFAULT true
);
```

**⚠️ KONFLIKTET:**
- Tabela jonë quhet `ref.supplier_terms` (jo `ref.ref_supplier_terms`)
- **MUNGOJNË** kolonat: `credit_limit_rsd`, `credit_used_rsd`

---

## 5️⃣ BLOCKED WORDS (Banned Patterns)

### Çfarë përdor `wellona-order-brain`:

```sql
blocked AS (
    SELECT UNNEST(ARRAY[
        'IGLA', 'IGLE', 'SPRIC', 'RUKAVICA', 'RUKAVICE',
        'CONTOUR PLUS', 'MASKE', 'MASKA'
    ]) AS banned_pattern
)
```

### Çfarë KEMI në wph_ai:

❌ **NUK EKZISTON** - as në kod, as në DB!

**Alternativa:**
1. ✅ Hardcode në function `wph_core.get_orders()`
2. ✅ Krijoj tabelë `ref.banned_words`
3. ✅ Lexoj nga JSON config

---

## 6️⃣ PRIORITY_CLASS LOGIC

### Formula në `wellona-order-brain`:

```sql
CASE
    WHEN q.avg_daily_sales_28d = 0 THEN 'LOW'
    WHEN q.days_cover < 3 THEN 'HIGH'      -- KRITIKE: < 3 ditë
    WHEN q.days_cover < 10 THEN 'MID'      -- MEDIUM: 3-10 ditë
    ELSE 'LOW'                              -- LOW: > 10 ditë
END AS priority_class
```

### Çfarë KEMI në wph_ai:

❌ **NUK EKZISTON** - `wph_core.get_orders()` nuk llogarit `priority_class`!

---

## 7️⃣ SALES WINDOW FLEXIBILITY

### `wellona-order-brain`:

```sql
-- Wellona_Order_Brain_v11.sql → sales_28d CTE
FROM artiklikartica ak
WHERE ak.datum >= now() - INTERVAL '28 days'  -- ❌ HARDCODED 28 days!
```

### `wph_ai`:

```sql
-- wph_core.get_orders(p_sales_window INT)
v_mv_name := format('ops._sales_%sd', p_sales_window);  -- ✅ DYNAMIC!
```

**✅ AVANTAZH:** Sistemi ynë është **më fleksibël** (7/15/30/60/180 days)!

---

## 8️⃣ SUPPLIER SELECTION LOGIC

### `wellona-order-brain`:

```sql
best_supplier AS (
    SELECT DISTINCT ON (u.sifra)
        u.sifra,
        u.dobavljac                                AS best_supplier,
        u.vpcena::numeric                          AS supplier_price,
        u.kasa1::numeric                           AS supplier_discount,
        (u.vpcena * (1 - COALESCE(u.kasa1,0)/100.0))::numeric AS final_price
    FROM artikliuslovi u
    WHERE u.vpcena IS NOT NULL
    ORDER BY
        u.sifra,
        (u.vpcena * (1 - COALESCE(u.kasa1,0)/100.0)) ASC  -- Cheapest first
)
```

### `wph_ai`:

```sql
-- wph_core.get_orders_v3() → pricefeed join
LEFT JOIN stg.pricefeed pf ON ar.barkod = pf.sifra
ORDER BY c.sifra, pf.price ASC NULLS LAST
```

**⚠️ NDRYSHIMI:**
- wellona përdor `artikliuslovi` (ERP live)
- wph_ai përdor `stg.pricefeed` (snapshot)

**Cila është më e mirë?**
- `artikliuslovi`: ✅ Real-time, ❌ Më ngadalë (FDW overhead)
- `stg.pricefeed`: ✅ Më shpejt, ❌ Duhet refresh (ETL)

---

## 9️⃣ FORMULA COMPARISON

### `wellona-order-brain`:

```sql
needed_qty_raw = GREATEST(
    (target_days - days_cover) × avg_daily_sales_28d,
    0
)
final_order_qty = CEIL(needed_qty_raw / pack_size) × pack_size
```

### `wph_ai`:

```sql
-- wph_core.get_orders()
qty_to_order = CEIL(
    GREATEST(
        0,
        effective_min - current_stock
    )
)
WHERE effective_min = CEIL(avg_daily × p_target_days)
```

**✅ IDENTIKE!** Vetëm naming ndryshon:
- `needed_qty_raw` → `effective_min - current_stock`
- `final_order_qty` → `qty_to_order`

---

## 🎯 PLAN INTEGRIMI (REKOMANDIM)

### ✅ Opsioni 1: HYBRID (RECOMMENDED)

**Strategji:**
1. ✅ Mbaj `wph_core.get_orders()` për **UI realtime**
2. ✅ Krijo `stg.order_proposal` VIEW për **ERP compatibility**
3. ✅ Shto kolonat e munguar në `get_orders()`:
   - `priority_class`
   - `cash_impact`
   - `supplier_price`
   - `supplier_discount`

**Pro:**
- ✅ Performance (FUNCTION > VIEW)
- ✅ Compatibility me wellona-order-brain
- ✅ UI e shpejtë (function call)
- ✅ Raporte ERP (VIEW query)

**Cons:**
- ⚠️ Duhet të mirëmbajmë 2 logjika (por janë identike!)

---

### ❌ Opsioni 2: VIEW ONLY

**Strategji:**
1. Importo `Wellona_Order_Brain_v11.sql` ashtu si është
2. DROP `wph_core.get_orders()`
3. UI thërret `SELECT * FROM stg.order_proposal`

**Pro:**
- ✅ 1 logjikë e vetme (VIEW)
- ✅ 100% identical me wellona-order-brain

**Cons:**
- ❌ Më ngadalë për UI (VIEW > FUNCTION)
- ❌ Nuk përdor materialized views (ops._sales_*)
- ❌ Duhet të re-scan artiklikartica çdo herë

---

### ⚠️ Opsioni 3: REPLACE EVERYTHING

**Strategji:**
1. DROP të gjitha views/functions ekzistuese
2. Importo të gjithë folder `wellona-order-brain`
3. Riskonstruo nga zero

**Pro:**
- ✅ 100% wellona-order-brain architecture

**Cons:**
- ❌ Humbasim punën e bërë në wph_core
- ❌ UI duhet të ri-shkruhet
- ❌ Materialized views (ops._sales_*) humbasin

---

## 📊 NAMING CONVENTIONS MAPPING

| wellona-order-brain | wph_ai | Recommendation |
|---------------------|--------|----------------|
| `avg_daily_sales_28d` | `avg_daily_sales` | ✅ Përdor emrin e wellona |
| `final_order_qty` | `qty_to_order` | ✅ Përdor emrin e wellona |
| `best_supplier` | `supplier_name` | ✅ Përdor emrin e wellona |
| `barcode` | `barkod` | ✅ Përdor emrin e wellona |
| `emri_artikullit` | `emri` | ✅ Përdor emrin e wellona |
| `ref.ref_supplier_terms` | `ref.supplier_terms` | ⚠️ Rename table |

---

## 🚀 NEXT STEPS (Recommended Order)

### Phase 1: ADD MISSING COLUMNS ✅
```sql
-- Modifikojmë wph_core.get_orders() që të kthejë:
ALTER FUNCTION wph_core.get_orders(...) 
RETURNS TABLE(
    sifra text,
    barcode text,                    -- 🆕 Rename barkod → barcode
    emri_artikullit text,             -- 🆕 Rename emri → emri_artikullit
    current_stock numeric,
    avg_daily_sales_28d numeric,      -- 🆕 Rename avg_daily_sales
    days_cover numeric,
    min_zaliha numeric,
    final_order_qty numeric,          -- 🆕 Rename qty_to_order
    best_supplier text,               -- 🆕 Rename supplier_name
    supplier_price numeric,           -- 🆕 NEW
    supplier_discount numeric,        -- 🆕 NEW
    final_price numeric,              -- 🆕 NEW
    cash_impact numeric,              -- 🆕 NEW
    priority_class text               -- 🆕 NEW
);
```

### Phase 2: CREATE VIEW FOR ERP COMPATIBILITY ✅
```sql
-- Importo order_proposal_view.sql (modified)
CREATE OR REPLACE VIEW stg.order_proposal AS
SELECT * FROM wph_core.get_orders(28, 30, false, NULL, NULL);
```

### Phase 3: ADD REFERENCE TABLES ✅
```sql
-- Rename dhe expand supplier_terms
ALTER TABLE ref.supplier_terms 
  ADD COLUMN credit_limit_rsd numeric(18,2),
  ADD COLUMN credit_used_rsd numeric(18,2);

-- Create banned_words table
CREATE TABLE ref.banned_words (
    id SERIAL PRIMARY KEY,
    pattern text NOT NULL,
    active boolean DEFAULT true
);
INSERT INTO ref.banned_words (pattern) VALUES
    ('IGLA'), ('IGLE'), ('SPRIC'), 
    ('RUKAVICA'), ('RUKAVICE'), 
    ('CONTOUR PLUS'), ('MASKE'), ('MASKA');
```

### Phase 4: UPDATE UI ✅
```javascript
// orders_pro_plus.html → Përditëso column names
{
    field: 'avg_daily_sales_28d',  // Ishte avg_daily_sales
    field: 'final_order_qty',      // Ishte qty_to_order
    field: 'best_supplier',        // Ishte supplier_name
    field: 'priority_class',       // 🆕 NEW column
    field: 'cash_impact'           // 🆕 NEW column
}
```

---

## ✅ COMPATIBILITY CHECKLIST

| Feature | wellona-order-brain | wph_ai | Action |
|---------|---------------------|--------|--------|
| **Data Sources** |
| artikli | ✅ | ✅ eb_fdw | ✅ OK |
| artiklikartica | ✅ | ✅ eb_fdw | ✅ OK |
| artikliuslovi | ✅ | ✅ eb_fdw | ✅ OK |
| **Schemas** |
| stg | ✅ | ✅ | ✅ OK |
| ref | ✅ | ✅ | ✅ OK |
| ops | ✅ | ✅ | ✅ OK |
| **Views** |
| stg.order_proposal | ✅ | ❌ | ⚠️ TODO: Krijo |
| **Reference Tables** |
| ref.ref_supplier_terms | ✅ | ⚠️ Partial | ⚠️ TODO: Expand |
| ref.banned_words | ✅ (hardcoded) | ❌ | ⚠️ TODO: Krijo |
| **Columns** |
| priority_class | ✅ | ❌ | ⚠️ TODO: Shto |
| cash_impact | ✅ | ❌ | ⚠️ TODO: Shto |
| supplier_price | ✅ | ❌ | ⚠️ TODO: Shto |
| supplier_discount | ✅ | ❌ | ⚠️ TODO: Shto |
| final_price | ✅ | ❌ | ⚠️ TODO: Shto |

---

## 📝 NOTES

1. **Materialized Views**: wellona NUK përdor MV (ops._sales_*), por bën `FROM artiklikartica` direkt. Kjo është **më ngadalë** por **më e thjeshtë**.

2. **Sales Window**: wellona hardcode 28 days, ne kemi dynamic (7/15/30/60/180). **Avantazhi ynë!**

3. **Supplier Source**: wellona përdor `artikliuslovi` (live), ne përdorim `stg.pricefeed` (snapshot). Duhet të vendosim: **performance vs freshness**.

4. **Priority Class**: wellona ka logjikë të thjeshtë (days_cover < 3/10). Ne mund të bëjmë më kompleks nëse duam.

5. **Target Days**: wellona përdor 15 (ERP style), por dokumentimi thotë Wellona duhet të jetë 28. **Konfuzion!**

---

## 🎓 MËSIMET E NXJERRA

1. ✅ **Infrastruktura jonë është solide** - kemi të gjitha tabelat e nevojshme
2. ⚠️ **Column naming duhet standardizuar** - wellona emrat janë më të qartë
3. ❌ **Mungojnë kolonat financiare** - cash_impact, supplier_price kritike për CFO
4. ✅ **Function vs VIEW trade-off** - Function është më e shpejtë, VIEW më e thjeshtë
5. ⚠️ **Materialized Views jo-optimale** - wellona nuk i përdor, por ne duhet!

---

## � NODE.JS API SERVER (wellona-order-brain)

### Struktura e folderit:

```
wellona-order-brain-WellonaVSCODE-main/
├── src/
│   ├── eb-core-db.js           # DB connection (PORT 5434!)
│   └── ... 
├── calculate-min-stock.js      # Auto-calculate minzaliha
├── apply-minzaliha-100.js      # Apply calculated minzaliha
├── export-recommendations-csv.js
├── ADMIN-GUIDE.md              # API usage guide
└── Wellona_Order_Brain_v11.sql # SQL schema
```

### API Endpoints (Node.js Express):

```
http://localhost:3001/api/auto-order/check-stock       # Products below min
http://localhost:3001/api/auto-order/recommendations   # Order recommendations
http://localhost:3001/api/auto-order/product/:id/forecast
http://localhost:3001/api/auto-order/execute           # Execute orders (NOT IMPLEMENTED!)
```

### ⚠️ CRITICAL ISSUE: Port Mismatch

**wellona-order-brain expects:**
```javascript
// src/eb-core-db.js
port: parseInt(process.env.EBCORE_PORT || '5434'),  // ❌ PORT 5434
database: process.env.EBCORE_DB || 'eb_core',        // ❌ DB eb_core
```

**wphAI has:**
```
PostgreSQL 18:
  - Port 5432 → wph_ai database (✅ ACTIVE)
  - Port 5433 → ebdev, ebtest (✅ ACTIVE)
  - Port 5434 → ❌ DOES NOT EXIST!

eb_core database exists on PORT 5432 (size: 754 MB)
```

### 🔧 SOLUTION OPTIONS:

#### Option A: Redirect wellona to PORT 5432
```bash
# .env file
EBCORE_HOST=localhost
EBCORE_PORT=5432          # ✅ Change from 5434 → 5432
EBCORE_DB=eb_core         # ✅ DB exists on 5432!
EBCORE_USER=postgres      # ✅ Change from 'wellona'
EBCORE_PASSWORD=0262000   # ✅ Correct password
```

#### Option B: Create PORT 5434 alias (PostgreSQL config)
```bash
# postgresql.conf
port = 5432               # Keep primary
additional_ports = 5434   # ❌ NOT SUPPORTED by PostgreSQL!
```
❌ **NOT POSSIBLE** - PostgreSQL cannot listen on multiple ports natively.

#### Option C: Use pg_bouncer (Connection Pooler)
```bash
# pgbouncer.ini
[databases]
eb_core = host=localhost port=5432 dbname=eb_core

[pgbouncer]
listen_port = 5434        # ✅ Expose on 5434
```
✅ **RECOMMENDED** nëse duam të mbajmë folder ashtu si është.

---

## �🔚 KONKLUZION

**VENDIMI:** Rekomandoj **Opsioni 1 (HYBRID) + Port Fix**

### Phase 1: Fix Port Configuration ✅
```bash
# Create .env in wellona-order-brain/
EBCORE_HOST=localhost
EBCORE_PORT=5432          # ❌ NOT 5434!
EBCORE_DB=eb_core
EBCORE_USER=postgres
EBCORE_PASSWORD=0262000
```

### Phase 2: Integrate SQL Schema ✅
- ✅ Shto kolonat e munguar në `wph_core.get_orders()`
- ✅ Krijo `stg.order_proposal` VIEW për kompatibilitet
- ✅ Expand `ref.supplier_terms` me credit management
- ✅ Krijo `ref.banned_words` table

### Phase 3: Keep Node.js Scripts (Optional) ⚠️
- ✅ `calculate-min-stock.js` - Useful për bulk updates
- ✅ `export-recommendations-csv.js` - CSV exports
- ⚠️ Node.js API server (port 3001) - **NUK NEVOJITET** (kemi Flask!)

Kjo na jep **best of both worlds**:
- ✅ Performance (function për UI)
- ✅ Compatibility (VIEW për ERP)
- ✅ Flexibility (dynamic sales_window)
- ✅ Financial intelligence (cash_impact, priority_class)
- ✅ Node.js scripts për maintenance (optional)
- ❌ **NO NEED** për Node.js API server (redundant me Flask)

**Kostoja:** ~3-4 orë punë për refactoring + port config.  
**Benefiti:** 100% kompatibilitet me wellona-order-brain + performance improvements.

---

## ⚡ IMMEDIATE ACTION ITEMS

1. ✅ **Fix port config** në wellona-order-brain folder (5434 → 5432)
2. ✅ **Import Wellona_Order_Brain_v11.sql** (modified për compatibility)
3. ✅ **Extend wph_core.get_orders()** me kolonat e reja
4. ✅ **Update UI** (orders_pro_plus.html) me kolonat e reja
5. ⚠️ **Test Node.js scripts** (optional, për maintenance)

**A vazhdoj me implementimin?** 🚀

# 📊 Organizimi i Databazës - Përmbledhje e Plotë

**Data:** 2025-11-06  
**Gjendja:** FDW ekziston por `artiklikartica` mungon, `ops._sales_30d` është BOSH (0 rreshta)

---

## 🎯 Gjendje Aktuale (Verifikuar me PG18)

### ✅ FDW Setup - EKZISTON
- **Server:** `erp93_fdw` 
- **Host:** `100.69.251.92:5432` (Tailscale IP - Wellona-Server)
- **Database:** `ebdata` (PostgreSQL 9.3)
- **Credentials:** `smart_pedja / wellona-server`

### ✅ Foreign Tables - PJESËRISHT
```sql
eb_fdw.artikli       ✅ (2426 rreshta me stanje > 0)
eb_fdw.kalkopste     ✅ (44 rreshta në 30 ditë - SHUMË PAK!)
eb_fdw.kalkstavke    ✅ 
eb_fdw.kalkkasa      ✅
eb_fdw.artiklikartica ❌ MUNGON (por ekziston në ERP me 11,607 shitje në 30 ditë!)
```

### ✅ Views & Tables
```sql
stg.stock_on_hand    ✅ VIEW → eb_fdw.artikli.stanje (STALE snapshot)
ops._sales_7d        ❌ BOSH (0 rreshta)
ops._sales_30d       ❌ BOSH (0 rreshta) 
ops._sales_180d      ❌ BOSH (0 rreshta)
```

### ✅ Functions
```sql
wph_core.get_orders(target_days, sales_window, include_zero, search_query)
  ✅ Ekziston - 4 parametra
  ❌ Nuk ka supplier filtering (5-param version)
```

---

## 📁 Skedarët e Organizimit të DB

### 1️⃣ **FDW Setup (Bazë)**
**Skedari:** `sql/01_fdw_setup.sql`
```sql
-- Krijon server erp93_fdw (idempotent)
-- Importon: artikli, promet_artikala, stanje, pos
-- Statusi: ✅ E EKZEKUTUAR (server ekziston)
```

### 2️⃣ **Fix FDW Artiklikartica** ⭐ DUHET EKZEKUTUAR
**Skedari:** `sql/fix_fdw_artiklikartica.sql`
```sql
-- Importon artiklikartica (ledger real me ulaz/izlaz)
-- Statusi: ❌ JO E EKZEKUTUAR
-- Efekti: Mundëson kalkulimin e saktë të shitjeve
```

### 3️⃣ **Sales Windows (Materialized Views)** ⭐ DUHET REFRESH
**Skedari:** `patches/sales_windows_7d_30d.sql`
```sql
-- Krijon ops._sales_7d, _sales_30d, _sales_180d
-- Burimi: eb_fdw.artiklikartica (magacin='101')
-- Formula: SUM(izlaz) / ditë
-- Statusi: ✅ VIEWS EKZISTOJNË por ❌ BOSHE (0 rreshta)
-- Shkak: artiklikartica foreign table nuk ekziston
```

### 4️⃣ **Bootstrap Ops/Stg Schemas**
**Skedari:** `patches/bootstrap_ops_stg.sql`
```sql
-- Krijon stock_on_hand VIEW
-- Krijon sales MVs nga kalkopste/kalkstavke
-- Statusi: ⚠️ Përdor kalkopste (vetëm 44 rreshta), jo artiklikartica
```

### 5️⃣ **Bootstrap Orders (Alternative)**
**Skedari:** `patches/bootstrap_orders.sql`
```sql
-- Si bootstrap_ops_stg.sql por më i plotë
-- Përdor kalkopste/kalkstavke (JO artiklikartica)
-- Statusi: ⚠️ I njëjtë problem - pak të dhëna
```

### 6️⃣ **Query Get Orders v3 (Supplier Filtering)** ⭐ DUHET DEPLOY
**Skedari:** `sql/query_get_orders_v3_with_suppliers.sql`
```sql
-- 5-param version: (target_days, sales_window, include_zero, search, suppliers[])
-- Backward compatible: 4-param overload që call 5-param me NULL suppliers
-- Statusi: ❌ JO E DEPLOYUAR (vetëm 4-param ekziston në DB)
```

### 7️⃣ **Rebuild FDW 5432**
**Skedari:** `patches/rebuild_fdw_5432.sql`
```sql
-- Ndryshon server nga 5433 → 5432
-- Importon kalkopste/kalkstavke/kalkkasa
-- Krijon eb_ro schema për app_user
-- Statusi: ⚠️ Tashmë ekzekuton 5432, por mungon artiklikartica
```

---

## 🔧 Zgjidhja: 3 Hapa të Thjeshtë

### Hapi 1: Importo `artiklikartica` në FDW
```bash
cd C:\Wellona\wphAI
$env:PGPASSWORD = "0262000"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" `
  -h 127.0.0.1 -p 5432 -U postgres -d wph_ai `
  -f sql/fix_fdw_artiklikartica.sql
```

**Rezultati:** `eb_fdw.artiklikartica` ekziston (11,607 rreshta shitjesh)

### Hapi 2: Refresh Materialized Views
```bash
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" `
  -h 127.0.0.1 -p 5432 -U postgres -d wph_ai `
  -f patches/sales_windows_7d_30d.sql
```

**Rezultati:** 
- `ops._sales_30d` → ~2000 rreshta me avg_daily > 0
- `ops._sales_7d` → ~800 rreshta
- `ops._sales_180d` → ~2500 rreshta

### Hapi 3: Deploy Supplier Filtering Function
```bash
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" `
  -h 127.0.0.1 -p 5432 -U postgres -d wph_ai `
  -f sql/query_get_orders_v3_with_suppliers.sql
```

**Rezultati:** `wph_core.get_orders()` mbështet supplier filtering

---

## 📊 Verifikime pas Ekzekutimit

```sql
-- 1. Kontrollo artiklikartica
SELECT COUNT(*) FROM eb_fdw.artiklikartica 
WHERE datum >= CURRENT_DATE - INTERVAL '30 days' AND izlaz > 0;
-- Pritet: 11607

-- 2. Kontrollo sales MVs
SELECT COUNT(*) FROM ops._sales_30d WHERE avg_daily > 0;
-- Pritet: ~2000

-- 3. Kontrollo funksionin
\df wph_core.get_orders
-- Pritet: 2 overloads (4-param dhe 5-param)

-- 4. Test qty_to_order
SELECT sifra, emri, avg_daily_sales, qty_to_order 
FROM wph_core.get_orders(28, 30, false, 'bromaz')
LIMIT 5;
-- Pritet: qty_to_order > 1 (jo vetëm 1!)
```

---

## ⚠️ Probleme të Zgjidh-ura

### ❌ Problem 1: QTY gjithmonë "1"
**Shkak:** `ops._sales_30d` është BOSH → avg_daily = 0 → formula kthen min_zaliha only  
**Zgjidhje:** Import artiklikartica + refresh MVs

### ❌ Problem 2: Stock values STALE (9,34,7 vs 14,121,14)
**Shkak:** `eb_fdw.artikli.stanje` është snapshot, jo live calculation  
**Zgjidhje:** VIEW tashmë ekziston, por snapshot duhet refresh në ERP  
**Alternative:** Krijo VIEW që llogarit nga artiklikartica (ulaz-izlaz)

### ❌ Problem 3: Supplier filtering nuk funksionon
**Shkak:** Funksioni 5-param nuk është deployed  
**Zgjidhje:** Ekzekuto `query_get_orders_v3_with_suppliers.sql`

---

## 🗂️ Struktura e Folderëve

```
wphAI/
├── sql/                          # DDL bazë dhe setup
│   ├── 01_fdw_setup.sql         ✅ E EKZEKUTUAR
│   ├── fix_fdw_artiklikartica.sql  ⭐ DUHET EKZEKUTUAR
│   ├── query_get_orders_v3_with_suppliers.sql  ⭐ DUHET EKZEKUTUAR
│   └── ...
├── patches/                      # Patches dhe migrations
│   ├── sales_windows_7d_30d.sql    ⭐ DUHET REFRESH
│   ├── bootstrap_ops_stg.sql       ⚠️ Alternative (përdor kalkopste)
│   ├── bootstrap_orders.sql        ⚠️ Alternative (përdor kalkopste)
│   └── rebuild_fdw_5432.sql        ✅ Tashmë 5432
└── docs/
    └── DB_ORGANIZATION_SUMMARY.md  📄 IKI SKEDARI
```

---

## 🚀 Quick Start (Ekzekuto në këtë rend)

```powershell
# Set environment
$PSQL = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$env:PGPASSWORD = "0262000"

# 1. Import artiklikartica
& $PSQL -h 127.0.0.1 -U postgres -d wph_ai -f sql/fix_fdw_artiklikartica.sql

# 2. Refresh sales views
& $PSQL -h 127.0.0.1 -U postgres -d wph_ai -f patches/sales_windows_7d_30d.sql

# 3. Deploy supplier filtering
& $PSQL -h 127.0.0.1 -U postgres -d wph_ai -f sql/query_get_orders_v3_with_suppliers.sql

# 4. Verify
& $PSQL -h 127.0.0.1 -U postgres -d wph_ai -c "
SELECT 'artiklikartica' AS tbl, COUNT(*) FROM eb_fdw.artiklikartica WHERE izlaz > 0
UNION ALL
SELECT 'sales_30d', COUNT(*) FROM ops._sales_30d WHERE avg_daily > 0
UNION ALL
SELECT 'get_orders', COUNT(*) FROM wph_core.get_orders(28,30,false,null) WHERE qty_to_order > 1;
"
```

---

## 📝 Shënime

1. **PostgreSQL Paths:**
   - ✅ PG 18: `C:\Program Files\PostgreSQL\18\bin\psql.exe`
   - ❌ PG 9.x (i vjetër): `C:\psql\bin\psql.exe` (no SCRAM support)

2. **FDW Connection:**
   - Local DB (wph_ai): `127.0.0.1:5432` (PG 18)
   - ERP DB (ebdata): `100.69.251.92:5432` (PG 9.3 via Tailscale)

3. **Credentials:**
   - Local: `postgres / 0262000`
   - ERP: `smart_pedja / wellona-server`

4. **Magacin ID:**
   - Main warehouse: `magacin='101'`
   - Use në sales calculations

---

**Status:** Dokumenti i kompletuar. Gati për ekzekutim në chat të ri. ✅

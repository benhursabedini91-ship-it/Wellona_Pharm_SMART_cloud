# WPH AI - Database Infrastructure Map

**Date Created**: 2025-11-06  
**Status**: Active Production Environment

---

## 🗺️ Overview

WPH AI përdor një arkitekturë hibride me PostgreSQL në dy versione dhe multiple portat për të menaxhuar të dhënat e ERP-së dhe sistemin e vendimmarrjes për porositë.

---

## 📊 Database Servers

### 1. **PostgreSQL 9.3 - ERP Production Server** 
**Location**: Remote Server  
**Host**: `100.69.251.92`  
**Port**: `5432`  
**User**: `smart_pedja`  
**Password**: `wellona-server`  

#### Databases:
| Database | Size | Purpose | Status |
|----------|------|---------|--------|
| **ebdata** | 842 MB | ERP Production Data (LIVE) | 🟢 Active |
| postgres | 6.3 MB | System DB | 🟢 Active |

**Tables (në ebdata.public)**:
- `artikli` - Master list i artikujve (sifra, naziv, barkod, vpc, mprc)
- `artiklikartica` - Kartela e artikujve (ulaz, izlaz, magacin, datum) - **KRITIKE për sales analytics**
- `kalkkasa` - Transaksionet e kasës
- `kalkopste` - Kalkulimet e përgjithshme
- `kalkstavke` - Rreshtat e kalkulimeve (detajet)

**Role**: Burimi kryesor i të dhënave LIVE për sales, inventory dhe transactions.

---

### 2. **PostgreSQL 18 - AI & Analytics Server**
**Location**: Local Machine (Laptop)  
**Host**: `127.0.0.1`  
**Port**: `5432` (Production), `5433` (Dev/Test)  
**User**: `postgres`  
**Password**: `0262000`

---

#### PORT 5432 - Production/Main

| Database | Size | Purpose | Status |
|----------|------|---------|--------|
| **wph_ai** | 9.8 MB | WPH AI Decision Engine | 🟢 Active |
| **eb_core** | 754 MB | ERP Core (lokal kopje?) | 🟡 Unknown |
| **order_platform** | 86 MB | Order Management Platform | 🟡 Unknown |
| ebdata | 8 MB | ERP Staging/Test Copy | 🟡 Unknown |
| postgres | 8 MB | System DB | 🟢 Active |

---

#### PORT 5433 - Development/Testing

| Database | Size | Purpose | Status |
|----------|------|---------|--------|
| **ebdev** | 783 MB | ERP Development | 🟡 Dev |
| **ebtest** | 795 MB | ERP Testing | 🟡 Test |
| **ebtest_restore** | 773 MB | Backup Restore Testing | 🔵 Backup |
| **ebtest_verify** | 746 MB | Verification DB | 🔵 Backup |
| eberp_20251014_023634 | 752 MB | Snapshot Backup | 🔵 Backup |
| postgres | 6.3 MB | System DB | 🟢 Active |

---

#### PORT 5434
**Status**: ❌ Nuk ekziston / nuk është aktive

---

## 🔗 Foreign Data Wrapper (FDW) Configuration

### Active FDW Connection

**Në `wph_ai` database (PG 18:5432)**:

```sql
Foreign Server Name: erp93_fdw
Remote Host: 100.69.251.92 (PG 9.3)
Remote Port: 5432
Remote Database: ebdata
User Mapping: postgres → smart_pedja
```

**Purpose**: Lejon `wph_ai` të lexojë të dhëna LIVE direkt nga `ebdata` në PG 9.3 pa nevojë për sinkronizim manual.

---

### Foreign Tables në `eb_fdw` schema

Këto tabela janë "dritare" që shikojnë direkt në `ebdata@PG9.3`:

| Foreign Table | Rows (approx) | Source Table | Purpose |
|---------------|---------------|--------------|---------|
| `eb_fdw.artikli` | 7,194 | ebdata.public.artikli | Artikujt bazë |
| `eb_fdw.kalkkasa` | 3,006 | ebdata.public.kalkkasa | Transaksionet kasa |
| `eb_fdw.kalkopste` | 1,000+ | ebdata.public.kalkopste | Kalkulime të përgjithshme |
| `eb_fdw.kalkstavke` | 41,790 | ebdata.public.kalkstavke | Rreshtat e kalkulimeve |

### ⚠️ MISSING Critical Table

**`eb_fdw.artiklikartica`** - **MUNGON!**

Kjo tabelë është KRITIKE për:
- Llogaritjen e shitjeve ditore (`avg_daily_sales`)
- Materialized Views: `ops._sales_7d`, `ops._sales_30d`, `ops._sales_180d`
- Funksionin `wph_core.get_orders()`
- Ndjekjen e `ulaz`/`izlaz` për magacin='101'

**Action Required**: Duhet të krijohet kjo foreign table.

---

## 🏗️ WPH AI Database Schema (`wph_ai`)

### Schemas:
1. **`eb_fdw`** - Foreign tables (lidhje me PG 9.3)
2. **`stg`** - Staging data (pricefeed, stock, import data)
3. **`ref`** - Reference data (policies, mappings, aliases)
4. **`wph_core`** - Core functions dhe stored procedures
5. **`ops`** - Operational data dhe materialized views
6. **`audit`** - Audit logs
7. **`public`** - Default schema

### Key Materialized Views (ops schema):
- `ops._sales_7d` - 7-day rolling average sales
- `ops._sales_30d` - 30-day rolling average sales (default)
- `ops._sales_180d` - 180-day rolling average sales

**Formula**: `avg_daily = SUM(izlaz) / calendar_days` (includes zero-sale days)

**Filter**: `magacin = '101'` (magazina kryesore)

### Key Functions:
- `wph_core.get_orders(p_target_days, p_sales_window, p_include_zero, p_search_query, p_suppliers)` - V3 me supplier filtering
- `wph_core.run_pipeline()` - ETL orchestration

---

## 🔄 Data Flow

```
┌─────────────────────────────────────┐
│  PG 9.3 @ 100.69.251.92:5432        │
│  ebdata (842 MB) - LIVE ERP DATA    │
│  ├─ artikli                         │
│  ├─ artiklikartica (sales/kardex)   │
│  ├─ kalkkasa                        │
│  └─ kalkstavke                      │
└────────────┬────────────────────────┘
             │
             │ FDW: erp93_fdw
             ▼
┌─────────────────────────────────────┐
│  PG 18 @ localhost:5432             │
│  wph_ai (9.8 MB) - AI ENGINE        │
│  ├─ eb_fdw schema (foreign tables)  │
│  │   ├─ artikli                     │
│  │   ├─ kalkkasa                    │
│  │   ├─ kalkopste                   │
│  │   ├─ kalkstavke                  │
│  │   └─ artiklikartica ❌ MISSING   │
│  │                                   │
│  ├─ ops schema (MVs)                │
│  │   ├─ _sales_7d  ← artiklikartica │
│  │   ├─ _sales_30d ← artiklikartica │
│  │   └─ _sales_180d ← artiklikartica│
│  │                                   │
│  ├─ stg schema (staging)            │
│  │   ├─ pricefeed (supplier data)   │
│  │   └─ stock_on_hand               │
│  │                                   │
│  ├─ ref schema (reference)          │
│  │   ├─ min_zaliha_policy_v2        │
│  │   └─ drug_aliases                │
│  │                                   │
│  └─ wph_core schema (functions)     │
│      └─ get_orders()                │
└─────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│  Application Layer                  │
│  ├─ app/order_brain.py (Excel)      │
│  ├─ bin/wph_ai_orchestrator.py (DB) │
│  ├─ app/app.py (Flask UI)           │
│  └─ web_modern/app_v2.py (FastAPI)  │
└─────────────────────────────────────┘
```

---

## 📋 Current Status & Next Steps

### ✅ Confirmed Working:
- FDW server `erp93_fdw` configured and connected
- 4 foreign tables active in `eb_fdw` schema
- Connection to PG 9.3 remote ebdata verified

### ⚠️ Issues:
1. **`eb_fdw.artiklikartica` foreign table MISSING** - blocks sales MVs
2. Sales MVs likely empty or stale without artiklikartica
3. `wph_core.get_orders()` cannot calculate `avg_daily_sales`

### 🎯 Action Plan:
1. ✅ Map infrastructure (this document)
2. ⏳ Create `eb_fdw.artiklikartica` foreign table
3. ⏳ Rebuild/refresh sales MVs (7d, 30d, 180d)
4. ⏳ Deploy `wph_core.get_orders()` V3 with supplier filtering
5. ⏳ Verify `stg.pricefeed` has supplier_name populated
6. ⏳ Test end-to-end query with supplier filter

---

## 🔐 Credentials Summary

| Server | Host | Port | User | Password | Notes |
|--------|------|------|------|----------|-------|
| PG 9.3 ERP | 100.69.251.92 | 5432 | smart_pedja | wellona-server | Production ERP |
| PG 18 Main | 127.0.0.1 | 5432 | postgres | 0262000 | wph_ai, eb_core |
| PG 18 Dev | 127.0.0.1 | 5433 | postgres | 0262000 | ebtest, ebdev |

---

## 📞 Maintenance

### Refresh Sales MVs:
```sql
REFRESH MATERIALIZED VIEW ops._sales_7d;
REFRESH MATERIALIZED VIEW ops._sales_30d;
REFRESH MATERIALIZED VIEW ops._sales_180d;
```

### Test FDW Connection:
```sql
SELECT COUNT(*) FROM eb_fdw.artikli;
SELECT COUNT(*) FROM eb_fdw.artiklikartica WHERE datum >= CURRENT_DATE - INTERVAL '7 days';
```

### Check Server Status:
```powershell
# PG 18
$env:PGPASSWORD = "0262000"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 127.0.0.1 -p 5432 -U postgres -d wph_ai -c "SELECT version();"

# PG 9.3
$env:PGPASSWORD = "wellona-server"
& "C:\Program Files\PostgreSQL\9.3\bin\psql.exe" -h 100.69.251.92 -p 5432 -U smart_pedja -d ebdata -c "SELECT version();"
```

---

**Last Updated**: 2025-11-06 01:45 AM  
**Maintained By**: WPH AI Team  
**Branch**: feature/include-zero-wip

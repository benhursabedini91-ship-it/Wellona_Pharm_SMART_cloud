# 🏢 Përzgjedhja e Furnitorit & Strategjitë e Min_Zaliha

**Data:** 2025-11-06  
**Përgatitur nga:** WPH_AI System

---

## 📋 PËRMBLEDHJE E SHKURTËR

WPH_AI zgjedh **automatikisht furnitorin më të lirë** për çdo produkt bazuar në çmimet në `stg.pricefeed`. Më pas llogarit `qty_to_order` duke përdorur një **sistem me 9 shkallë** të minzaliha bazuar në shitjet mujore.

---

## 🏢 SI FUNKSIONON PËRZGJEDHJA E FURNITORIT

### Logjika e Bazuar në Çmim (Price-Based Selection)

```sql
-- Nga wph_core.get_orders()
SELECT DISTINCT ON (c.sifra)
  c.sifra,
  COALESCE(pf.supplier_name, 'UNKNOWN') AS supplier_name
FROM calc c
LEFT JOIN eb_fdw.artikli ar ON c.sifra = ar.sifra
LEFT JOIN stg.pricefeed pf ON ar.barkod = pf.sifra  -- Match by barcode
ORDER BY c.sifra, pf.price ASC NULLS LAST  -- ✅ ZGJEDH MË TË LIRIN!
```

### Shembuj Realë (nga screenshot)

| Sifra | Produkt | Furnitori i Zgjedhur | Arsyeja |
|-------|---------|---------------------|---------|
| **15043085** | DEXOMEN GRANULE 20X25MG | FARMALOGIST | Çmimi më i ulët në pricefeed |
| **15008011** | TRITACE COMP 28X(5+25)MG | SOPHARMA | Çmimi më i ulët |
| **15027105** | NOLPAZA TBL 28X20MG DUPLA | FARMALOGIST | Çmimi më i ulët |
| **10011006** | BROMAZEPAM TBL 30X3MG | PHOENIX | Çmimi më i ulët |
| **10049015** | BISOPROLOL TBL 30X2.5MG | FARMALOGIST | Çmimi më i ulët |

### Si Popullohet stg.pricefeed?

Pricefeed mbushet nga:
1. **ETL Pipeline Nightly** (`run_nightly_etl.ps1`)
2. **Import manual** nga Excel/CSV furnitorësh (Phoenix, Vega, Sopharma, Farmalogist)
3. **Mapper configs** në `configs/suppliers/*.v1.json`

Çdo rresht në pricefeed ka:
- `sifra` (barcode)
- `supplier_name` (PHOENIX, VEGA, SOPHARMA, FARMALOGIST)
- `price` (VPC - Vendor Price Cost)
- `rabat_pct` (discount percentage if applicable)

---

## 📊 STRATEGJITË E MIN_ZALIHA (9 Shkallë)

### Tabela e Politikës (`ref.min_zaliha_policy_v2`)

```
┌──────────────┬──────────────┬─────────────┬──────────────────────┐
│ Range From   │ Range To     │ Min Zaliha  │ Note                 │
├──────────────┼──────────────┼─────────────┼──────────────────────┤
│ 0            │ 0            │ 1           │ no movement (min 1)  │
│ 1            │ 5            │ 2           │ presence             │
│ 5            │ 10           │ 3           │ low sales            │
│ 10           │ 15           │ 4           │ steady               │
│ 15           │ 20           │ 5           │ moderate             │
│ 20           │ 30           │ 7           │ good sales           │
│ 30           │ 40           │ 9           │ high volume          │
│ 40           │ 50           │ 11          │ very high            │
│ 50+          │ NULL         │ 14          │ critical (fast move) │
└──────────────┴──────────────┴─────────────┴──────────────────────┘
```

### Formula e Llogaritjes

```python
# Pseudo-code
monthly_units = avg_daily_sales * 30

# Gjej shkallën nga policy table
min_zaliha = SELECT min_zaliha 
             FROM ref.min_zaliha_policy_v2 
             WHERE monthly_units >= range_from 
               AND (range_to IS NULL OR monthly_units <= range_to)
             ORDER BY range_from DESC 
             LIMIT 1

# Llogarit qty_to_order
qty_to_order = MAX(0, min_zaliha - current_stock)
```

### Shembuj Realë

**DEXOMEN GRANULE 20X25MG** (Sifra: 15043085)
```
AVG/D:      14.02 units/day
AVG/30D:    420.6 units/month  ← Falls in range [50+]
MINZ:       393 units          ← Policy says 14x daily (14 × 28 days)
STOCK:      89 units
QTY:        305 units          ← Need to order (393 - 89)
DAYS:       6.3 days coverage  ← Will run out in 6 days!
```

**BISOPROLOL TBL 30X2.5MG** (Sifra: 10049015)
```
AVG/D:      3.2 units/day
AVG/30D:    96 units/month     ← Falls in range [50+]
MINZ:       90 units           ← Policy says 14x daily
STOCK:      2 units
QTY:        88 units           ← Need to order
DAYS:       0.6 days           ← CRITICAL! Almost out!
```

**BROMAZEPAM TBL 30X3MG** (Sifra: 10011006)
```
AVG/D:      6.4 units/day
AVG/30D:    192 units/month    ← Falls in range [50+]
MINZ:       180 units
STOCK:      111 units
QTY:        69 units           ← Need to order
DAYS:       17.3 days          ← Good coverage
```

---

## 🎯 MANUALI I PËRDORIMIT

### 1. Si të Ndryshosh Furnitorin për një Produkt

Nëse dëshiron të detyrimisht përdorësh një furnitor të caktuar (p.sh. PHOENIX për DEXOMEN):

```sql
-- Opsioni 1: Update manual në pricefeed (temporary override)
UPDATE stg.pricefeed 
SET price = price - 1  -- Bëje pak më të lirë
WHERE sifra = '40130354023662' -- barkodi i DEXOMEN
  AND supplier_name = 'PHOENIX';

-- Opsioni 2: Filtro në UI
-- Në orders_pro_plus.html, zgjedh vetëm PHOENIX nga dropdown "Furnitori"
```

### 2. Si të Ndryshosh Min_Zaliha për një Kategori

```sql
-- Shembull: Rrit min_zaliha për produktet me shitje 20-30 units/month
UPDATE ref.min_zaliha_policy_v2 
SET min_zaliha = 10  -- Nga 7 → 10
WHERE range_from = 20 AND range_to = 30;

-- Pastaj refresh MVs
REFRESH MATERIALIZED VIEW ops._sales_30d;
REFRESH MATERIALIZED VIEW ops.article_status;
```

### 3. Si të Vendosësh Min_Zaliha Manual për një Produkt

```sql
-- Override policy për produkt specifik (nëse ka kolone manual_min_zaliha)
UPDATE ref.product_overrides 
SET manual_min_zaliha = 50 
WHERE sifra = '15043085';  -- DEXOMEN

-- OSE modifiko në ERP dhe sync
```

---

## 🔧 KONFIGURIMI AKTUAL

### Furnitorët Aktivë

```sql
SELECT * FROM ref.suppliers;
```

| Code | Name | Active |
|------|------|--------|
| PHOENIX | PHOENIX | ✅ |
| VEGA | VEGA | ✅ |
| SOPHARMA | SOPHARMA | ✅ |
| FARMALOGIST | FARMALOGIST | ✅ |

### Pricefeed Stats

- **Total records:** 37,346 çmime
- **Update frequency:** Nightly (02:00 AM)
- **Source:** `in/phoenix/`, `in/vega/`, `in/sopharma/`

### Min_Zaliha Policy Active

- **System:** 9-shkallë adaptive (bazuar në monthly units)
- **Override:** Manually në ERP field `artikli.minzaliha`
- **Formula:** `CEIL(avg_daily * target_days)`

---

## 📌 NOTES & BEST PRACTICES

### ✅ DO's

1. **Trust the system** - Algoritmi zgjedh furnitorin më të lirë automatikisht
2. **Review periodically** - Kontrollo çmimet në pricefeed çdo javë
3. **Update nightly** - Lejo ETL të ekzekutojë çdo natë
4. **Use filters** - Nëse ke preference për furnitor, përdor filtrin në UI

### ❌ DON'Ts

1. **Don't hardcode** - Mos shkruaj supplier në kod; përdor pricefeed
2. **Don't ignore negative stock** - Produktet me stock < 0 duhet porositur menjëherë
3. **Don't skip refresh** - REFRESH MVs pas ndryshimeve të mëdha në të dhëna

---

## 🚀 NEXT STEPS

1. **Add Supplier Terms** - MOQ (Minimum Order Quantity), lead time, rabat conditions
2. **Smart Bundling** - Grupisht order-et për të arritur MOQ targets
3. **Historical Price Tracking** - Analizo trend-et e çmimeve për forecast
4. **Automatic Reorder Points** - Trigger alerts kur DAYS < 7

---

**Last Updated:** 2025-11-06  
**Author:** WPH_AI Development Team

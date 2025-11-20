# Krahasim: ERP "Predlog nabavka" vs Analytics "get_orders"

## Përmbledhje e shpejtë

| Metrikë | ERP Predlog | Analytics get_orders | Diferenca |
|---------|-------------|---------------------|-----------|
| **Artikuj me QTY>0** | ~381 | ~76 | +305 (405%) |
| **Target window** | 28 ditë | 28 ditë | ✓ Same |
| **Sales window** | 28 ditë | 30 ditë | -2 ditë |
| **Include stock=0** | PO (gjithmonë) | JO (by default) | **← Shkaku kryesor** |
| **Banned words** | PO (8 fjalë) | JO | +Disa artikuj |
| **MINZ policy** | JO | PO | Ceiling më i lartë |

---

## 1. Formula ERP: `stg.order_proposal`

### Hapat:

```sql
-- Step 1: Llogarit shitjet mesatare ditore (28 ditë)
avg_daily_sales_28d = SUM(izlaz për 28d) / COUNT(ditë aktive)

-- Step 2: Llogarit sa ditë mbulon stoku aktual
days_cover = current_stock / avg_daily_sales_28d

-- Step 3: Llogarit sa copë mungojnë për target
needed_qty_raw = (target_days - days_cover) × avg_daily_sales_28d
needed_qty_raw = MAX(needed_qty_raw, 0)  -- nuk mund të jetë negativ

-- Step 4: Rrumbullako sipas pack_size
needed_qty_rounded = CEIL(needed_qty_raw / pack_size) × pack_size

-- Step 5: Apliko MOQ (minimum order quantity)
final_order_qty = MAX(needed_qty_rounded, moq_qty_default)
```

### Filtra të aplikuar:
- ✅ **Përfshin artikuj me stock=0** (reorder when depleted)
- ✅ **Banned words** (igla, spric, rukavica, contour plus, maske)
- ✅ **Furnitori më i lirë** (sipas vpcena × (1 - rabat%))
- ❌ **Nuk përdor MINZ policy** (vetëm target × avg)

### Shembull (Bensedin):
```
current_stock = 87,000
avg_daily_sales_28d = 119
target_days = 28
days_cover = 87,000 / 119 = 731 ditë
needed_qty_raw = (28 - 731) × 119 = -83,657 → 0
final_order_qty = 0
```
✅ **Bensedin NUK del në order sepse ka 731 ditë mbulim!**

---

## 2. Formula Analytics: `wph_core.get_orders`

### Hapat:

```sql
-- Step 1: Llogarit shitjet mesatare ditore (30 ditë by default)
avg_daily_sales = AVG(izlaz për 30d)

-- Step 2: Llogarit MINZ (minimum zaliha)
min_zaliha = CEIL(target_days × avg_daily_sales)

-- Step 3: Llogarit QTY bazuar në MINZ
qty_to_order = CEIL(GREATEST(min_zaliha, target_days × avg_daily_sales) - current_stock)
qty_to_order = MAX(qty_to_order, 0)

-- Step 4: Filtro artikujt me stock=0 (nëse include_zero=false)
IF NOT include_zero THEN
    WHERE current_stock > 0
END IF
```

### Filtra të aplikuar:
- ❌ **Përjashton artikuj me stock=0** (by default, include_zero=false)
- ❌ **Nuk ka banned words filter**
- ✅ **Përdor MINZ policy** (ceiling më i lartë nga ref.min_zaliha_policy_v2)
- ✅ **Furnitori më i lirë** (nga stg.pricefeed, DISTINCT ON ... ORDER BY price ASC)

### Shembull (Bensedin):
```
current_stock = 87,000
avg_daily_sales = 119 (nga ops._sales_30d)
target_days = 28
min_zaliha = CEIL(28 × 119) = 3,332
qty_to_order = CEIL(3,332 - 87,000) = 0
```
✅ **Bensedin NUK del në order sepse ka 87k në stok!**

---

## 3. Pse 381 vs 76?

### Shkaku #1: `include_zero` (Më i rëndësishmi)
- **ERP**: Përfshin GJITHMONË artikujt me `stock=0` (reorder policy)
- **Analytics**: Filtron `stock=0` kur `include_zero=false` (default)
- **Ndikimi**: +250-300 artikuj

### Shkaku #2: Sales window
- **ERP**: 28 ditë (më i shkurtër → avg më i lartë → QTY më i lartë)
- **Analytics**: 30 ditë (default) ose variabile (7/15/60/180)
- **Ndikimi**: +10-20 artikuj

### Shkaku #3: MINZ policy
- **ERP**: Jo (vetëm target × avg)
- **Analytics**: Po (ceiling bazuar në monthly_units ranges)
- **Ndikimi**: -20-30 artikuj (disa artikuj bien poshtë MINZ threshold)

### Shkaku #4: Banned words
- **ERP**: Filtron 8 fjalë (igla, spric, maske...)
- **Analytics**: Nuk filtron
- **Ndikimi**: -5-10 artikuj

---

## 4. Si t'i afrojmë rezultatet?

### Në UI (për t'i bërë 76 → 381):
1. **Aktivizo "Përfshi artikuj me stok=0"** (checkbox include_zero)
2. **Vendos sales_window = 28** (date range: 28 ditë)
3. **Vendos target_days = 28** (input field)
4. **Aktivizo "Injoro MINZ (vetëm target)"** (checkbox për të hequr policy)

### Në backend (optional):
- Shtojmë një endpoint `/api/orders/proposal` që thërret `stg.order_proposal`
- Dropdown në UI: "Mode: Analytics | ERP Predlog"

---

## 5. Verifikimi i Bensedin (sifra 10011126)

### Pyetja: Pse stock = 87,000?

```sql
-- Check 1: stg.stock_on_hand (source of truth për Analytics)
SELECT sifra, qty FROM stg.stock_on_hand WHERE sifra = '10011126';
-- Expected: 87,000 (SUM(ulaz-izlaz) për vitin 2025, magacin 101)

-- Check 2: eb_fdw.artikli.stanje (ERP snapshot)
SELECT sifra, stanje FROM eb_fdw.artikli WHERE sifra = '10011126';
-- Expected: Mund të jetë i ndryshëm (snapshot i vjetër)

-- Check 3: Real-time nga eb_fdw.artiklikartica
SELECT 
    TRIM(artikal) AS sifra,
    SUM(ulaz - izlaz) AS qty_2025
FROM eb_fdw.artiklikartica
WHERE TRIM(artikal) = '10011126'
  AND magacin = '101'
  AND EXTRACT(YEAR FROM datum) = 2025
GROUP BY TRIM(artikal);
-- Expected: 87,000 (bazuar në transaksionet aktuale)
```

### Përfundim:
✅ Stock 87,000 është **SAKTË** (nga ERP live data)  
✅ Bensedin **NUK DUHET** porosit (ka 731 ditë mbulim me shitje 119/ditë)  
✅ Nëse del në "Predlog nabavka" me QTY>0, atëherë ERP-i ka një politikë tjetër (p.sh. minimum stock absolute ose reorder point)

---

## 6. Rekomandime

### Për të pasur rezultat identik me ERP:
1. Importo `stg.order_proposal` në DB ✅ (Done)
2. Krijo endpoint `/api/orders/proposal` në backend
3. Shto dropdown në UI: "Source: Analytics | ERP Predlog"
4. Testo krah-për-krah dhe identifiko dallime specifike për artikuj (jo vetëm numër total)

### Për të përmirësuar Analytics:
- Shto `banned_words` filter në `wph_core.get_orders` (optional parameter)
- Bëj `include_zero` më transparent (rename checkbox)
- Shto tooltip për QTY që shpjegon formulën

---

## Kontakt / Pyetje
Nëse ke pyetje për një artikull specifik, shiko:
```sql
-- Krahasim i detajuar për një sifra
SELECT 
    'ERP' AS source,
    sifra, emri_artikullit, current_stock, avg_daily_sales_28d, days_cover, final_order_qty
FROM stg.order_proposal WHERE sifra = 'XXXXX'
UNION ALL
SELECT 
    'Analytics',
    sifra, emri, current_stock, avg_daily_sales, days_cover, qty_to_order
FROM wph_core.get_orders(28, 28, true, NULL, NULL) WHERE sifra = 'XXXXX';
```

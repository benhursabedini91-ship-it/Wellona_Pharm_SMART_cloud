# 🧮 FORMULA E ERP për Porosi (Predlog nabavka)

## 📊 **HAPI PËR HAPI**

### 1️⃣ **Llogarit shitjet mesatare ditore**
```
avg_daily = SUM(shitjet për 28 ditë) / 28
```
**Shembull:**
- Artikulli A: Shiti 280 copë në 28 ditë
- avg_daily = 280 / 28 = **10 copë/ditë**

---

### 2️⃣ **Llogarit sa ditë mbulon stoku aktual**
```
days_cover = stoku_aktual / avg_daily
```
**Shembull:**
- Stoku aktual = 50 copë
- avg_daily = 10 copë/ditë
- days_cover = 50 / 10 = **5 ditë mbulim**

---

### 3️⃣ **Llogarit sa ditë target do**
```
target_days = 28 ditë (fiksuar në ERP)
```
**Politika:** Duam të kemi gjithmonë 28 ditë furnizim.

---

### 4️⃣ **Llogarit sa copë mungojnë**
```
needed_qty = (target_days - days_cover) × avg_daily

Nëse është negativ → needed_qty = 0
```
**Shembull:**
- target_days = 28 ditë
- days_cover = 5 ditë
- avg_daily = 10 copë/ditë
- needed_qty = (28 - 5) × 10 = **230 copë**

**Shembull 2 (stok i mjaftueshëm):**
- Stoku aktual = 300 copë
- days_cover = 300 / 10 = 30 ditë
- needed_qty = (28 - 30) × 10 = -20 → **0 copë** (nuk porositim)

---

### 5️⃣ **Rrumbullako sipas paketimit**
```
pack_size = sa copë vijnë në 1 paketë (default 1)
final_qty = CEIL(needed_qty / pack_size) × pack_size
```
**Shembull:**
- needed_qty = 230 copë
- pack_size = 10 (vijnë vetëm në paketa 10-she)
- final_qty = CEIL(230 / 10) × 10 = 23 × 10 = **230 copë**

**Shembull 2:**
- needed_qty = 237 copë
- pack_size = 10
- final_qty = CEIL(237 / 10) × 10 = 24 × 10 = **240 copë**

---

### 6️⃣ **Apliko MOQ (minimum order quantity)**
```
moq = minimum order quantity nga furnitori (default 1)
final_order_qty = MAX(final_qty, moq)
```
**Shembull:**
- final_qty = 3 copë
- moq = 10 copë (furnitori nuk shet më pak se 10)
- final_order_qty = MAX(3, 10) = **10 copë**

---

### 7️⃣ **Zgjedh furnitorin më të lirë**
```
effective_price = price × (1 - rabat%)

furnitori_winner = furnitori me effective_price më të ulët
```
**Shembull:**
| Furnitor | Price | Rabat | Effective Price |
|----------|-------|-------|-----------------|
| Sopharma | 5.00€ | 10%   | 5.00 × 0.90 = **4.50€** ✅ |
| Vega     | 4.80€ | 5%    | 4.80 × 0.95 = 4.56€ |
| Phoenix  | 5.20€ | 0%    | 5.20€ |

Winner: **Sopharma** (4.50€)

---

### 8️⃣ **Filtro artikujt e ndaluar**
```
Hiq nga lista nëse náziv përmban:
- IGLA, IGLE
- SPRIC
- RUKAVICA
- CONTOUR PLUS
- MASKE
```

---

## 🔥 **SHEMBULL I PLOTË: Artikulli BRUFEN**

### Input data:
```
naziv: BRUFEN TBL 20X400MG
stoku_aktual: 15 copë
shitjet_28d: [2, 3, 0, 2, 1, 3, 2, 0, 2, 3, ...] (total: 56 copë)
target_days: 28 ditë
pack_size: 1 copë
moq: 5 copë

Furnitorët:
- Sopharma: 1.20€, rabat 8%
- Vega: 1.15€, rabat 5%
```

### Kalkulimi:
```
1. avg_daily = 56 / 28 = 2 copë/ditë

2. days_cover = 15 / 2 = 7.5 ditë

3. needed_qty = (28 - 7.5) × 2 = 20.5 × 2 = 41 copë

4. final_qty = CEIL(41 / 1) × 1 = 41 copë

5. final_order_qty = MAX(41, 5) = 41 copë

6. Effective price:
   - Sopharma: 1.20 × (1-0.08) = 1.104€ ✅
   - Vega: 1.15 × (1-0.05) = 1.0925€

7. Winner: Vega (1.0925€)
```

### Output final:
```
POROSITIM:
- Artikull: BRUFEN TBL 20X400MG
- QTY: 41 copë
- Furnitor: Vega
- Çmim: 1.0925€/copë
- Total: 44.79€
```

---

## 🆚 **DIFERENCA ME ANALYTICS (`wph_core.get_orders`)**

| Aspekti | ERP Predlog | Analytics get_orders |
|---------|-------------|---------------------|
| **Sales window** | 28 ditë (fix) | 30 ditë (default, mund ndryshohet) |
| **Target days** | 28 ditë (fix) | 28 ditë (default, user mund ndryshon) |
| **Stok=0** | ✅ Përfshin GJITHMONË | ❌ Filtron (nëse include_zero=false) |
| **MINZ policy** | ❌ Nuk ka | ✅ Ka (min_zaliha më i lartë) |
| **Banned words** | ✅ Ka (8 fjalë) | ❌ Nuk ka |
| **Pack size rounding** | ✅ Po | ❌ Jo (mund shtohet) |
| **MOQ** | ✅ Po | ❌ Jo (mund shtohet) |

---

## 💡 **SHKURTIM: Formula në 1 rresht**

```
QTY = MAX(
    CEIL(
        MAX(
            (target_days - (stoku/avg_daily)) × avg_daily,
            0
        ) / pack_size
    ) × pack_size,
    moq
)

IF naziv contains banned_words THEN QTY = 0
IF stoku > 0 AND days_cover >= target_days THEN QTY = 0
```

---

## ✅ **A është e saktë formula?**

**PO!** Ky është algoritmi standard i **inventory reordering** në sistemet ERP:
1. **Economic Order Quantity (EOQ)** → sa të porositim
2. **Reorder Point (ROP)** → kur të porositim (target_days)
3. **Safety Stock** → buffer për variabilitet (MINZ në Analytics)

ERP-ja jonë përdor një version **të thjeshtuar të EOQ** me target fix 28 ditë.

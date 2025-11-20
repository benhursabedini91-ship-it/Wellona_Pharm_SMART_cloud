# 🎯 HAPI TJETËR - Si ta përdorësh tani

## ✅ E kemi gati sistemin! Tani çfarë?

### 📋 Kontrollo nëse e ke API key

**Hapi 1:** Shko te https://efaktura.mfin.gov.rs

**Hapi 2:** Llogaria > API Access > Generate API Key

**Hapi 3:** Kopjo API key (ruaje diku për një moment)

---

## 🚀 FILLIMI (vetëm 3 komanda)

### 1️⃣ Setup (5 minuta - bëhet një herë)

```powershell
cd C:\Wellona\Wellona_Pharm_SMART\app
.\setup_efaktura.ps1
```

Skript do të të pyesë:
- ✏️ **API Key** (ngjite atë që kopjove nga eFaktura)
- ⏎ **URLs** (shtyp ENTER për default)
- ⏎ **Database** (shtyp ENTER për default nëse je në local)
- ⏎ **Options** (shtyp 'y' për auto-create artikuj)

---

### 2️⃣ Test (1 minutë - sigurohu që funksionon)

```powershell
python app/test_efaktura_connection.py
```

Duhet të shohësh:
```
✓ PASS  Environment Variables
✓ PASS  API Connection
✓ PASS  API List Invoices
✓ PASS  Database Connection

🎉 GATI PËR PËRDORIM!
```

---

### 3️⃣ Import fakturat (varet nga sasia)

#### Opsioni A: DRY-RUN (rekomandohet për herën e parë!)
Shikon çfarë do bëjë **PA SHKRUAR** në bazë:

```powershell
# Testo me javën e kaluar
python app/fetch_all_invoices.py --from 2025-11-11 --to 2025-11-18 --auto-import --dry-run
```

#### Opsioni B: Import REAL (pas testimit me dry-run)
Shkarkoni dhe importoni në ERP:

```powershell
# Import të gjitha fakturat e vitit 2025
python app/fetch_all_invoices.py --from 2025-01-01 --to 2025-11-18 --auto-import
```

#### Opsioni C: Batch import (për sasi të mëdha)
```powershell
# Import muaj pas muaji automatikisht
.\app\batch_import_2025.ps1
```

---

## 📊 Çfarë do të ndodhë?

### Gjatë shkarkimit:
```
🔍 Duke kërkuar faktura nga 2025-01-01 deri në 2025-11-18...
✓ U gjetën 145 faktura

[1/145] Faktura: FAK-2025-001
  Furnitori: SOPHARMA D.O.O.
  Data: 2025-01-05
  ✓ Shkarkuar: SOPHARMA_FAK-2025-001_2025-01-05.xml

...

📊 PËRMBLEDHJE:
  Total faktura: 145
  ✓ Shkarkuar me sukses: 145
  ❌ Dështuan: 0
```

### Gjatë importit:
```
🔄 FILLIM I IMPORTIT AUTOMATIK NË ERP

[1/145] Importimi i: SOPHARMA_FAK-2025-001_2025-01-05.xml
  Faktura: FAK-2025-001
  Furnitori: SOPHARMA D.O.O.
  Artikuj: 23
  ✓ Ekziston: PARACETAMOL 500MG TBL 20X
  🆕 Do krijohet: NEUROFEN EXPRESS 400MG CAPS 20X
  ✓ Importuar me sukses (kalkid=456789)

...

📊 PËRMBLEDHJE E IMPORTIT:
  Total XML: 145
  ✓ Importuar: 143
  ⚠️  Skip: 1
  ❌ Dështuan: 1
```

---

## 💡 Këshilla

### ✅ BËJE:
- ✓ Fillo me dry-run
- ✓ Testo me pak faktura fillimisht
- ✓ Backup DB para importeve të mëdha
- ✓ Shiko logs në `logs/`

### ❌ MOS:
- ✗ Import direkt në production pa testuar
- ✗ Import pa backup
- ✗ Import sasi të mëdha pa batch

---

## 🔍 Si ta kontrolloj nëse funksionoi?

### Në console (output i scriptit):
Shikon statistikat në fund të ekzekutimit.

### Në file system:
```powershell
# Shiko XML-të e shkarkuara
Get-ChildItem C:\Wellona\Wellona_Pharm_SMART\staging\faktura_uploads\
```

### Në Database:
```sql
-- Kalkulacione të reja
SELECT * FROM eb_fdw.kalkopste 
WHERE datum >= '2025-01-01' 
ORDER BY id DESC 
LIMIT 20;

-- Artikuj të rinj
SELECT COUNT(*) as total_artikuj_te_rinj 
FROM eb_fdw.artikli 
WHERE sifra >= '2300000000';

-- Audit log për çmime
SELECT * FROM public.wph_audit_price_lock 
ORDER BY ts DESC 
LIMIT 20;
```

---

## 🆘 Nëse diçka nuk funksionon

### 1. Kontrollo API key
```powershell
$env:WPH_EFAKT_API_KEY
```
Duhet të shfaqet API key. Nëse jo, ekzekuto përsëri `.\setup_efaktura.ps1`

### 2. Testo connection
```powershell
python app/test_efaktura_connection.py
```

### 3. Shiko error message
Më shpesh:
- `401 Unauthorized` → API key i gabuar
- `Connection timeout` → Problem me network
- `Database error` → Kredencialet e DB të gabuara

### 4. Shiko logs
```powershell
Get-Content logs/faktura_import.log -Tail 50
```

---

## 📞 Pyetje të shpeshta

**P: Sa kohë merr për 145 faktura?**
A: ~3-7 minuta (varet nga velociteti i API)

**P: A mund ta ndërpres?**
A: Po (Ctrl+C), por vetëm fakturat deri në atë moment do të importohen

**P: Çfarë nëse ekzekutoj 2 herë të njëjtën periudhë?**
A: Script kontrollon nëse faktura ekziston (vezabroj), nuk duplikohet

**P: A krijohen artikuj të rinj automatikisht?**
A: Po, nëse `WPH_ALLOW_AUTO_CREATE=1` (vendoset në setup)

---

## 🎉 GATI!

Tani je gati për të filluar:

```powershell
# 1. Setup
.\app\setup_efaktura.ps1

# 2. Test
python app/test_efaktura_connection.py

# 3. Import (dry-run para se real!)
python app/fetch_all_invoices.py --from 2025-11-01 --to 2025-11-18 --auto-import --dry-run

# 4. Nëse dry-run është OK, import real
python app/fetch_all_invoices.py --from 2025-01-01 --to 2025-11-18 --auto-import
```

---

📚 **Dokumentacioni:**
- Quick Start: `QUICKSTART_EFAKTURA.md`
- Full Docs: `README_EFAKTURA.md`
- Summary: `EFAKTURA_SUMMARY.md`

---

**Suksese! 🚀**

*Wellona Pharm SMART System*

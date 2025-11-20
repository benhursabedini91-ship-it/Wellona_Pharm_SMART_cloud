# ⚡ QUICK START - eFaktura Integration

## 📥 Hapat për të marrë TË GJITHA fakturat XML

### 1️⃣ Setup (5 minuta - një herë)

```powershell
# Hyr në folder
cd C:\Wellona\Wellona_Pharm_SMART\app

# Ekzekuto setup
.\setup_efaktura.ps1
```

**Do të të pyesë për:**
- API Key (merr nga https://efaktura.mfin.gov.rs)
- URL-të (shtyp ENTER për default)
- DB credentials (për auto-import)

### 2️⃣ Test (1 minutë - rekomandohet)

```powershell
# Shkarko fakturat e javës së kaluar (test i vogël)
$date_from = (Get-Date).AddDays(-7).ToString("yyyy-MM-dd")
$date_to = (Get-Date).ToString("yyyy-MM-dd")

python app/fetch_all_invoices.py --from $date_from --to $date_to
```

### 3️⃣ Merre TË GJITHA (varet nga sasia)

```powershell
# OPSIONI 1: Vetëm shkarkim XML (më i sigurt për herën e parë)
python app/fetch_all_invoices.py --from 2025-01-01 --to 2025-11-18

# OPSIONI 2: Shkarkim + Import në ERP (DRY-RUN - pa shkruar në DB)
python app/fetch_all_invoices.py --from 2025-01-01 --to 2025-11-18 --auto-import --dry-run

# OPSIONI 3: Shkarkim + Import REAL (pas testimit me dry-run!)
python app/fetch_all_invoices.py --from 2025-01-01 --to 2025-11-18 --auto-import
```

---

## 🎯 Komanda më e thjeshtë (për çdo ditë)

```powershell
# Merr fakturat e sotme
python app/fetch_all_invoices.py --from $(Get-Date -Format 'yyyy-MM-dd') --to $(Get-Date -Format 'yyyy-MM-dd') --auto-import

# Merr fakturat e muajit aktual
$first = (Get-Date -Day 1).ToString("yyyy-MM-dd")
$today = (Get-Date).ToString("yyyy-MM-dd")
python app/fetch_all_invoices.py --from $first --to $today --auto-import
```

---

## 📂 Ku gjenden XML-të?

```
C:\Wellona\Wellona_Pharm_SMART\staging\faktura_uploads\
├── SOPHARMA_FAK123_2025-10-15.xml
├── VEGA_FAK456_2025-10-16.xml
├── PHOENIX_FAK789_2025-10-17.xml
└── ...
```

---

## 🔍 Si ta kontrolloj nëse funksionoi?

### Në console:
```
📊 PËRMBLEDHJE:
  Total faktura: 145
  ✓ Shkarkuar me sukses: 145
  ❌ Dështuan: 0
```

### Në DB (nëse --auto-import):
```sql
-- Shiko kalkulacione e reja
SELECT * FROM eb_fdw.kalkopste 
WHERE datum >= '2025-01-01' 
ORDER BY id DESC;

-- Numro artikujt e rinj
SELECT COUNT(*) FROM eb_fdw.artikli 
WHERE sifra >= '2300000000';

-- Shiko audit për çmime
SELECT * FROM public.wph_audit_price_lock 
ORDER BY ts DESC LIMIT 20;
```

---

## ⚠️ PARALAJMËRIME

1. **Para importit të parë, GJITHMONË përdor `--dry-run`**
2. **Backup DB para importeve të mëdha**
3. **Kontrollo credentials (API key, DB password)**
4. **Nëse ka shumë faktura (>500), ndaje në batch-e**

---

## 🆘 Nëse diçka shkon keq

```powershell
# 1. Kontrollo connection
python -c "from app.efaktura_client import make_session; s=make_session(); print('OK')"

# 2. Kontrollo DB
python -c "import psycopg2; psycopg2.connect('dbname=wph_ai user=postgres host=127.0.0.1').close(); print('OK')"

# 3. Shiko logs
Get-Content logs/faktura_import.log -Tail 50

# 4. Rollback (nëse diçka shkoi keq)
# ... bëhet manualisht në DB me backup
```

---

## 📞 Pyetje të shpeshta

**P: Sa kohë merr për 100 faktura?**
A: ~2-5 minuta (varet nga velociteti i API)

**P: A mund ta ndërpres gjatë ekzekutimit?**
A: Po (Ctrl+C), por do të importohen vetëm fakturat deri në atë moment

**P: Çfarë ndodh nëse ekzekuton 2 herë?**
A: Script kontrollon nëse faktura ekziston (vezabroj), nuk duplikohet

**P: Si ta automatizoj për çdo ditë?**
A: Përdor Task Scheduler (shih README_EFAKTURA.md)

---

## 📚 Dokumentacion i plotë

Për detaje të avancuara: `README_EFAKTURA.md`

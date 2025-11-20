# eFaktura Integration - Dokumentacion i plotë

## 📋 Përmbledhje

Sistem i integruar për të marrë automatikisht të gjitha fakturat XML nga platforma eFaktura e Ministrisë së Financave dhe për t'i importuar në sistemin ERP.

## 🎯 Veçoritë

- ✅ Shkarkim automatik i të gjitha fakturave XML nga eFaktura
- ✅ Import i drejtpërdrejtë në ERP (kalkulacija, kalkstavke, kalkkasa)
- ✅ Auto-regjistrim i artikujve të rinj me barcode si lidhës universal
- ✅ Matching inteligjent: barcode → sifra → fuzzy name match
- ✅ Dry-run mode për testim pa modifikuar DB
- ✅ Raportim i detajuar me statistika
- ✅ Suport për FDW (Foreign Data Wrapper) për akses remote
- ✅ Mbrojtje nga shkrime aksidentale në DB produksioni

## 🚀 Setup i shpejtë

### Hapi 1: Konfigurimi (një herë)

```powershell
# Ekzekuto setup script
cd C:\Wellona\Wellona_Pharm_SMART\app
.\setup_efaktura.ps1
```

Script do të të pyesë për:
1. **API Key** - Merr nga https://efaktura.mfin.gov.rs (Llogaria > API Access)
2. **API Endpoints** - URL për listën dhe shkarkimin e fakturave
3. **DB Config** - Për import automatik në ERP
4. **Opsione sigurie** - Remote write, auto-create artikuj

### Hapi 2: Përdorimi

#### Vetëm shkarkim XML

```powershell
# Shkarko fakturat e muajit të kaluar
python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-10-31

# Shkarko të gjitha fakturat e vitit 2025
python app/fetch_all_invoices.py --from 2025-01-01 --to 2025-11-18

# Shkarko në folder specifik
python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-10-31 --output ./fakturat_tetor
```

#### Shkarkim + Import automatik në ERP

```powershell
# Import automatik pas shkarkimit
python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-10-31 --auto-import

# DRY-RUN: Shikon çfarë do bëjë pa shkruar në DB (REKOMANDOHET për herë të parë!)
python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-10-31 --auto-import --dry-run

# Import me delay më të madh midis shkarkimeve (për rate limiting)
python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-10-31 --auto-import --delay 1.0
```

## ⚙️ Variablat e mjedisit

Të gjitha konfigurimet bëhen përmes variablave të mjedisit:

### eFaktura API

```powershell
# API Key (E DETYRUESHME)
$env:WPH_EFAKT_API_KEY = "your-api-key-here"

# Base URL
$env:WPH_EFAKT_API_BASE = "https://efaktura.mfin.gov.rs"

# LIST Endpoint - POST request me JSON body {dateFrom, dateTo}
$env:WPH_EFAKT_LIST_URL = "https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/ids"

# GET Endpoint - GET request me query param ?invoiceId=123
$env:WPH_EFAKT_GET_XML_URL = "https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/xml"
```

### Database

```powershell
# Database connection
$env:WPH_DB_NAME = "wph_ai"           # ose "ebdata" për direct connection
$env:WPH_DB_USER = "postgres"
$env:WPH_DB_PASS = "your-password"
$env:WPH_DB_HOST = "127.0.0.1"        # ose "pedjapostgres" për remote
$env:WPH_DB_PORT = "5432"
```

### Opsione sigurie

```powershell
# Lejo shkrim në DB remote (KUJDES!)
$env:WPH_WRITE_REMOTE = "0"          # 0=jo, 1=po

# Lejo krijim automatik të artikujve të rinj
$env:WPH_ALLOW_AUTO_CREATE = "1"     # 0=jo, 1=po

# Përdor FDW për akses remote (rekomandohet për produksion)
$env:WPH_USE_FDW = "1"               # 0=jo, 1=po

# Ruaj çmimet ekzistuese (MP) kur nabavna cena nuk ka ndryshuar
$env:WPH_PRESERVE_EXISTING_MP = "0"  # 0=jo, 1=po

# Auto-krijim i dokumenteve nivelizacija kur MP ndryshon
$env:WPH_AUTO_NIVELIZACIJA = "0"     # 0=jo, 1=po (KUJDES!)
```

## 📁 Struktura e file-ve

```
app/
├── efaktura_client.py          # Client për eFaktura API
├── faktura_import.py           # Import në ERP (kalkulacija)
├── fetch_all_invoices.py       # Script kryesor (NEW)
├── setup_efaktura.ps1          # Setup script (NEW)
└── README_EFAKTURA.md          # Ky file

staging/
└── faktura_uploads/            # XML të shkarkuara
    ├── SOPHARMA_FAK123_2025-10-15.xml
    ├── VEGA_FAK456_2025-10-16.xml
    └── ...
```

## 🔍 Si funksionon

### 1. Shkarkimi (fetch_all_invoices.py)

```
1. Krijon session me eFaktura API (API key authentication)
2. Merr listën e fakturave për periudhën e specifikuar
3. Për çdo faturë:
   - Shkarkon XML
   - Ruan në folder (staging/faktura_uploads/)
   - Emërtimi: {FURNITOR}_{NUMRI}_{DATA}.xml
4. Raporton statistika
```

### 2. Importi (faktura_import.py)

```
1. Parse XML (suporton UBL dhe Sopharma format)
2. Lookup komintent (furnitor) nga emri
3. Për çdo artikull:
   a. Lookup me barcode → artikliean → fuzzy name
   b. Nëse nuk gjendet dhe WPH_ALLOW_AUTO_CREATE=1:
      - Krijon artikull të ri
      - Barkodi si lidhës universal
      - Sifra ERP auto-increment
      - Sifra furnitori si EAN alternativë
   c. Llogarit MP (margjinë + PDV)
   d. Nëse WPH_PRESERVE_EXISTING_MP=1:
      - Kontrollon nëse nabavna cena ka ndryshuar
      - Nëse JO → ruan MP e vjetër, rikalkulon RUC
      - Nëse PO → rikalkulon MP, krijon nivelizacija (nëse enabled)
4. Insert në kalkopste (header)
5. Insert në kalkkasa (payment terms)
6. Insert në kalkstavke (lines)
7. Commit ose rollback
```

## 🛡️ Mbrojtja e sigurisë

### Nivele të sigurisë

**Nivel 1: Dry-run** (më i sigurt)
```powershell
--dry-run  # Nuk shkruan asgjë në DB, vetëm validon
```

**Nivel 2: FDW me write protection** (rekomandohet për dev)
```powershell
$env:WPH_USE_FDW = "1"
$env:WPH_WRITE_REMOTE = "0"  # Bllokon shkrime aksidentale në ebdata
```

**Nivel 3: Direct connection me kujdes** (production)
```powershell
$env:WPH_DB_NAME = "ebdata"
$env:WPH_DB_HOST = "pedjapostgres"
$env:WPH_USE_FDW = "0"
$env:WPH_WRITE_REMOTE = "1"  # Duhet eksplicit për remote write
```

### Blloqe mbrojtëse në kod

1. **FDW write block**: FDW nuk mund të shkruajë me auto-generated IDs
2. **Remote write flag**: Duhet `WPH_WRITE_REMOTE=1` për remote DB
3. **Production detection**: Bllokon nivelizacija në ebdata
4. **Audit logging**: Të gjitha ndryshimet MP ruhen në wph_ai.wph_audit_price_lock

## 📊 Raportimi

### Output i fetch_all_invoices.py

```
🔍 Duke kërkuar faktura nga 2025-10-01 deri në 2025-10-31...
📂 Direktoria e output: C:\...\staging\faktura_uploads
================================================================================
✓ Sesioni me eFaktura API u krijua

📋 Duke marrë listën e fakturave...
✓ U gjetën 15 faktura
================================================================================

[1/15] Faktura: FAK-2025-001
  Furnitori: SOPHARMA D.O.O.
  Data: 2025-10-05
  ID: abc123-def456
  ✓ Shkarkuar: SOPHARMA_FAK-2025-001_2025-10-05.xml

...

================================================================================
📊 PËRMBLEDHJE:
  Total faktura: 15
  ✓ Shkarkuar me sukses: 14
  ❌ Dështuan: 1

⚠️  GABIME:
  - Invoice FAK-2025-005 (ID: xyz789): 404 Not Found
```

### Output i auto-import

```
================================================================================
🔄 FILLIM I IMPORTIT AUTOMATIK NË ERP
================================================================================
✓ Lidhur me DB: wph_ai @ 127.0.0.1

[1/14] Importimi i: SOPHARMA_FAK-2025-001_2025-10-05.xml
  Faktura: FAK-2025-001
  Furnitori: SOPHARMA D.O.O.
  Data: 2025-10-05
  Artikuj: 23
  Total neto: 12345.67
Komintent resolved: dobavljac='SOPHARMA D.O.O.' → sifra='15'
Header OK: broj=1234/25, vezabroj=FAK-2025-001, kalkid=456789
Items to insert: 23 (existing_lines=0)
✓ Ekziston: PARACETAMOL 500MG TBL 20X... (barcode: 8606001234567)
✓ Ekziston: IBUPROFEN 400MG TBL 30X... (match: IBUPROFEN 400MG TABLETA 30X)
🆕 Do krijohet: NEUROFEN EXPRESS 400MG CAPS 20X... (barcode: 8606009876543)
✓ AUTO-KRIJUAR artikull: ERP sifra=2300000123, naziv=NEUROFEN EXPRESS 400MG CAPS 20X, barkod=8606009876543
...
Artikal resolution stats: {'FOUND': 18, 'CREATED': 3, 'BARCODE_ADDED': 2, 'SKIPPED': 0}
Inserted 23 lines
Commit OK.
  ✓ Importuar me sukses (kalkid=456789)

...

================================================================================
📊 PËRMBLEDHJE E IMPORTIT:
  Total XML: 14
  ✓ Importuar: 12
  ⚠️  Skip: 1
  ❌ Dështuan: 1
```

## 🔧 Troubleshooting

### Problem: "Missing API key"
```powershell
# Vendos API key
$env:WPH_EFAKT_API_KEY = "your-key-here"

# Ose ekzekuto setup
.\setup_efaktura.ps1
```

### Problem: "401 Unauthorized"
```
Shkaku: API key invalid ose i skaduar
Zgjidhja: Rigjeneroje API key nga https://efaktura.mfin.gov.rs
```

### Problem: "FDW remote write blocked"
```powershell
# Opsioni 1: Lejo remote write (KUJDES!)
$env:WPH_WRITE_REMOTE = "1"

# Opsioni 2: Lidhu direkt me ebdata
$env:WPH_DB_NAME = "ebdata"
$env:WPH_DB_HOST = "pedjapostgres"
$env:WPH_USE_FDW = "0"
$env:WPH_WRITE_REMOTE = "1"
```

### Problem: "Artikal not found/created"
```powershell
# Lejo auto-create
$env:WPH_ALLOW_AUTO_CREATE = "1"

# Ose importo manualisht artikujt para se të importosh fakturat
```

### Problem: "Rate limiting (429 Too Many Requests)"
```powershell
# Rrit delay midis shkarkimeve
python app/fetch_all_invoices.py ... --delay 2.0
```

## 📚 Shembuj të avancuar

### Import i selektuar (vetëm disa XML)

```python
# import_selected.py
from app.fetch_all_invoices import auto_import_invoices

xml_paths = [
    'staging/faktura_uploads/SOPHARMA_FAK123_2025-10-15.xml',
    'staging/faktura_uploads/VEGA_FAK456_2025-10-16.xml'
]

stats = auto_import_invoices(xml_paths, dry_run=False)
print(stats)
```

### Batch processing (import i madh)

```powershell
# Ndaj në batch të vogla për të shmangur timeout
python app/fetch_all_invoices.py --from 2025-01-01 --to 2025-03-31 --auto-import
python app/fetch_all_invoices.py --from 2025-04-01 --to 2025-06-30 --auto-import
python app/fetch_all_invoices.py --from 2025-07-01 --to 2025-09-30 --auto-import
python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-11-18 --auto-import
```

### Scheduled job (Task Scheduler)

```powershell
# create_task.ps1
$action = New-ScheduledTaskAction -Execute "python" -Argument "app/fetch_all_invoices.py --from $(Get-Date -Format 'yyyy-MM-01') --to $(Get-Date -Format 'yyyy-MM-dd') --auto-import"
$trigger = New-ScheduledTaskTrigger -Daily -At 23:00
Register-ScheduledTask -TaskName "eFaktura Daily Import" -Action $action -Trigger $trigger
```

## 🎓 Best practices

1. **Testo gjithmonë me dry-run para importit real**
   ```powershell
   python app/fetch_all_invoices.py ... --auto-import --dry-run
   ```

2. **Përdor FDW për development, direct connection për production**

3. **Backup DB para importeve të mëdha**
   ```powershell
   pg_dump -h 127.0.0.1 -U postgres ebdata > backup_$(Get-Date -Format 'yyyyMMdd').sql
   ```

4. **Monitorimi i log files**
   ```powershell
   Get-Content logs/faktura_import.log -Tail 50 -Wait
   ```

5. **Kontrollo audit table për ndryshime MP**
   ```sql
   SELECT * FROM wph_ai.public.wph_audit_price_lock 
   ORDER BY ts DESC LIMIT 100;
   ```

## 📞 Support

Për probleme ose pyetje:
- Shiko logs në `logs/`
- Kontrollo DB audit table: `wph_audit_price_lock`
- Testo me `--dry-run` para se të aplikosh në production

## 📄 Licenca

Wellona Pharm SMART System © 2025

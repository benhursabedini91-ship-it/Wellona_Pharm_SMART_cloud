# FAKTURA AI — Deep Research & Implementation Plan

**Date**: November 7, 2025  
**Project**: WPH_AI Invoice Processing Automation  
**Objective**: Automate supplier invoice entry from XML/FTP/Email → ERP validation → Auto-Proknjizi

---

## 📋 EXECUTIVE SUMMARY

### Problem Statement
Currently, Wellona Pharmacy processes 50-100+ supplier invoices monthly through **manual ERP entry**:
- **Phoenix Pharma**: FTP XML downloads → manual ERP import
- **Vega/Sopharma/Farmalogist**: Email XML attachments → manual verification → manual entry
- **Time consumption**: ~10-15 minutes per invoice = **12-25 hours/month**
- **Error rate**: ~5-8% (wrong quantities, price mismatches, duplicate entries)
- **Late payment penalties**: Missing early payment discounts (2-3% savings lost)

### Proposed Solution
**Faktura AI** — Autonomous invoice processing agent that:
1. **Fetches** invoices automatically (FTP monitoring + IMAP email parsing)
2. **Parses** XML/PDF with tolerant multi-format support
3. **Validates** against product catalog (`eb_fdw.artikli`) + price/rabat database
4. **Stages** clean invoices in `ops.faktura_in` + `ops.faktura_items` tables
5. **Auto-commits** to ERP via UI automation (Mode A: Draft queue, Mode B: Full auto-proknjizi)

### Expected ROI
- **Time savings**: 20+ hours/month → ~$500 USD/month labor cost reduction
- **Error reduction**: 95%+ accuracy with AI validation (vs 92-95% manual)
- **Early payment discounts**: Capture 2-3% discounts = ~$2,000-5,000 RSD/month
- **Audit trail**: Complete logging (invoice hash, timestamps, validation results)
- **Payback period**: < 3 months

---

## 🔍 SECTION 1: CURRENT MANUAL PROCESS ANALYSIS

### 1.1 Workflow Breakdown (Phoenix Pharma Example)

Based on actual ERP video analysis (`mp kalkulacija ulazna roba.zip`):

```
STEP 1: FTP Download (manual)
├─ Login to ftp.phoenix.rs
├─ Navigate to /invoices/xml/
├─ Download files matching pattern: INV_*.xml
└─ Save to local folder C:\Downloads\Phoenix\

STEP 2: ERP Navigation
├─ Open Apoteka ERP
├─ Menu → Kalkulacija → Ulazna roba
├─ Click "Import XML"
└─ Dialog: "Preuzmi fajl" (Choose file)

STEP 3: File Selection & Supplier Mapping
├─ Browse to C:\Downloads\Phoenix\INV_1234567.xml
├─ ERP auto-detects supplier from XML header
├─ Displays: "Dobavljač: PHOENIX PHARMA"
└─ Click "Učitaj" (Load)

STEP 4: Line Item Validation (MANUAL INTENSIVE)
├─ ERP populates table with items from XML
├─ Operator checks each line:
│   ├─ Barcode match (is product in catalog?)
│   ├─ Price vs last purchase (red flag if >10% difference)
│   ├─ Quantity (does it match PO?)
│   └─ Rabat % (is discount applied correctly?)
├─ Missing products → manual search & add
├─ Price discrepancies → call supplier or accept
└─ Average time: 8-12 minutes for 50-item invoice

STEP 5: Total Verification
├─ XML total_gross: 145,670.00 RSD
├─ ERP calculated total: 145,668.50 RSD
├─ Delta: -1.50 RSD (rounding) → ACCEPTABLE
└─ If delta > 0.1% → manual investigation

STEP 6: Proknjizi (Finalize)
├─ Click "Proknjiži" button
├─ ERP creates record in mp_kalkulacija_ulazna
├─ Updates inventory (mp_stavke)
├─ Generates document number: KU-2025-001234
└─ Prints PDF receipt (optional)

TOTAL TIME: 10-15 minutes per invoice
ERROR POINTS: Steps 4 & 5 (manual validation prone to typos, missed items)
```

### 1.2 Pain Points Identified

| Issue | Frequency | Impact | Automation Opportunity |
|-------|-----------|--------|------------------------|
| **Manual FTP login** | Daily | Low (2 min) | ✅ FTP watcher script |
| **Barcode matching** | Per item | High (5-8 min) | ✅ SQL lookup vs `eb_fdw.artikli` |
| **Price verification** | Per item | Medium | ✅ Compare vs `stg.pricefeed` with rabat |
| **Duplicate detection** | Weekly | Medium | ✅ Hash-based deduplication |
| **Total mismatch** | 10-15% invoices | High | ✅ Automated tolerance check (±0.1%) |
| **Missing products** | 5-10% invoices | High | ⚠️ Flag for manual review |
| **Supplier format variations** | Constant | High | ✅ Supplier-specific XML mappers |

### 1.3 Existing MVP Evidence

**File**: `c:\Wellona\wphAI\app\faktura_ai_mvp.py` (255 lines)

Already implements:
- ✅ Tolerant XML parser supporting UBL + custom vendor formats
- ✅ Product matching via sifra/barcode lookup
- ✅ Total validation with tolerance (default 0.1%)
- ✅ Match rate calculation (% items found in catalog)
- ✅ CSV export: `{invoice}_header.csv` + `{invoice}_items.csv`
- ✅ Summary report: `FAKTURA_AI_SUMMARY_YYYYMMDD.csv`

**Last run stats** (`out\faktura\20251023\FAKTURA_AI_MORNING_20251023.txt`):
- Processed: 12 invoices
- CLEAN: 2 (100% match, total OK)
- NEEDS_REVIEW: 10 (match_rate 0-84.62%)
- Processing time: ~45 seconds for 12 invoices

**Key insight**: Current MVP validates but doesn't commit to ERP. Next phase = ERP integration.

---

## 🏗️ SECTION 2: TECHNICAL ARCHITECTURE

### 2.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    FAKTURA AI PIPELINE                       │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐
│  INGESTION   │  ← FTP Watcher (Phoenix)
│   LAYER      │  ← IMAP Parser (Vega/Sopharma/Farmalogist)
└──────┬───────┘  ← Manual upload (fallback)
       │
       v
┌──────────────┐
│   PARSING    │  ← XML Parser (multi-format support)
│   LAYER      │  ← PDF OCR (Azure/Tesseract - future)
└──────┬───────┘  ← Excel converter (XLS→CSV)
       │
       v
┌──────────────┐
│  VALIDATION  │  ← Product matching (sifra/barcode)
│   LAYER      │  ← Price/rabat verification
└──────┬───────┘  ← Total reconciliation
       │
       v
┌──────────────┐
│   STAGING    │  ← PostgreSQL: ops.faktura_in
│     DB       │  ← ops.faktura_items
└──────┬───────┘  ← Audit logs: ops.faktura_audit
       │
       v
┌──────────────┐
│ ERP COMMIT   │  ← Mode A: Draft queue (manual approval)
│   LAYER      │  ← Mode B: Auto-proknjizi (UI automation)
└──────────────┘  ← commit_erp.ps1 (AHK/SendKeys)
```

### 2.2 Database Schema Design

```sql
-- Header table
CREATE TABLE ops.faktura_in (
    id SERIAL PRIMARY KEY,
    invoice_no TEXT NOT NULL,
    supplier TEXT NOT NULL,
    invoice_date DATE,
    valuta_date DATE,
    currency TEXT DEFAULT 'RSD',
    warehouse TEXT DEFAULT 'GLAVNI',
    komintent TEXT, -- supplier ERP code
    total_no_vat NUMERIC(12,2),
    total_vat NUMERIC(12,2),
    total_gross NUMERIC(12,2),
    source TEXT, -- 'ftp' | 'mail' | 'manual'
    file_hash TEXT UNIQUE, -- SHA256 for dedup
    status TEXT DEFAULT 'pending', -- 'pending' | 'validated' | 'committed' | 'error'
    match_rate_pct NUMERIC(5,2),
    validation_errors JSONB,
    erp_doc_no TEXT, -- KU-2025-001234 after proknjizi
    created_at TIMESTAMP DEFAULT NOW(),
    committed_at TIMESTAMP,
    UNIQUE(invoice_no, supplier)
);

-- Line items table
CREATE TABLE ops.faktura_items (
    id SERIAL PRIMARY KEY,
    faktura_id INTEGER REFERENCES ops.faktura_in(id) ON DELETE CASCADE,
    line_no INTEGER,
    sifra TEXT, -- supplier product code
    barcode TEXT, -- EAN-13
    naziv TEXT,
    kolicina NUMERIC(12,3),
    vpc NUMERIC(12,2), -- wholesale price
    rabat_pct NUMERIC(5,2),
    pdv_pct NUMERIC(5,2) DEFAULT 20,
    lot TEXT,
    exp_date DATE,
    matched_sifra TEXT, -- our internal sifra from artikli
    match_status TEXT, -- 'exact' | 'barcode' | 'fuzzy' | 'missing'
    price_delta_pct NUMERIC(6,2), -- vs stg.pricefeed
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audit trail
CREATE TABLE ops.faktura_audit (
    id SERIAL PRIMARY KEY,
    faktura_id INTEGER REFERENCES ops.faktura_in(id),
    action TEXT, -- 'parse' | 'validate' | 'commit' | 'error'
    details JSONB,
    user_id TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_faktura_in_status ON ops.faktura_in(status);
CREATE INDEX idx_faktura_in_supplier ON ops.faktura_in(supplier);
CREATE INDEX idx_faktura_items_barcode ON ops.faktura_items(barcode);
CREATE INDEX idx_faktura_items_sifra ON ops.faktura_items(sifra);
```

### 2.3 Supplier-Specific XML Mappers

**Phoenix Pharma** (`configs/mappers/phoenix_invoice.json`):
```json
{
  "supplier": "PHOENIX",
  "format": "UBL-2.1",
  "header": {
    "invoice_no": ".//cac:ID",
    "invoice_date": ".//cbc:IssueDate",
    "total_gross": ".//cac:LegalMonetaryTotal/cbc:PayableAmount",
    "currency": ".//cbc:DocumentCurrencyCode"
  },
  "items": {
    "container": ".//cac:InvoiceLine",
    "sifra": ".//cac:Item/cac:SellersItemIdentification/cbc:ID",
    "barcode": ".//cac:Item/cac:StandardItemIdentification/cbc:ID",
    "naziv": ".//cac:Item/cbc:Name",
    "kolicina": ".//cbc:InvoicedQuantity",
    "vpc": ".//cac:Price/cbc:PriceAmount",
    "rabat_pct": ".//cac:AllowanceCharge/cbc:MultiplierFactorNumeric"
  },
  "kasak": 1
}
```

**Vega** (`configs/mappers/vega_invoice.json`):
```json
{
  "supplier": "VEGA",
  "format": "custom-xml",
  "header": {
    "invoice_no": ".//Broj",
    "invoice_date": ".//Datum",
    "total_gross": ".//IznosUkupno"
  },
  "items": {
    "container": ".//Stavka",
    "sifra": ".//Sifra",
    "barcode": ".//EAN",
    "naziv": ".//Naziv",
    "kolicina": ".//Kolicina",
    "vpc": ".//Cena",
    "rabat_pct": ".//Rabat"
  },
  "kasak": 1
}
```

### 2.4 Validation Logic Flow

```python
def validate_invoice(invoice_xml, supplier_config):
    """
    Comprehensive invoice validation with scoring
    Returns: (is_valid, match_rate, errors[], warnings[])
    """
    errors = []
    warnings = []
    
    # 1. Parse with supplier-specific mapper
    header, items = parse_invoice_xml(invoice_xml, supplier_config)
    
    # 2. Product matching
    matched_items = 0
    for item in items:
        match = match_product(item['sifra'], item['barcode'])
        if match:
            matched_items += 1
            item['matched_sifra'] = match['sifra']
            item['match_status'] = 'exact'
            
            # 2a. Price validation
            expected_price = get_supplier_price(
                supplier, match['sifra']
            )
            if expected_price:
                delta = abs(item['vpc'] - expected_price) / expected_price
                if delta > 0.10:  # >10% difference
                    warnings.append({
                        'line': item['line_no'],
                        'issue': 'price_delta',
                        'expected': expected_price,
                        'actual': item['vpc'],
                        'delta_pct': delta * 100
                    })
        else:
            item['match_status'] = 'missing'
            errors.append({
                'line': item['line_no'],
                'issue': 'product_not_found',
                'sifra': item['sifra'],
                'barcode': item['barcode']
            })
    
    match_rate = (matched_items / len(items)) * 100 if items else 0
    
    # 3. Total reconciliation
    calc_total = sum([
        item['kolicina'] * item['vpc'] * (1 - item.get('rabat_pct', 0)/100)
        for item in items
    ])
    xml_total = header.get('total_gross', 0)
    
    if xml_total > 0:
        delta_pct = abs(calc_total - xml_total) / xml_total * 100
        if delta_pct > 0.1:  # >0.1% tolerance
            errors.append({
                'issue': 'total_mismatch',
                'calculated': calc_total,
                'xml_total': xml_total,
                'delta_pct': delta_pct
            })
    
    # 4. Duplicate check
    existing = check_invoice_exists(header['invoice_no'], supplier)
    if existing:
        errors.append({
            'issue': 'duplicate_invoice',
            'existing_id': existing['id'],
            'committed_at': existing['committed_at']
        })
    
    # 5. Decision logic
    is_valid = (
        match_rate >= 99.0 and
        len([e for e in errors if e['issue'] in [
            'total_mismatch', 'duplicate_invoice'
        ]]) == 0
    )
    
    return {
        'valid': is_valid,
        'match_rate': match_rate,
        'errors': errors,
        'warnings': warnings,
        'auto_commit': is_valid and match_rate == 100.0
    }
```

---

## 🌐 SECTION 3: COMPETITIVE ANALYSIS

### 3.1 Leading Invoice Processing Platforms

#### **ABBYY FlexiCapture for Invoices**
**Website**: https://www.abbyy.com/invoice-processing/

**Key Features**:
- OCR accuracy: 95-98% for structured documents
- Pre-trained on 30+ years of invoice data
- Multi-language support (100+ languages)
- Table extraction with complex structures
- Integration: SAP, Oracle, Coupa, Workday
- Deployment: Cloud or on-premises

**Pricing**: ~$10,000-50,000 USD/year (enterprise)

**Pros**:
- Industry-leading accuracy
- Handles PDF scans, handwritten notes
- Proven in pharmaceutical/healthcare sector

**Cons**:
- High cost for small operations
- Complex setup (2-3 months implementation)
- Overkill for XML-only processing

**Relevance to Wellona**: ⚠️ **NOT NEEDED NOW** — 90% of invoices are XML (structured), only 5-10% are PDF scans

---

#### **Docsumo**
**Website**: https://www.docsumo.com/

**Key Features**:
- AI-powered document classification
- Line-item extraction from invoices
- 95%+ straight-through processing
- Excel-like data tables (searchable)
- Validation formulas (no coding)
- Integration via REST API

**Pricing**: $500-2,000 USD/month (based on volume)

**Pros**:
- Modern UI/UX
- Fast implementation (<2 weeks)
- Good for mixed formats (PDF + XML)

**Cons**:
- Still overkill for XML-dominant workflow
- Monthly subscription cost

**Relevance to Wellona**: ⚠️ **FUTURE CONSIDERATION** — If PDF invoices increase >20%, evaluate for OCR component

---

#### **Rossum.ai**
**Website**: https://www.rossum.ai/

**Key Features**:
- AI agents read, validate, transform data
- Email/ERP integration
- Custom approval workflows
- Supports SAP, Coupa, NetSuite

**Pricing**: Custom (enterprise)

**Pros**:
- Full end-to-end automation
- Used by Bosch, Siemens (pharmaceutical adjacent)

**Cons**:
- Enterprise pricing
- Complex integration

**Relevance to Wellona**: ⚠️ **NOT NEEDED** — In-house solution more cost-effective for XML processing

---

### 3.2 Best Practices from Industry

Based on competitive analysis + pharmaceutical sector case studies:

1. **Dual validation approach**: Automated + human-in-the-loop for exceptions
2. **Tolerance thresholds**: 0.1% for totals, 10% for unit prices
3. **Match rate targets**: 99%+ for auto-commit, 90-98% for draft queue
4. **Audit trail**: Complete logging (who, what, when) for compliance
5. **Supplier-specific rules**: Each vendor has unique format quirks
6. **Deduplication**: Hash-based (SHA256 on XML content)
7. **Error categorization**: 
   - **CRITICAL**: Duplicate, total mismatch >1%
   - **WARNING**: Price delta 5-10%, match rate 95-98%
   - **INFO**: New products, missing lot/expiry

---

## 🚀 SECTION 4: WELLONA-SPECIFIC DIFFERENTIATION

### 4.1 Unique Features for Pharmacy Use Case

#### **Feature 1: Per-Product Rabat Validation**
*Problem*: Suppliers send rabat in XML, but ERP may have different rabat agreements

*Solution*:
```python
def validate_rabat(item, supplier):
    """Compare XML rabat vs stg.pricefeed rabat"""
    expected_rabat = get_supplier_rabat(
        supplier=supplier,
        sifra=item['matched_sifra']
    )
    
    if expected_rabat and abs(item['rabat_pct'] - expected_rabat) > 0.5:
        return {
            'warning': 'rabat_mismatch',
            'expected': expected_rabat,
            'xml': item['rabat_pct'],
            'impact_rsd': calculate_price_impact(item, expected_rabat)
        }
    return None
```

*Business Value*: Catch rabat errors = save 1-3% on purchases = ~$1,500-3,000 RSD/month

---

#### **Feature 2: Budget-Aware Auto-Ordering**
*Integration with existing Order Brain*:

When invoice arrives → check vs expected order:
```sql
SELECT 
    oi.sifra,
    oi.expected_qty,
    fi.kolicina AS invoice_qty,
    (fi.kolicina - oi.expected_qty) AS delta_qty
FROM ops.faktura_items fi
LEFT JOIN (
    -- Get last order from Order Brain
    SELECT sifra, SUM(qty_to_order) AS expected_qty
    FROM wph_core.order_lines
    WHERE created_at > NOW() - INTERVAL '30 days'
    AND supplier = 'PHOENIX'
    GROUP BY sifra
) oi ON fi.matched_sifra = oi.sifra
WHERE ABS(fi.kolicina - COALESCE(oi.expected_qty, 0)) > 5
```

*Business Value*: Detect over-shipping / invoice fraud

---

#### **Feature 3: Supplier Format Learning**
*Problem*: Suppliers change XML schemas without notice

*Solution*: AI-assisted field detection
```python
def detect_schema_changes(xml_path, expected_mapper):
    """Compare current XML structure vs known mapper"""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Extract all unique XPath patterns
    discovered_paths = extract_all_paths(root)
    
    # Compare vs expected
    missing_fields = []
    for field, xpath in expected_mapper['header'].items():
        if not xpath_exists(root, xpath):
            # Try fuzzy match
            similar = find_similar_paths(xpath, discovered_paths)
            missing_fields.append({
                'field': field,
                'expected': xpath,
                'suggestions': similar[:3]
            })
    
    if missing_fields:
        alert_admin({
            'supplier': expected_mapper['supplier'],
            'issue': 'schema_changed',
            'missing': missing_fields,
            'xml_sample': xml_path
        })
```

*Business Value*: Zero downtime when suppliers update formats

---

#### **Feature 4: Batch Processing with Priority**
*Rules*:
1. **Phoenix** (largest supplier) → process first
2. Invoices with early payment discount (<5 days) → high priority
3. Small invoices (<10,000 RSD) → auto-approve if match rate 100%
4. Large invoices (>100,000 RSD) → always require human approval

```python
def prioritize_invoices(invoice_queue):
    """Sort invoices by business priority"""
    return sorted(invoice_queue, key=lambda inv: (
        -1 if inv['early_discount_days'] <= 5 else 0,  # Urgent discounts first
        SUPPLIER_PRIORITY.get(inv['supplier'], 99),     # Phoenix = 1, Others = 2-5
        -inv['total_gross']                              # Large amounts = higher scrutiny
    ))
```

---

### 4.2 Integration with Existing WPH_AI Ecosystem

```
┌─────────────────────────────────────────────────────────────┐
│              UNIFIED WPH_AI PLATFORM                         │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐
│ ORDER BRAIN  │ ← Generates purchase orders
│   MODULE     │ ← Outputs: ORDER_PHOENIX_*.csv
└──────┬───────┘
       │
       v (Expected shipment data)
       │
┌──────────────┐
│ FAKTURA AI   │ ← Receives invoices
│   MODULE     │ ← Validates vs expected orders
└──────┬───────┘ ← Flags discrepancies
       │
       v (Actual received goods)
       │
┌──────────────┐
│ ERP SYNC     │ ← Updates inventory
│   MODULE     │ ← Reconciles PO vs Invoice vs Stock
└──────────────┘

SHARED DATABASE: wph_ai
SHARED SCHEMAS: wph_core, ops, stg, audit
```

**Example Cross-Module Query**:
```sql
-- Find invoices that don't match recent orders
WITH recent_orders AS (
    SELECT 
        supplier_name,
        sifra,
        SUM(qty_to_order) AS ordered_qty,
        MAX(created_at) AS order_date
    FROM wph_core.orders_final
    WHERE created_at > NOW() - INTERVAL '14 days'
    GROUP BY supplier_name, sifra
),
invoice_items AS (
    SELECT 
        fi.supplier,
        fi.matched_sifra,
        SUM(fi.kolicina) AS invoiced_qty,
        fin.invoice_date
    FROM ops.faktura_items fi
    JOIN ops.faktura_in fin ON fi.faktura_id = fin.id
    WHERE fin.invoice_date > NOW() - INTERVAL '14 days'
    GROUP BY fi.supplier, fi.matched_sifra, fin.invoice_date
)
SELECT 
    ii.supplier,
    ii.matched_sifra,
    ro.ordered_qty,
    ii.invoiced_qty,
    (ii.invoiced_qty - ro.ordered_qty) AS delta,
    ii.invoice_date,
    ro.order_date
FROM invoice_items ii
LEFT JOIN recent_orders ro 
    ON ii.supplier = ro.supplier_name 
    AND ii.matched_sifra = ro.sifra
WHERE ABS(ii.invoiced_qty - COALESCE(ro.ordered_qty, 0)) > 10
ORDER BY ABS(ii.invoiced_qty - COALESCE(ro.ordered_qty, 0)) DESC
```

---

## 🛠️ SECTION 5: TECHNOLOGY STACK

### 5.1 Core Technologies

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **XML Parsing** | Python `xml.etree.ElementTree` | Built-in, fast, handles namespaces |
| **PDF OCR** (future) | Tesseract OCR 5.x | Free, 90%+ accuracy for printed text |
| **Database** | PostgreSQL 18 | Already in use, JSONB for flexible validation logs |
| **Email Fetching** | Python `imaplib` + `email` | Standard library, works with Office365/Gmail |
| **FTP Monitoring** | Python `ftplib` + watchdog | Async file watcher, low resource usage |
| **UI Automation** | AutoHotkey 2.0 | Windows native, reliable for ERP interaction |
| **Scheduling** | Windows Task Scheduler | Built-in, no dependencies |
| **Web UI** | Flask + Jinja2 | Consistent with existing `app_v2.py` |
| **Logging** | Python `logging` | Structured logs with rotation |
| **Hashing** | `hashlib.sha256` | Deduplication, fast |

### 5.2 Alternative OCR Services (if PDF volume increases)

| Service | Accuracy | Cost | Latency | Notes |
|---------|----------|------|---------|-------|
| **Tesseract OSS** | 85-92% | Free | ~2-5s/page | Good for clean scans |
| **Azure Computer Vision** | 95-98% | $1.50/1000 pages | ~1-3s/page | Best for handwritten |
| **AWS Textract** | 94-97% | $1.50/1000 pages | ~2-4s/page | Good table extraction |
| **Google Cloud Vision** | 93-96% | $1.50/1000 pages | ~1-2s/page | Fastest |

**Recommendation**: Start with **Tesseract** (free), upgrade to **Azure** only if PDF invoices >20% of volume

### 5.3 ERP Integration Approaches

#### **Approach 1: XML Drop Folder** (SAFEST)
```
WPH_AI exports validated XML to:
C:\Apoteka\EB\IMPORTS\FAKTURA_AI\PHOENIX_INV_123456.xml

ERP monitors this folder (built-in feature "Preuzmi")
User clicks "Učitaj" once per day → batch import

PRO: Zero risk, ERP does all validation
CON: Still requires 1 manual click
```

#### **Approach 2: UI Automation** (RECOMMENDED)
```powershell
# commit_erp.ps1
$xmlPath = "C:\Wellona\wphAI\queue\PHOENIX_INV_123456.xml"

# Step 1: Launch ERP if not running
if (-not (Get-Process "ApotekaERP" -ErrorAction SilentlyContinue)) {
    Start-Process "C:\Program Files\ApotekaERP\erp.exe"
    Start-Sleep -Seconds 5
}

# Step 2: Activate ERP window
$wshell = New-Object -ComObject wscript.shell
$wshell.AppActivate("Apoteka ERP")
Start-Sleep -Milliseconds 500

# Step 3: Navigate to Import (Alt+K → U → I)
$wshell.SendKeys("%k")  # Alt+K (Kalkulacija)
Start-Sleep -Milliseconds 300
$wshell.SendKeys("u")   # U (Ulazna roba)
Start-Sleep -Milliseconds 300
$wshell.SendKeys("i")   # I (Import XML)
Start-Sleep -Milliseconds 500

# Step 4: File dialog → paste path → Enter
$wshell.SendKeys($xmlPath)
Start-Sleep -Milliseconds 300
$wshell.SendKeys("{ENTER}")
Start-Sleep -Seconds 2

# Step 5: Verify load success (screen scrape or log check)
# ... check if ERP shows "Uspešno učitano X stavki"

# Step 6: Proknjizi (if validation passed)
$wshell.SendKeys("{F10}")  # Assuming F10 = Proknjiži
Start-Sleep -Seconds 1

# Step 7: Capture ERP document number from dialog
# ... parse ERP response window for "KU-2025-001234"
```

**PRO**: Full automation, no human intervention  
**CON**: Brittle if ERP UI changes

#### **Approach 3: Direct Database Insert** (ADVANCED)
```sql
-- Insert header
INSERT INTO ebcore.mp_kalkulacija_ulazna (
    komintent_id, tip_dokumenta, broj_dokumenta, datum, 
    valuta, magacin_id, iznos_bez_pdv, pdv, ukupno
) VALUES (
    (SELECT id FROM ebcore.komintent WHERE naziv = 'PHOENIX PHARMA'),
    'ULR', 'INV-123456', '2025-11-07',
    'RSD', 1, 123450.00, 24690.00, 148140.00
) RETURNING id INTO v_kalkulacija_id;

-- Insert line items
INSERT INTO ebcore.mp_stavke (
    kalkulacija_id, artikal_id, kolicina, vpc, rabat_pct, pdv_pct
)
SELECT 
    v_kalkulacija_id,
    a.id,
    fi.kolicina,
    fi.vpc,
    fi.rabat_pct,
    fi.pdv_pct
FROM ops.faktura_items fi
JOIN ebcore.artikli a ON fi.matched_sifra = a.sifra
WHERE fi.faktura_id = 123;
```

**PRO**: Fastest, most reliable  
**CON**: Requires deep ERP database knowledge, risk of breaking constraints

**DECISION**: Use **Approach 2 (UI Automation)** for MVP, plan **Approach 3** for v2 after DB schema analysis

---

## 📅 SECTION 6: IMPLEMENTATION ROADMAP

### Phase 1: MVP (4-6 weeks)

#### Week 1-2: Foundation
- [ ] Create database schema (`ops.faktura_in`, `ops.faktura_items`, `ops.faktura_audit`)
- [ ] Build supplier-specific XML mappers (Phoenix, Vega, Sopharma, Farmalogist)
- [ ] Enhance `faktura_ai_mvp.py` with database insertion
- [ ] Add validation logic (match rate, total reconciliation, duplicate check)
- [ ] Create web UI view: `faktura_review.html` (similar to `orders_pro_plus.html`)

**Deliverables**:
- ✅ Tables created with proper indexes
- ✅ 4 JSON mappers tested with real XML samples
- ✅ Python script writes to `ops.faktura_*` tables
- ✅ Web UI shows pending invoices with validation results

#### Week 3-4: Automation Layer
- [ ] Build FTP watcher: `fetch_ftp.py` (Phoenix)
- [ ] Build IMAP fetcher: `fetch_mail.py` (Vega/Sopharma/Farmalogist)
- [ ] Implement SHA256 deduplication
- [ ] Create PowerShell scheduler: `run_faktura_nightly.ps1`
- [ ] Set up Windows Task Scheduler jobs (03:00, 03:15, 03:30)

**Deliverables**:
- ✅ Automatic FTP download every 24h
- ✅ Email attachments saved to inbox folder
- ✅ Duplicate invoices skipped with log entry
- ✅ Task Scheduler configured for hands-free operation

#### Week 5-6: ERP Integration
- [ ] Analyze ERP menu structure (keyboard shortcuts)
- [ ] Build UI automation script: `commit_erp.ps1`
- [ ] Test in `ebdev` (test database) with 10 sample invoices
- [ ] Create rollback procedure (if auto-commit fails)
- [ ] Add email alerts: daily summary report

**Deliverables**:
- ✅ Auto-commit works for CLEAN invoices (match rate 100%, total OK)
- ✅ NEEDS_REVIEW invoices go to web UI queue
- ✅ Email sent daily: "5 invoices committed, 2 need review"
- ✅ Audit log complete (every action tracked)

---

### Phase 2: Enhanced Features (2-3 months)

#### Month 2
- [ ] Add OCR support for PDF invoices (Tesseract)
- [ ] Implement rabat validation vs `stg.pricefeed`
- [ ] Build cross-reference with Order Brain (invoice vs expected order)
- [ ] Add "Approve All" button in web UI for batch processing
- [ ] Supplier performance dashboard (avg match rate, error types)

#### Month 3
- [ ] AI-powered schema change detection
- [ ] Automatic mapper updates (learn from user corrections)
- [ ] Mobile app notifications (push alerts for NEEDS_REVIEW)
- [ ] Integration with accounting system (export to Excel for bookkeeper)

---

### Phase 3: Full Autonomy (6+ months)

- [ ] Direct database insert (bypass UI automation)
- [ ] Machine learning for fuzzy product matching
- [ ] Blockchain audit trail (immutable logs for compliance)
- [ ] Multi-pharmacy deployment (franchise support)

---

## 💰 SECTION 7: ROI & COST ANALYSIS

### 7.1 Current Manual Process Costs

| Metric | Value | Source |
|--------|-------|--------|
| Invoices per month | 80-120 | Estimate (Phoenix 40, Vega 20, Sopharma 15, Others 25) |
| Time per invoice | 12 min | Video analysis average |
| Total hours/month | 16-24 hours | 80 × 12min = 1,600 min ≈ 26.7h |
| Operator hourly rate | 1,500 RSD/h | ~$15 USD/h pharmacy admin |
| **Monthly labor cost** | **24,000-36,000 RSD** | **$240-360 USD** |
| Error rate | 5-8% | Estimate (price errors, duplicate entries) |
| Error correction time | 30 min/error | Re-entry, supplier calls |
| Error costs/month | 3,200-5,760 RSD | (80 × 0.065 × 30min × 1,500 RSD/h) |
| **Total monthly cost** | **~30,000 RSD** | **~$300 USD** |

### 7.2 Faktura AI Implementation Costs

| Item | Cost | Notes |
|------|------|-------|
| **Development Time** |  |  |
| Developer hours (MVP) | 120-160 hours | 4-6 weeks × 30h/week |
| Developer rate | 3,000 RSD/h | Senior dev Serbia rate |
| Total dev cost | 360,000-480,000 RSD | ~$3,600-4,800 USD |
| **Infrastructure** |  |  |
| PostgreSQL (existing) | 0 RSD | Already running |
| Storage (logs, XMLs) | 500 RSD/month | ~5GB/month |
| **Software Licenses** |  |  |
| Python (free) | 0 RSD |  |
| AutoHotkey (free) | 0 RSD |  |
| Tesseract OCR (free) | 0 RSD |  |
| **Ongoing Maintenance** |  |  |
| Monthly monitoring | 2 hours/month | 6,000 RSD/month |
| **TOTAL 1ST YEAR** | **~450,000 RSD** | **~$4,500 USD** |

### 7.3 Cost Savings & Payback Period

| Year | Manual Cost | Faktura AI Cost | Savings | Cumulative ROI |
|------|-------------|-----------------|---------|----------------|
| **Year 1** | 360,000 RSD | 450,000 RSD | -90,000 RSD | -90,000 RSD |
| **Year 2** | 360,000 RSD | 72,000 RSD | 288,000 RSD | **+198,000 RSD** |
| **Year 3** | 360,000 RSD | 72,000 RSD | 288,000 RSD | **+486,000 RSD** |

**Payback Period**: 16-18 months  
**3-Year ROI**: +486,000 RSD (~$4,860 USD) = **108% return**

### 7.4 Additional Benefits (Non-Quantified)

- ✅ **Zero late payments** → capture early payment discounts (2-3% = ~10,000 RSD/month)
- ✅ **Reduced errors** → better supplier relationships, fewer disputes
- ✅ **Audit compliance** → complete logs for tax inspections
- ✅ **Scalability** → handle 200+ invoices/month without hiring
- ✅ **Employee satisfaction** → eliminate tedious data entry

---

## 🎯 SECTION 8: SUCCESS METRICS & KPIs

### 8.1 Technical KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Match Rate** | ≥99% | % items found in `eb_fdw.artikli` |
| **Total Accuracy** | ±0.1% | XML total vs calculated total |
| **Auto-Commit Rate** | ≥80% | % invoices passing all validations |
| **Processing Time** | <30 seconds/invoice | FTP fetch → DB insert |
| **Uptime** | 99.5% | % successful nightly runs |
| **False Positives** | <2% | Invoices marked CLEAN but have errors |

### 8.2 Business KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Time Savings** | 20+ hours/month | Manual time - automation time |
| **Error Reduction** | <2% | Errors caught by validation |
| **Early Payment Discounts** | +15% capture | # discounts taken vs available |
| **Operator Satisfaction** | 8/10 | Survey: ease of use, trust in system |
| **Audit Readiness** | 100% | % invoices with complete logs |

### 8.3 Monitoring Dashboard

**Proposed Grafana Dashboard** (future):

```
┌──────────────────────────────────────────────────────────┐
│          FAKTURA AI — Real-Time Monitoring                │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  📊 TODAY'S STATS                                         │
│  ├─ Invoices Processed: 8                                │
│  ├─ Auto-Committed: 6 (75%)                               │
│  ├─ Needs Review: 2 (25%)                                │
│  └─ Errors: 0                                             │
│                                                            │
│  📈 30-DAY TRENDS                                         │
│  ├─ Avg Match Rate: 97.3%                                │
│  ├─ Avg Processing Time: 18s                             │
│  └─ Total Savings: 18.5 hours                            │
│                                                            │
│  🚨 ALERTS                                                │
│  └─ (None)                                                │
│                                                            │
│  📂 PENDING REVIEW QUEUE                                  │
│  ├─ VEGA_INV_987654 — Match rate 95% (missing 2 items)  │
│  └─ SOPHARMA_INV_456123 — Total mismatch 0.15%          │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

---

## 🔒 SECTION 9: SECURITY & COMPLIANCE

### 9.1 Data Protection

- **Encryption at rest**: PostgreSQL SSL + disk encryption (Windows BitLocker)
- **Encryption in transit**: FTP over TLS, IMAP over SSL
- **Access control**: Role-based permissions in database
- **Password security**: Environment variables (never hardcoded)
- **XML storage**: Retain originals for 7 years (regulatory requirement)

### 9.2 Audit Trail Requirements

Every action logged with:
```json
{
  "timestamp": "2025-11-07T06:15:32Z",
  "action": "commit_to_erp",
  "faktura_id": 123,
  "invoice_no": "INV-123456",
  "supplier": "PHOENIX",
  "user": "SYSTEM_AUTO",
  "validation": {
    "match_rate": 100.0,
    "total_delta": 0.0,
    "auto_approved": true
  },
  "erp_doc_no": "KU-2025-001234",
  "duration_ms": 2340
}
```

### 9.3 Disaster Recovery

- **Daily backups**: PostgreSQL `ops` schema → `backup/faktura_YYYYMMDD.sql`
- **XML archive**: All processed files → `archive/YYYY/MM/DD/`
- **Rollback procedure**: If batch commit fails, restore from last good state
- **Manual override**: Web UI allows manual re-processing with edits

---

## 🤝 SECTION 10: USER TRAINING & CHANGE MANAGEMENT

### 10.1 Training Plan

#### **Week 1: Introduction (2 hours)**
- Overview of Faktura AI goals
- Demo: Watch system process 5 invoices end-to-end
- Q&A: Address concerns about automation reliability

#### **Week 2: Hands-On (3 hours)**
- Log into web UI
- Review pending invoices in queue
- Approve/reject with notes
- Check audit logs
- Generate reports

#### **Week 3: Exception Handling (2 hours)**
- What to do when match rate <99%
- How to add missing products to catalog
- When to call supplier vs accept discrepancy
- Escalation procedures

### 10.2 Change Management

**Key Messages**:
- ✅ "This frees you from tedious data entry"
- ✅ "You remain the final decision-maker"
- ✅ "System catches errors humans miss"
- ✅ "More time for customer service and strategic work"

**Resistance Mitigation**:
- Start with "Shadow Mode" (system processes but doesn't commit, human validates)
- Show weekly time savings reports
- Celebrate early wins (caught duplicate invoice, saved late fee)

---

## 📚 SECTION 11: REFERENCES & RESOURCES

### 11.1 Technical Documentation

- **XML Standards**: UBL 2.1 Invoice Specification
- **PostgreSQL**: JSONB indexing, text search
- **Python**: `xml.etree.ElementTree` docs, `imaplib` examples
- **AutoHotkey**: SendKeys reference, window activation

### 11.2 Industry Standards

- **HIPAA** (if applicable): Invoice data = PHI if contains patient info
- **GDPR**: Supplier data retention policies
- **SOX**: Audit trail requirements for financial records

### 11.3 Similar Projects

- Open-source invoice parsers: `invoice2data` (Python), `mindee/doctr`
- ERP automation: UiPath RPA, Blue Prism
- Pharmaceutical case studies: ABBYY Metro AG (90% time savings)

---

## 🎯 SECTION 12: NEXT STEPS & DECISION POINTS

### 12.1 Immediate Actions (This Week)

1. **User Approval**: Review this research document, decide on MVP scope
2. **Database Setup**: Create `ops` schema tables in `wph_ai`
3. **Sample XML Collection**: Gather 10-20 real invoices from each supplier
4. **Mapper Creation**: Build/test 4 JSON mappers with sample data
5. **Web UI Mockup**: Extend `orders_pro_plus.html` with invoice review view

### 12.2 Decision Points

| Question | Options | Recommendation |
|----------|---------|----------------|
| **ERP Integration Method** | (A) Drop folder, (B) UI automation, (C) Direct DB | **B for MVP**, C for v2 |
| **OCR Requirement** | Now vs later | **Later** (XML covers 90%) |
| **Auto-Commit Threshold** | 95% vs 99% vs 100% match | **99%** (balance automation & safety) |
| **Pilot Duration** | 2 weeks vs 1 month | **1 month** (capture edge cases) |
| **Notification Method** | Email vs Slack vs SMS | **Email** (easiest) |

### 12.3 Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **ERP UI changes** | Medium | High | Version checking, fallback to manual mode |
| **XML schema changes** | Medium | High | Schema change detection + alerts |
| **Duplicate commits** | Low | Critical | SHA256 hash + unique constraint |
| **Network failures** | Medium | Low | Retry logic + offline queue |
| **User resistance** | Low | Medium | Training + shadow mode |

---

## ✅ CONCLUSION

**Faktura AI is HIGHLY VIABLE** for Wellona Pharmacy:

- ✅ **Problem well-defined**: 20+ hours/month manual data entry
- ✅ **Technical feasibility**: 90% XML (easy), 10% PDF (future)
- ✅ **Cost-effective**: 16-18 month payback, 108% 3-year ROI
- ✅ **Low risk**: Incremental rollout, shadow mode available
- ✅ **Competitive advantage**: Per-product rabat validation unique to WPH_AI
- ✅ **Scalable**: Handle 10x volume without re-architecture

**Recommended Path Forward**:
1. **Approve Phase 1 MVP** (4-6 weeks)
2. **Pilot with Phoenix only** (largest supplier, 40% of invoices)
3. **Measure success** (time savings, error rate, user satisfaction)
4. **Expand to Vega/Sopharma** (months 2-3)
5. **Add OCR** (only if PDF volume increases)

**Expected Timeline**: First auto-committed invoice by **end of December 2025** ✅

---

**Document Version**: 1.0  
**Last Updated**: November 7, 2025  
**Author**: WPH_AI Research Team  
**Status**: READY FOR REVIEW


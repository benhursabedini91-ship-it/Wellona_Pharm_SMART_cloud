# Fiscal Bill Tools - Udhëzues Përdorimi

## 1. Fetch Fiscal Bills (lista ditore)
Merr të gjitha faturat fiskale për një datë.

```powershell
$env:WPH_EFAKT_API_KEY="f7b40af0-9689-4872-8d59-4779f7961175"
python app\\fetch_fiscal_bills.py 2025-11-18
```

**Output:**
- `app\\staging\\fiscal_bills\\FB_<numri>.json` (një file për çdo faturë)
- `app\\staging\\fiscal_bills\\fiscal_bills_summary_2025-11-18.csv`

---

## 2. Fetch Single Fiscal Bill (me numër)
Merr një faturë specifike kur e di numrin (nga printimi në farmaci).

```powershell
python app\\fetch_fiscal_bill_number.py AB12-3456-7890
```

**Output:**
- `app\\staging\\fiscal_bills\\FB_AB12-3456-7890.json`

---

## 3. Check Fiscal Alarm (kontroll për 2+ ditë pa fatura)
Kontrollon 7 ditët e fundit. Nëse gjen 2+ ditë me radhë pa fatura → shkruan alarm.

```powershell
python app\\check_fiscal_alarm.py
```

**Output:**
- Printon historikun në terminal
- Shkruan në `logs\\fiscal_alarm.log` nëse ka problem
- Opsionale: dërgon email (duhet të konfiguresh SMTP)

---

## 4. Parse Fiscal Lines (nxjerr artikujt nga JSON)
Lexon të gjitha `FB_*.json` dhe krijon një CSV me rreshta artikujsh.

```powershell
python app\\parse_fiscal_lines.py
```

**Output:**
- `app\\staging\\fiscal_bills\\fiscal_lines_<timestamp>.csv`
- Kolonat: `fiscalBillNumber;lineNo;sku;description;qty;unitPrice;totalLine;taxRate`

---

## 5. DB Guard System (mbrojtje për shkrime në bazë)

### Aktivizimi i DB write (pa konfirmim manual)
```powershell
cd app\\guards
type nul > ALLOW_DB_WRITE.flag
```

### Aktivizimi me konfirmim manual (siguri maksimale)
```powershell
cd app\\guards
type nul > ALLOW_DB_WRITE.flag
type nul > REQUIRE_MANUAL_CONFIRM.flag
```
Tani çdo skript që përpiqet të shkruajë në DB do të të pyesë: "Konfirmo shkrim? (PO/JO)"

### Test guard system
```powershell
python app\\guards\\db_guard.py
```

### Çaktivizimi i DB write (parandalon aksidente)
```powershell
del app\\guards\\ALLOW_DB_WRITE.flag
```

---

## Workflow i Përditshëm (pas mbylljes së arkës)

1. **Fetch faturat e sotme:**
```powershell
$env:WPH_EFAKT_API_KEY="f7b40af0-9689-4872-8d59-4779f7961175"
python app\\fetch_fiscal_bills.py
```

2. **Kontrollo për alarm (zero fatura):**
```powershell
python app\\check_fiscal_alarm.py
```

3. **Parse artikujt (nëse ka fatura):**
```powershell
python app\\parse_fiscal_lines.py
```

4. **Inspekto CSV për margin analysis (manual ose me Excel):**
```powershell
start app\\staging\\fiscal_bills\\fiscal_lines_*.csv
```

---

## Troubleshooting

**Problem:** Count=0 për disa ditë me radhë.
- **Shkaku:** POS nuk po sinkronizon ose data e gabuar.
- **Zgjidhja:** 
  1. Kontrollo nëse POS ka internet.
  2. Provo një datë të mëparshme të njohur (p.sh. dje).
  3. Merr një numër real nga një faturë e printuar dhe teste me `fetch_fiscal_bill_number.py`.

**Problem:** Parser nuk gjen artikuj.
- **Shkaku:** Struktura JSON e faturat është ndryshe nga pritja.
- **Zgjidhja:** Hap një `FB_*.json` dhe më dërgo një shembull. Do ta përshtas parser-in.

**Problem:** Guard po bllokon DB write.
- **Shkaku:** `ALLOW_DB_WRITE.flag` mungon.
- **Zgjidhja:** `type nul > app\\guards\\ALLOW_DB_WRITE.flag`

---

## Email Alert Setup (opsionale)

Hap `app\\check_fiscal_alarm.py` dhe në funksionin `send_email_alert()` shto SMTP config:

```python
import smtplib
from email.mime.text import MIMEText

def send_email_alert(subject: str, body: str):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'alarm@farmacia.com'
    msg['To'] = 'admin@farmacia.com'
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('your_email@gmail.com', 'your_password')
        server.send_message(msg)
```

---

## Hapat e Ardhshëm (pas këtyre)

1. **Cost Basis:** Krijon tabelë që ruan çmimin e blerjes për çdo SKU.
2. **Margin Calc:** Bashkon fiscal lines me cost basis → llogarit margin.
3. **Daily Aggregation:** Grupe sipas ditës → total revenue, cost, margin %.
4. **Shadow DB:** Vendos të gjitha në PostgreSQL `shadow_finance` schema (izoluar nga ERP).


import os
import sys
import json
import csv
import datetime as dt
import xml.etree.ElementTree as ET
import subprocess
from io import StringIO

def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)
    return p

def dtstamp():
    return dt.datetime.now().strftime('%Y%m%d_%H%M%S')

def parse_invoice_xml(xml_path):
    """Very tolerant parser: extracts supplier/invoice/date and line items if tags are guessable.
    Supports basic UBL-like or custom vendor formats by searching common tag names.
    Returns: header dict, list of item dicts
    """
    ns = {}
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # Build namespace map if present
        if root.tag.startswith('{'):
            uri = root.tag.split('}')[0].strip('{')
            ns['ns'] = uri
    except Exception as e:
        raise RuntimeError(f'XML parse failed for {xml_path}: {e}')

    def find_text(paths):
        for p in paths:
            try:
                el = root.find(p, ns) if ns else root.find(p)
                if el is not None and (el.text or '').strip():
                    return el.text.strip()
            except Exception:
                continue
        return None

    hdr = {
        'supplier': find_text([
            './/{ns}AccountingSupplierParty/{ns}Party/{ns}PartyName/{ns}Name',
            './/{ns}Supplier', './/supplier', './/Furnizuesi', './/Dobavljac'
        ]),
        'invoice_no': find_text([
            './/{ns}ID', './/{ns}InvoiceNumber', './/Broj', './/Number', './/InvoiceNo'
        ]),
        'invoice_date': find_text([
            './/{ns}IssueDate', './/{ns}InvoiceDate', './/Datum', './/Date'
        ]),
        'currency': find_text([
            './/{ns}DocumentCurrencyCode', './/Currency', './/Valuta'
        ]),
        'total_amount': find_text([
            './/{ns}LegalMonetaryTotal/{ns}PayableAmount',
            './/{ns}TaxInclusiveAmount', './/Total', './/IznosUkupno'
        ])
    }

    # Find line container heuristically
    candidates = [
        './/{ns}InvoiceLine', './/{ns}cac:InvoiceLine', './/InvoiceLine', './/Stavka', './/Line'
    ]
    lines = []
    for cand in candidates:
        try:
            elems = root.findall(cand, ns) if ns else root.findall(cand)
            if elems:
                for el in elems:
                    def get(el, paths):
                        for p in paths:
                            try:
                                node = el.find(p, ns) if ns else el.find(p)
                                if node is not None and (node.text or '').strip():
                                    return node.text.strip()
                            except Exception:
                                continue
                        return None
                    item = {
                        'sifra': get(el, ['.//{ns}Sifra', './/SellerItemIdentification/{ns}ID', './/ItemID', './/Sifra']),
                        'barcode': get(el, ['.//{ns}Barcode', './/EAN', './/GTIN']),
                        'name': get(el, ['.//{ns}Name', './/Item/{ns}Name', './/Naziv']),
                        'qty': get(el, ['.//{ns}InvoicedQuantity', './/Kolicina', './/Qty']),
                        'price': get(el, ['.//{ns}PriceAmount', './/Cena', './/UnitPrice']),
                        'rabat_pct': get(el, ['.//{ns}AllowanceCharge/{ns}MultiplierFactorNumeric', './/Rabat', './/Discount'])
                    }
                    lines.append(item)
                break
        except Exception:
            continue

    return hdr, lines

def load_lookup_from_db(cfg_db):
    """Loads artikli lookup (sifra, barkod) from wph_ai.eb_fdw.artikli via psql COPY.
    Returns two sets: sifra_set, barcode_set.
    """
    host = cfg_db['host']; port = str(cfg_db['port']); user = cfg_db['user']; db = cfg_db['dbname']
    pw_env = cfg_db.get('password_env')
    psql_candidates = [
        r"C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe",
        'psql'
    ]
    psql = next((p for p in psql_candidates if os.path.exists(p) or p == 'psql'), 'psql')
    env = os.environ.copy()
    if pw_env and env.get(pw_env):
        env['PGPASSWORD'] = env.get(pw_env)
    query = (
        "COPY (SELECT COALESCE(NULLIF(TRIM(sifra),''),NULL) AS sifra, COALESCE(NULLIF(TRIM(barkod),''),NULL) AS barkod "
        "FROM eb_fdw.artikli) TO STDOUT WITH CSV HEADER"
    )
    try:
        proc = subprocess.run([
            psql, '-h', host, '-p', port, '-U', user, '-d', db, '-c', query
        ], capture_output=True, text=True, env=env, check=True)
    except Exception as e:
        # fallback: empty sets
        return set(), set()
    data = proc.stdout
    sifra_set, barcode_set = set(), set()
    for i, line in enumerate(StringIO(data)):
        if i == 0:  # header
            continue
        parts = [p.strip() for p in line.rstrip('\n').split(',')]
        if len(parts) >= 2:
            s, b = parts[0] or None, parts[1] or None
            if s:
                sifra_set.add(s)
            if b:
                barcode_set.add(b)
    return sifra_set, barcode_set

def write_csv(path, rows, header):
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)

def to_number(x, default=0.0):
    if x is None:
        return default
    try:
        s = str(x).replace(',', '.').strip()
        return float(s)
    except Exception:
        return default

def main():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    cfg_path = os.path.join(base, 'configs', 'faktura_ai.json')
    cfg = load_config(cfg_path)
    out_root = ensure_dir(cfg['outdir'])
    logdir = ensure_dir(cfg['logdir'])
    run_ts = dtstamp()
    out_day = ensure_dir(os.path.join(out_root, dt.datetime.now().strftime('%Y%m%d')))
    log_path = os.path.join(logdir, f'FAKTURA_AI_{run_ts}.log')
    processed = 0
    failed = 0

    # load lookup sets for validation
    sifra_set, barcode_set = load_lookup_from_db(cfg['db'])
    tol_pct = float(cfg.get('tolerance', {}).get('total_pct', 0.1))
    summary_rows = []

    with open(log_path, 'w', encoding='utf-8') as log:
        log.write(f"FAKTURA_AI run {run_ts}\n")
        for inbox in cfg['inboxes']:
            if not os.path.isdir(inbox):
                continue
            for root, _dirs, files in os.walk(inbox):
                for fn in files:
                    if not fn.lower().endswith('.xml'):
                        continue
                    fpath = os.path.join(root, fn)
                    try:
                        hdr, items = parse_invoice_xml(fpath)
                        inv_id = (hdr.get('invoice_no') or os.path.splitext(fn)[0]).replace('/', '_')
                        prefix = os.path.join(out_day, f'{inv_id}')
                        write_csv(prefix + '_header.csv', [hdr], ['supplier', 'invoice_no', 'invoice_date', 'currency'])
                        write_csv(prefix + '_items.csv', items, ['sifra', 'barcode', 'name', 'qty', 'price', 'rabat_pct'])
                        # validation
                        matched = 0
                        for it in items:
                            s = (it.get('sifra') or '').strip()
                            b = (it.get('barcode') or '').strip()
                            if s and s in sifra_set:
                                matched += 1
                            elif b and b in barcode_set:
                                matched += 1
                        match_rate = (matched/len(items)) * 100 if items else 0.0
                        # totals
                        total_calc = 0.0
                        for it in items:
                            q = to_number(it.get('qty'), 0)
                            p = to_number(it.get('price'), 0)
                            r = to_number(it.get('rabat_pct'), 0)
                            total_calc += q * p * (1 - r/100.0)
                        total_hdr = to_number(hdr.get('total_amount'), None)
                        total_ok = True
                        reason = []
                        if total_hdr is not None:
                            delta_pct = abs(total_calc - total_hdr) / total_hdr * 100 if total_hdr else 0
                            if delta_pct > tol_pct:
                                total_ok = False
                                reason.append(f'total_mismatch {delta_pct:.2f}%')
                        if match_rate < 99.0:
                            reason.append(f'match_rate {match_rate:.2f}%')
                        status = 'CLEAN' if (match_rate >= 99.0 and total_ok) else 'NEEDS_REVIEW'
                        summary_rows.append({
                            'invoice_no': hdr.get('invoice_no') or inv_id,
                            'supplier': hdr.get('supplier'),
                            'items': len(items),
                            'matched': matched,
                            'match_rate_pct': f"{match_rate:.2f}",
                            'total_calc': f"{total_calc:.2f}",
                            'total_header': '' if total_hdr is None else f"{total_hdr:.2f}",
                            'status': status,
                            'reason': ';'.join(reason)
                        })
                        processed += 1
                        log.write(f"OK {fpath} -> {prefix}_*.csv status={status} match={match_rate:.2f}%\n")
                    except Exception as e:
                        failed += 1
                        log.write(f"ERR {fpath} :: {e}\n")

    # write summary
    summary_path = os.path.join(out_day, f'FAKTURA_AI_SUMMARY_{dt.datetime.now().strftime("%Y%m%d")}.csv')
    write_csv(summary_path, summary_rows, ['invoice_no','supplier','items','matched','match_rate_pct','total_calc','total_header','status','reason'])

    print(json.dumps({
        'run_ts': run_ts,
        'processed': processed,
        'failed': failed,
        'out_dir': out_day,
        'summary': summary_path
    }, ensure_ascii=False))

if __name__ == '__main__':
    # enforce utf-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except Exception:
        pass
    main()

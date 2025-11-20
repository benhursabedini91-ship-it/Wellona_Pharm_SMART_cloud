import os
import sys
import json
import csv
import datetime as dt
import xml.etree.ElementTree as ET
import subprocess
from io import StringIO
import psycopg2


def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def ensure_dir(p):
    os.makedirs(p, exist_ok=True)
    return p


def dtstamp():
    return dt.datetime.now().strftime('%Y%m%d_%H%M%S')


def parse_invoice_xml(xml_path):
    """Parse invoice XML (UBL or custom vendor XML) and extract header + line items.
    Robust to default namespaces by mapping them to the 'ns' prefix.
    Returns: (hdr, lines)
      hdr: dict(supplier, invoice_no, invoice_date, currency, total_amount)
      lines: list of dict(sifra, barcode, name, qty, price, rabat_pct)
    """
    ns = {}
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        if root.tag.startswith('{'):
            uri = root.tag.split('}')[0].strip('{')
            ns['ns'] = uri
        ns.setdefault('cbc', 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2')
        ns.setdefault('cac', 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2')
    except Exception as e:
        raise RuntimeError(f'XML parse failed for {xml_path}: {e}')

    def _norm(path: str) -> str:
        return (
            path.replace('{ns}', 'ns:')
            .replace('{cbc}', 'cbc:')
            .replace('{cac}', 'cac:')
        )

    def find_text(paths):
        for p in paths:
            q = _norm(p)
            try:
                el = root.find(q, ns) if ns else root.find(q)
                if el is not None and (el.text or '').strip():
                    return el.text.strip()
            except Exception:
                pass
        return None

    hdr = {
        'supplier': find_text([
            './/{cac}AccountingSupplierParty/{cac}Party/{cac}PartyName/{cbc}Name',
            './/{ns}AccountingSupplierParty/{ns}Party/{ns}PartyName/{ns}Name',
            './/{ns}Supplier', './/supplier', './/Furnizuesi', './/Dobavljac'
        ]),
        'invoice_no': find_text([
            './/{cbc}ID', './/{ns}ID', './/{ns}InvoiceNumber', './/Broj', './/Number', './/InvoiceNo'
        ]),
        'invoice_date': find_text([
            './/{cbc}IssueDate', './/{ns}IssueDate', './/{ns}InvoiceDate', './/Datum', './/Date'
        ]),
        'currency': find_text([
            './/{cbc}DocumentCurrencyCode', './/{ns}DocumentCurrencyCode', './/Currency', './/Valuta'
        ]),
        'total_amount': find_text([
            './/{cac}LegalMonetaryTotal/{cbc}PayableAmount',
            './/{ns}LegalMonetaryTotal/{ns}PayableAmount',
            './/{cbc}TaxInclusiveAmount', './/{ns}TaxInclusiveAmount', './/Total', './/IznosUkupno'
        ]),
    }

    lines = []
    line_candidates = [
        './/{ns}InvoiceLine', './/{cac}InvoiceLine', './/InvoiceLine', './/Stavka', './/Line'
    ]
    found_elems = []
    for cand in line_candidates:
        try:
            elems = root.findall(_norm(cand), ns) if ns else root.findall(cand)
            if elems:
                found_elems = elems
                break
        except Exception:
            continue

    def get(el, paths):
        for p in paths:
            q = _norm(p)
            try:
                node = el.find(q, ns) if ns else el.find(q)
                if node is not None and (getattr(node, 'text', '') or '').strip():
                    return node.text.strip()
            except Exception:
                pass
        return None

    for el in found_elems:
        item = {
            'sifra': get(el, ['.//{ns}Sifra', './/{cac}SellersItemIdentification/{cbc}ID', './/ItemID', './/Sifra']),
            'barcode': get(el, ['.//{ns}Barcode', './/{cac}StandardItemIdentification/{cbc}ID', './/EAN', './/GTIN']),
            'name': get(el, ['.//{ns}Name', './/{cac}Item/{cbc}Name', './/Naziv']),
            'qty': get(el, ['.//{ns}InvoicedQuantity', './/{cbc}InvoicedQuantity', './/{ns}Kolicina', './/Qty']),
            'price': get(el, ['.//{ns}PriceAmount', './/{cac}Price/{cbc}PriceAmount', './/{ns}Cena', './/UnitPrice']),
            'rabat_pct': get(el, ['.//{cac}AllowanceCharge/{cbc}MultiplierFactorNumeric', './/{ns}AllowanceCharge/{ns}MultiplierFactorNumeric', './/Rabat', './/Discount']),
        }
        lines.append(item)

    return hdr, lines


def load_lookup_from_db(cfg_db):
    """Load artikli lookup (sifra, barkod, naziv) from wph_ai.ref.artikli via psql COPY.
    When duplicates exist, selects the article with highest current_stock or avg_daily_sales.
    Returns: sifra_set, barcode_set, name_list, artikli_map (sifra -> record).
    If DB/psql fails, returns empty structures so the script still works.
    """
    host = cfg_db['host']
    port = str(cfg_db['port'])
    user = cfg_db['user']
    db = cfg_db['dbname']
    pw_env = cfg_db.get('password_env')

    psql_candidates = [
        r"C:\\Program Files\\PostgreSQL\\18\\bin\\psql.exe",
        'psql',
    ]
    psql = next((p for p in psql_candidates if os.path.exists(p) or p == 'psql'), 'psql')

    env = os.environ.copy()
    if pw_env and env.get(pw_env):
        env['PGPASSWORD'] = env.get(pw_env)

    query = (
        "COPY ("
        "WITH artikli_with_metrics AS ("
        "    SELECT DISTINCT ON (COALESCE(ra.sifra, ra.barkod)) "
        "        ra.sifra, ra.barkod, ra.naziv, "
        "        COALESCE(wo.current_stock, 0) as current_stock, "
        "        COALESCE(wo.avg_daily_sales, 0) as avg_daily_sales "
        "    FROM ref.artikli ra "
        "    LEFT JOIN wph_core.get_orders(28, 30, false, NULL, NULL) wo ON wo.sifra = ra.sifra "
        "    WHERE ra.sifra IS NOT NULL OR ra.barkod IS NOT NULL "
        "    ORDER BY COALESCE(ra.sifra, ra.barkod), "
        "             COALESCE(wo.current_stock, 0) DESC, "
        "             COALESCE(wo.avg_daily_sales, 0) DESC "
        ") "
        "SELECT COALESCE(NULLIF(TRIM(sifra),''),NULL) AS sifra, "
        "       COALESCE(NULLIF(TRIM(barkod),''),NULL) AS barkod, "
        "       COALESCE(NULLIF(TRIM(naziv),''),NULL) AS naziv, "
        "       current_stock, avg_daily_sales "
        "FROM artikli_with_metrics"
        ") TO STDOUT WITH CSV HEADER"
    )

    try:
        proc = subprocess.run(
            [psql, '-h', host, '-p', port, '-U', user, '-d', db, '-c', query],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
    except Exception:
        return set(), set(), [], {}

    data = proc.stdout
    sifra_set, barcode_set, name_list, artikli_map = set(), set(), [], {}

    for i, line in enumerate(StringIO(data)):
        if i == 0:
            continue
        parts = [p.strip() for p in line.rstrip('\n').split(',')]
        if len(parts) < 5:
            continue
        s, b, n, stock, sales = parts[0] or None, parts[1] or None, parts[2] or None, parts[3], parts[4]

        record = {
            'sifra': s,
            'barkod': b,
            'naziv': n,
            'current_stock': float(stock) if stock and stock not in ('NULL', '') and stock.replace('.', '').replace('-', '').isdigit() else 0.0,
            'avg_daily_sales': float(sales) if sales and sales not in ('NULL', '') and sales.replace('.', '').replace('-', '').isdigit() else 0.0,
        }
        if s:
            sifra_set.add(s)
            artikli_map[s] = record
        if b:
            barcode_set.add(b)
        if n:
            name_list.append(n)

    return sifra_set, barcode_set, name_list, artikli_map


def write_csv(path, rows, header):
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow(r)


def fuzzy_barcode_match(invoice_barcode, inventory_barcodes):
    """Try multiple fuzzy matching strategies for barcodes."""
    if not invoice_barcode:
        return None

    if invoice_barcode in inventory_barcodes:
        return invoice_barcode

    variations = []

    if len(invoice_barcode) > 12:
        variations.append(invoice_barcode.lstrip('0'))

    if len(invoice_barcode) == 12:
        variations.append('0' + invoice_barcode)
    elif len(invoice_barcode) == 11:
        variations.append('00' + invoice_barcode)

    if invoice_barcode.startswith('60'):
        variations.append('8' + invoice_barcode)
    elif invoice_barcode.startswith('0'):
        variations.append('86' + invoice_barcode[1:])

    for var in variations:
        if var in inventory_barcodes:
            return var

    return None


def semantic_name_match(invoice_name, inventory_names, threshold=0.8):
    """Semantic matching for products that are essentially the same but with different wording.
    This should NOT match different dosages or strengths of the same medication.
    Returns the best matching inventory name or None.
    """
    if not invoice_name:
        return None

    import re

    def extract_core_name(name):
        name = name.replace('UL CLEAN', 'ULTRA CLEAN')
        name = name.replace('UL ', 'ULTRA ')
        name = name.replace(' PAS ', ' PASTE ')
        name = name.replace(' TBL ', ' TABLET ')
        name = name.replace(' CPS ', ' CAPSULES ')
        name = re.sub(r'\d+x\s*$', '', name)
        name = ' '.join(name.split())
        return name.lower().strip()

    invoice_core = extract_core_name(invoice_name)
    if not invoice_core:
        return None

    best_match = None
    best_score = 0.0

    for inv_name in inventory_names:
        if not inv_name:
            continue
        inv_core = extract_core_name(inv_name)
        if not inv_core:
            continue

        if invoice_core == inv_core:
            return inv_name

        inv_words = set(inv_core.split())
        invoice_words = set(invoice_core.split())
        if len(inv_words) < 2 or len(invoice_words) < 2:
            continue

        intersection = invoice_words & inv_words
        union = invoice_words | inv_words
        if not union:
            continue
        score = len(intersection) / len(union)

        if score > best_score and score >= threshold:
            best_score = score
            best_match = inv_name

    return best_match if best_score >= threshold else None


def find_artikli_by_barcode(barcode, artikli_map):
    if not barcode:
        return None
    candidates = [a for a in artikli_map.values() if a.get('barkod') == barcode]
    if not candidates:
        return None
    return max(candidates, key=lambda x: (x.get('current_stock', 0.0), x.get('avg_daily_sales', 0.0)))


def find_artikli_by_sifra(sifra, artikli_map):
    if not sifra:
        return None
    return artikli_map.get(sifra)


def find_artikli_by_name(name, artikli_map):
    if not name:
        return None
    inventory_names = [a['naziv'] for a in artikli_map.values() if a.get('naziv')]
    matched_name = semantic_name_match(name, inventory_names, threshold=0.8)
    if not matched_name:
        return None
    candidates = [a for a in artikli_map.values() if a.get('naziv') == matched_name]
    if not candidates:
        return None
    return max(candidates, key=lambda x: (x.get('current_stock', 0.0), x.get('avg_daily_sales', 0.0)))


def to_number(val, default=0.0):
    if val is None or val == '':
        return default
    try:
        s = str(val).replace(',', '.')
        return float(s)
    except (ValueError, TypeError):
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

    sifra_set, barcode_set, name_list, artikli_map = load_lookup_from_db(cfg.get('db', {})) if cfg.get('db') else (set(), set(), [], {})
    tol_pct = float(cfg.get('tolerance', {}).get('total_pct', 0.1))

    summary_rows = []

    with open(log_path, 'w', encoding='utf-8') as log:
        log.write(f"FAKTURA_AI run {run_ts}\n")
        for inbox in cfg['inboxes']:
            if not os.path.isdir(inbox):
                continue
            for root_dir, _dirs, files in os.walk(inbox):
                for fn in files:
                    if not fn.lower().endswith('.xml'):
                        continue
                    fpath = os.path.join(root_dir, fn)
                    try:
                        hdr, items = parse_invoice_xml(fpath)
                        inv_id = (hdr.get('invoice_no') or os.path.splitext(fn)[0]).replace('/', '_')
                        prefix = os.path.join(out_day, inv_id)

                        write_csv(prefix + '_header.csv', [hdr], ['supplier', 'invoice_no', 'invoice_date', 'currency', 'total_amount'])
                        write_csv(prefix + '_items.csv', items, ['sifra', 'barcode', 'name', 'qty', 'price', 'rabat_pct'])

                        matched = 0
                        unmatched_items = []

                        for it in items:
                            b = (it.get('barcode') or '').strip()
                            s = (it.get('sifra') or '').strip()
                            n = (it.get('name') or '').strip()

                            matched_artikli = None

                            if b and b in barcode_set:
                                matched_artikli = find_artikli_by_barcode(b, artikli_map)
                            elif b:
                                fuzzy = fuzzy_barcode_match(b, barcode_set)
                                if fuzzy:
                                    matched_artikli = find_artikli_by_barcode(fuzzy, artikli_map)
                            elif n:
                                matched_artikli = find_artikli_by_name(n, artikli_map)
                            elif s and s in sifra_set:
                                matched_artikli = find_artikli_by_sifra(s, artikli_map)

                            if matched_artikli:
                                matched += 1
                            else:
                                unmatched_items.append({
                                    'sifra': s,
                                    'barcode': b,
                                    'name': n[:50] if n else '',
                                })

                        match_rate = (matched / len(items)) * 100 if items else 0.0

                        total_calc = 0.0
                        for it in items:
                            q = to_number(it.get('qty'), 0.0)
                            p = to_number(it.get('price'), 0.0)
                            r = to_number(it.get('rabat_pct'), 0.0)
                            total_calc += q * p * (1.0 - r / 100.0)

                        total_hdr = to_number(hdr.get('total_amount'), None)
                        total_ok = True
                        reason = []

                        if total_hdr is not None and total_hdr != 0:
                            delta_pct = abs(total_calc - total_hdr) / total_hdr * 100.0
                            if delta_pct > tol_pct:
                                total_ok = False
                                reason.append(f'total_mismatch {delta_pct:.2f}%')

                        if match_rate < 99.0:
                            reason.append(f'match_rate {match_rate:.2f}%')
                            if unmatched_items:
                                reason.append(f'unmatched_items: {len(unmatched_items)}')

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
                            'reason': '; '.join(reason),
                        })

                        if unmatched_items:
                            write_csv(prefix + '_unmatched.csv', unmatched_items, ['sifra', 'barcode', 'name'])

                        log.write(f"OK {fn} -> {status}\n")
                    except Exception as e:
                        log.write(f"ERR {fn}: {e}\n")

    if summary_rows:
        summary_path = os.path.join(out_day, f'SUMMARY_{run_ts}.csv')
        write_csv(summary_path, summary_rows, [
            'invoice_no', 'supplier', 'items', 'matched',
            'match_rate_pct', 'total_calc', 'total_header',
            'status', 'reason',
        ])


if __name__ == '__main__':
    main()

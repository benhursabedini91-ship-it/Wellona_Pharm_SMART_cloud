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
    """
    # Build namespace map
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
        return (path.replace('{ns}', 'ns:')
                    .replace('{cbc}', 'cbc:')
                    .replace('{cac}', 'cac:'))

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
        ])
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
            'rabat_pct': get(el, ['.//{cac}AllowanceCharge/{cbc}MultiplierFactorNumeric', './/{ns}AllowanceCharge/{ns}MultiplierFactorNumeric', './/Rabat', './/Discount'])
        }
        lines.append(item)

    return hdr, lines

def load_lookup_from_db(cfg_db):
    """Loads artikli lookup (sifra, barkod, naziv) from wph_ai.ref.artikli via psql COPY.
    When duplicates exist, selects the article with highest current_stock or avg_daily_sales.
    Returns: sifra_set, barcode_set, name_list, artikli_map (sifra -> full record).
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
    
    # Query that selects best article when duplicates exist
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
        "COALESCE(NULLIF(TRIM(barkod),''),NULL) AS barkod, "
        "COALESCE(NULLIF(TRIM(naziv),''),NULL) AS naziv, "
        "current_stock, avg_daily_sales "
        "FROM artikli_with_metrics"
        ") TO STDOUT WITH CSV HEADER"
    )
    
    try:
        proc = subprocess.run([
            psql, '-h', host, '-p', port, '-U', user, '-d', db, '-c', query
        ], capture_output=True, text=True, env=env, check=True)
    except Exception as e:
        # fallback: empty sets and list
        return set(), set(), [], {}
    
    data = proc.stdout
    sifra_set, barcode_set, name_list, artikli_map = set(), set(), [], {}
    
    for i, line in enumerate(StringIO(data)):
        if i == 0:  # header
            continue
        parts = [p.strip() for p in line.rstrip('\n').split(',')]
        if len(parts) >= 5:
            s, b, n, stock, sales = parts[0] or None, parts[1] or None, parts[2] or None, parts[3], parts[4]
            
            # Create artikli record
            artikli_record = {
                'sifra': s,
                'barkod': b, 
                'naziv': n,
                'current_stock': float(stock) if stock and stock not in ('NULL', '') and stock.replace('.', '').replace('-', '').isdigit() else 0,
                'avg_daily_sales': float(sales) if sales and sales not in ('NULL', '') and sales.replace('.', '').replace('-', '').isdigit() else 0
            }
            
            if s:
                sifra_set.add(s)
                artikli_map[s] = artikli_record
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
    
    # Exact match
    if invoice_barcode in inventory_barcodes:
        return invoice_barcode
    
    # Try different variations
    variations = []
    
    # Remove leading zeros (but keep at least 12 digits for EAN-13)
    if len(invoice_barcode) > 12:
        variations.append(invoice_barcode.lstrip('0'))
    
    # Add leading zeros to make 13 digits
    if len(invoice_barcode) == 12:
        variations.append('0' + invoice_barcode)
    elif len(invoice_barcode) == 11:
        variations.append('00' + invoice_barcode)
    
    # Try with different country prefixes (860 -> 8, etc.)
    if invoice_barcode.startswith('60'):
        variations.append('8' + invoice_barcode)
    elif invoice_barcode.startswith('0'):
        variations.append('86' + invoice_barcode[1:])
    
    # Check all variations
    for var in variations:
        if var in inventory_barcodes:
            return var
    
    return None

def find_artikli_by_barcode(barcode, artikli_map):
    """Find artikli record by barcode (exact or fuzzy match). Returns best artikli if duplicates."""
    if not barcode:
        return None
    
    candidates = []
    
    # Try exact match first
    for artikli in artikli_map.values():
        if artikli['barkod'] == barcode:
            candidates.append(artikli)
    
    # Try fuzzy variations if no exact match
    if not candidates:
        variations = []
        if len(barcode) > 12:
            variations.append(barcode.lstrip('0'))
        if barcode.startswith('0'):
            variations.append('86' + barcode[1:])
        if barcode.startswith('60'):
            variations.append('8' + barcode)
        
        for var in variations:
            for artikli in artikli_map.values():
                if artikli['barkod'] == var:
                    candidates.append(artikli)
    
    # Return best candidate (highest stock or sales)
    if candidates:
        return max(candidates, key=lambda x: (x['current_stock'], x['avg_daily_sales']))
    
    return None

def find_artikli_by_sifra(sifra, artikli_map):
    """Find artikli record by sifra. Returns best artikli if duplicates."""
    if not sifra:
        return None
    
    artikli = artikli_map.get(sifra)
    return artikli  # artikli_map already contains the best one per sifra

def find_artikli_by_name(name, artikli_map):
    """Find artikli record by semantic name match. Returns best artikli if duplicates."""
    if not name:
        return None
    
    # Get all names from artikli_map
    inventory_names = [art['naziv'] for art in artikli_map.values() if art['naziv']]
    
    matched_name = semantic_name_match(name, inventory_names, threshold=0.8)
    if matched_name:
        # Find all artikli records with this name
        candidates = [art for art in artikli_map.values() if art['naziv'] == matched_name]
        
        # Return best candidate (highest stock or sales)
        if candidates:
            return max(candidates, key=lambda x: (x['current_stock'], x['avg_daily_sales']))
    
def register_new_artikuj(new_items, cfg_db, supplier_name):
    """Register new artikuj in the database using advanced lookup logic."""
    if not new_items:
        return 0
    
    host = cfg_db['host']; port = str(cfg_db['port']); user = cfg_db['user']; db = cfg_db['dbname']
    pw_env = cfg_db.get('password_env')
    
    # Connect to database
    conn = None
    try:
        conn = psycopg2.connect(
            host=host, port=port, user=user, dbname=db,
            password=os.environ.get(pw_env) if pw_env else None
        )
        cur = conn.cursor()
        
        registered = 0
        for item in new_items:
            # Convert our format to sopharma format
            sopharma_item = {
                'sifra': item.get('sifra', ''),
                'barcode': item.get('barcode', ''),
                'naziv': item.get('name', ''),
                'pdv_pct': 10.0  # Default PDV for medications
            }
            
            # Use the advanced lookup logic from sopharma_to_erp.py
            sifra, naziv, ruc, action = lookup_or_create_artikal(cur, sopharma_item, 'ref.', auto_register=True, supplier_name=supplier_name)
            
            if action == 'CREATED':
                registered += 1
                print(f"✓ Regjistruar artikull i ri: {sifra} - {naziv}")
            elif action in ['FOUND', 'BARCODE_ADDED', 'SIFRA_FALLBACK']:
                print(f"✓ Artikulli ekzistonte: {sifra} - {naziv} (action: {action})")
        
        conn.commit()
        return registered
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Gabim gjatë regjistrimit: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def lookup_or_create_artikal(cur, item, schema_prefix='ref.', auto_register=True, supplier_name='Unknown'):
    """Resolve or create an artikal by barcode/name - adapted from sopharma_to_erp.py"""
    
    barcode = (item.get('barcode') or '').strip()
    supplier_sifra = (item.get('sifra') or '').strip()
    naziv = (item.get('naziv') or 'UNKNOWN')[:40]
    
    def get_last_ruc(sifra):
        """Get RUC from most recent purchase of this article."""
        try:
            cur.execute(f"""
                SELECT rucstopa FROM {schema_prefix}kalkstavke 
                WHERE artikal=%s AND rucstopa > 0 
                ORDER BY id DESC LIMIT 1
            """, [sifra])
            row = cur.fetchone()
            return row[0] if row else None
        except:
            return None

    # Auto-create flag from environment (overrides passed default)
    allow_auto_create = os.getenv('WPH_ALLOW_AUTO_CREATE', '1') == '1'  # Default enabled for our system
    auto_register = auto_register and allow_auto_create

    # 1. Primary barcode match in artikli
    if barcode:
        cur.execute(f"SELECT sifra, naziv, barkod FROM {schema_prefix}artikli WHERE barkod=%s LIMIT 1", [barcode])
        row = cur.fetchone()
        if row:
            ruc = get_last_ruc(row[0])
            return (row[0], row[1], ruc, 'FOUND')
        
        # Trim leading zeros variant
        b_trim = barcode.lstrip('0')
        if b_trim and b_trim != barcode:
            cur.execute(f"SELECT sifra, naziv, barkod FROM {schema_prefix}artikli WHERE LTRIM(barkod,'0')=%s LIMIT 1", [b_trim])
            row = cur.fetchone()
            if row:
                ruc = get_last_ruc(row[0])
                return (row[0], row[1], ruc, 'FOUND')

    # 2. Fuzzy name match
    if naziv and naziv != 'UNKNOWN':
        norm_name = ' '.join(naziv.upper().split())
        try:
            cur.execute(f"""
                SELECT sifra, naziv FROM {schema_prefix}artikli
                WHERE UPPER(naziv) LIKE %s
                ORDER BY sifra LIMIT 1
            """, [f"%{norm_name[:25]}%"])
            row = cur.fetchone()
            if row:
                # If we have a barcode, register it as alternative if possible
                if barcode:
                    try:
                        # Try to add barcode as alternative (if artikliean table exists)
                        cur.execute(f"INSERT INTO {schema_prefix}artikliean(sifra, ean) VALUES (%s,%s)", [row[0], barcode])
                    except Exception:
                        pass  # Table might not exist or barcode already exists
                ruc = get_last_ruc(row[0])
                return (row[0], row[1], ruc, 'BARCODE_ADDED')
        except Exception:
            pass

    # 3. Fallback by supplier sifra
    if supplier_sifra:
        cur.execute(f"SELECT sifra, naziv FROM {schema_prefix}artikli WHERE sifra=%s LIMIT 1", [supplier_sifra])
        row = cur.fetchone()
        if row:
            ruc = get_last_ruc(row[0])
            return (row[0], row[1], ruc, 'SIFRA_FALLBACK')

    # 4. Auto-register if allowed
    if auto_register and (barcode or naziv != 'UNKNOWN'):
        # Generate new sifra
        cur.execute(f"SELECT COALESCE(MAX(sifra::bigint),2300000000)+1 FROM {schema_prefix}artikli WHERE sifra ~ '^\\d+$'")
        new_sifra = str(cur.fetchone()[0])
        
        # Intelligent defaults based on item data
        default_vrsta = 'LEK'  # Default as medication
        default_jedmere = 'KOM'
        default_minzaliha = 10.0
        default_pakovanje = 1.0
        default_marza = 25.0  # Higher margin for medications
        
        # Map PDV to tax code
        pdv_pct = item.get('pdv_pct', 10.0)
        if pdv_pct >= 20:
            default_vrstaporeza = 'Ð'  # 20%
        elif pdv_pct >= 10:
            default_vrstaporeza = 'E'  # 10%
        else:
            default_vrstaporeza = 'Γ'  # 0%
        
        note = f'Auto-regjistruar nga fatura {supplier_name}'
        
        try:
            # Try full insert with all fields
            cur.execute(f"""
                INSERT INTO {schema_prefix}artikli
                  (sifra, naziv, jedmere, vrstaartikla, vrstaporeza, barkod, napomena, pakovanje, minzaliha, marza)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [
                new_sifra, naziv, default_jedmere, default_vrsta, default_vrstaporeza,
                barcode if barcode else None, note, default_pakovanje, default_minzaliha, default_marza
            ])
            
            # Try to add barcode as alternative
            if barcode:
                try:
                    cur.execute(f"INSERT INTO {schema_prefix}artikliean(sifra, ean) VALUES (%s,%s)", [new_sifra, barcode])
                except Exception:
                    pass  # Table might not exist
            
            return (new_sifra, naziv, None, 'CREATED')
            
        except Exception as e:
            # Fallback to minimal insert
            try:
                cur.execute(f"""
                    INSERT INTO {schema_prefix}artikli
                      (sifra, naziv, jedmere, vrstaartikla, vrstaporeza, barkod, napomena)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, [
                    new_sifra, naziv, default_jedmere, default_vrsta, default_vrstaporeza,
                    barcode if barcode else None, note
                ])
                return (new_sifra, naziv, None, 'CREATED')
            except Exception as e2:
                print(f"❌ Dështoi regjistrimi i artikullit: {e2}")
                return (None, None, None, 'NOT_FOUND')

    return (None, None, None, 'NOT_FOUND')
    """Semantic matching for products that are essentially the same but with different wording.
    This should NOT match different dosages or strengths of the same medication."""
    if not invoice_name:
        return None
    
    # Extract core product name by normalizing abbreviations but keeping key identifiers
    import re
    
    def extract_core_name(name):
        # Normalize common abbreviations
        name = name.replace('UL CLEAN', 'ULTRA CLEAN')
        name = name.replace('UL ', 'ULTRA ')
        name = name.replace(' PAS ', ' PASTE ')
        name = name.replace(' TBL ', ' TABLET ')
        name = name.replace(' CPS ', ' CAPSULES ')
        
        # For semantic matching, we want to keep the dosage as part of the identity
        # Only remove packaging quantities (30x, 20x) but keep the actual dosage
        name = re.sub(r'\d+x\s*$', '', name)  # Remove trailing quantities like "30x"
        
        # Clean up extra spaces
        name = ' '.join(name.split())
        return name.lower().strip()
    
    invoice_core = extract_core_name(invoice_name)
    if not invoice_core:
        return None
    
    best_match = None
    best_score = 0
    
    for inv_name in inventory_names:
        if not inv_name:
            continue
        
        inv_core = extract_core_name(inv_name)
        if not inv_core:
            continue
        
        # For semantic matching, require very high similarity
        # This prevents matching different dosages
        if invoice_core == inv_core:
            return inv_name  # Exact match after normalization
        
        # For fuzzy matching, require most words to match
        inv_words = set(inv_core.split())
        invoice_words = set(invoice_core.split())
        
        if len(inv_words) < 2 or len(invoice_words) < 2:
            continue
            
        intersection = invoice_words & inv_words
        union = invoice_words | inv_words
        
        if union:
            score = len(intersection) / len(union)
            
            # Only match if score is very high (near identical)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = inv_name
    
    return best_match if best_score >= threshold else None

def to_number(val, default=0):
    """Convert string to number, return default if conversion fails."""
    if val is None or val == '':
        return default
    try:
        # Handle comma as decimal separator (common in some locales)
        val_str = str(val).replace(',', '.')
        return float(val_str)
    except (ValueError, TypeError):
        return default

def generate_new_sifra(existing_sifra_set, supplier_prefix=""):
    """Gjeneron një šifrë të re unike për artikullin e ri.
    Përdor logjikë autoregjenerimi: merr numrin më të lartë dhe shton 1."""
    if not existing_sifra_set:
        return "10000001"  # Šifra fillestare
    
    # Merr vetëm šifrat numerike
    numeric_sifra = []
    for s in existing_sifra_set:
        if s and s.isdigit():
            try:
                numeric_sifra.append(int(s))
            except ValueError:
                continue
    
    if numeric_sifra:
        next_sifra = max(numeric_sifra) + 1
        return str(next_sifra)
    
    # Fallback nëse nuk ka šifra numerike
    return f"{supplier_prefix}{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"

def create_new_artikli_record(invoice_item, supplier_name, existing_sifra_set):
    """Krijon një rekord të ri për artikullin bazuar në të dhënat nga fatura."""
    
    # Gjenero šifrën e re
    new_sifra = generate_new_sifra(existing_sifra_set, supplier_name[:3].upper())
    
    # Pastro emrin e produktit
    name = (invoice_item.get('name') or '').strip()
    
    # Pastro barcode-in
    barcode = (invoice_item.get('barcode') or '').strip()
    
    # Vendos vlerat default sipas udhëzuesit
    artikli_record = {
        'sifra': new_sifra,
        'naziv': name,
        'jedinica_mere': 'KOM',  # Default: copë
        'barkod': barcode,
        'poreska_stopa': 'E',  # Default: 10% për barna
        'vrsta_artikla': 'LEK',  # Default: ilaç
        'proizvodac': supplier_name,  # Prodhuesi = furnitori
        'grupa': 'MEDIKAMENTE',  # Default grup
        'podgrupa': '',
        'trgovacko_pakovanje': '1',  # Default: 1 copë
        'minimalna_zaliha': '10',  # Default minimal
        'napomena': f'Importuar nga fatura {supplier_name}',
        'opis': f'Artikull i ri nga {supplier_name} - {name}',
        'marza': '25',  # Default marzhë 25%
        'jkl': 'JKL',  # Default për ilaçet
        'vrsta_leka': '',  # Do vendoset manualisht nëse është antibiotik etj.
        'barkod_shtese': []  # Lista për barkode shtesë
    }
    
    # Inteligjent guessing për disa fusha bazuar në emër
    name_lower = name.lower()
    
    # Vendos njësia bazuar në emër
    if any(word in name_lower for word in ['tablete', 'tbl', 'caps', 'kapsula']):
        artikli_record['jedinica_mere'] = 'KOM'
    elif any(word in name_lower for word in ['ampula', 'amp']):
        artikli_record['jedinica_mere'] = 'AMP'
    elif any(word in name_lower for word in ['sirup', 'sir']):
        artikli_record['jedinica_mere'] = 'BOC'
    elif any(word in name_lower for word in ['krema', 'gel', 'pasta']):
        artikli_record['jedinica_mere'] = 'TUB'
    
    # Vendos TVSH bazuar në lloj
    if any(word in name_lower for word in ['antibiotik', 'insulin', 'vaccine']):
        artikli_record['poreska_stopa'] = 'E'  # 10%
    elif any(word in name_lower for word in ['pajisje', 'material']):
        artikli_record['poreska_stopa'] = 'Ð'  # 20%
    
    # Vendos llojin e ilaçit nëse mund të identifikohet
    if 'antibiotik' in name_lower or 'antibiotic' in name_lower:
        artikli_record['vrsta_leka'] = 'antibiotik'
    elif any(word in name_lower for word in ['sedativ', 'anxiolitik', 'hipnotik']):
        artikli_record['vrsta_leka'] = 'sedativ'
    elif any(word in name_lower for word in ['narkotik', 'opioid', 'morfin']):
        artikli_record['vrsta_leka'] = 'narkotik'
    
    return artikli_record

def write_new_artikuj_csv(new_artikuj, output_path):
    """Shkruan artikujt e rinj në një skedar CSV për import në ERP."""
    if not new_artikuj:
        return
    
    ensure_dir(os.path.dirname(output_path))
    
    fieldnames = [
        'sifra', 'naziv', 'jedinica_mere', 'barkod', 'poreska_stopa', 
        'vrsta_artikla', 'proizvodac', 'grupa', 'podgrupa', 
        'trgovacko_pakovanje', 'minimalna_zaliha', 'napomena', 'opis',
        'marza', 'jkl', 'vrsta_leka'
    ]
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for artikli in new_artikuj:
            writer.writerow(artikli)

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
    sifra_set, barcode_set, name_list, artikli_map = load_lookup_from_db(cfg['db'])
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
                        
                        # validation - enhanced matching with fallbacks
                        matched = 0
                        unmatched_items = []
                        matched_artikuj = []  # Track which artikuj were matched
                        
                        for it in items:
                            b = (it.get('barcode') or '').strip()
                            s = (it.get('sifra') or '').strip()
                            n = (it.get('name') or '').strip()
                            
                            matched_artikli = None
                            
                            # Priority 1: Exact barcode match
                            if b and b in barcode_set:
                                matched_artikli = find_artikli_by_barcode(b, artikli_map)
                                if matched_artikli:
                                    matched += 1
                                    matched_artikuj.append(matched_artikli)
                            
                            # Priority 2: Fuzzy barcode match
                            elif b:
                                fuzzy_barcode = fuzzy_barcode_match(b, barcode_set)
                                if fuzzy_barcode:
                                    matched_artikli = find_artikli_by_barcode(fuzzy_barcode, artikli_map)
                                    if matched_artikli:
                                        matched += 1
                                        matched_artikuj.append(matched_artikli)
                            
                            # Priority 3: Semantic name match (for items without barcode)
                            elif n:
                                matched_artikli = find_artikli_by_name(n, artikli_map)
                                if matched_artikli:
                                    matched += 1
                                    matched_artikuj.append(matched_artikli)
                            
                            # Priority 4: Sifra fallback (least reliable for invoices)
                            elif s and s in sifra_set:
                                matched_artikli = find_artikli_by_sifra(s, artikli_map)
                                if matched_artikli:
                                    matched += 1
                                    matched_artikuj.append(matched_artikli)
                            
                            if not matched_artikli:
                                # Track unmatched items for review
                                unmatched_items.append({
                                    'sifra': s,
                                    'barcode': b,
                                    'name': n[:50] if n else ''  # truncate long names
                                })
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
                            'reason': ';'.join(reason),
                            'new_artikuj': 0,  # Will be updated if new artikuj are created
                            'new_artikuj_file': ''
                        })
                        processed += 1
                        log.write(f"OK {fpath} -> {prefix}_*.csv status={status} match={match_rate:.2f}% unmatched={len(unmatched_items)}\n")
                        
                        # Create new artikuj for unmatched items
                        if unmatched_items:
                            new_artikuj = []
                            supplier_name = hdr.get('supplier', 'UNKNOWN_SUPPLIER')
                            
                            for unmatched_item in unmatched_items:
                                # Convert unmatched item format to invoice item format
                                invoice_item = {
                                    'sifra': unmatched_item.get('sifra', ''),
                                    'barcode': unmatched_item.get('barcode', ''),
                                    'name': unmatched_item.get('name', '')
                                }
                                
                                # Only create artikli if it has meaningful data
                                if invoice_item['name'] or invoice_item['barcode']:
                                    new_artikli = create_new_artikli_record(invoice_item, supplier_name, sifra_set)
                                    new_artikuj.append(new_artikli)
                            
                            # Write new artikuj to CSV
                            if new_artikuj:
                                new_artikuj_path = os.path.join(out_day, f'{inv_id}_new_artikuj.csv')
                                write_new_artikuj_csv(new_artikuj, new_artikuj_path)
                                log.write(f"CREATED {len(new_artikuj)} new artikuj -> {new_artikuj_path}\n")
                                
                                # Update summary with new artikuj info
                                summary_rows[-1]['new_artikuj'] = len(new_artikuj)
                                summary_rows[-1]['new_artikuj_file'] = os.path.basename(new_artikuj_path)
                    
                    except Exception as e:
                        failed += 1
                        log.write(f"ERR {fpath} :: {e}\n")

    # write summary
    summary_path = os.path.join(out_day, f'FAKTURA_AI_SUMMARY_{dt.datetime.now().strftime("%Y%m%d")}.csv')
    write_csv(summary_path, summary_rows, ['invoice_no','supplier','items','matched','match_rate_pct','total_calc','total_header','status','reason','new_artikuj','new_artikuj_file'])

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

# file: app/sopharma_to_erp.py
import os
import sys
import argparse
from getpass import getpass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import xml.etree.ElementTree as ET
import psycopg2

# Ensure local app path import
sys.path.insert(0, r'C:\Wellona\wphAI\app')
from mpkalk import mp_kalk, MPCfg

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Defaults can be overridden via env or CLI flags
def env_or(name, default=None):
    v = os.getenv(name)
    return v if v is not None and v != "" else default

DB_DEFAULTS = {
    'dbname': env_or('WPH_DB_NAME', 'wph_ai'),        # connect to wph_ai DB for FDW access
    'user': env_or('WPH_DB_USER', 'postgres'),        # adjust as needed
    'password': env_or('WPH_DB_PASS'),
    'host': env_or('WPH_DB_HOST', '127.0.0.1'),
    'port': int(env_or('WPH_DB_PORT', '5432')),
    'application_name': env_or('WPH_DB_APP', 'wphAI_sopharma_import'),
}

# Schema prefix for FDW tables (eb_fdw.kalkopste, eb_fdw.kalkstavke, etc.)
# Set WPH_USE_FDW=1 to use remote ebdata via FDW, or 0 for local public schema
USE_FDW = bool(int(env_or('WPH_USE_FDW', '1')))
SCHEMA_PREFIX = 'eb_fdw.' if USE_FDW else 'public.'

# MP config defaults (your existing ones)
MP_CONFIG = MPCfg(
    pdv_pct=10.0,     # fallback PDV if not per-item
    marza_pct=18.0,
    trosak_pct=0.0,
    rounding='END_99',
    round_threshold=0.0,
    min_decimals=2
)

# Behavior flags for price preservation
# When enabled, for existing artikli we PRESERVE the previously used retail price (MP sa PDV)
# instead of recalculating it from nabavna + marža. This keeps cash price stable and delegates
# price changes to a dedicated "nivelizacija" workflow (nivopste/nivstavke).
PRESERVE_EXISTING_MP = bool(int(env_or('WPH_PRESERVE_EXISTING_MP', '0')))
# Optional absolute difference threshold (RSD) under which differences are ignored in logs
MP_DIFF_THRESHOLD = float(env_or('WPH_MP_DIFF_THRESHOLD', '0.01') or 0.01)
# CRITICAL: Auto-nivelizacija disabled by default to protect production ebdata
# All audit and nivelizacija logs ALWAYS go to wph_ai database (development), NEVER to ebdata
AUTO_NIVELIZACIJA = bool(int(env_or('WPH_AUTO_NIVELIZACIJA', '0')))
# Auto-create nivelizacija documents when MP changes (default 0 = log only, no DB writes)
AUTO_NIVELIZACIJA = bool(int(env_or('WPH_AUTO_NIVELIZACIJA', '0')))

def create_nivelizacija(cur, price_changes, magacin='101', periodid=4, userid=14, schema_prefix='public.', dry_run=False):
    """
    Create a nivelizacija (MP adjustment) document when purchase prices change.
    
    Args:
        price_changes: list of dicts with keys: artikal, stara_cena, nova_cena, kolicina
        Returns: nivid (nivelizacija document ID) or None
    """
    if not price_changes:
        return None
    
    try:
        # Get next broj for nivelizacija
        cur.execute(f"""
            SELECT MAX(CAST(SPLIT_PART(broj, '/', 1) AS INTEGER))
            FROM {schema_prefix}nivopste
            WHERE broj LIKE %s
        """, [f'%/{datetime.now().strftime("%y")}'])
        result = cur.fetchone()[0]
        next_num = (result + 1) if result else 1
        broj = f"{next_num}/{datetime.now().strftime('%y')}"
        
        if dry_run:
            print(f"[DRY-RUN] Would create nivelizacija: broj={broj}, items={len(price_changes)}")
            return None
        
        # Insert header
        cur.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {schema_prefix}nivopste")
        niv_id = cur.fetchone()[0]
        
        cur.execute(f"""
            INSERT INTO {schema_prefix}nivopste
            (id, broj, magacin, datum, status, napomena, periodid, dokvrsta, pc, pdv, tip, userid, useridk, datumk)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, [
            niv_id, broj, magacin, datetime.now(), 'PROKNJIŽEN', 
            'AUTO: Import kalk - nabavna cena changed', periodid, '25', True, False, '1',
            userid, userid, datetime.now()
        ])
        
        # Insert lines
        for pc in price_changes:
            cur.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {schema_prefix}nivstavke")
            line_id = cur.fetchone()[0]
            
            # Get PDV for this artikal
            cur.execute(f"SELECT vrstaporeza FROM {schema_prefix}artikli WHERE sifra=%s", [pc['artikal']])
            row_pdv = cur.fetchone()
            pdv_pct = 10.0  # default
            if row_pdv and row_pdv[0]:
                if row_pdv[0] in ['OPO', 'PDV10']:
                    pdv_pct = 10.0
                elif row_pdv[0] in ['PDV20']:
                    pdv_pct = 20.0
            
            stara_bez = float(pc['stara_cena']) / (1 + pdv_pct/100.0)
            nova_bez = float(pc['nova_cena']) / (1 + pdv_pct/100.0)
            
            cur.execute(f"""
                INSERT INTO {schema_prefix}nivstavke
                (id, nivid, artikal, jedmere, kolicina, staracena, novacena, stariporez, noviporez, 
                 staracenasaporezom, novacenasaporezom)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                line_id, niv_id, pc['artikal'], 'KOM', pc.get('kolicina', 0),
                stara_bez, nova_bez, pdv_pct, pdv_pct,
                pc['stara_cena'], pc['nova_cena']
            ])
        
        print(f"✓ Nivelizacija created: broj={broj}, nivid={niv_id}, items={len(price_changes)}")
        return niv_id
    except Exception as e:
        print(f"ERROR creating nivelizacija: {e}")
        import traceback
        traceback.print_exc()
        return None

def D(val, default='0'):
    if val is None:
        return Decimal(default)
    s = str(val).strip().replace(',', '.')
    if not s:
        return Decimal(default)
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return Decimal(default)

def get_next_broj(cur, year_suffix=None, schema_prefix=SCHEMA_PREFIX):
    # Let year suffix default to current YY
    if not year_suffix:
        year_suffix = datetime.now().strftime('%y')
    cur.execute(f"""
        SELECT MAX(CAST(SPLIT_PART(broj, '/', 1) AS INTEGER))
        FROM {schema_prefix}kalkopste
        WHERE broj LIKE %s
    """, [f'%/{year_suffix}'])
    result = cur.fetchone()[0]
    next_num = (result + 1) if result else 1
    return f"{next_num}/{year_suffix}"

def parse_sopharma_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # UBL namespace definitions
    ns = {
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
    }
    
    dok = root.find('.//Dokument')

    # Valuta datum - podržava oba Sopharma i UBL (eFaktura.rs) format
    valuta_node = root.find('.//Valutacije/Valutacija/Datum')
    if valuta_node is None:
        # Fallback za UBL format (eFaktura.rs)
        valuta_node = root.find('.//cbc:DueDate', ns)
    valuta_dt = datetime.strptime(valuta_node.text, '%Y-%m-%d') if valuta_node is not None and valuta_node.text else None

    popust_node = root.find('.//Valutacije/Valutacija/Popust')
    vrednost_node = root.find('.//Valutacije/Valutacija/Vrednost')
    cash_discount = D(popust_node.text if popust_node is not None else None, '0')
    payable_amount = D(vrednost_node.text if vrednost_node is not None else None, '0')

    # Broj fakture - podržava Sopharma i UBL format
    broj_node = dok.find('Broj') if dok is not None else None
    if broj_node is None:
        broj_node = root.find('.//cbc:ID', ns)
    broj_faktura = broj_node.text.strip() if broj_node is not None and broj_node.text else ''

    # Datum fakture - podržava Sopharma i UBL format
    datum_node = dok.find('Datum') if dok is not None else None
    if datum_node is None:
        datum_node = root.find('.//cbc:IssueDate', ns)
    datum_text = datum_node.text if datum_node is not None and datum_node.text else None
    datum = datetime.strptime(datum_text, '%Y-%m-%d') if datum_text else datetime.now()

    # Dobavljač - podržava Sopharma i UBL format
    dobavljac_node = root.find('.//Dobavljac/Naziv')
    if dobavljac_node is None:
        dobavljac_node = root.find('.//cac:AccountingSupplierParty//cbc:RegistrationName', ns)
    dobavljac = dobavljac_node.text.strip() if dobavljac_node is not None and dobavljac_node.text else ''

    # Total neto - podržava Sopharma i UBL format  
    total_neto_node = root.find('.//Vrednosti/NetoFakturna')
    if total_neto_node is None:
        total_neto_node = root.find('.//cbc:TaxExclusiveAmount', ns)
    total_neto = D(total_neto_node.text, '0') if total_neto_node is not None and total_neto_node.text else D('0')

    header = {
        'broj_faktura': broj_faktura,
        'datum': datum,
        'dobavljac': dobavljac,
        'total_neto': total_neto,
        'valuta_datum': valuta_dt,
        'cash_discount': cash_discount,
        'payable_amount': payable_amount,
    }

    items = []
    # Try legacy vendor format first
    stavke = root.findall('.//Stavke/Stavka') or root.findall('.//Stavka')
    if stavke:
        print(f'Parsed items: {len(stavke)} (legacy vendor format)')
        for stavka in stavke:
            pdv_txt = (stavka.findtext('PorezProcenat') or '').strip()
            pdv_val = D(pdv_txt, '10.0')

            sifra = (stavka.findtext('Sifra') or '').strip()
            gtin = (stavka.findtext('GTIN') or '').strip() or None
            naziv = (stavka.findtext('Naziv') or '').strip()
            serija = (stavka.findtext('BrojSerije') or '').strip()
            rok = (stavka.findtext('RokUpotrebe') or '').strip()

            if serija in ('0', '0000', 'None', ''):
                serija = None
            if rok in ('0', '0000-00-00', 'None', ''):
                rok_dt = None
            else:
                rok_dt = datetime.strptime(rok, '%Y-%m-%d')

            items.append({
                'sifra': sifra,
                'barcode': gtin,
                'naziv': naziv,
                'kolicina': D(stavka.findtext('Kolicina'), '0'),
                'cena_fakturna': D(stavka.findtext('CenaFakturna'), '0'),
                'rabat_pct': D(stavka.findtext('RabatProcenat'), '0'),
                'serija': serija,
                'rok_dt': rok_dt,
                'pdv_pct': float(pdv_val),
            })
    else:
        # Fallback to UBL eFaktura format
        inv_lines = root.findall('.//cac:InvoiceLine', ns)
        print(f'Parsed items: {len(inv_lines)} (UBL format)')
        for il in inv_lines:
            qty_txt = il.findtext('./cbc:InvoicedQuantity', namespaces=ns) or '0'
            price_txt = il.findtext('./cac:Price/cbc:PriceAmount', namespaces=ns) or '0'
            disc_pct_txt = il.findtext('./cac:AllowanceCharge/cbc:MultiplierFactorNumeric', namespaces=ns) or '0'
            pdv_txt = (
                il.findtext('./cac:Item/cac:ClassifiedTaxCategory/cbc:Percent', namespaces=ns)
                or il.findtext('./cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:Percent', namespaces=ns)
                or '10'
            )
            supplier_id = il.findtext('./cac:Item/cac:SellersItemIdentification/cbc:ID', namespaces=ns) or ''
            gtin = il.findtext('./cac:Item/cac:StandardItemIdentification/cbc:ID', namespaces=ns) or None
            name = il.findtext('./cac:Item/cbc:Name', namespaces=ns) or ''

            items.append({
                'sifra': supplier_id.strip(),
                'barcode': (gtin or '').strip() or None,
                'naziv': name.strip(),
                'kolicina': D(qty_txt, '0'),
                'cena_fakturna': D(price_txt, '0'),
                'rabat_pct': D(disc_pct_txt, '0'),
                'serija': None,
                'rok_dt': None,
                'pdv_pct': float(D(pdv_txt, '10.0')),
            })

    return header, items

def _build_napomena(header):
    # Empty napomena to avoid ERP filter exclusion (originally had "AUTO:" prefix)
    parts = []
    if header.get('cash_discount') is not None and header['cash_discount'] > 0:
        parts.append(f"CASH_DISC={header['cash_discount']:.2f}")
    if header.get('payable_amount') is not None and header['payable_amount'] > 0:
        parts.append(f"PAYABLE={header['payable_amount']:.2f}")
    if header.get('valuta_datum') is not None:
        parts.append(f"PAYABLE_UNTIL={header['valuta_datum'].strftime('%Y-%m-%d')}")
    return ' | '.join(parts) if parts else None

def _find_existing_header(cur, vezabroj, dokvrsta='20', magacin='101', schema_prefix=SCHEMA_PREFIX):
    cur.execute(f"""
        SELECT id, broj
        FROM {schema_prefix}kalkopste
        WHERE dokvrsta=%s AND vezabroj=%s AND magacin=%s
        ORDER BY id DESC
        LIMIT 1
    """, [dokvrsta, vezabroj, magacin])
    return cur.fetchone()

def _kalkstavke_count(cur, kalkid, schema_prefix=SCHEMA_PREFIX):
    cur.execute(f'SELECT COUNT(*) FROM {schema_prefix}kalkstavke WHERE kalkid=%s', [kalkid])
    return cur.fetchone()[0]

def _kalkkasa_exists(cur, dokbroj, schema_prefix=SCHEMA_PREFIX):
    cur.execute(f"SELECT 1 FROM {schema_prefix}kalkkasa WHERE dokvrsta='20' AND dokbroj=%s LIMIT 1", [dokbroj])
    return cur.fetchone() is not None

def lookup_komintent(cur, dobavljac_name, schema_prefix=SCHEMA_PREFIX):
    """Resolve komintent (supplier code) from a raw supplier name.

    Matching strategy:
    1. Normalize (remove DOO/D.O.O., punctuation, collapse spaces)
    2. Alias map (VEGA→7, SOPHARMA→15, PHOENIX→6)
    3. Exact normalized match against stripped name in table
    4. LIKE %core%
    5. Token-wise LIKE (tokens length>=3)
    6. Alias contained anywhere in cleaned string
    Fallback → '1'.
    """
    if not dobavljac_name or dobavljac_name.strip() == '':
        return '1'

    original = dobavljac_name.strip()
    clean_name = original.upper()
    for token in ['D.O.O.', 'D.O.O', 'DOO', 'D O O']:
        clean_name = clean_name.replace(token, '')
    clean_name = clean_name.replace('.', ' ').replace(',', ' ')
    while '  ' in clean_name:
        clean_name = clean_name.replace('  ', ' ')
    clean_name = clean_name.strip()

    parts = clean_name.split()
    clean_core = parts[0] if parts else clean_name

    alias_map = {'VEGA': '7', 'SOPHARMA': '15', 'PHOENIX': '6'}
    if clean_core in alias_map:
        return alias_map[clean_core]

    # Exact normalized (after removing legal suffixes inside SQL as well)
    cur.execute(f"""
        SELECT sifra FROM {schema_prefix}komintenti
        WHERE TRIM(REPLACE(REPLACE(REPLACE(UPPER(naziv), 'D.O.O.', ''), 'DOO', ''), '.', '')) = %s
        LIMIT 1
    """, [clean_name])
    row = cur.fetchone()
    if row:
        return row[0]

    # LIKE %core%
    cur.execute(f"SELECT sifra FROM {schema_prefix}komintenti WHERE UPPER(naziv) LIKE UPPER(%s) LIMIT 1", [f'%{clean_core}%'])
    row = cur.fetchone()
    if row:
        return row[0]

    # Token-wise LIKE
    for token in parts:
        if len(token) < 3:
            continue
        cur.execute(f"SELECT sifra FROM {schema_prefix}komintenti WHERE UPPER(naziv) LIKE UPPER(%s) LIMIT 1", [f'%{token}%'])
        row = cur.fetchone()
        if row:
            return row[0]

    # Alias contained anywhere
    for alias, sifra in alias_map.items():
        if alias in clean_name:
            return sifra

    print(f"Warning: No komintent found for '{dobavljac_name}', using fallback='1'")
    return '1'

def lookup_or_create_artikal(cur, item, schema_prefix='public.', auto_register=True):
    """Resolve or create an artikal by barcode/name.

    Returns (sifra, naziv, ruc, action): action in
      FOUND          – existing match (primary or alternative barcode)
      BARCODE_ADDED  – matched by name; barcode appended in artikliean
      SIFRA_FALLBACK – matched by supplier-provided sifra
      CREATED        – new artikal inserted
      NOT_FOUND      – no match and auto_register disabled/failed
    
    ruc is the existing RUC% (marža) from last purchase, or None for new artikli.
    """
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
        
        # 2. Alternative barcode in artikliean
        try:
            cur.execute(f"""
                SELECT ae.sifra, a.naziv
                FROM {schema_prefix}artikliean ae
                JOIN {schema_prefix}artikli a ON ae.sifra=a.sifra
                WHERE ae.ean=%s LIMIT 1
            """, [barcode])
            row = cur.fetchone()
            if row:
                ruc = get_last_ruc(row[0])
                return (row[0], row[1], ruc, 'FOUND')
        except:
            pass  # artikliean might not exist
        
        # 3. Fuzzy name match
        norm_name = ' '.join(naziv.upper().split())
        cur.execute(f"""
            SELECT sifra, naziv FROM {schema_prefix}artikli
            WHERE UPPER(REGEXP_REPLACE(naziv,'[^A-Z0-9 ]','','g')) LIKE %s
            LIMIT 1
        """, [f"%{norm_name[:20]}%"])
        row = cur.fetchone()
        if row:
            ruc = get_last_ruc(row[0])
            return (row[0], row[1], ruc, 'BARCODE_ADDED')

    # 4. Fallback by supplier sifra
    if supplier_sifra:
        cur.execute(f"SELECT sifra, naziv FROM {schema_prefix}artikli WHERE sifra=%s LIMIT 1", [supplier_sifra])
        row = cur.fetchone()
        if row:
            ruc = get_last_ruc(row[0])
            return (row[0], row[1], ruc, 'SIFRA_FALLBACK')

    # 5. Auto-register if allowed
    if auto_register and (barcode or supplier_sifra):
        cur.execute(f"SELECT COALESCE(MAX(sifra::bigint),2300000000)+1 FROM {schema_prefix}artikli WHERE sifra ~ '^\\d+$'")
        new_sifra = str(cur.fetchone()[0])
        try:
            cur.execute(f"""
                INSERT INTO {schema_prefix}artikli
                  (sifra,naziv,jedmere,vrstaartikla,vrstaporeza,barkod,napomena)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, [
                new_sifra,
                naziv,
                'KOM',
                'AR',
                'OPO',
                barcode if barcode else None,
                f"AUTO-REG from supplier sifra={supplier_sifra}" if supplier_sifra else "AUTO-REG from XML"
            ])
            print(f"✓ AUTO-REGISTERED: sifra={new_sifra}, naziv={naziv}, barkod={barcode or 'N/A'}")
            return (new_sifra, naziv, None, 'CREATED')
        except Exception as e:
            print(f"ERROR: Failed to auto-register artikal: {e}")
            return (None, None, None, 'NOT_FOUND')

    print(f"Warning: No artikal found for barcode='{barcode}' or sifra='{supplier_sifra}'")
    return (None, None, None, 'NOT_FOUND')
    
    # 2. Fallback: Match by supplier sifra (some suppliers use their own codes)
    if supplier_sifra:
        cur.execute(f"""
            SELECT sifra, naziv FROM {schema_prefix}artikli 
            WHERE sifra = %s 
            LIMIT 1
        """, [supplier_sifra])
        row = cur.fetchone()
        if row:
            # Update barcode if missing in ERP
            if barcode and (not row[1] or row[1] == ''):
                try:
                    cur.execute(f"""
                        UPDATE {schema_prefix}artikli 
                        SET barkod = %s 
                        WHERE sifra = %s
                    """, [barcode, row[0]])
                    print(f"INFO: Updated barkod={barcode} for existing artikal sifra={row[0]}")
                except Exception as e:
                    print(f"Warning: Failed to update barcode: {e}")
            return (row[0], row[1], 'SIFRA_FALLBACK')
    
    # 3. Auto-register new artikal if enabled
    if auto_register and (barcode or supplier_sifra):
        # Generate new sifra (max + 1)
        cur.execute(f"""
            SELECT COALESCE(MAX(sifra::bigint), 2300000000) + 1 
            FROM {schema_prefix}artikli 
            WHERE sifra ~ '^\\d+$'
        """)
        new_sifra = str(cur.fetchone()[0])
        
        # Insert new artikal (minimal required fields)
        try:
            cur.execute(f"""
                INSERT INTO {schema_prefix}artikli 
                (sifra, naziv, jedmere, vrstaartikla, vrstaporeza, barkod, napomena)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [
                new_sifra,
                naziv,
                'KOM',  # Default unit
                'AR',   # Default type (regular article)
                'OPO',  # Default tax type
                barcode if barcode else None,
                f"AUTO-REG from supplier sifra={supplier_sifra}" if supplier_sifra else "AUTO-REG from XML"
            ])
            print(f"✓ AUTO-REGISTERED: sifra={new_sifra}, naziv={naziv}, barkod={barcode or 'N/A'}")
            return (new_sifra, naziv, 'CREATED')
        except Exception as e:
            print(f"ERROR: Failed to auto-register artikal: {e}")
            return (None, None, 'NOT_FOUND')
    
    # 4. Not found and auto-register disabled
    print(f"Warning: No artikal found for barcode='{barcode}' or sifra='{supplier_sifra}'")
    return (None, None, 'NOT_FOUND')

def insert_kalkulacija(conn, header, items, mp_cfg, *, dokvrsta='20', magacin='101', komintent='1', periodid=4, userid=14, dry_run=False, allow_remote_write=False, schema_override=None):
    """
    Insert kalkulacija header and items.
    
    Args:
        schema_override: If provided, overrides SCHEMA_PREFIX (use 'public.' for dry-run, 'eb_fdw.' for production)
    """
    cur = conn.cursor()
    # Use schema override if provided (for dry-run), else global SCHEMA_PREFIX
    active_schema = schema_override if schema_override is not None else SCHEMA_PREFIX
    
    try:
        # Safety check: verify connection and schema
        cur.execute("SELECT current_database()")
        current_db = cur.fetchone()[0]
        
        # CRITICAL: Block FDW writes - FDW cannot handle INSERT with auto-generated IDs
        if active_schema == 'eb_fdw.' and not dry_run:
            raise RuntimeError(
                "❌ BLOCKED: Cannot write through FDW (eb_fdw schema)!\n"
                "FDW does not support auto-generated IDs for kalkkasa/kalkopste.\n"
                "Connect DIRECTLY to ebdata:\n"
                "  $env:WPH_DB_HOST='pedjapostgres'\n"
                "  $env:WPH_DB_NAME='ebdata'\n"
                "  $env:WPH_USE_FDW='0'\n"
                "  $env:WPH_WRITE_REMOTE='1'"
            )

        # Auto-detect schema based on connected database
        if current_db == 'ebdata':
            active_schema = 'public.'
            print(f"✅ Connected directly to ebdata → using schema 'public.'")


        # Auto-detect schema based on connected database
        if current_db == "ebdata":
            active_schema = "public."
            print(f"NOTE: Connected directly to ebdata → using schema 'public.'")
        if current_db == 'ebdata' and not allow_remote_write:
            raise RuntimeError(f"Attempt to write directly to remote ebdata without allow_remote_write=True. Use wph_ai.eb_fdw instead, or set WPH_WRITE_REMOTE=1.")
        
        # For dry-run with wph_ai, keep eb_fdw for reads (no actual writes happen)
        if dry_run and current_db == 'wph_ai' and active_schema == 'eb_fdw.':
            print("NOTE: dry-run with eb_fdw schema - reads allowed, no writes will be executed")
        
        # Block FDW writes unless explicitly allowed
        if (active_schema == 'eb_fdw.') and (not dry_run) and (not allow_remote_write):
            raise RuntimeError("FDW remote write blocked for safety. Set WPH_WRITE_REMOTE=1 to enable.")
        
        # Dynamic komintent lookup by supplier name
        resolved_komintent = lookup_komintent(cur, header.get('dobavljac', ''), active_schema)
        print(f"Komintent resolved: dobavljac='{header.get('dobavljac','')}' → sifra='{resolved_komintent}'")
        
        # 1) Header: reuse if exists
        existing = _find_existing_header(cur, header['broj_faktura'], dokvrsta=dokvrsta, magacin=magacin, schema_prefix=active_schema)
        if existing:
            kalk_id, broj_rendor = existing
            lines = _kalkstavke_count(cur, kalk_id, active_schema)
            print(f'Existing header: broj={broj_rendor}, kalkid={kalk_id}, lines={lines}')
        else:
            broj_rendor = get_next_broj(cur, schema_prefix=active_schema)
            if dry_run:
                print(f"[DRY-RUN] Would INSERT header into {active_schema}kalkopste: broj={broj_rendor}, vezabroj={header['broj_faktura']}, komintent={resolved_komintent}")
                kalk_id = None
                lines = 0
            else:
                # FDW remote write requires explicit id; fetch next from max+1
                cur.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {active_schema}kalkopste")
                next_kalkopste_id = cur.fetchone()[0]
                cur.execute(
                    f"""
                    INSERT INTO {active_schema}kalkopste
                    (id, broj, vezabroj, vezadatum, vezavaluta, datum, komintent, magacin, dokvrsta, status, periodid, userid, useridk, datumk, napomena)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        next_kalkopste_id, broj_rendor, header['broj_faktura'], header['datum'], header.get('valuta_datum'),
                        datetime.now(), resolved_komintent, magacin, dokvrsta, 'PROKNJIŽEN', periodid, userid, userid, datetime.now(),
                        _build_napomena(header),
                    ],
                )
                # Fetch kalk_id back by searching inserted header
                rec = _find_existing_header(cur, header['broj_faktura'], dokvrsta=dokvrsta, magacin=magacin, schema_prefix=active_schema)
                kalk_id = rec[0] if rec else None
                lines = 0
                print(f'Header OK: broj={broj_rendor}, vezabroj={header["broj_faktura"]}, kalkid={kalk_id}')

        # 2) Payment terms (kalkkasa): ensure due-date is recorded so the invoice shows in payment list
        #    We insert (or update) kalkkasa for this document whenever we have a payable amount or a due date.
        payable_amount = header.get('payable_amount')
        valuta_datum = header.get('valuta_datum')
        cash_disc = header.get('cash_discount')
        iznos_for_payment = None
        if payable_amount is not None and payable_amount > 0:
            iznos_for_payment = payable_amount
        elif cash_disc is not None and cash_disc > 0:
            # fallback – older XMLs provided only a cash discount; still write something so it appears in schedules
            iznos_for_payment = cash_disc
        else:
            iznos_for_payment = D('0') if 'D' in globals() else 0

        if valuta_datum is not None or (iznos_for_payment is not None and iznos_for_payment > 0):
            if not _kalkkasa_exists(cur, broj_rendor, active_schema):
                if dry_run:
                    print(f"[DRY-RUN] Would INSERT kalkkasa into {active_schema}kalkkasa: iznos={float(iznos_for_payment):.2f}, datumuplate={valuta_datum}, dokbroj={broj_rendor}")
                else:
                    # FDW remote write requires explicit id; fetch next from max+1 (sequence might not be accessible)
                    cur.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {active_schema}kalkkasa")
                    next_id = cur.fetchone()[0]
                    cur.execute(
                        f"""
                        INSERT INTO {active_schema}kalkkasa
                        (id, datumkase, iznos, datumuplate, dokvrsta, dokbroj, magacin, vezadatum, vezabroj, periodid, dokdatum)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            next_id, header['datum'], iznos_for_payment, valuta_datum,
                            dokvrsta, broj_rendor, magacin, header['datum'], header['broj_faktura'], periodid, header['datum'],
                        ],
                    )
                    print(f'kalkkasa OK (id={next_id}): iznos={float(iznos_for_payment):.2f}, datumuplate={valuta_datum}')
            else:
                # Optional gentle update if present but missing date or amount
                if dry_run:
                    print('[DRY-RUN] kalkkasa already present (skip/update if missing)')
                else:
                    cur.execute(
                        f"""
                        UPDATE {active_schema}kalkkasa
                        SET datumuplate = COALESCE(%s, datumuplate),
                            iznos = CASE WHEN COALESCE(iznos,0)=0 AND COALESCE(%s,0)>0 THEN %s ELSE iznos END
                        WHERE dokvrsta=%s AND dokbroj=%s AND magacin=%s
                        """,
                        [valuta_datum, iznos_for_payment, iznos_for_payment, dokvrsta, broj_rendor, magacin],
                    )
                    print('kalkkasa present → updated if missing date/amount')

        # 3) Lines: insert only if none yet
        print(f'Items to insert: {len(items)} (existing_lines={lines})')
        if lines == 0 and items:
            stats = {'FOUND': 0, 'CREATED': 0, 'BARCODE_ADDED': 0, 'SIFRA_FALLBACK': 0, 'SKIPPED': 0}
            preserve_flag = os.getenv('WPH_PRESERVE_EXISTING_MP', '0') == '1'
            preserve_source = os.getenv('WPH_MP_PRESERVE_SOURCE', 'LAST_KALK')  # LAST_KALK | ARTIKLI
            audit_inited = False
            price_changes = []  # Track items where MP changed due to nabavna change
            for item in items:
                # Lookup or auto-create artikal (returns: sifra, naziv, ruc_placeholder, action)
                erp_sifra, erp_naziv, _, action = lookup_or_create_artikal(
                    cur, item, active_schema, auto_register=(not dry_run)
                )

                if not erp_sifra:
                    print(f"Warning: Artikal not found/created for item={item.get('naziv')}, barcode={item.get('barcode')}, skipping")
                    stats['SKIPPED'] += 1
                    continue

                stats[action] += 1

                item_pdv = item.get('pdv_pct', mp_cfg.pdv_pct)
                mp_result = mp_kalk(
                    float(item['cena_fakturna']), float(item['rabat_pct']),
                    MPCfg(pdv_pct=item_pdv, marza_pct=mp_cfg.marza_pct, trosak_pct=mp_cfg.trosak_pct,
                          rounding=mp_cfg.rounding, round_threshold=mp_cfg.round_threshold, min_decimals=mp_cfg.min_decimals),
                )

                # For existing articles, try to fetch RUC, last MP, and last nabavna cena from last kalkulacija
                existing_ruc = None
                last_mp = None
                last_nabavna = None
                if action in ['FOUND', 'BARCODE_ADDED', 'SIFRA_FALLBACK']:
                    cur.execute(f"""
                        SELECT rucstopa, cenasapdv, nabavnacena FROM {active_schema}kalkstavke
                        WHERE artikal=%s AND rucstopa IS NOT NULL AND rucstopa > 0
                        ORDER BY id DESC LIMIT 1
                    """, [erp_sifra])
                    ruc_row = cur.fetchone()
                    if ruc_row:
                        existing_ruc = ruc_row[0]
                        last_mp = ruc_row[1]
                        last_nabavna = ruc_row[2]
                    if preserve_flag and preserve_source == 'ARTIKLI':
                        # Fallback to artikli.cena if user wants master price as source
                        cur.execute(f"SELECT cena FROM {active_schema}artikli WHERE sifra=%s LIMIT 1", [erp_sifra])
                        row_c = cur.fetchone()
                        if row_c and row_c[0]:
                            last_mp = row_c[0]

                # Decide MP and RUC to use
                final_mp = mp_result['mp_rounded']
                ruc_to_use = existing_ruc if existing_ruc is not None else mp_result['marza_na_mp_pct']
                price_action = 'COMPUTED'  # default: new calculation

                # SMART PRESERVATION: Only preserve MP if nabavnacena has NOT changed
                if preserve_flag and action in ['FOUND', 'BARCODE_ADDED', 'SIFRA_FALLBACK'] and last_mp is not None:
                    # Check if nabavna cena changed (allow small tolerance for float comparison)
                    nabavna_tolerance = 0.01
                    nabavna_changed = (last_nabavna is None or 
                                      abs(float(item['cena_fakturna']) - float(last_nabavna)) > nabavna_tolerance)
                    
                    if nabavna_changed:
                        # Nabavna cena changed → RECALCULATE MP with new margin
                        price_action = 'RECALC_NABAVNA_CHANGED'
                        final_mp = mp_result['mp_rounded']
                        ruc_to_use = mp_result['marza_na_mp_pct']
                        # Track for nivelizacija document
                        price_changes.append({
                            'artikal': erp_sifra,
                            'stara_cena': float(last_mp) if last_mp else 0,
                            'nova_cena': float(final_mp),
                            'kolicina': float(item.get('kolicina', 0))
                        })
                        if not dry_run:
                            print(f"  ⚠️  {erp_sifra} ({erp_naziv[:25]}): Nabavna changed {last_nabavna:.2f}→{item['cena_fakturna']:.2f} → MP recalculated {last_mp:.2f}→{final_mp:.2f}")
                    else:
                        # Nabavna cena UNCHANGED → PRESERVE old MP, adjust RUC to fit
                        price_action = 'PRESERVED'
                        try:
                            net_purchase = float(item['cena_fakturna']) * (1 - float(item['rabat_pct'])/100.0)
                            mp_without_pdv = float(last_mp) / (1 + item_pdv/100.0)
                            ruc_adjusted = ((mp_without_pdv - net_purchase) / net_purchase * 100.0) if net_purchase > 0 else ruc_to_use
                            final_mp = float(last_mp)
                            ruc_to_use = ruc_adjusted
                            if not dry_run:
                                print(f"  ✓  {erp_sifra} ({erp_naziv[:25]}): Nabavna stable → MP preserved {final_mp:.2f}, RUC adjusted {ruc_to_use:.2f}%")
                        except Exception as _e:
                            print(f"  ⚠️  {erp_sifra}: RUC recompute failed: {_e}; falling back to computed values")
                            price_action = 'FALLBACK'

                    # Audit table init (ALWAYS in wph_ai localhost, NEVER on remote ebdata server)
                    if not audit_inited and not dry_run:
                        # Force audit connection to LOCAL wph_ai database
                        audit_conn = psycopg2.connect(
                            dbname='wph_ai',
                            user='postgres',  # Local user
                            password=os.getenv('WPH_LOCAL_PASS', ''),  # Local password
                            host='127.0.0.1',  # ALWAYS localhost
                            port=5432
                        )
                        audit_cur = audit_conn.cursor()
                        audit_cur.execute("""
                            CREATE TABLE IF NOT EXISTS public.wph_audit_price_lock (
                                id bigserial PRIMARY KEY,
                                ts timestamptz DEFAULT now(),
                                kalkid bigint,
                                artikal varchar(15),
                                source varchar(20),
                                computed_mp numeric(19,4),
                                preserved_mp numeric(19,4),
                                last_nabavna numeric(19,4),
                                new_nabavna numeric(19,4),
                                rabat_pct numeric(10,4),
                                pdv_pct numeric(10,4),
                                ruc_used numeric(10,4),
                                action_tag varchar(30)
                            )
                        """)
                        audit_conn.commit()
                        audit_cur.close()
                        audit_conn.close()
                        audit_inited = True
                    if not dry_run and price_action in ['PRESERVED', 'RECALC_NABAVNA_CHANGED']:
                        # Write audit to LOCAL wph_ai (NEVER to remote ebdata server)
                        audit_conn = psycopg2.connect(
                            dbname='wph_ai',
                            user='postgres',
                            password=os.getenv('WPH_LOCAL_PASS', ''),
                            host='127.0.0.1',  # ALWAYS localhost
                            port=5432
                        )
                        audit_cur = audit_conn.cursor()
                        audit_cur.execute("""
                            INSERT INTO public.wph_audit_price_lock
                            (kalkid, artikal, source, computed_mp, preserved_mp, last_nabavna, new_nabavna, rabat_pct, pdv_pct, ruc_used, action_tag)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, [
                            kalk_id, erp_sifra, preserve_source, mp_result['mp_rounded'], final_mp,
                            last_nabavna, item['cena_fakturna'], item['rabat_pct'], item_pdv, ruc_to_use, price_action
                        ])
                        audit_conn.commit()
                        audit_cur.close()
                        audit_conn.close()

                if dry_run:
                    preserve_marker = ''
                    if preserve_flag and price_action == 'PRESERVED':
                        preserve_marker = ' ✓PRESERVED'
                    elif preserve_flag and price_action == 'RECALC_NABAVNA_CHANGED':
                        preserve_marker = ' ⚠RECALC(nabavna↑)'
                    print(f"[DRY-RUN] Would INSERT line into {active_schema}kalkstavke: sifra={erp_sifra} ({action}), barcode={item.get('barcode')}, naziv={erp_naziv}, qty={item['kolicina']}, pdv={item_pdv}, mp={final_mp:.2f}, ruc={ruc_to_use:.2f}%{preserve_marker}")
                else:
                    # FDW remote write requires explicit id for kalkstavke too
                    cur.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {active_schema}kalkstavke")
                    next_stavka_id = cur.fetchone()[0]
                    cur.execute(
                        f"""
                        INSERT INTO {active_schema}kalkstavke
                        (id, kalkid, artikal, jedmere, kolicina, nabavnacena, rabatstopa, trosak, rucstopa, cena, pdvstopa, cenasapdv, serija, roktrajanja)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            next_stavka_id, kalk_id, erp_sifra, 'KOM', item['kolicina'], item['cena_fakturna'],
                            item['rabat_pct'], 0.0, ruc_to_use, 0.0, item_pdv,
                            final_mp, item['serija'], item['rok_dt'],
                        ],
                    )

            print(f"Artikal resolution stats: {stats}")
            if not dry_run:
                print(f'Inserted {len(items)} lines')
                # Log price changes (NEVER creates nivelizacija in production ebdata)
                if price_changes and preserve_flag:
                    print(f'\n📊 PRICE CHANGES DETECTED: {len(price_changes)} items')
                    for pc in price_changes:
                        delta = pc['nova_cena'] - pc['stara_cena']
                        delta_pct = (delta / pc['stara_cena'] * 100) if pc['stara_cena'] > 0 else 0
                        print(f"  • {pc['artikal']}: {pc['stara_cena']:.2f} → {pc['nova_cena']:.2f} (Δ {delta:+.2f} / {delta_pct:+.1f}%)")
                    
                    auto_niv = os.getenv('WPH_AUTO_NIVELIZACIJA', '0') == '1'
                    current_db = cur.connection.info.dbname if hasattr(cur.connection, 'info') else 'unknown'
                    
                    if current_db == 'ebdata':
                        print('\n❌ PRODUCTION DATABASE DETECTED (ebdata)')
                        print('   Nivelizacija creation BLOCKED for safety.')
                        print('   → Price changes logged to wph_ai audit table only.')
                        print('   → Manual nivelizacija must be created in ERP UI.')
                    elif auto_niv:
                        print(f'\n⚠️  WPH_AUTO_NIVELIZACIJA=1 → Creating nivelizacija in {current_db}...')
                        niv_id = create_nivelizacija(
                            cur, price_changes, magacin=magacin, periodid=periodid, userid=userid,
                            schema_prefix=active_schema, dry_run=False
                        )
                        if niv_id:
                            print(f'✓ Nivelizacija document created: nivid={niv_id}, price changes={len(price_changes)}')
                    else:
                        print(f'\n✅ Safe mode: Price changes logged only (no auto-nivelizacija).')
                        print(f'   → Set WPH_AUTO_NIVELIZACIJA=1 to enable (NOT recommended for ebdata)')
            else:
                print(f'[DRY-RUN] Would insert {len(items)} lines')
                if price_changes and preserve_flag:
                    print(f'[DRY-RUN] Would log {len(price_changes)} price changes (nivelizacija creation depends on WPH_AUTO_NIVELIZACIJA flag)')
        elif lines > 0:
            print('Lines already exist (skip)')
        else:
            print('No items to insert')

        if dry_run:
            conn.rollback()
            print('\n[D R Y - R U N] No DB writes executed.')
        else:
            conn.commit()
            print('\nCommit OK.')

        return kalk_id
    except Exception as e:
        conn.rollback()
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        return None
    finally:
        cur.close()

def main():
    ap = argparse.ArgumentParser(description='Import Sopharma XML into ERP (kalkopste/kalkstavke/kalkkasa)')
    ap.add_argument('xml', help='Path to supplier XML (Sopharma)')
    ap.add_argument('--dry-run', action='store_true', help='Parse and validate, but do not write')
    ap.add_argument('--db-name', default=DB_DEFAULTS['dbname'])
    ap.add_argument('--db-user', default=DB_DEFAULTS['user'])
    ap.add_argument('--db-pass', default=DB_DEFAULTS['password'])
    ap.add_argument('--db-host', default=DB_DEFAULTS['host'])
    ap.add_argument('--db-port', default=str(DB_DEFAULTS['port']))
    ap.add_argument('--dokvrsta', default='20')
    ap.add_argument('--magacin', default='101')
    ap.add_argument('--komintent', default='1')
    ap.add_argument('--periodid', type=int, default=4)
    ap.add_argument('--userid', type=int, default=14)
    args = ap.parse_args()

    header, items = parse_sopharma_xml(args.xml)

    db_cfg = dict(
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_pass or DB_DEFAULTS['password'],
        host=args.db_host,
        port=int(args.db_port),
        application_name=DB_DEFAULTS['application_name'],
    )
    if not db_cfg['password']:
        db_cfg['password'] = getpass(f"DB password for {db_cfg['user']}@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['dbname']}: ")

    conn = psycopg2.connect(**db_cfg)
    
    # Check environment flag for remote write safety
    allow_remote = os.getenv('WPH_WRITE_REMOTE', '0') == '1'
    if not allow_remote:
        print("Note: WPH_WRITE_REMOTE=0 (default). Remote DB writes blocked for safety. Set WPH_WRITE_REMOTE=1 to enable.")
    
    kalk_id = insert_kalkulacija(
        conn, header, items, MP_CONFIG,
        dokvrsta=args.dokvrsta, magacin=args.magacin, komintent=args.komintent,
        periodid=args.periodid, userid=args.userid, dry_run=args.dry_run, allow_remote_write=allow_remote
    )
    conn.close()

    if kalk_id:
        # Determine schema for readback
        readback_schema = 'eb_fdw.' if (db_cfg.get('dbname') == 'wph_ai' and USE_FDW) else 'public.'
        
        # Recap readback (safe also in dry-run: it reads by kalkid if committed; otherwise shows the target broj/vezabroj)
        db2 = psycopg2.connect(**db_cfg)
        cur = db2.cursor()
        try:
            cur.execute(f"SELECT broj, vezabroj, to_char(vezadatum,'YYYY-MM-DD'), to_char(vezavaluta,'YYYY-MM-DD'), napomena FROM {readback_schema}kalkopste WHERE id=%s", [kalk_id])
            row = cur.fetchone()
            if row:
                print('Stored kalkopste:', row)
            cur.execute(f'SELECT COUNT(*) FROM {readback_schema}kalkstavke WHERE kalkid=%s', [kalk_id])
            print('Stored kalkstavke count:', cur.fetchone()[0])
            cur.execute(f"SELECT datumkase, iznos, datumuplate FROM {readback_schema}kalkkasa WHERE dokbroj=(SELECT broj FROM {readback_schema}kalkopste WHERE id=%s)", [kalk_id])
            kasa_row = cur.fetchone()
            if kasa_row:
                print('Stored kalkkasa:', kasa_row)
        finally:
            cur.close()
            db2.close()

if __name__ == '__main__':
    main()
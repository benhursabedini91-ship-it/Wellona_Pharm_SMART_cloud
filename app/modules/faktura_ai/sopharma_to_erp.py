# file: app/modules/faktura_ai/sopharma_to_erp.py
# Faktura AI Import System - adapted for main app
import os
import sys
import argparse
from getpass import getpass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import xml.etree.ElementTree as ET
import psycopg2

# Ensure local app path import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app'))

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
    'application_name': env_or('WPH_DB_APP', 'wphAI_faktura_api'),
}

# Schema prefix for FDW tables (eb_fdw.kalkopste, eb_fdw.kalkstavke, etc.)
# Set WPH_USE_FDW=1 to use remote ebdata via FDW, or 0 for local public schema
USE_FDW = bool(int(env_or('WPH_USE_FDW', '1')))
SCHEMA_PREFIX = 'eb_fdw.' if USE_FDW else 'public.'

# MP config defaults (your existing ones)
MP_CONFIG = {
    'pdv_pct': 10.0,     # fallback PDV if not per-item
    'marza_pct': 18.0,
    'trosak_pct': 0.0,
    'rounding': 'END_99',
    'round_threshold': 0.0,
    'min_decimals': 2
}

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
            gtin = il.findtext('./cac:StandardItemIdentification/cbc:ID', namespaces=ns) or None
            name = il.findtext('./cac:Item/cbc:Name', namespaces=ns) or ''

            items.append({
                'sifra': supplier_id.strip(),
                'barcode': gtin.strip() if gtin else None,
                'naziv': name.strip(),
                'kolicina': D(qty_txt, '0'),
                'cena_fakturna': D(price_txt, '0'),
                'rabat_pct': D(disc_pct_txt, '0'),
                'serija': None,
                'rok_dt': None,
                'pdv_pct': float(D(pdv_txt, '10.0')),
            })

    return header, items

def insert_kalkulacija(conn, header, items, mp_cfg, *, dokvrsta='20', magacin='101', komintent='1', periodid=4, userid=14, dry_run=False, allow_remote_write=False, schema_override=None):
    """
    Insert kalkulacija header and items.
    
    Args:
        schema_override: If provided, overrides SCHEMA_PREFIX (use 'public.' for dry-run, 'eb_fdw.' for production)
    """
    # In dry-run mode we don't intend to persist anything; autocommit avoids transaction-aborted cascades on harmless failures
    try:
        if dry_run:
            conn.autocommit = True
    except Exception:
        pass
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
        elif current_db == 'wph_ai' and USE_FDW:
            # Already set to eb_fdw. by SCHEMA_PREFIX
            pass
        if current_db == 'ebdata' and not allow_remote_write:
            raise RuntimeError(f"Attempt to write directly to remote ebdata without allow_remote_write=True. Use wph_ai.eb_fdw instead, or set WPH_WRITE_REMOTE=1.")
        
        # For dry-run with wph_ai, keep eb_fdw for reads (no actual writes happen)
        if dry_run and current_db == 'wph_ai' and active_schema == 'eb_fdw.':
            pass
        
        # Block FDW writes unless explicitly allowed
        if (active_schema == 'eb_fdw.') and (not dry_run) and (not allow_remote_write):
            raise RuntimeError("FDW remote write blocked for safety. Set WPH_WRITE_REMOTE=1 to enable.")
        
        # Dynamic komintent lookup by supplier name
        resolved_komintent = lookup_komintent(cur, header.get('dobavljac', ''), active_schema)
        
        # 1) Header: reuse if exists
        existing = _find_existing_header(cur, header['broj_faktura'], dokvrsta=dokvrsta, magacin=magacin, schema_prefix=active_schema)
        if existing:
            kalk_id, broj_rendor = existing
        else:
            broj_rendor = get_next_broj(cur, schema_prefix=active_schema)
            if dry_run:
                kalk_id = None
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
                    pass
                else:
                    # FDW remote write requires explicit id for kalkkasa too
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

        # 3) Lines: insert only if none yet
        if items:
            stats = {'FOUND': 0, 'CREATED': 0, 'BARCODE_ADDED': 0, 'SIFRA_FALLBACK': 0, 'SKIPPED': 0}
            for item in items:
                # Lookup or auto-create artikal (returns: sifra, naziv, ruc_placeholder, action)
                erp_sifra, erp_naziv, _, action = lookup_or_create_artikal(
                    cur, item, active_schema, auto_register=(not dry_run)
                )

                if not erp_sifra:
                    stats['SKIPPED'] += 1
                    continue

                stats[action] += 1

                item_pdv = item.get('pdv_pct', mp_cfg['pdv_pct'])
                # Simple MP calculation
                net_purchase = float(item['cena_fakturna']) * (1 - float(item['rabat_pct'])/100.0)
                mp_rounded = round(net_purchase * (1 + mp_cfg['marza_pct']/100.0), 2)
                ruc_to_use = mp_cfg['marza_pct']

                if dry_run:
                    pass
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
                            mp_rounded, item['serija'], item['rok_dt'],
                        ],
                    )

        if dry_run:
            conn.rollback()
        else:
            conn.commit()

        return kalk_id
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()

# Helper functions
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

def lookup_komintent(cur, dobavljac_name, schema_prefix=SCHEMA_PREFIX):
    """Resolve komintent (supplier code) from a raw supplier name."""
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

    # Exact normalized match
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

    return '1'

def lookup_or_create_artikal(cur, item, schema_prefix='public.', auto_register=True):
    """Resolve or create an artikal by barcode/name."""
    
    barcode = (item.get('barcode') or '').strip()
    supplier_sifra = (item.get('sifra') or '').strip()
    naziv = (item.get('naziv') or 'UNKNOWN')[:40]
    
    # Auto-create flag
    allow_auto_create = os.getenv('WPH_ALLOW_AUTO_CREATE', '1') == '1'
    auto_register = auto_register and allow_auto_create

    # 1. Primary barcode match
    if barcode:
        cur.execute(f"SELECT sifra, naziv, barkod FROM {schema_prefix}artikli WHERE barkod=%s LIMIT 1", [barcode])
        row = cur.fetchone()
        if row:
            return (row[0], row[1], None, 'FOUND')

    # 2. Fuzzy name match
    if naziv and naziv != 'UNKNOWN':
        norm_name = ' '.join(naziv.upper().split())
        cur.execute(f"""
            SELECT sifra, naziv FROM {schema_prefix}artikli
            WHERE UPPER(naziv) LIKE %s
            ORDER BY sifra LIMIT 1
        """, [f"%{norm_name[:25]}%"])
        row = cur.fetchone()
        if row:
            return (row[0], row[1], None, 'BARCODE_ADDED')

    # 3. Fallback by supplier sifra
    if supplier_sifra:
        cur.execute(f"SELECT sifra, naziv FROM {schema_prefix}artikli WHERE sifra=%s LIMIT 1", [supplier_sifra])
        row = cur.fetchone()
        if row:
            return (row[0], row[1], None, 'SIFRA_FALLBACK')

    # 4. Auto-register
    if auto_register and (barcode or naziv != 'UNKNOWN'):
        cur.execute(f"SELECT COALESCE(MAX(sifra::bigint),2300000000)+1 FROM {schema_prefix}artikli WHERE sifra ~ '^\\d+$'")
        new_sifra = str(cur.fetchone()[0])
        
        default_vrsta = 'LEK'
        default_jedmere = 'KOM'
        default_minzaliha = 10.0
        default_pakovanje = 1.0
        default_marza = 25.0
        default_vrstaporeza = 'E'
        
        note = f'Auto-regjistruar nga fatura'
        
        try:
            cur.execute(f"""
                INSERT INTO {schema_prefix}artikli
                  (sifra, naziv, jedmere, vrstaartikla, vrstaporeza, barkod, napomena, pakovanje, minzaliha, marza)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, [
                new_sifra, naziv, default_jedmere, default_vrsta, default_vrstaporeza,
                barcode if barcode else None, note, default_pakovanje, default_minzaliha, default_marza
            ])
            return (new_sifra, naziv, None, 'CREATED')
        except Exception as e:
            return (None, None, None, 'NOT_FOUND')

    return (None, None, None, 'NOT_FOUND')
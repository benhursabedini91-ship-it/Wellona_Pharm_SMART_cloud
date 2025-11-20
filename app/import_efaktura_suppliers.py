"""
Extract supplier info from eFaktura XMLs and save to database.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import psycopg2
import xml.etree.ElementTree as ET
from collections import defaultdict

def extract_suppliers_from_xml(xml_dir):
    """Extract unique suppliers from XML invoices."""
    suppliers = defaultdict(lambda: {
        'pib': None,
        'name': None,
        'address': None,
        'city': None,
        'postal_code': None,
        'invoice_count': 0,
        'invoice_ids': []
    })
    
    ns = {
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
    }
    
    for xml_file in os.listdir(xml_dir):
        if not xml_file.endswith('.xml'):
            continue
        
        xml_path = os.path.join(xml_dir, xml_file)
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Supplier party
            supplier_party = root.find('.//cac:AccountingSupplierParty/cac:Party', ns)
            
            if supplier_party is None:
                continue
            
            # Get PIB (CompanyID with schemeID="PIB")
            pib_elem = supplier_party.find('.//cac:PartyTaxScheme/cbc:CompanyID[@schemeID="PIB"]', ns)
            if pib_elem is None:
                pib_elem = supplier_party.find('.//cac:PartyIdentification/cbc:ID[@schemeID="PIB"]', ns)
            
            pib = pib_elem.text.strip() if pib_elem is not None and pib_elem.text else None
            
            # Get name
            name_elem = supplier_party.find('.//cac:PartyLegalEntity/cbc:RegistrationName', ns)
            name = name_elem.text.strip() if name_elem is not None and name_elem.text else None
            
            if not name:
                continue
            
            # Get address
            address_elem = supplier_party.find('.//cac:PostalAddress/cbc:StreetName', ns)
            address = address_elem.text.strip() if address_elem is not None and address_elem.text else None
            
            city_elem = supplier_party.find('.//cac:PostalAddress/cbc:CityName', ns)
            city = city_elem.text.strip() if city_elem is not None and city_elem.text else None
            
            postal_elem = supplier_party.find('.//cac:PostalAddress/cbc:PostalZone', ns)
            postal = postal_elem.text.strip() if postal_elem is not None and postal_elem.text else None
            
            # Get invoice ID
            inv_id_elem = root.find('.//cbc:ID', ns)
            invoice_id = inv_id_elem.text.strip() if inv_id_elem is not None and inv_id_elem.text else xml_file
            
            # Store
            key = name  # Use name as key
            suppliers[key]['pib'] = pib or suppliers[key]['pib']
            suppliers[key]['name'] = name
            suppliers[key]['address'] = address or suppliers[key]['address']
            suppliers[key]['city'] = city or suppliers[key]['city']
            suppliers[key]['postal_code'] = postal or suppliers[key]['postal_code']
            suppliers[key]['invoice_count'] += 1
            suppliers[key]['invoice_ids'].append(invoice_id)
            
        except Exception as e:
            print(f"⚠️  Error parsing {xml_file}: {e}")
    
    return list(suppliers.values())

def create_table(conn):
    """Create suppliers table."""
    cursor = conn.cursor()
    
    sql = """
    CREATE TABLE IF NOT EXISTS public.efaktura_suppliers (
        id SERIAL PRIMARY KEY,
        pib VARCHAR(20),
        name VARCHAR(500) NOT NULL UNIQUE,
        address VARCHAR(500),
        city VARCHAR(200),
        postal_code VARCHAR(20),
        invoice_count INTEGER DEFAULT 0,
        first_invoice_date TIMESTAMP,
        last_invoice_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_efaktura_sup_pib ON public.efaktura_suppliers(pib);
    CREATE INDEX IF NOT EXISTS idx_efaktura_sup_name ON public.efaktura_suppliers(name);
    
    COMMENT ON TABLE public.efaktura_suppliers IS 'Furnitorë nga të cilët kemi marrë eFaktura XML';
    """
    
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    print("✓ Tabela u krijua")

def insert_suppliers(conn, suppliers):
    """Insert suppliers into database."""
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    
    for sup in suppliers:
        try:
            cursor.execute("""
                INSERT INTO public.efaktura_suppliers 
                (pib, name, address, city, postal_code, invoice_count, last_invoice_date)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (name) DO UPDATE SET
                    pib = COALESCE(EXCLUDED.pib, efaktura_suppliers.pib),
                    address = COALESCE(EXCLUDED.address, efaktura_suppliers.address),
                    city = COALESCE(EXCLUDED.city, efaktura_suppliers.city),
                    postal_code = COALESCE(EXCLUDED.postal_code, efaktura_suppliers.postal_code),
                    invoice_count = efaktura_suppliers.invoice_count + EXCLUDED.invoice_count,
                    last_invoice_date = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS inserted
            """, (
                sup['pib'],
                sup['name'],
                sup['address'],
                sup['city'],
                sup['postal_code'],
                sup['invoice_count']
            ))
            
            is_insert = cursor.fetchone()[0]
            if is_insert:
                inserted += 1
            else:
                updated += 1
                
        except Exception as e:
            print(f"⚠️  Error inserting {sup['name']}: {e}")
    
    conn.commit()
    cursor.close()
    
    return inserted, updated

if __name__ == "__main__":
    print("=" * 80)
    print("  eFAKTURA SUPPLIER EXTRACTION")
    print("=" * 80)
    
    # Extract from XML
    xml_dir = '../staging/faktura_uploads'
    print(f"📂 Leximi i XML-ve nga: {xml_dir}")
    
    suppliers = extract_suppliers_from_xml(xml_dir)
    
    print(f"\n✓ U gjetën {len(suppliers)} furnitorë unikë\n")
    
    for sup in suppliers:
        print(f"  • {sup['name']}")
        print(f"    PIB: {sup['pib'] or 'N/A'}")
        print(f"    Adresa: {sup['address'] or 'N/A'}, {sup['city'] or 'N/A'}")
        print(f"    Faktura: {sup['invoice_count']}")
    
    # Connect to DB
    password = os.getenv('WPH_DB_PASS')
    if not password:
        from getpass import getpass
        password = getpass("\nDB Password: ")
    
    conn_params = {
        'host': 'localhost',
        'port': 5432,
        'dbname': 'wph_ai',
        'user': 'smart_pedja',
        'password': password
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        print(f"\n✓ Lidhur me DB: {conn_params['dbname']}")
        
        # Create table
        create_table(conn)
        
        # Insert
        inserted, updated = insert_suppliers(conn, suppliers)
        
        print("\n" + "=" * 80)
        print("  PËRFUNDIM")
        print("=" * 80)
        print(f"✓ U shtuan: {inserted} furnitorë të rinj")
        print(f"↻ U përditësuan: {updated} furnitorë ekzistues")
        print("=" * 80)
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

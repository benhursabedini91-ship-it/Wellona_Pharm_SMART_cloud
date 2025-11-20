"""
Extract supplier info from eFaktura XMLs and create a simple reference table.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import xml.etree.ElementTree as ET
import psycopg2
from datetime import datetime

def extract_supplier_from_xml(xml_path):
    """Extract supplier details from UBL XML."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        ns = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
        }
        
        supplier_party = root.find('.//cac:AccountingSupplierParty/cac:Party', ns)
        
        if supplier_party is None:
            return None
        
        # Extract info
        name_elem = supplier_party.find('.//cac:PartyLegalEntity/cbc:RegistrationName', ns)
        pib_elem = supplier_party.find('.//cac:PartyTaxScheme/cbc:CompanyID', ns)
        address_elem = supplier_party.find('.//cac:PostalAddress/cac:AddressLine/cbc:Line', ns)
        city_elem = supplier_party.find('.//cac:PostalAddress/cbc:CityName', ns)
        
        return {
            'name': name_elem.text.strip() if name_elem is not None and name_elem.text else None,
            'pib': pib_elem.text.strip() if pib_elem is not None and pib_elem.text else None,
            'address': address_elem.text.strip() if address_elem is not None and address_elem.text else None,
            'city': city_elem.text.strip() if city_elem is not None and city_elem.text else None
        }
    
    except Exception as e:
        print(f"⚠️  Error parsing {os.path.basename(xml_path)}: {e}")
        return None

def create_table(conn):
    """Create suppliers table."""
    cursor = conn.cursor()
    
    sql = """
    CREATE TABLE IF NOT EXISTS public.efaktura_suppliers (
        pib VARCHAR(20) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        address VARCHAR(500),
        city VARCHAR(100),
        invoice_count INTEGER DEFAULT 1,
        first_invoice_date TIMESTAMP,
        last_invoice_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_efaktura_supp_name ON public.efaktura_suppliers(name);
    
    COMMENT ON TABLE public.efaktura_suppliers IS 'Furnitorët nga të cilët marrim faktura në eFaktura';
    """
    
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    print("✓ Tabela u krijua")

def import_suppliers(conn, xml_dir):
    """Import suppliers from XML files."""
    cursor = conn.cursor()
    
    suppliers = {}
    
    # Extract from all XMLs
    for xml_file in os.listdir(xml_dir):
        if not xml_file.endswith('.xml'):
            continue
        
        xml_path = os.path.join(xml_dir, xml_file)
        supplier = extract_supplier_from_xml(xml_path)
        
        if supplier and supplier['pib']:
            pib = supplier['pib']
            
            if pib not in suppliers:
                suppliers[pib] = {
                    'name': supplier['name'],
                    'address': supplier['address'],
                    'city': supplier['city'],
                    'count': 0
                }
            
            suppliers[pib]['count'] += 1
    
    print(f"\n📋 {len(suppliers)} furnitorë unikë gjetur\n")
    
    # Insert into DB
    for pib, info in suppliers.items():
        try:
            cursor.execute(
                """
                INSERT INTO public.efaktura_suppliers 
                (pib, name, address, city, invoice_count, first_invoice_date, last_invoice_date)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (pib) DO UPDATE SET
                    name = EXCLUDED.name,
                    address = EXCLUDED.address,
                    city = EXCLUDED.city,
                    invoice_count = public.efaktura_suppliers.invoice_count + EXCLUDED.invoice_count,
                    last_invoice_date = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (pib, info['name'], info['address'], info['city'], info['count'])
            )
            print(f"  ✓ {info['name'][:50]:50s} | PIB: {pib} | {info['count']} faktura")
        
        except Exception as e:
            print(f"  ❌ {pib}: {e}")
    
    conn.commit()
    cursor.close()
    
    return len(suppliers)

if __name__ == "__main__":
    print("=" * 80)
    print("  eFAKTURA SUPPLIER REGISTRY")
    print("  (Vetëm furnitorët që kemi invoice)")
    print("=" * 80)
    
    # DB connection
    password = os.getenv('WPH_DB_PASS')
    if not password:
        from getpass import getpass
        password = getpass("DB Password: ")
    
    conn_params = {
        'host': 'localhost',
        'port': 5432,
        'dbname': 'wph_ai',
        'user': 'smart_pedja',
        'password': password,
        'application_name': 'eFaktura_SupplierRegistry'
    }
    
    try:
        conn = psycopg2.connect(**conn_params)
        print(f"✓ Connected to DB: {conn_params['dbname']}\n")
        
        create_table(conn)
        
        xml_dir = '../staging/faktura_uploads'
        total = import_suppliers(conn, xml_dir)
        
        # Summary
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_suppliers,
                SUM(invoice_count) as total_invoices,
                MAX(invoice_count) as max_invoices_per_supplier
            FROM public.efaktura_suppliers
        """)
        
        stats = cursor.fetchone()
        cursor.close()
        
        print("\n" + "=" * 80)
        print("  PËRFUNDIM")
        print("=" * 80)
        print(f"✓ Furnitorë të regjistruar: {stats[0]}")
        print(f"📋 Total faktura: {stats[1]}")
        print(f"📊 Max faktura nga 1 furnitor: {stats[2]}")
        print("=" * 80)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

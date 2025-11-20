"""
Export supplier info from eFaktura XMLs to CSV (no DB changes).
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import xml.etree.ElementTree as ET
import csv
from collections import Counter

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
        postal_elem = supplier_party.find('.//cac:PostalAddress/cbc:PostalZone', ns)
        country_elem = supplier_party.find('.//cac:PostalAddress/cac:Country/cbc:IdentificationCode', ns)
        
        return {
            'name': name_elem.text.strip() if name_elem is not None and name_elem.text else '',
            'pib': pib_elem.text.strip() if pib_elem is not None and pib_elem.text else '',
            'address': address_elem.text.strip() if address_elem is not None and address_elem.text else '',
            'city': city_elem.text.strip() if city_elem is not None and city_elem.text else '',
            'postal': postal_elem.text.strip() if postal_elem is not None and postal_elem.text else '',
            'country': country_elem.text.strip() if country_elem is not None and country_elem.text else ''
        }
    
    except Exception as e:
        return None

def export_suppliers_csv(xml_dir, output_csv):
    """Export suppliers to CSV."""
    suppliers = {}
    invoice_count = Counter()
    
    # Extract from all XMLs
    print(f"📂 Duke lexuar XML nga: {xml_dir}\n")
    
    for xml_file in os.listdir(xml_dir):
        if not xml_file.endswith('.xml'):
            continue
        
        xml_path = os.path.join(xml_dir, xml_file)
        supplier = extract_supplier_from_xml(xml_path)
        
        if supplier and supplier['pib']:
            pib = supplier['pib']
            
            if pib not in suppliers:
                suppliers[pib] = supplier
            
            invoice_count[pib] += 1
    
    # Write to CSV
    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['PIB', 'Emri', 'Adresa', 'Qyteti', 'Postal', 'Vendi', 'Nr_Fakturave'])
        
        for pib, info in sorted(suppliers.items(), key=lambda x: invoice_count[x[0]], reverse=True):
            writer.writerow([
                pib,
                info['name'],
                info['address'],
                info['city'],
                info['postal'],
                info['country'],
                invoice_count[pib]
            ])
            
            print(f"  {invoice_count[pib]:3d} faktura | {info['name'][:60]:60s} | PIB: {pib}")
    
    return len(suppliers), sum(invoice_count.values())

if __name__ == "__main__":
    print("=" * 80)
    print("  eFAKTURA SUPPLIER EXPORT")
    print("  (Vetëm CSV, pa ndryshime në DB)")
    print("=" * 80)
    
    xml_dir = '../staging/faktura_uploads'
    output_csv = '../staging/efaktura_suppliers.csv'
    
    total_suppliers, total_invoices = export_suppliers_csv(xml_dir, output_csv)
    
    print("\n" + "=" * 80)
    print("  PËRFUNDIM")
    print("=" * 80)
    print(f"✓ Furnitorë unikë: {total_suppliers}")
    print(f"📋 Total faktura: {total_invoices}")
    print(f"📄 CSV u krijua: {output_csv}")
    print("=" * 80)

"""
List all unique suppliers from eFaktura XML invoices.
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import xml.etree.ElementTree as ET
from collections import Counter

xml_dir = '../staging/faktura_uploads'

suppliers = []
invoice_count = Counter()

for xml_file in os.listdir(xml_dir):
    if not xml_file.endswith('.xml'):
        continue
    
    xml_path = os.path.join(xml_dir, xml_file)
    
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # UBL namespace
        ns = {'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
              'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'}
        
        # Find supplier name
        supplier_elem = root.find('.//cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName', ns)
        
        if supplier_elem is not None and supplier_elem.text:
            supplier = supplier_elem.text.strip()
            suppliers.append(supplier)
            invoice_count[supplier] += 1
    
    except Exception as e:
        print(f"Error parsing {xml_file}: {e}", file=sys.stderr)

print("=" * 80)
print("  FURNITORËT NË eFAKTURA XML-të")
print("=" * 80)
print(f"Total XML: {len([f for f in os.listdir(xml_dir) if f.endswith('.xml')])}")
print(f"Total furnitorë unikë: {len(set(suppliers))}")
print("=" * 80)

# Sort by invoice count
for supplier, count in invoice_count.most_common():
    print(f"{count:3d} faktura | {supplier}")

print("=" * 80)

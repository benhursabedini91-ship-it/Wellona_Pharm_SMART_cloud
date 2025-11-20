#!/bin/bash
# Test script for Wellona Pharm SMART Cloud API
# This script tests all API endpoints

API_KEY="f7b40af0-9689-4872-8d59-4779f7961175"
BASE_URL="http://localhost:8055"

echo "========================================"
echo "Wellona Pharm SMART Cloud API Tests"
echo "========================================"
echo ""

echo "1. Testing /health endpoint (no auth)..."
curl -s ${BASE_URL}/health | python -m json.tool
echo ""
echo ""

echo "2. Testing /api/orders without API key (should fail)..."
curl -s ${BASE_URL}/api/orders | python -m json.tool
echo ""
echo ""

echo "3. Testing /api/orders with API key..."
curl -s -H "X-API-Key: ${API_KEY}" ${BASE_URL}/api/orders | python -m json.tool
echo ""
echo ""

echo "4. Testing /api/orders with urgent_only filter..."
curl -s -H "X-API-Key: ${API_KEY}" "${BASE_URL}/api/orders?urgent_only=true" | python -m json.tool
echo ""
echo ""

echo "5. Testing /api/orders/export (CSV)..."
curl -s -H "X-API-Key: ${API_KEY}" "${BASE_URL}/api/orders/export?format=csv" | head -5
echo ""
echo ""

echo "6. Testing /api/orders/approve..."
curl -s -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"order_ids": ["order1", "order2"]}' \
  ${BASE_URL}/api/orders/approve | python -m json.tool
echo ""
echo ""

echo "7. Creating test CSV file..."
cat > /tmp/test_invoice.csv << EOF
Sifra;Kolicina
ART001;100
ART002;200
ART003;50
EOF
echo "Test CSV created."
echo ""

echo "8. Testing /faktura-ai/import-csv (dry_run)..."
curl -s -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -F "file=@/tmp/test_invoice.csv" \
  -F "mode=dry_run" \
  ${BASE_URL}/faktura-ai/import-csv | python -m json.tool
echo ""
echo ""

echo "9. Testing /faktura-ai/import-csv (commit)..."
curl -s -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -F "file=@/tmp/test_invoice.csv" \
  -F "mode=commit" \
  ${BASE_URL}/faktura-ai/import-csv | python -m json.tool
echo ""
echo ""

echo "10. Creating test XML file..."
cat > /tmp/test_invoice.xml << EOF
<?xml version="1.0" encoding="UTF-8"?>
<Invoice>
    <InvoiceNo>INV-2025-001</InvoiceNo>
    <Supplier>Test Supplier</Supplier>
    <Date>2025-01-15</Date>
</Invoice>
EOF
echo "Test XML created."
echo ""

echo "11. Testing /faktura-ai/import-xml/parse..."
curl -s -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -F "file=@/tmp/test_invoice.xml" \
  ${BASE_URL}/faktura-ai/import-xml/parse | python -m json.tool
echo ""
echo ""

echo "12. Testing /faktura-ai/import-xml/commit..."
curl -s -X POST \
  -H "X-API-Key: ${API_KEY}" \
  -F "file=@/tmp/test_invoice.xml" \
  ${BASE_URL}/faktura-ai/import-xml/commit | python -m json.tool
echo ""
echo ""

echo "========================================"
echo "All tests completed!"
echo "========================================"

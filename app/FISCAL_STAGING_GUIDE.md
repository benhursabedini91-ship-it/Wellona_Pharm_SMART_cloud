# Fiscal (eFiskalizim) Staging & Shadow Architecture

Goal: ingest daily retail fiscal bills (maloprodaje) safely WITHOUT touching production ERP tables; prepare margin/cash-flow analytics.

## 1. Data Sources
- Purchase invoices (XML) -> `app/staging/faktura_uploads/INV_*.xml`
- Fiscal bills (JSON) -> `app/staging/fiscal_bills/FB_*.json`
- Summary CSV (created by script) -> `fiscal_bills_summary_<date>.csv`

## 2. Shadow Schema (Proposed: `shadow_finance`)
Tables (all truncated/rebuilt as needed, never read by ERP core logic):
- `raw_purchase_invoice (invoice_id, supplier, issue_date, xml_raw, parsed_at)`
- `raw_purchase_invoice_line (invoice_id, line_no, sku_raw, qty, unit_price_net, rabat_pct, tax_rate)`
- `raw_fiscal_bill (bill_number, issue_dt, total_amount, raw_json, parsed_at)`
- `raw_fiscal_bill_line (bill_number, line_no, sku_raw, qty, unit_price_gross, tax_rate)`
- `sku_map (sku_raw, barcode, sifra, canonical_name, last_seen_source)`
- `cost_basis (sku_key, last_purchase_price_net, updated_at, source_invoice_id)`
Derived / aggregation:
- `daily_revenue (day, gross_revenue, bills_count, items_count, avg_basket_value)`
- `daily_margin (day, gross_revenue, cost_of_goods, gross_margin_value, gross_margin_pct)`
- `inventory_snapshot (day, sku_key, theoretical_stock_qty)` (optional future)

## 3. ETL Steps
1. Loader (file -> raw tables): parse new XML/JSON only (hash compare) -> insert raw.
2. Parser Normalization: extract line items; build/update `sku_map` (cascade: barcode | sifra | name fuzzy).
3. Cost Basis Refresh: from most recent purchase lines per sku (apply rabat%).
4. Margin Calc: join fiscal lines to cost basis -> line_margin.
5. Daily Aggregation: group by day -> `daily_revenue`, `daily_margin`.
6. Anomaly Checks: zero bills, negative margins, price spikes; write to `logs/finance_alerts.log`.

## 4. Isolation & Safety
- Use separate connection string env vars: `WPH_SHADOW_DB_*` (never reuse ERP prod creds).
- All writes confined to `shadow_finance` schema.
- No triggers or foreign keys linking to ERP core schemas.
- Purge strategy: keep 12 months raw, archive older to compressed CSV/Parquet.

## 5. Idempotency
- File hash table (`ingest_file_hash (path, sha256, first_seen)`) prevents double load.
- Upserts on `cost_basis` only when price changes.

## 6. Feature Flags
- `ENABLE_FISCAL_ETL` (env) controls running loader.
- `ENABLE_MARGIN_AGG` controls aggregation job.
- Guard file: presence of `app/guards/ALLOW_REAL_IMPORT.flag` required for any future prod DB writes (not used here yet).

## 7. Scheduling
- Daily job after store close (~23:30 local) to ensure all bills posted.
- Optional mid-day incremental (read-only) if `ENABLE_FISCAL_ETL_INCREMENTAL` set.

## 8. Error Handling
- Network/API errors -> retry (max 3) then log and skip.
- Parse anomalies -> log JSON snippet and continue; never halt entire batch.

## 9. Next Implementation Order
1. Minimal shadow schema DDL.
2. Loader for fiscal JSON -> `raw_fiscal_bill` / `raw_fiscal_bill_line`.
3. Purchase XML parser -> raw + lines.
4. SKU mapping + cost basis.
5. Margin aggregation + alerts.

## 10. Metrics (to log/CSV)
- `daily_metrics_<date>.csv`: bills_count, items_count, gross_revenue, margin_pct, anomalies_count.

## 11. Rollback / Clean
- To reset: `DROP SCHEMA shadow_finance CASCADE;` then re-run loader; production remains untouched.

## 12. Security
- Never persist API keys in DB.
- Files remain on disk; ensure Windows ACL limits access to staging folder.

---
This guide is the blueprint; confirm any field name changes from real JSON/XML samples before writing parsers.

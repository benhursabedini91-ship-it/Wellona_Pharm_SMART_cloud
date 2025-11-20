-- Baseline ERP-identik (2025-11-01)
-- Stock = FY current year for magacin=101; Demand = sales window logic with cap; Article status uses those.

-- 1) Stock on hand (FY current year, magacin 101)
DROP MATERIALIZED VIEW IF EXISTS stg.stock_on_hand CASCADE;
CREATE MATERIALIZED VIEW stg.stock_on_hand AS
SELECT TRIM(artikal)::text AS sifra,
       CURRENT_DATE        AS datum,
       COALESCE(SUM(ulaz - izlaz), 0)::numeric AS qty
FROM eb_fdw.artiklikartica
WHERE magacin = '101'
  AND EXTRACT(YEAR FROM datum) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY TRIM(artikal);
CREATE INDEX IF NOT EXISTS ix_stock_on_hand_sifra ON stg.stock_on_hand(sifra);
CREATE INDEX IF NOT EXISTS ix_stock_on_hand_datum ON stg.stock_on_hand(datum);

-- 2) Sales 180d (magacin 101 + anomaly cap)
DROP MATERIALIZED VIEW IF EXISTS ops._sales_180d CASCADE;
CREATE MATERIALIZED VIEW ops._sales_180d AS
WITH d AS (
  SELECT TRIM(artikal)::text AS sifra,
         DATE(datum)         AS dte,
         GREATEST(SUM(izlaz), -10) AS izlaz_capped
  FROM eb_fdw.artiklikartica
  WHERE datum >= CURRENT_DATE - INTERVAL '180 days'
    AND magacin = '101'
  GROUP BY TRIM(artikal), DATE(datum)
)
SELECT sifra,
       AVG(izlaz_capped)::numeric(12,4) AS avg_daily,
       MAX(dte)                          AS last_sale_date
FROM d
GROUP BY sifra;
CREATE UNIQUE INDEX IF NOT EXISTS ix_sales_180d_sifra ON ops._sales_180d(sifra);

-- 3) Article status (joins demand + inventory)
DROP MATERIALIZED VIEW IF EXISTS ops.article_status CASCADE;
CREATE MATERIALIZED VIEW ops.article_status AS
WITH demand AS (
  SELECT s.sifra,
         COALESCE(s.avg_daily,0) AS avg_daily,
         s.last_sale_date,
         (CURRENT_DATE - s.last_sale_date) <= 90 AS has_recent_sales,
         COALESCE(s.avg_daily*30,0) AS monthly_units
  FROM ops._sales_180d s
),
inventory AS (
  SELECT sifra, qty AS stock FROM stg.stock_on_hand
),
calc AS (
  SELECT COALESCE(d.sifra, i.sifra) AS sifra,
         COALESCE(i.stock,0)        AS current_stock,
         COALESCE(d.avg_daily,0)    AS avg_daily_sales,
         COALESCE(d.monthly_units,0)AS monthly_units,
         COALESCE(d.has_recent_sales,FALSE) AS has_recent_sales,
         (
           SELECT p.min_zaliha
           FROM ref.min_zaliha_policy_v2 p
           WHERE COALESCE(d.avg_daily,0)*30 >= p.range_from
             AND (p.range_to IS NULL OR COALESCE(d.avg_daily,0)*30 <= p.range_to)
           ORDER BY p.range_from DESC
           LIMIT 1
         ) AS min_zaliha,
         6.0 AS target_days
  FROM demand d
  FULL OUTER JOIN inventory i ON d.sifra = i.sifra
)
SELECT sifra, current_stock, avg_daily_sales, monthly_units, min_zaliha, target_days, has_recent_sales,
       CASE 
         WHEN NOT has_recent_sales THEN CASE WHEN current_stock=0 AND avg_daily_sales>0 THEN 2 ELSE 0 END
         ELSE GREATEST(0, GREATEST(COALESCE(min_zaliha,0), CEIL(target_days*avg_daily_sales)) - current_stock)
       END AS qty_to_order
FROM calc;
CREATE UNIQUE INDEX IF NOT EXISTS idx_article_status_sifra ON ops.article_status(sifra);
CREATE INDEX IF NOT EXISTS idx_article_status_order ON ops.article_status(qty_to_order) WHERE qty_to_order>0;

-- Optional immediate refresh (uncomment when applying):
-- REFRESH MATERIALIZED VIEW stg.stock_on_hand;
-- REFRESH MATERIALIZED VIEW ops._sales_180d;
-- REFRESH MATERIALIZED VIEW ops.article_status;

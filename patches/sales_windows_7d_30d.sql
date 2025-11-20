-- Sales windows as calendar-day averages (includes zero-sale days)
-- Rebuild 7d, 30d, 180d MVs with magacin='101'

DROP MATERIALIZED VIEW IF EXISTS ops._sales_7d CASCADE;
CREATE MATERIALIZED VIEW ops._sales_7d AS
SELECT TRIM(artikal)::text AS sifra,
       ROUND(COALESCE(SUM(GREATEST(izlaz,0)),0) / 7.0, 6) AS avg_daily,
       MAX(CASE WHEN GREATEST(izlaz,0) > 0 THEN DATE(datum) END) AS last_sale_date
FROM eb_fdw.artiklikartica
WHERE datum >= CURRENT_DATE - INTERVAL '7 days'
  AND magacin = '101'
GROUP BY TRIM(artikal);
CREATE UNIQUE INDEX IF NOT EXISTS ix_sales_7d_sifra ON ops._sales_7d(sifra);

DROP MATERIALIZED VIEW IF EXISTS ops._sales_30d CASCADE;
CREATE MATERIALIZED VIEW ops._sales_30d AS
SELECT TRIM(artikal)::text AS sifra,
       ROUND(COALESCE(SUM(GREATEST(izlaz,0)),0) / 30.0, 6) AS avg_daily,
       MAX(CASE WHEN GREATEST(izlaz,0) > 0 THEN DATE(datum) END) AS last_sale_date
FROM eb_fdw.artiklikartica
WHERE datum >= CURRENT_DATE - INTERVAL '30 days'
  AND magacin = '101'
GROUP BY TRIM(artikal);
CREATE UNIQUE INDEX IF NOT EXISTS ix_sales_30d_sifra ON ops._sales_30d(sifra);

DROP MATERIALIZED VIEW IF EXISTS ops._sales_180d CASCADE;
CREATE MATERIALIZED VIEW ops._sales_180d AS
SELECT TRIM(artikal)::text AS sifra,
       ROUND(COALESCE(SUM(GREATEST(izlaz,0)),0) / 180.0, 6) AS avg_daily,
       MAX(CASE WHEN GREATEST(izlaz,0) > 0 THEN DATE(datum) END) AS last_sale_date
FROM eb_fdw.artiklikartica
WHERE datum >= CURRENT_DATE - INTERVAL '180 days'
  AND magacin = '101'
GROUP BY TRIM(artikal);
CREATE UNIQUE INDEX IF NOT EXISTS ix_sales_180d_sifra ON ops._sales_180d(sifra);

-- Refresh immediately for interactive use
REFRESH MATERIALIZED VIEW ops._sales_7d;
REFRESH MATERIALIZED VIEW ops._sales_30d;
REFRESH MATERIALIZED VIEW ops._sales_180d;

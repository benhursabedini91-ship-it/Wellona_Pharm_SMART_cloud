-- ==== schemas
CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS stg;

-- ==== stock-on-hand (VIEW) — burim: artikli.stanje
DROP VIEW IF EXISTS stg.stock_on_hand;
CREATE VIEW stg.stock_on_hand AS
SELECT
  a.sifra,
  COALESCE(a.stanje, 0)::numeric(18,3) AS qty,
  now()::timestamp without time zone AS last_update
FROM eb_fdw.artikli a;

-- ==== demand windows (MVs) nga kalkopste/kalkstavke
-- NË ERP-in tënd dokvrsta '20' = lëvizja që na duhet për shitje
DROP MATERIALIZED VIEW IF EXISTS ops._sales_7d  CASCADE;
DROP MATERIALIZED VIEW IF EXISTS ops._sales_30d CASCADE;
DROP MATERIALIZED VIEW IF EXISTS ops._sales_180d CASCADE;

CREATE MATERIALIZED VIEW ops._sales_7d AS
SELECT ks.artikal AS sifra,
       SUM(ks.kolicina) / 7.0 AS avg_daily,
       MAX(ko.datum)::date AS last_sale_date
FROM eb_fdw.kalkstavke ks
JOIN eb_fdw.kalkopste ko ON ks.kalkid = ko.id
WHERE ko.dokvrsta = '20'
  AND ko.datum >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY ks.artikal;

CREATE INDEX IF NOT EXISTS ix_sales_7d_sifra ON ops._sales_7d (sifra);

CREATE MATERIALIZED VIEW ops._sales_30d AS
SELECT ks.artikal AS sifra,
       SUM(ks.kolicina) / 30.0 AS avg_daily,
       MAX(ko.datum)::date AS last_sale_date
FROM eb_fdw.kalkstavke ks
JOIN eb_fdw.kalkopste ko ON ks.kalkid = ko.id
WHERE ko.dokvrsta = '20'
  AND ko.datum >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY ks.artikal;

CREATE INDEX IF NOT EXISTS ix_sales_30d_sifra ON ops._sales_30d (sifra);

CREATE MATERIALIZED VIEW ops._sales_180d AS
SELECT ks.artikal AS sifra,
       SUM(ks.kolicina) / 180.0 AS avg_daily,
       MAX(ko.datum)::date AS last_sale_date
FROM eb_fdw.kalkstavke ks
JOIN eb_fdw.kalkopste ko ON ks.kalkid = ko.id
WHERE ko.dokvrsta = '20'
  AND ko.datum >= CURRENT_DATE - INTERVAL '180 days'
GROUP BY ks.artikal;

CREATE INDEX IF NOT EXISTS ix_sales_180d_sifra ON ops._sales_180d (sifra);

-- ==== verifikime të shpejta
SELECT '_v_stock_on_hand' AS obj, COUNT(*) AS cnt FROM stg.stock_on_hand
UNION ALL
SELECT '_sales_7d',  COUNT(*) FROM ops._sales_7d
UNION ALL
SELECT '_sales_30d', COUNT(*) FROM ops._sales_30d
UNION ALL
SELECT '_sales_180d', COUNT(*) FROM ops._sales_180d
ORDER BY 1;

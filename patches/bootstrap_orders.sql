-- =====[ SCHEMAS ]=====
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS app;

-- =====[ STAGING: STOCK ON HAND ]=====
-- Lexon stokun real nga ERP (RO permes FDW)
CREATE OR REPLACE VIEW stg.stock_on_hand AS
SELECT
  a.sifra,
  COALESCE(a.stanje,0)::numeric AS qty
FROM eb_fdw.artikli a;

-- =====[ SALES MVs ]=====
-- Nese i ke tashme, ok; po i ribëj për siguri (dokvrsta='20' = shitje)
DROP MATERIALIZED VIEW IF EXISTS ops._sales_7d     CASCADE;
DROP MATERIALIZED VIEW IF EXISTS ops._sales_30d    CASCADE;
DROP MATERIALIZED VIEW IF EXISTS ops._sales_180d   CASCADE;

CREATE MATERIALIZED VIEW ops._sales_7d AS
SELECT ks.artikal AS sifra,
       SUM(ks.kolicina)::numeric / 7.0 AS avg_daily,
       MAX(ko.datum)::date AS last_sale_date
FROM eb_fdw.kalkstavke ks
JOIN eb_fdw.kalkopste  ko ON ko.id = ks.kalkid
WHERE ko.dokvrsta = '20'
  AND ko.datum >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY ks.artikal;
CREATE INDEX IF NOT EXISTS idx__sales_7d_sifra ON ops._sales_7d(sifra);

CREATE MATERIALIZED VIEW ops._sales_30d AS
SELECT ks.artikal AS sifra,
       SUM(ks.kolicina)::numeric / 30.0 AS avg_daily,
       MAX(ko.datum)::date AS last_sale_date
FROM eb_fdw.kalkstavke ks
JOIN eb_fdw.kalkopste  ko ON ko.id = ks.kalkid
WHERE ko.dokvrsta = '20'
  AND ko.datum >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY ks.artikal;
CREATE INDEX IF NOT EXISTS idx__sales_30d_sifra ON ops._sales_30d(sifra);

CREATE MATERIALIZED VIEW ops._sales_180d AS
SELECT ks.artikal AS sifra,
       SUM(ks.kolicina)::numeric / 180.0 AS avg_daily,
       MAX(ko.datum)::date AS last_sale_date
FROM eb_fdw.kalkstavke ks
JOIN eb_fdw.kalkopste  ko ON ko.id = ks.kalkid
WHERE ko.dokvrsta = '20'
  AND ko.datum >= CURRENT_DATE - INTERVAL '180 days'
GROUP BY ks.artikal;
CREATE INDEX IF NOT EXISTS idx__sales_180d_sifra ON ops._sales_180d(sifra);

-- =====[ VIEW kandidatësh: kombinon demand + stock + artikuj ]
-- Ky view s’ka target_days brenda (qëllimisht); API-ja e aplikon formulën me parametrat.
-- Por e bën gati setin bazë që duhet.
CREATE OR REPLACE VIEW ops.order_candidates AS
WITH sales AS (
  -- i bashkojme te tre dhe i dallojme me 'win'
  SELECT 7  AS win,  sifra, avg_daily, last_sale_date FROM ops._sales_7d
  UNION ALL
  SELECT 30 AS win,  sifra, avg_daily, last_sale_date FROM ops._sales_30d
  UNION ALL
  SELECT 180 AS win, sifra, avg_daily, last_sale_date FROM ops._sales_180d
),
base AS (
  SELECT
    s.win,
    a.sifra,
    a.naziv,
    LOWER(COALESCE(a.barkod,'')) AS barkod,
    COALESCE(a.pakovanje,1)::numeric AS pakovanje,
    COALESCE(a.minzaliha,0)::numeric AS minzaliha,
    COALESCE(a.cena,0)::numeric AS unit_cost,
    COALESCE(st.qty,0)::numeric AS current_stock,
    COALESCE(s.avg_daily,0)::numeric AS avg_daily,
    s.last_sale_date
  FROM eb_fdw.artikli a
  LEFT JOIN stg.stock_on_hand st ON st.sifra = a.sifra
  LEFT JOIN sales s            ON s.sifra = a.sifra
)
SELECT * FROM base;

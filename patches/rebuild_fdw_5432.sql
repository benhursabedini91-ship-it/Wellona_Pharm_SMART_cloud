-- rebuild_fdw_5432.sql
SELECT srvname, srvoptions FROM pg_foreign_server WHERE srvname='erp93_fdw';

ALTER SERVER erp93_fdw OPTIONS (
  SET host '127.0.0.1',
  SET port '5432',
  SET dbname 'ebdata'
);

DROP SCHEMA IF EXISTS eb_fdw CASCADE;
DROP SCHEMA IF EXISTS eb_ro CASCADE;
CREATE SCHEMA eb_fdw;
CREATE SCHEMA eb_ro;

IMPORT FOREIGN SCHEMA public
  LIMIT TO (artikli, kalkkasa, kalkopste, kalkstavke)
  FROM SERVER erp93_fdw INTO eb_fdw;

CREATE OR REPLACE VIEW eb_ro.artikli    AS SELECT * FROM eb_fdw.artikli;
CREATE OR REPLACE VIEW eb_ro.kalkopste  AS SELECT * FROM eb_fdw.kalkopste;
CREATE OR REPLACE VIEW eb_ro.kalkstavke AS SELECT * FROM eb_fdw.kalkstavke;
CREATE OR REPLACE VIEW eb_ro.kalkkasa   AS SELECT * FROM eb_fdw.kalkkasa;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_user') THEN
    CREATE ROLE app_user LOGIN PASSWORD 'changeme';
  END IF;
END$$;

GRANT USAGE ON SCHEMA eb_ro TO app_user;
GRANT SELECT ON ALL TABLES IN SCHEMA eb_ro TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA eb_ro GRANT SELECT ON TABLES TO app_user;

SELECT 'artikli' AS tbl, COUNT(*) AS cnt FROM eb_ro.artikli
UNION ALL
SELECT 'kalkopste', COUNT(*) FROM eb_ro.kalkopste
UNION ALL
SELECT 'kalkstavke', COUNT(*) FROM eb_ro.kalkstavke
UNION ALL
SELECT 'kalkkasa', COUNT(*) FROM eb_ro.kalkkasa
ORDER BY 1;

SELECT dokvrsta, magacin, COUNT(*) AS cnt
FROM eb_ro.kalkopste
GROUP BY 1,2
ORDER BY 3 DESC
LIMIT 10;

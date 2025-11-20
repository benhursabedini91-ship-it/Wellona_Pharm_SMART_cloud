-- Fix type mismatch: change TEXT to VARCHAR for sifra/emri/barkod
DROP FUNCTION IF EXISTS wph_core.get_orders(integer, integer, boolean, text, text[]);

CREATE OR REPLACE FUNCTION wph_core.get_orders(
    p_target_days integer DEFAULT 28,
    p_sales_window integer DEFAULT 30,
    p_include_zero boolean DEFAULT false,
    p_search_query text DEFAULT NULL::text,
    p_suppliers text[] DEFAULT NULL::text[]
)
RETURNS TABLE(
    sifra character varying,
    emri character varying,
    barkod character varying,
    current_stock numeric,
    avg_daily_sales numeric,
    days_cover numeric,
    min_zaliha numeric,
    qty_to_order numeric,
    supplier_name text
)
LANGUAGE plpgsql
AS $function$
DECLARE
    v_mv_name      TEXT;
    v_where_clause TEXT := '';
    v_search_sql   TEXT := '';
    v_supplier_sql TEXT := '';
    v_sql          TEXT;
    v_pattern      TEXT;
BEGIN
    -- 1) Resolve MV name
    IF p_sales_window IN (7, 15, 30, 60, 180) THEN
        v_mv_name := format('ops._sales_%sd', p_sales_window);
    ELSE
        v_mv_name := 'ops._sales_30d';
    END IF;

    -- 2) include_zero filter
    IF NOT p_include_zero THEN
        v_where_clause := 'AND COALESCE(c.current_stock,0) > 0';
    END IF;

    -- 3) search query
    IF p_search_query IS NOT NULL AND btrim(p_search_query) <> '' THEN
        v_search_sql := '
          AND (
                LOWER(ar.naziv)  LIKE LOWER($1)
             OR LOWER(c.sifra)   LIKE LOWER($1)
             OR LOWER(ar.barkod) LIKE LOWER($1)
          )';
        v_pattern := '%' || p_search_query || '%';
    END IF;

    -- 4) supplier filter
    IF p_suppliers IS NOT NULL AND array_length(p_suppliers, 1) > 0 THEN
        IF p_search_query IS NOT NULL THEN
            v_supplier_sql := '
          AND UPPER(COALESCE(pf.supplier_name, '''')) = ANY($2)';
        ELSE
            v_supplier_sql := '
          AND UPPER(COALESCE(pf.supplier_name, '''')) = ANY($1)';
        END IF;
    END IF;

    -- 5) Build SQL (removed ::text casts, added ::VARCHAR for sifra)
    v_sql := format($Q$
        WITH demand AS (
          SELECT s.sifra,
                 COALESCE(s.avg_daily,0) AS avg_daily,
                 s.last_sale_date,
                 (CURRENT_DATE - s.last_sale_date) <= 90 AS has_recent_sales,
                 COALESCE(s.avg_daily*30,0) AS monthly_units
          FROM %1$s s
        ),
        inventory AS (
          SELECT sifra, qty AS stock FROM stg.stock_on_hand
        ),
        calc AS (
          SELECT COALESCE(d.sifra, i.sifra) AS sifra,
                 COALESCE(i.stock,0) AS current_stock,
                 COALESCE(d.avg_daily,0) AS avg_daily_sales,
                 COALESCE(d.avg_daily*30,0) AS monthly_units,
                 COALESCE(d.has_recent_sales,FALSE) AS has_recent_sales,
                 CEIL(COALESCE(d.avg_daily,0) * %2$L) AS min_zaliha,
                 CEIL(COALESCE(d.avg_daily,0) * %2$L) AS effective_min,
                 (CURRENT_DATE - d.last_sale_date) AS days_since_last_sale,
                 CASE WHEN COALESCE(d.avg_daily,0) > 0
                      THEN ROUND(COALESCE(i.stock,0) / d.avg_daily, 1)
                      ELSE NULL
                 END AS days_cover
          FROM demand d
          FULL OUTER JOIN inventory i ON d.sifra = i.sifra
        )
        SELECT DISTINCT ON (c.sifra)
          c.sifra::VARCHAR,
          COALESCE(ar.naziv, '') AS emri,
          COALESCE(ar.barkod, '') AS barkod,
          c.current_stock,
          c.avg_daily_sales,
          c.days_cover,
          c.min_zaliha,
          CEIL(
            GREATEST(
              0,
              c.effective_min - c.current_stock
            )
          ) AS qty_to_order,
          COALESCE(pf.supplier_name, 'UNKNOWN') AS supplier_name
        FROM calc c
        LEFT JOIN eb_fdw.artikli ar ON c.sifra = ar.sifra
        LEFT JOIN stg.pricefeed pf ON ar.barkod = pf.sifra
        WHERE 1=1
          %3$s
          %4$s
          %5$s
        ORDER BY c.sifra, pf.price ASC NULLS LAST
    $Q$,
    v_mv_name,
    p_target_days,
    v_where_clause,
    v_search_sql,
    v_supplier_sql
    );

    -- 6) Execute with parameters
    IF p_search_query IS NOT NULL AND p_suppliers IS NOT NULL THEN
        RETURN QUERY EXECUTE v_sql USING v_pattern, p_suppliers;
    ELSIF p_search_query IS NOT NULL THEN
        RETURN QUERY EXECUTE v_sql USING v_pattern;
    ELSIF p_suppliers IS NOT NULL THEN
        RETURN QUERY EXECUTE v_sql USING p_suppliers;
    ELSE
        RETURN QUERY EXECUTE v_sql;
    END IF;
END;
$function$;

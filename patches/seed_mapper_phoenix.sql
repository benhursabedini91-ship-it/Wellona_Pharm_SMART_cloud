SET search_path = wph_core, public;

-- siguro mappers/pipelines ekzistojnë
-- (nëse i ke prej patch-it, këto UPDATE/INSERT-e janë idempotente)

-- Mapper PHOENIX@v1: barcode=kol.8, vpc=14, kasa=19; + rregulla bazë
INSERT INTO wph_core.mappers(supplier_code, mapper_version, config)
VALUES (
  'PHOENIX','v1',
  jsonb_build_object(
    'columns', jsonb_build_object(
      'barcode', 8,
      'vpc',     14,
      'kasa',    19
    ),
    'rules', jsonb_build_object(
      'banned_words', ARRAY[
        'IGLA','IGLE','SPRIC','RUKAVICA','RUKAVICE','CONTOUR PLUS','MASKE','MASKA'
      ],
      'budget_daily_limit_rsd', 1000000,
      'invoice_approval_threshold_rsd', 250000
    )
  )
)
ON CONFLICT (supplier_code, mapper_version)
DO UPDATE SET config = EXCLUDED.config;

-- pipeline nightly_etl aktiv (nëse mungon, krijo; përndryshe rifresko cfg)
INSERT INTO wph_core.pipelines(pipeline_code, is_active, config)
VALUES (
  'nightly_etl', TRUE,
  jsonb_build_object(
    'steps', jsonb_build_array(
      jsonb_build_object(
        'id','import_phoenix','type','load_xlsx',
        'input','C:/Wellona/wphAI/in/phoenix/*.xlsx',
        'mapper','PHOENIX@v1','staging','stg.phoenix'
      ),
      jsonb_build_object('id','validate','type','validate','rules',jsonb_build_array('banned_words','price>0')),
      jsonb_build_object('id','choose_supplier','type','map','logic','best_price_with_filters'),
      jsonb_build_object('id','export_orders','type','emit','dest','C:/Wellona/wphAI/out/orders/'),
      jsonb_build_object('id','log','type','log_run')
    )
  )
)
ON CONFLICT (pipeline_code)
DO UPDATE SET is_active = TRUE, config = EXCLUDED.config;

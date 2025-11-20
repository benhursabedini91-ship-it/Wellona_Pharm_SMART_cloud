SET search_path = wph_core, public;

CREATE OR REPLACE FUNCTION wph_core.run_pipeline(p_code text)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    cfg jsonb;
BEGIN
    SELECT config INTO cfg
    FROM wph_core.pipelines
    WHERE pipeline_code = p_code
      AND is_active = TRUE
    LIMIT 1;

    IF cfg IS NULL THEN
        RAISE EXCEPTION 'Pipeline % nuk ekziston ose është joaktiv.', p_code;
    END IF;

    INSERT INTO audit.events(actor, action, payload)
    VALUES (current_user, 'run_pipeline',
            jsonb_build_object('pipeline', p_code, 'cfg', cfg));

    RETURN jsonb_build_object(
        'status',   'ok',
        'pipeline', p_code,
        'steps',    cfg->'steps'
    );
END;
$$;

GRANT EXECUTE ON FUNCTION wph_core.run_pipeline(text) TO PUBLIC;

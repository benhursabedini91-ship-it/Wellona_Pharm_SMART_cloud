# Quick patch: after line 244 (after current_db check), add:

# Auto-detect schema based on connected database
if current_db == 'ebdata':
    active_schema = 'public.'
    print(f"NOTE: Connected directly to ebdata → using schema 'public.'")
elif current_db == 'wph_ai' and USE_FDW:
    # Already set to eb_fdw. by SCHEMA_PREFIX
    pass

# Backend

Files:

- `app_v2.py` – main Flask app you are running on port 8056
- `app.py` – older / alternative app entry
- `efaktura_client.py` – helper that talks to the Serbia eFaktura Public API
- `faktura_import.py` – import / orchestration logic for Faktura AI
- `faktura_ai_import_legacy.py` – older import variant (renamed from `FAKTURA_Ai_IMPORT.PY`)
- `faktura_ai_mvp.py` – early MVP script
- `swagger.json` – OpenAPI JSON exported from efaktura.mfin.gov.rs

Suggested virtualenv + run command (local):

```bash
cd backend
python app_v2.py
```

Later you can refactor, but for now this is just a clean archive of what you had.

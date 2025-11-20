# Mock Server (pa DB) – Për Zhvillim UI

Ky është një server i thjeshtë Flask që kthen JSON/CSV nga `docs/samples/*.json` për të testuar UI pa pasur nevojë për DB ose backend-in real.

## Kërkesat
- Python 3.9+ (Windows)
- Paketat: `flask`

## Instalimi i varësive
```powershell
# nga rrënja e projektit
python -m pip install flask
```

## Nisja e serverit
```powershell
# nga rrënja e projektit ose nga folderi docs/
python docs/mock_server.py
```

Serveri hapet në:
```
http://127.0.0.1:8055
```

UI-ja (`orders_pro_plus.html`) bën thirrje tek `http://localhost:8055/api/orders`, kështu që mock-u përputhet.

## Endpoints
- `GET /api/orders` – kthen JSON listë me artikuj
  - Parametra: `sales_window`, `target_days`, `include_zero`, `q`, `supplier` (mund të përsëritet)
  - `download=csv` – shkarkon CSV
  - `download=xlsx` – (nuk implementohet në mock, kthen 501)

## Rregullat e thjeshta të mock-ut
- Nëse `supplier=PHOENIX` → kthen `docs/samples/api_orders_phoenix.json`
- Nëse `q` përmban `para` → kthen `docs/samples/api_orders_search_para.json`
- Përndryshe → `docs/samples/api_orders_sample.json`
- Nëse `include_zero=0` → heq rreshtat me `avg_daily_sales == 0`

## Përdorimi me Postman
- Importo `docs/postman_collection.json`
- Vendos `baseUrl = http://localhost:8055`
- Testo request-et: GET Orders, Download CSV, Download XLSX

## Përdorimi me OpenAPI/Swagger
- Skedari: `docs/openapi.json`
- Mund të importohet në Postman/Insomnia ose të shërbehet me një viewer Swagger lokal

## Probleme të zakonshme
- Porti 8055 i zënë: ose ndalo procesin ekzistues, ose ndrysho portin në `mock_server.py`
- Mungon Flask: instalo me `python -m pip install flask`

## Shënim
Ky mock nuk ka asnjë lidhje me DB dhe nuk ekzekuton logjikë biznesi – vetëm ndihmon për zhvillimin e UI-së. Për testime reale përdorni backend-in `app_v2.py` me databazë.

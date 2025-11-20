# WPH_AI — CHANGELOG (Operime me etiketa zyrtare)

Data: 2025-10-23

[VENDIM] Kalojmë në 3A (pg_dump/pg_restore) për Data Bridge; 3B mbetet fallback.

[NDRYSHIME]

- Shtuar scaffold 3A: configs/bridge_3A.json, scripts/bridge_3A_{restore,refresh,report}.ps1.
- Skriptet u bënë tolerantë ndaj dy formateve konfigurimi (nested `pg15{}` ose flat në root).
- Përdorim env var `WPH_PG18_PASS` për autentikim (mos shëno fjalëkalime në repo).
- Shtuar dokumente: docs/OPS_CODES.md, logs/templates/OPS_STATUS_TEMPLATE.txt.

[STATUS]

- Scaffold i 3A gati; kërkohet vetëm vendosja e env var dhe ekzekutimi i tre skripteve në rend.
- Raporti do të dalë në `logs/reports/BRIDGE_3A_*.csv`.

[RREZIK]

- Latencë OneDrive gjatë sinkronizimit të .backup.
- Gabime konfigurimi (p.sh., `password_env` me vlerë fjalëkalimi dhe jo emri i variablës).

[PENGESË]

- Asnjë aktive. Nëse env var mungon, skripti kërkon password në runtime.

[MIRATIM]

- Miratohet ekzekutimi i parë i 3A (restore → refresh → report).

[PING_OK]

- Do vendoset pas raportit të parë të suksesshëm.

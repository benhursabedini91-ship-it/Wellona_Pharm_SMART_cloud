# [SPECIFIKIM] Data Bridge 3A (EB → PG18 → wphAI)

Data: 2025-10-23 | Version: 1.0

## [QËLLIM]

Të kemi mirror të lexueshëm të të dhënave të EB në PostgreSQL 18 çdo natë, pa prekur PROD 9.3, që modulët (FAKTURA_AI, Analyst, Orders) të lexojnë vetëm nga wphAI.

## [SCOPE]

- Import nga .backup (pg_dump custom) i EB.
- Restore në DB `eb_core` (PG18, 127.0.0.1:5432).
- FDW ‘eb_core_local’ në DB `wph_ai` + MV bazë në `wph_core`.
- Raport verifikimi në `logs/reports`.

## [KRITERE PRANIMI]

- `eb_core` rikthehet pa error nga .backup i fundit.
- `wph_ai` ka skemat `eb_fdw` dhe `wph_core` me MV: `mv_katalog`, `mv_kalk`.
- Raport CSV me numra rreshtash dhe max(datum) gjenerohet.

## [INPUTE]

- .backup: `C:\Users\Lenovo\OneDrive\Documents\wphAI-BACKUPS\*.backup`
- Env var: `WPH_PG18_PASS`
- Postgres klient/bin: `C:\Program Files\PostgreSQL\18\bin`

## [SIGURI]

- Asnjë shkrim në ERP 9.3.
- Sekretet vetëm nga env vars; pa hardcode në repo.

---

## [PLAN] Ekzekutim

1. Konfigurim

- Vendos env var `WPH_PG18_PASS` (0262000) dhe rihap VS Code/PowerShell.
- Kontrollo `configs/bridge_3A.json` (bin/host/port/password_env/path).

2. Restore

- Nis `scripts/bridge_3A_restore.ps1`.
- Verifiko mesazhet: Using backup → Running pg_restore → Restore complete.

3. FDW + MV

- Nis `scripts/bridge_3A_refresh.ps1`.
- Verifiko: “FDW linked and MVs refreshed…”.

4. Raport

- Nis `scripts/bridge_3A_report.ps1`.
- Dërgo CSV nga `logs/reports/` për verifikim.

5. Orar i natës (pasi kalon testi)

- Task Scheduler: 02:30 restore → 02:45 refresh → 03:00 report.

## [RREZIK]

- Latencë OneDrive (backup ende në sinkronizim). Zgjidhje: prit + verifiko madhësinë/mtime.
- `password_env` gabim → kërkesë password runtime.

## [PENGESË]

- Asnjë aktive.

## [OUTPUTE]

- DB: `eb_core` (PG18), FDW: `eb_fdw` te `wph_ai`, MV: `wph_core.mv_*`.
- Raportet: `logs/reports/BRIDGE_3A_*.csv`.

## [PING]

- PING_OK do të vendoset pas raportit të parë OK.

# WPH_AI — KODET ZYRTARE TË KOMUNIKIMIT DHE OPERIMIT

Version: 1.0  |  Data: 2025-10-23

Ky dokument standardizon etiketat që do përdorim në komunikim dhe në log-et operative gjatë zhvillimit dhe operimit të wphAI.

## 1) KOMUNIKIMI STRATEGJIK
- [QËLLIM] (GOAL): Rezultati final i kërkuar.
  - Shembull: [QËLLIM] Automatizohet importi i faturave deri në 06:00.
- [VENDIM] (DECISION): Zgjedhje drejtimi/alternative/prioriteti.
  - Shembull: [VENDIM] Zgjedhim 3A për mirror-in e DB.
- [KËRKESË] (REQ): Urdhër pune pa kod konkret.
  - Shembull: [KËRKESË] Ndërto tabelën wph_core.stg_invoices.
- [PENGESË] (BLOCKER): Çka na ndal derisa të zgjidhet.
  - Shembull: [PENGESË] FTP nuk pranon lidhje.
- [RREZIK] (RISK): Rrezik potencial.
  - Shembull: [RREZIK] Furnitori mund të ndryshojë XML.
- [MIRATIM] (APPROVE): Leje për të kaluar fazën.
  - Shembull: [MIRATIM] Faza 1 mund të startojë.

## 2) OPERACIONET TEKNIKE
- [SPECIFIKIM] (SPEC): Çfarë ndërtohet, pse, si testohet (kritere pranimi).
- [PLAN] (PLAN): Hapat teknikë, varësitë, afatet.
- [NDRYSHIME] (CHANGELOG): Çfarë u ndryshua dhe pse.
- [STATUS] (STATUS): Progres aktual, çfarë mbetet.
- [INCIDENT] (NGJARJE): Problem real me kohë/ngjarje dhe veprim të menjëhershëm.
- [PING] (PING): Konfirmim sinkronizimi/logu; mbyllja me PING_OK.

Konventa e datave/orës: ISO 8601 (p.sh. 2025-10-23 06:00:00+01).

## 3) INTELIGJENCA OPERACIONALE
- [NGRIRJE] (HOLD): Stop automatik kur ngecja > 30 min.
- [RIRIMENDIM] (RETHINK): Arsyetim për zhbllokim.
- [RILINDJE] (SHINE): Përmbledhje pas zgjidhjes dhe rifillim.

## 4) Si përdoren
- Në chat dhe commit-mesazhe: prefikso me etiketa, p.sh. "[VENDIM] Kalojmë në 3A; [PLAN] Nis restore 02:30."
- Në raporte ditore: përfshij [STATUS], [PENGESË], [RREZIK], [PING_OK].
- Në logjet e skripteve: një rresht final me [PING_OK] kur run-i përfundon me sukses.

## 5) Lokacionet
- Dokumenti: c:\Wellona\wphAI\docs\OPS_CODES.md
- Template statusi: c:\Wellona\wphAI\logs\templates\OPS_STATUS_TEMPLATE.txt


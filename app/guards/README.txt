GUARD FILES - Mbrojtje për operacione kritike
==============================================

Këto file kontrollojnë nëse lejohet ekzekutimi i operacioneve që prekin bazën e të dhënave (DB).

1. ALLOW_DB_WRITE.flag
   - Nëse ky file ekziston → lejohen shkrime në PostgreSQL shadow schema.
   - Nëse nuk ekziston → ASNJË shkrim në DB (vetëm staging/logs).
   - Për ta aktivizuar: type nul > ALLOW_DB_WRITE.flag

2. REQUIRE_MANUAL_CONFIRM.flag
   - Nëse ky file ekziston → çdo herë që skripti dëshiron të shkruajë në DB, të pyet TY në terminal: "Konfirmo shkrim? (PO/JO)"
   - Përdor këtë për siguri maksimale gjatë testimit.
   - Për ta aktivizuar: type nul > REQUIRE_MANUAL_CONFIRM.flag

SHEMBULL - Guard i plotë (parandalon aksidente):
   1. Krijo ALLOW_DB_WRITE.flag (lejon akses).
   2. Krijo REQUIRE_MANUAL_CONFIRM.flag (kërkon konfirmim live).
   3. Kur je i sigurt, fshij REQUIRE_MANUAL_CONFIRM.flag por mbaj ALLOW_DB_WRITE.flag.

RREZIK - Nëse fshij të dyja:
   - Asnjë skript s'mund të prekë DB fare (vetëm read-only staging).

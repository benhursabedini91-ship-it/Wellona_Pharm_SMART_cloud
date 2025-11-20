# Wellona Porosi AI — Udhëzues vendimmarrjeje

## Sistemet, rrugët, DB dhe rolet

- UI: GET /smart (SPA), kontrollon targetDays dhe salesWindow.
- API: GET /api/orders?target_days={n}&sales_window={15|30|60}; opsionale: GET /api/orders/recalc?date_from&date_to&include_zero&target_days.
- DB (lokale, PG18): skemat stg, ops, ref; FDW drejt ERP (ebdata PG9.3) për artikli/kalk* dhe artiklikartica.
- Përdorues: lokalisht postgres/app_user (SELECT), FDW user i kufizuar (p.sh. smart_pedja) për lexim nga ERP.

## Burimet e të dhënave

- Shitjet (avg_daily): ops._sales_15d/_30d/_60d (SUM daljesh / dritarja); ose lyt.sales_in_range(p_from,p_to,p_min_out) për range custom.
- Stoku: stg.stock_on_hand (COALESCE(stanje,0)); fallback eb_fdw.artikli.stanje.
- Politika min_zaliha (ref.min_zaliha_policy): intervale mbi lëvizje mujore (30×avg_daily):
  - 0–0 → 1 (pa lëvizje, mbaj 1 kuti)
  - 1–5 → 2, 5–10 → 3, 10–15 → 4, 15–20 → 5, 20–30 → 7, 30–40 → 9, 40–50 → 11, 50+ → 14.

## Rrjedha e vendimit

1) UI → targetDays ∈ {3,6,7,10,14,21,28}, salesWindow ∈ {15,30,60}.
2) API zgjedh MV sipas salesWindow → avg_daily_sales.
3) current_stock nga stoku; days_cover = stock/avg_daily (nëse >0), urgent = days_cover < 3 (indikativ).
4) monthly_units = 30×avg_daily; min_zaliha = lookup nga politika (0–0 → 1, …).
5) target_qty = max(min_zaliha, ceil(targetDays×avg_daily)).
6) deficit = max(0, target_qty − current_stock).
7) qty_to_order = ceil(deficit).  ← Sasia finale që porositet.

Formula të plota:

- monthly_units = 30 × avg_daily
- min_zaliha = policy(monthly_units)
- target_qty = max(min_zaliha, ceil(targetDays × avg_daily))
- qty_to_order = ceil( max(0, target_qty − current_stock) )

Raste skajore:
- avg_daily = 0 → monthly_units = 0 → min_zaliha = 1; nëse stock < 1, qty_to_order = 1, ndryshe 0.
- Fraksione → CEIL në fund siguron njësi të plota.

## Parametrat e kontrollit

- targetDays: sa ditë mbulim synohet përveç min_zaliha.
- salesWindow: 15/30/60 ditë; kompromis reaktivitet/stabilitet.
- include_zero (te /recalc): për diagnostikë.

## Gjendja aktuale dhe verifikimet

- Politika e min_zaliha: 0–0 → 1 e aplikuar.
- CEIL i qty_to_order në API → gjithmonë sasi të plota.
- Verifikuar: target_days=6, sales_window=60 → Total=7169, qty>0=4811, pa shitje por me porosi=4811.

## Pikat e ardhshme (opsionale)

- Sinkronizo sql/patch3_min_zaliha_policy.sql me 0–0 → 1 në repo.
- Unifiko të gjitha path-et e llogaritjes me CEIL në fund.
- POST /api/orders/{supplier} për gjenerim CSV (Phoenix/Vega/Sopharma).


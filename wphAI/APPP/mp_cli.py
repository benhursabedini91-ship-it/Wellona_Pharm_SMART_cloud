# coding: utf-8
import os, sys, datetime
import pandas as pd
from mpkalk import mp_kalk, MPCfg

# UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

OB_OUTDIR = os.environ.get("OB_OUTDIR", r"C:\Wellona\wphAI\out\orders")
WORKDIR   = r"C:\Wellona\wphAI\app\work"
IN_XLSX   = os.path.join(WORKDIR, "MP_INPUT.xlsx")  # pritja e inputit
TODAY_DIR = os.path.join(OB_OUTDIR, datetime.date.today().strftime("%Y-%m-%d"))
os.makedirs(TODAY_DIR, exist_ok=True)
OUT_XLSX  = os.path.join(TODAY_DIR, "MP_KALK.xlsx")

if not os.path.exists(IN_XLSX):
    print(f"[BLOCKED] S'gjeta {IN_XLSX}. Përdor template-n që u krijua.")
    sys.exit(2)

df = pd.read_excel(IN_XLSX)

# Kolonat e pritura minimale:
# Sifra | Naziv | NabavnaNet | RabatPct | PDVPct | TrosakPct | MarzaPct | ExtraCost
required = ["Sifra","Naziv","NabavnaNet","RabatPct","PDVPct","TrosakPct","MarzaPct"]
missing = [c for c in required if c not in df.columns]
if missing:
    print("[BLOCKED] Mungojnë kolona:", missing)
    sys.exit(2)

rows = []
for _, r in df.iterrows():
    cfg = MPCfg(
        trosak_pct = float(r.get("TrosakPct", 0) or 0),
        marza_pct  = float(r.get("MarzaPct", 0) or 0),
        pdv_pct    = float(r.get("PDVPct",   0) or 0),
        rounding   = str(r.get("RoundMode","END_99") or "END_99"),
        round_threshold = float(r.get("RoundThreshold", 0) or 0),
        min_decimals = int(r.get("MinDecimals", 2) or 2),
    )
    res = mp_kalk(
        nabavna_net = float(r.get("NabavnaNet", 0) or 0),
        rabat_pct   = float(r.get("RabatPct",   0) or 0),
        cfg=cfg,
        extra_cost_abs=float(r.get("ExtraCost", 0) or 0)
    )
    rows.append({
        **{k: r.get(k) for k in ["Sifra","Naziv"]},
        **res,
        "PDV_pct": cfg.pdv_pct,
        "Marza_pct": cfg.marza_pct,
        "Trosak_pct": cfg.trosak_pct,
        "RoundMode": cfg.rounding
    })

out_df = pd.DataFrame(rows)
with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as xw:
    out_df.to_excel(xw, index=False, sheet_name="MP_KALK")

print("[OK] MP_KALK.xlsx →", OUT_XLSX)

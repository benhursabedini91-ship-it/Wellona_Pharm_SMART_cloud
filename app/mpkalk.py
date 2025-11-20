# coding: utf-8
# MP Kalkulacija – motor llogaritës
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Literal, Dict
import math

RoundingMode = Literal["NONE","END_9","END_99","NEAREST_5","NEAREST_10"]

@dataclass
class MPCfg:
    trosak_pct: float = 0.0     # shpenzime (% mbi bazë pas rabatit)
    marza_pct:  float = 12.0    # marža nominale (% mbi bazë + trošak)
    pdv_pct:    float = 10.0    # PDV (TVSH) %
    rounding:   RoundingMode = "END_99"  # strategji rrumbullakimi
    round_threshold: float = 0.0  # minimal MP mbi të cilin aplikohet rregulli
    min_decimals: int = 2

def _round_strategy(v: float, mode: RoundingMode, threshold: float, min_decimals: int) -> float:
    if v < threshold or mode == "NONE":
        return round(v, min_decimals)
    if mode == "END_99":
        # p.sh. 123.12 -> 122.99 ose 123.99? Marrim drejt fund .99 më të afërt sipër nëse bie < v
        units = math.floor(v)
        cents = v - units
        target = units + 0.99
        if target < v:  # nëse .99 ra poshtë çmimit aktual -> ngjitemi në .99 të radhës
            target = (units + 1) + 0.99
        return round(target, 2)
    if mode == "END_9":
        # vendos fundin .9 (një shifër) – p.sh. 12.34 -> 12.9, 12.98 -> 12.9 (ose 13.9 nëse duhet sipër)
        units = math.floor(v)
        tenths = (v - units) * 10
        target = units + 0.9
        if target < v:
            target = (units + 1) + 0.9
        return round(target, 1)
    if mode == "NEAREST_5":
        # në 5-she më të afërt (për MP >= threshold)
        return float(int((v + 2.5) / 5) * 5)
    if mode == "NEAREST_10":
        return float(int((v + 5) / 10) * 10)
    return round(v, min_decimals)

def mp_kalk(nabavna_net: float, rabat_pct: float, cfg: MPCfg,
            extra_cost_abs: float = 0.0) -> Dict[str, float]:
    """
    Kthen fushat bazë të MP kalkulacijës.
    nabavna_net: çmimi i blerjes NETO (pa PDV)
    rabat_pct: rabat furnitori (%)
    extra_cost_abs: shpenzim absolut/akcizë (opsionale)
    """
    if nabavna_net is None: nabavna_net = 0.0
    if rabat_pct   is None: rabat_pct   = 0.0

    baza = nabavna_net * (1 - rabat_pct/100.0)
    trosak = baza * (cfg.trosak_pct/100.0) + (extra_cost_abs or 0.0)
    baza_plus = baza + trosak
    marza_iznos = baza_plus * (cfg.marza_pct/100.0)
    mp_bez_pdv = baza_plus + marza_iznos
    pdv_iznos = mp_bez_pdv * (cfg.pdv_pct/100.0)
    mp_sa_pdv = mp_bez_pdv + pdv_iznos

    # metrika efektive
    eff_rabat = 100.0 * (1 - (baza / nabavna_net)) if nabavna_net else 0.0
    marza_na_mp_pct = (marza_iznos / mp_sa_pdv * 100.0) if mp_sa_pdv else 0.0

    mp_rounded = _round_strategy(mp_sa_pdv, cfg.rounding, cfg.round_threshold, cfg.min_decimals)

    return {
        "baza_posle_rabata": round(baza, 4),
        "trosak_iznos": round(trosak, 4),
        "baza_plus": round(baza_plus, 4),
        "marza_iznos": round(marza_iznos, 4),
        "mp_bez_pdv": round(mp_bez_pdv, 4),
        "pdv_iznos": round(pdv_iznos, 4),
        "mp_sa_pdv": round(mp_sa_pdv, 4),
        "mp_rounded": mp_rounded,
        "eff_rabat_pct": round(eff_rabat, 4),
        "marza_na_mp_pct": round(marza_na_mp_pct, 4),
    }

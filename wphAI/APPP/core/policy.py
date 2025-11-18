from math import ceil
from typing import Tuple


def _pick_target(mes_muj: float, izlaz: float, mode: str) -> float:
    mode = str(mode or "").lower()
    if mode == "izlaz":
        return float(izlaz or 0.0)
    if mode == "mes_muj":
        return float(mes_muj or 0.0)
    return max(float(mes_muj or 0.0), float(izlaz or 0.0))


def compute_order_qty(
    stanje: float,
    ulaz: float,
    mes_muj: float,
    izlaz: float,
    min_zal: float,
    moq: int,
    *,
    target_mode: str = "izlaz",
    ignore_ulaz: bool = True,
    round_to_5_if_ge_10: bool = True,
) -> Tuple[float, float, float, int]:
    """Compute order policy.

    Returns: (target_stock, available, need, por_final)
    - target = based on mode (izlaz/mes_muj/max) and min_zal
    - available = stanje (+ ulaz if ignore_ulaz=False)
    - need = max(target - available, 0)
    - por_final = ceil(need), respect MOQ, and round to 5 if >=10
    """
    target_stock = max(_pick_target(mes_muj, izlaz, target_mode), float(min_zal or 0))
    available = max(float(stanje or 0), 0.0)
    if not ignore_ulaz:
        available += float(ulaz or 0.0)
    need = max(target_stock - available, 0.0)
    por_final = int(ceil(need))
    if moq and por_final < int(moq):
        por_final = int(moq)
    if round_to_5_if_ge_10 and por_final >= 10 and por_final % 5 != 0:
        por_final = ((por_final // 5) + 1) * 5
    return target_stock, available, need, por_final

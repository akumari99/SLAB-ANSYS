"""DCP per ASTM D6951/D6951M-18.

The k column follows the FAA chain: E = 1500 CBR, then the power law
E = 20.15 k^1.284 inverted, which is k = 28.66 CBR^0.7788.
AASHTO is the separate route k = M_R / 19.4. They disagree by roughly three
times on the same data, so both are reported and never averaged.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

MM_PER_IN = 25.4


def cbr_from_dcpi(dcpi_mm: np.ndarray, equation: str = "general") -> np.ndarray:
    """dcpi_mm in mm per blow, already multiplied by the hammer factor."""
    d = np.asarray(dcpi_mm, dtype=float)
    if equation == "cl":            # CL soils with CBR below 10
        return 1.0 / (0.017019 * d) ** 2
    if equation == "ch":            # high plasticity clay
        return 1.0 / (0.002871 * d)
    return 292.0 / d ** 1.12        # general


def mr_from_cbr(cbr):                       # MEPDG
    return 2555.0 * np.asarray(cbr, float) ** 0.64


def k_faa_from_cbr(cbr):                    # AC 150/5320-6G, E = 1500 CBR
    return (1500.0 * np.asarray(cbr, float) / 20.15) ** (1 / 1.284)


def k_aashto_from_cbr(cbr):                 # AASHTO 1993 Part III
    return mr_from_cbr(cbr) / 19.4


def profile(blows, cum_mm, hammer_factor: float = 1.0,
            equation: str = "general") -> pd.DataFrame:
    """One DCP sounding to a per-interval table.

    cum_mm may increase or decrease; the direction is taken from the data.
    """
    b = np.asarray(blows, float)
    d = np.asarray(cum_mm, float)
    sign = -1.0 if d[-1] < d[0] else 1.0
    pen = sign * np.diff(d)
    bl = b[1:]

    keep = (bl > 0) & (pen > 0)
    pen, bl = pen[keep], bl[keep]

    dcpi = pen / bl * hammer_factor
    cbr = cbr_from_dcpi(dcpi, equation)
    return pd.DataFrame({
        "blows": bl,
        "pen_mm": pen,
        "depth_mm": np.cumsum(pen),
        "dcpi_mm_per_blow": dcpi,
        "cbr_pct": cbr,
        "mr_psi": mr_from_cbr(cbr),
        "k_faa_pci": k_faa_from_cbr(cbr),
        "k_aashto_pci": k_aashto_from_cbr(cbr),
    })


def layer_summary(df: pd.DataFrame, boundary_mm: float = 254.0) -> pd.DataFrame:
    """Penetration-weighted averages above and below the layer boundary.

    Weighting by penetration, not a plain mean over rows, so a thick soft
    interval counts more than a thin one. A plain AVERAGE over rows with
    unequal penetration is the usual spreadsheet mistake here.
    """
    def agg(sub, label):
        if sub.empty:
            return None
        w = sub["pen_mm"].to_numpy()
        tot, bl = w.sum(), sub["blows"].sum()
        out = {"layer": label, "rows": len(sub), "depth_mm": tot,
               "dcpi_mm_per_blow": tot / bl}
        for col in ("cbr_pct", "mr_psi", "k_faa_pci", "k_aashto_pci"):
            out[col] = float(np.average(sub[col], weights=w))
        return out

    rows = [agg(df[df.depth_mm <= boundary_mm], "upper (aggregate)"),
            agg(df[df.depth_mm > boundary_mm], "lower (soil)"),
            agg(df, "whole profile")]
    return pd.DataFrame([r for r in rows if r])

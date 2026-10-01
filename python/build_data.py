#!/usr/bin/env python3
"""Rebuild everything the page reads, then commit web/data alongside the page.

    python build_data.py --daq raw/fatigue_run1.csv --force "244.23A Force"

With no arguments it rebuilds only what it can find, so it is safe to run.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

from slabkit import dcp, daq, export
from slabkit.westergaard import backcalculate_edge

HERE = Path(__file__).resolve().parent


def build_dcp(xlsx: Path):
    """Read a DCP workbook: blows in column A, cumulative penetration in B."""
    book = pd.read_excel(xlsx, sheet_name=None, header=None)
    out = {}
    for sheet, raw in book.items():
        pairs = raw.iloc[:, :2].apply(pd.to_numeric, errors="coerce").dropna()
        pairs = pairs[(pairs.iloc[:, 0] >= 0) & (pairs.iloc[:, 0] < 200)]
        if len(pairs) < 4:
            continue
        prof = dcp.profile(pairs.iloc[:, 0], pairs.iloc[:, 1])
        out[sheet] = {
            "profile": export.frame_to_json(prof.round(4)),
            "layers": export.frame_to_json(dcp.layer_summary(prof).round(2)),
        }
    return out


def build_peaks(path: Path, force_col: str):
    df = daq.read_daq(path)
    peaks = daq.cycle_peaks(df, force_col)
    print(f"  {len(df):,} raw rows -> {len(peaks):,} cycles")
    return export.frame_to_json(daq.decimate_log(peaks).round(5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dcp", type=Path, help="DCP workbook")
    ap.add_argument("--daq", type=Path, help="raw DAQ export")
    ap.add_argument("--force", default="244.23A Force", help="force column")
    a = ap.parse_args()

    print("building web/data")
    if a.dcp and a.dcp.exists():
        export.write_json("dcp.json", build_dcp(a.dcp))
    if a.daq and a.daq.exists():
        export.write_json("cyclic_peaks.json", build_peaks(a.daq, a.force))

    # the reference case, so the page and the paper always agree on one number
    r = backcalculate_edge(P=16000, E=4.1e6, h=8, mu=0.15, a=5.5, b=5.5,
                           z_j=0.00740, z_j_free=0.00628)
    export.write_json("reference_case.json", {
        "note": "FAA slab 2, 15.86 kip static, joint deflections both sides",
        "j_measured": round(r.j, 4),
        "z_e_in": round(r.z_e, 6),
        "kl2": round(r.kl2_w26, 1),
        "k_w26_eq16_pci": round(r.k_w26, 1),
        "k_w48_eq14_pci": round(r.k_w48, 1),
        "sigma_e_psi": round(r.sigma_e, 1),
        "sigma_j_psi": round(r.sigma_j, 1),
    })
    print("done")


if __name__ == "__main__":
    main()

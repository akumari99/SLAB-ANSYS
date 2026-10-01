"""Read an ILLI-SLAB .out file into a tidy table.

One run is tens of thousands of lines and thousands of nodes, so this parses
once and caches to Parquet. Everything downstream queries the cache.

Never trust the title line. The sample file is headed
"SINGLE SLAB - WINKLER K=200 - 24X24IN 100PSI INTERIOR LOAD" and is in fact a
two-slab doweled model at k = 580 with the load on one panel. k is recovered
from the printed subgrade stress divided by deflection, which cannot lie.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd


def _coord_array(lines, tag, want):
    i = next(n for n, l in enumerate(lines) if tag in l)
    v = []
    for l in lines[i + 1:]:
        s = l.split()
        if not s:
            if len(v) >= want:
                break
            continue
        try:
            v += [float(x) for x in s]
        except ValueError:
            break
        if len(v) >= want:
            break
    return v[:want]


def parse(path) -> dict:
    """Return {'nodes': DataFrame, 'meta': dict} for one .out file."""
    path = Path(path)
    lines = path.read_text(errors="ignore").split("\n")

    # node counts are listed per slab, so sum them
    def _counts(tag):
        v = next(l for l in lines if tag in l).split("=")[1].split()
        return [int(x) for x in v if int(x) > 0]
    nx_slabs = _counts("NO. OF NODES IN SLABS ALONG X-AXIS")
    ny_slabs = _counts("NO. OF NODES IN SLABS ALONG Y-AXIS")
    nx, ny = sum(nx_slabs), sum(ny_slabs)
    X = _coord_array(lines, "X-COORDINATES ARE", nx)
    Y = _coord_array(lines, "Y-COORDINATES ARE", ny)

    i0 = next(n for n, l in enumerate(lines) if "SUBGRADE STRESS" in l)
    rows = []
    for l in lines[i0 + 1:]:
        p = l.split()
        if len(p) == 6 and p[0].isdigit():
            try:
                rows.append([int(p[0])] + [float(x) for x in p[1:]])
            except ValueError:
                pass
        if len(rows) >= nx * ny:
            break
    df = pd.DataFrame(rows, columns=["node", "w_in", "rot_x", "rot_y",
                                     "subgrade_stress_psi", "subgrade_force_lb"])
    ix = (df.node - 1) // ny
    iy = (df.node - 1) % ny
    df["x_in"] = [X[i] for i in ix]
    df["y_in"] = [Y[i] for i in iy]
    df["w_mils"] = df.w_in * 1000

    # k from the data, not the header
    m = (df.w_in > 1e-5) & (df.subgrade_stress_psi > 1e-4)
    k = float(np.median(df.subgrade_stress_psi[m] / df.w_in[m])) if m.any() else np.nan

    def _num(tag):
        try:
            return float(next(l for l in lines if tag in l).split()[-1])
        except StopIteration:
            return np.nan

    meta = {
        "run_id": path.stem,
        "source_file": path.name,
        "sha1": hashlib.sha1(path.read_bytes()).hexdigest()[:12],
        "nx": nx, "ny": ny, "n_slabs_x": len(nx_slabs), "n_nodes": len(df),
        "k_pci": round(k, 1),
        "title_line_unreliable": True,
        "applied_load_lb": sum(float(l.split()[-1]) for l in lines
                               if "TOTAL APPLIED LOAD IS" in l),
        "reaction_sum_lb": _num("SUM OF REACTION FORCES ="),
        "dowel_load_lb": abs(_num("LOAD TRANSFERRED BY DOWELS IN X- DIRECTION IS")),
        "w_max_mils": round(df.w_mils.max(), 3),
        "subgrade_stress_max_psi": round(df.subgrade_stress_psi.max(), 3),
    }
    meta["dowel_lte_pct"] = round(100 * meta["dowel_load_lb"]
                                  / meta["applied_load_lb"], 1)
    meta["load_balance_pct"] = round(100 * meta["reaction_sum_lb"]
                                     / meta["applied_load_lb"], 2)
    return {"nodes": df, "meta": meta}


def at(df: pd.DataFrame, x, y, side="right", tol=0.7) -> pd.Series:
    """Nearest node to (x, y).

    The joint x appears twice in the coordinate list, once per slab, so side
    picks which one. Getting this wrong silently reads the other slab.
    """
    cand = df[(df.x_in - x).abs() < tol]
    if cand.empty:
        cand = df.iloc[[(df.x_in - x).abs().idxmin()]]
    nodes = sorted(cand.node.unique())
    keep = cand[cand.node <= nodes[len(nodes) // 2]] if side == "left" \
        else cand[cand.node > nodes[len(nodes) // 2]]
    keep = keep if not keep.empty else cand
    return keep.iloc[(keep.y_in - y).abs().argmin()]


def to_parquet(path, out_dir) -> Path:
    r = parse(path)
    df = r["nodes"].copy()
    for key in ("run_id", "k_pci", "applied_load_lb"):
        df[key] = r["meta"][key]
    out = Path(out_dir) / f"{r['meta']['run_id']}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return out

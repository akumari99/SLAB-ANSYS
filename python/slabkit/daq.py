"""Raw DAQ handling. This is the part that does not belong in a browser.

A fatigue run is millions of rows across 27 channels. Read it here, reduce it
to one row per logged cycle, and hand the page something it can actually plot.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd


def read_daq(path, time_col="time_s", **kw) -> pd.DataFrame:
    """Read a DAQ export. Handles csv, tab separated, and parquet."""
    p = Path(path)
    if p.suffix.lower() == ".parquet":
        return pd.read_parquet(p)
    sep = "\t" if p.suffix.lower() in (".txt", ".tsv", ".dat") else ","
    df = pd.read_csv(p, sep=sep, **kw)
    df.columns = [c.strip() for c in df.columns]
    return df


def cycle_peaks(df: pd.DataFrame, force_col: str, channels=None,
                prominence_frac: float = 0.25) -> pd.DataFrame:
    """One row per load cycle: the peak value of every channel.

    Cycles are found on the force trace, so a dropped sample in one DCDT does
    not shift the cycle count.
    """
    from scipy.signal import find_peaks

    f = df[force_col].to_numpy(float)
    span = np.nanmax(f) - np.nanmin(f)
    idx, _ = find_peaks(f, prominence=prominence_frac * span)
    if len(idx) < 2:
        raise ValueError("fewer than two cycles found; check force_col")

    channels = channels or [c for c in df.columns
                            if df[c].dtype.kind == "f" and c != force_col]
    edges = np.concatenate(([0], (idx[:-1] + idx[1:]) // 2, [len(f)]))

    recs = []
    for n, (lo, hi) in enumerate(zip(edges[:-1], edges[1:]), start=1):
        win = df.iloc[lo:hi]
        rec = {"cycle": n, force_col: float(win[force_col].max())}
        for c in channels:
            v = win[c].to_numpy(float)
            # keep the larger excursion, so channels wired either way still work
            rec[c] = float(v[np.nanargmax(np.abs(v))]) if len(v) else np.nan
        recs.append(rec)
    return pd.DataFrame(recs)


def decimate_log(peaks: pd.DataFrame, cycle_col="cycle", n=400) -> pd.DataFrame:
    """Thin a long peaks table for plotting, log spaced in cycle count.

    Fatigue damage is a log story, so even spacing in log N keeps the early
    cycles where the interesting curvature lives.
    """
    N = peaks[cycle_col].to_numpy()
    if len(N) <= n:
        return peaks
    want = np.unique(np.round(np.logspace(0, np.log10(N.max()), n)).astype(int))
    keep = np.searchsorted(N, want).clip(0, len(N) - 1)
    return peaks.iloc[np.unique(keep)].reset_index(drop=True)

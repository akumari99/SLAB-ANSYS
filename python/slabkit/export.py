"""Write the small JSON files the page reads.

Everything here lands in ../web/data. Keep these under a megabyte; if one grows
past that, decimate harder rather than making the page wait.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

WEB_DATA = Path(__file__).resolve().parents[2] / "web" / "data"


def _clean(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    raise TypeError(type(o))


def write_json(name: str, payload, out_dir: Path | None = None) -> Path:
    d = Path(out_dir or WEB_DATA)
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(json.dumps(payload, default=_clean, separators=(",", ":")))
    kb = p.stat().st_size / 1024
    print(f"  {p.name:28s} {kb:8.1f} kB")
    return p


def frame_to_json(df: pd.DataFrame) -> dict:
    """Columnar, which is roughly half the size of a list of row objects."""
    return {"cols": list(df.columns),
            "rows": df.to_numpy().tolist()}

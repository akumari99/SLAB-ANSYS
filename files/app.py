"""Slab Pit — local analysis app for the FAA slab 2 fatigue test.

    streamlit run app.py

Nothing leaves this machine. Big files stay on disk and are read from the
folder set in the sidebar, not uploaded through the browser.
"""
from pathlib import Path
import pandas as pd
import streamlit as st

from slabkit import illislab
from slabkit.westergaard import forward, backcalculate_edge, CAVEATS, record

st.set_page_config(page_title="Slab Pit", layout="wide")

STATUS = {
    "1. Pavement response": [
        ("Westergaard forward", "live"),
        ("ILLI-SLAB", "parser live, UI pending"),
        ("FAARFIELD", "design outputs only, no stress or deflection"),
        ("Lab deflection", "spec pending"),
        ("Dowel strain", "spec pending"),
    ],
    "2. Stiffness and modulus": [
        ("Westergaard inversion", "live"),
        ("DCP to CBR to k", "module live, UI pending"),
        ("Direct ratio, cell over LVDT", "spec pending"),
        ("Load-deflection slope", "spec pending"),
        ("Consolidation to constrained modulus", "spec pending"),
        ("CBR and T307", "tests not yet run"),
    ],
    "3. Cross-checks": [
        ("Newmark and Boussinesq vs cells", "spec pending"),
        ("Lab vs ILLI-SLAB deflection", "spec pending"),
    ],
}

# ------------------------------------------------------------------ sidebar
st.sidebar.title("Slab Pit")
data_root = st.sidebar.text_input("Data folder", str(Path.home() / "SlabPit-Data"))
section = st.sidebar.radio("Section", list(STATUS))
st.sidebar.divider()
st.sidebar.caption("Status")
for name, state in STATUS[section]:
    st.sidebar.write(("✅ " if state == "live" else "⬜ ") + f"{name} — *{state}*")

# ------------------------------------------------------- section 1: forward
if section.startswith("1"):
    st.header("Westergaard forward")
    st.caption("Assume k and j, predict the joint. No measured deflection goes "
               "in, so comparing against the lab stays a real test.")
    c = st.columns(4)
    P  = c[0].number_input("P, lb", value=16000.0, step=500.0)
    E  = c[0].number_input("E, psi", value=4_100_000.0, step=100_000.0, format="%.0f")
    h  = c[1].number_input("h, in", value=8.0)
    mu = c[1].number_input("Poisson", value=0.15)
    a  = c[2].number_input("a, in (parallel to joint)", value=6.206)
    b  = c[2].number_input("b, in (across joint)", value=6.206)
    k  = c[3].number_input("k assumed, pci", value=430.0, step=10.0)
    j  = c[3].number_input("j assumed", value=0.90, min_value=0.01, max_value=1.0)
    y  = st.number_input("observation point y from joint, in", value=0.0)
    MOR = st.number_input("MOR, psi", value=550.0)

    f = forward(P, E, h, mu, a, b, k, j, y)
    m = st.columns(5)
    m[0].metric("ℓ", f"{f.l:.2f} in")
    m[1].metric("z_j loaded", f"{f.z_j*1000:.2f} mils")
    m[2].metric("z_j free", f"{f.z_j_free*1000:.2f} mils")
    m[3].metric("LTE predicted", f"{f.lte:.1f} %")
    m[4].metric("σ_j / MOR", f"{f.sigma_j/MOR:.3f}")
    st.write(pd.DataFrame([{
        "z_e, mils": round(f.z_e*1000, 3), "σ_e, psi": round(f.sigma_e, 1),
        "σ_j, psi": round(f.sigma_j, 1), "σ'_j, psi": round(f.sigma_j_free, 1)}]))
    st.info("Predicted LTE depends on j only, never on k. It is therefore an "
            "independent check on the joint alone.")

    with st.expander("Compare against a measurement"):
        cc = st.columns(2)
        zj_m  = cc[0].number_input("measured z_j, mils", value=7.40)
        zjf_m = cc[1].number_input("measured z'_j, mils", value=6.28)
        st.write(pd.DataFrame([
            {"quantity": "z_j, mils", "predicted": round(f.z_j*1000, 2),
             "measured": zj_m, "error %": round(100*(f.z_j*1000/zj_m - 1), 1)},
            {"quantity": "LTE, %", "predicted": round(f.lte, 1),
             "measured": round(100*zjf_m/zj_m, 1),
             "error %": round(f.lte - 100*zjf_m/zj_m, 1)}]))

# --------------------------------------------------- section 2: inversion
elif section.startswith("2"):
    st.header("Westergaard inversion for k")
    st.caption("Measured deflections both sides of the joint. Datum is the "
               "slab bottom and the value is composite — aggregate plus soil.")
    c = st.columns(4)
    P  = c[0].number_input("P, lb", value=16000.0, step=500.0)
    E  = c[0].number_input("E, psi", value=4_100_000.0, step=100_000.0, format="%.0f")
    h  = c[1].number_input("h, in", value=8.0)
    mu = c[1].number_input("Poisson", value=0.15)
    a  = c[2].number_input("a, in", value=6.206)
    b  = c[2].number_input("b, in", value=6.206)
    zj  = c[3].number_input("z_j loaded, mils", value=7.40)
    zjf = c[3].number_input("z'_j free, mils", value=6.28)
    jm  = st.radio("j", ["measured from both sides", "assumed"], horizontal=True)
    j_assumed = st.number_input("j assumed", value=0.90) if jm == "assumed" else None

    r = backcalculate_edge(P, E, h, mu, a, b, zj/1000,
                           z_j_free=None if j_assumed else zjf/1000,
                           j=j_assumed)
    m = st.columns(4)
    m[0].metric("k — W48 Eq 14", f"{r.k_w48:.0f} pci", help="primary")
    m[1].metric("k — W26 Eq 16+18", f"{r.k_w26:.0f} pci", help="legacy check")
    m[2].metric("j used", f"{r.j:.4f}")
    m[3].metric("z_e", f"{r.z_e*1000:.2f} mils")
    st.write(pd.DataFrame([{"ℓ (Eq 14), in": round(r.l_w48, 2),
                            "ℓ (Eq 16), in": round(r.l_w26, 2),
                            "kℓ², lb/in": round(r.kl2_w26),
                            "σ_e, psi": round(r.sigma_e, 1),
                            "σ_j, psi": round(r.sigma_j, 1)}]))
    if abs(r.k_w26/r.k_w48 - 1) > 0.25:
        st.warning(f"The two routes differ by {100*abs(r.k_w26/r.k_w48-1):.0f} %. "
                   "Eq 16 treats the load as a point at the edge; Eq 14 spreads "
                   "it over the footprint. State which one the paper reports.")
    with st.expander("Caveats that travel with this number"):
        for cv in CAVEATS:
            st.write("• " + cv)

# -------------------------------------------------- section 3 / ILLI-SLAB
else:
    st.header("Cross-checks")
    st.write("Specs pending. The ILLI-SLAB reader below is live and feeds them.")

st.divider()
with st.expander("ILLI-SLAB file reader"):
    f = st.text_input("path to a .out file", "")
    if f and Path(f).exists():
        res = illislab.parse(f)
        st.json(res["meta"])
        st.caption("k comes from subgrade stress ÷ deflection. The title line "
                   "in these files is frequently stale and is ignored.")
        d = res["nodes"]
        want = {"Right_B2": (48, 48, "right"), "Left_B2": (48, 48, "left"),
                "RB1": (48, 0, "right"), "RB3": (48, 96, "right"),
                "LB1": (48, 0, "left"), "LB3": (48, 96, "left"),
                "A2": (96, 48, "right"), "C2": (0, 48, "left")}
        st.write(pd.DataFrame([
            {"sensor": s, "x": n.x_in, "y": n.y_in,
             "w, mils": round(n.w_mils, 2),
             "k·w, psi": round(n.subgrade_stress_psi, 3)}
            for s, (x, y, sd) in want.items()
            for n in [illislab.at(d, x, y, sd)]]))
    elif f:
        st.error("No file at that path.")

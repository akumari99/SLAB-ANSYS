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
st.subheader("ILLI-SLAB results")
st.caption("Drop in one .out file to inspect it, or several to build the k sweep. "
           "Files are read in memory and never leave this machine.")

SENSORS = {"Right_B2": (48, 48, "right"), "Left_B2": (48, 48, "left"),
           "RB1": (48, 0, "right"), "RB3": (48, 96, "right"),
           "LB1": (48, 0, "left"), "LB3": (48, 96, "left"),
           "A1": (96, 0, "right"), "A2": (96, 48, "right"), "A3": (96, 96, "right"),
           "C1": (0, 0, "left"), "C2": (0, 48, "left"), "C3": (0, 96, "left")}

ups = st.file_uploader("ILLI-SLAB .out files", type=["out", "txt", "dat"],
                       accept_multiple_files=True)

if ups:
    runs = []
    for u in ups:
        try:
            runs.append(illislab.parse(u))
        except Exception as e:
            st.error(f"{u.name}: could not read it — {e}")

    if runs:
        st.write("**Runs**")
        st.dataframe(pd.DataFrame([{
            "run": r["meta"]["run_id"], "k, pci": r["meta"]["k_pci"],
            "load, lb": r["meta"]["applied_load_lb"],
            "balance, %": r["meta"]["load_balance_pct"],
            "dowel LTE, %": r["meta"]["dowel_lte_pct"],
            "w max, mils": r["meta"]["w_max_mils"],
            "nodes": r["meta"]["n_nodes"]} for r in runs]),
            use_container_width=True, hide_index=True)
        st.caption("k is recovered from subgrade stress ÷ deflection. The title "
                   "line in these files is often stale and is ignored.")

        for r in runs:
            if abs(r["meta"]["load_balance_pct"] - 100) > 0.5:
                st.warning(f"{r['meta']['run_id']}: reactions are "
                           f"{r['meta']['load_balance_pct']:.1f} % of the applied "
                           "load. The run may not have converged.")

        pick = st.selectbox("Deflection at the DCDT locations",
                            [r["meta"]["run_id"] for r in runs])
        r = next(x for x in runs if x["meta"]["run_id"] == pick)
        d = r["nodes"]
        tbl = pd.DataFrame([{
            "sensor": s_, "x, in": n.x_in, "y, in": n.y_in,
            "w, mils": round(n.w_mils, 2),
            "k·w, psi": round(n.subgrade_stress_psi, 3)}
            for s_, (x, y, sd) in SENSORS.items()
            for n in [illislab.at(d, x, y, sd)]])

        with st.expander("Paste measured deflections to compare"):
            meas = st.data_editor(
                pd.DataFrame({"sensor": list(SENSORS), "measured, mils": [None]*len(SENSORS)}),
                hide_index=True, use_container_width=True, key="meas")
            tbl = tbl.merge(meas, on="sensor", how="left")
            m = tbl["measured, mils"].notna()
            tbl.loc[m, "model/lab"] = (tbl.loc[m, "w, mils"]
                                       / tbl.loc[m, "measured, mils"]).round(2)
        st.dataframe(tbl, use_container_width=True, hide_index=True)

        if len(runs) > 1:
            sw = pd.DataFrame([{"k, pci": r["meta"]["k_pci"],
                                **{s_: round(illislab.at(r["nodes"], x, y, sd).w_mils, 3)
                                   for s_, (x, y, sd) in SENSORS.items()}}
                               for r in runs]).sort_values("k, pci")
            st.write("**k sweep — deflection per sensor**")
            st.dataframe(sw, use_container_width=True, hide_index=True)
            st.line_chart(sw.set_index("k, pci")[["Right_B2", "Left_B2", "RB1", "A2"]])
            st.download_button("Download the sweep as CSV",
                               sw.to_csv(index=False).encode(),
                               "illislab_k_sweep.csv", "text/csv")
            st.caption("This table is the response surface. Fit a measured basin "
                       "against it and you have a finite-element backcalculation "
                       "without rerunning the Fortran.")

        st.download_button(f"Download all {len(r['nodes'])} nodes of {pick} as CSV",
                           r["nodes"].to_csv(index=False).encode(),
                           f"{pick}_nodes.csv", "text/csv")

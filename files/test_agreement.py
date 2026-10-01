"""The test that matters: Python must agree with the JavaScript in index.html.

If someone edits a formula on one side only, this fails. Run it before every
commit that touches physics.
"""
import math
import pytest
from slabkit.westergaard import (
    radius_rel_stiffness, kl2_from_edge_defl, k_from_kl2,
    j_from_deflections, free_edge_defl, backcalculate_edge,
)
from slabkit import dcp

# measured on FAA slab 2, 15.86 kip static step
P, E, H, MU = 16000.0, 4.1e6, 8.0, 0.15
Z_J, Z_J_FREE = 0.00740, 0.00628


def test_excel_chain_reproduces_1482():
    """The workbook's own route: Eq 16 then Eq 18, with j assumed at 0.90."""
    z_e = free_edge_defl(Z_J, 0.90)
    k = k_from_kl2(kl2_from_edge_defl(P, z_e, MU), E, H, MU)
    assert k == pytest.approx(1482, rel=0.002)


def test_j_solved_from_both_sides():
    """Eq 22 over Eq 23. The workbook assumed 0.90; the data says 0.918."""
    assert j_from_deflections(Z_J, Z_J_FREE) == pytest.approx(0.9181, abs=1e-4)


def test_footprint_correction_is_not_small():
    """Eq 14 keeps the b/l term Eq 16 drops. Roughly a 60 percent gap in k."""
    r = backcalculate_edge(P, E, H, MU, a=5.5, b=5.5,
                           z_j=Z_J, z_j_free=Z_J_FREE)
    assert r.k_w26 / r.k_w48 == pytest.approx(1.63, rel=0.05)


def test_radius_matches_westergaard_table_1():
    """W26 Table 1: E = 3e6, mu = 0.15, h = 8, k = 100 gives l = 33.83 in."""
    assert radius_rel_stiffness(3e6, 8, 0.15, 100) == pytest.approx(33.83, abs=0.01)


@pytest.mark.parametrize("dcpi,cbr,k_faa,k_aashto", [
    (29.3333, 6.6365, 125.28, 442.21),
    (11.3333, 19.2532, 287.17, 874.32),
    (7.0000, 33.0273, 437.19, 1235.00),
])
def test_dcp_chain_matches_workbook(dcpi, cbr, k_faa, k_aashto):
    c = float(dcp.cbr_from_dcpi([dcpi])[0])
    assert c == pytest.approx(cbr, rel=1e-4)
    assert float(dcp.k_faa_from_cbr([c])[0]) == pytest.approx(k_faa, rel=1e-3)
    assert float(dcp.k_aashto_from_cbr([c])[0]) == pytest.approx(k_aashto, rel=1e-3)


def test_newmark_matches_the_vertical_stress_sheet():
    """Equal-area square of the 9 in cell, four quadrants, corner factors."""
    def newmark_I(B, L, z):
        m, n = (B / 2) / z, (L / 2) / z
        m2, n2 = m * m, n * n
        s = m2 + n2 + 1
        r = math.sqrt(s)
        t1 = 2 * m * n * r / (s + m2 * n2) * ((m2 + n2 + 2) / s)
        t2 = math.atan2(2 * m * n * r, s - m2 * n2)
        if m2 * n2 > s and t2 < 0:
            t2 += 2 * math.pi
        return (t1 + t2) / (4 * math.pi)

    side = 9 * math.sqrt(math.pi) / 2
    assert side == pytest.approx(7.976, abs=0.001)
    assert 4 * newmark_I(side, side, 12) == pytest.approx(0.178, abs=0.002)
    assert 4 * newmark_I(side, side, 4) == pytest.approx(0.699, abs=0.010)


# ---- Method 1 spec, docs/method_01_westergaard_edge_joint.md section 8 ----

def test_mode_b_primary():
    from slabkit.westergaard import backcalculate_edge
    r = backcalculate_edge(P=16000, E=4.1e6, h=8, mu=0.15, a=6.206, b=6.206,
                           z_j=0.00740, z_j_free=0.00628)
    assert r.k_w48 == pytest.approx(829.0, rel=0.005)
    assert r.k_w26 == pytest.approx(1431.4, rel=0.005)


def test_mode_a_forward():
    from slabkit.westergaard import forward
    f = forward(P=16000, E=4.1e6, h=8, mu=0.15, a=6.206, b=6.206, k=430, j=0.90)
    assert f.z_j * 1000 == pytest.approx(10.936, rel=0.005)
    assert f.lte == pytest.approx(81.82, rel=0.005)
    assert f.sigma_j == pytest.approx(284.5, rel=0.005)


def test_lte_independent_of_k():
    from slabkit.westergaard import forward
    kw = dict(P=16000, E=4.1e6, h=8, mu=0.15, a=6.206, b=6.206, j=0.90)
    assert forward(k=100, **kw).lte == pytest.approx(forward(k=2000, **kw).lte)


def test_round_trip():
    from slabkit.westergaard import forward, backcalculate_edge
    kw = dict(P=16000, E=4.1e6, h=8, mu=0.15, a=6.206, b=6.206)
    f = forward(k=700, j=0.90, **kw)
    r = backcalculate_edge(z_j=f.z_j, j=0.90, **kw)
    assert r.k_w48 == pytest.approx(700, rel=0.001)


def test_illislab_reads_k_from_data_not_the_title():
    from pathlib import Path
    from slabkit import illislab
    f = Path("/mnt/user-data/uploads/ilsl2.out")
    if not f.exists():
        pytest.skip("sample .out not present")
    m = illislab.parse(f)["meta"]
    assert m["k_pci"] == pytest.approx(580, rel=0.02)   # title claims 200
    assert m["n_nodes"] == 6642
    assert m["load_balance_pct"] == pytest.approx(100.0, abs=0.5)

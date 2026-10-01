"""Westergaard 1926 and 1948, kept numerically identical to the JavaScript.

Sources
-------
W26  Westergaard, H. M. "Stresses in Concrete Pavements Computed by Theoretical
     Analysis." Public Roads 7(2), 1926, pp. 25-35.  Eqs 1, 13-18.
W48  Westergaard, H. M. "New Formulas for Stresses in Concrete Pavements of
     Airfields." ASCE Transactions 113, 1948, Paper 2340, pp. 425-444.
     Cases 3 and 6, Eqs 12-14 and 19-23.
"""
from __future__ import annotations
import math
from dataclasses import dataclass


def radius_rel_stiffness(E: float, h: float, mu: float, k: float) -> float:
    """W26 Eq 1. Inches."""
    return (E * h ** 3 / (12 * (1 - mu ** 2) * k)) ** 0.25


def edge_defl_w26(P: float, k: float, l: float, mu: float) -> float:
    """W26 Eq 15. Concentrated force at the edge, no footprint correction.

    At mu = 0.15 the coefficient is 0.4328, which is the 0.433 in Eq 16.
    """
    return (1 / math.sqrt(6)) * (1 + 0.4 * mu) * P / (k * l * l)


def kl2_from_edge_defl(P: float, z_e: float, mu: float) -> float:
    """W26 Eq 16 rearranged. Returns k*l^2 in lb/in."""
    return (1 / math.sqrt(6)) * (1 + 0.4 * mu) * P / z_e


def k_from_kl2(kl2: float, E: float, h: float, mu: float) -> float:
    """W26 Eq 18."""
    return 12 * (1 - mu ** 2) * kl2 ** 2 / (E * h ** 3)


def edge_defl_w48(P, E, h, mu, k, a, b, y=0.0) -> float:
    """W48 Eq 14. Load spread over an ellipse tangent to the joint.

    a is the semiaxis parallel to the joint, b the one across it.
    """
    l = radius_rel_stiffness(E, h, mu, k)
    return (P * math.sqrt(2 + 1.2 * mu) / math.sqrt(E * h ** 3 * k)
            * (1 - (0.76 + 0.4 * mu) * b / l)
            * (1 - (0.76 + 0.4 * mu) * y / l))


def edge_stress_w48(P, E, h, mu, k, a, b) -> float:
    """W48 Eq 13. Tensile stress at the bottom along the edge or joint."""
    l = radius_rel_stiffness(E, h, mu, k)
    ab = (a + b) / 2
    return (2.2 * (1 + mu) * P / ((3 + mu) * h ** 2)
            * math.log10(E * h ** 3 / (100 * k * ab ** 4))
            + 3 * (1 + mu) * P / (math.pi * (3 + mu) * h ** 2)
            * (1.84 - 4 * mu / 3 + (1 + mu) * (a - b) / (a + b)
               + 2 * (1 - mu) * a * b / (a + b) ** 2
               + 1.18 * (1 + 2 * mu) * b / l))


def j_from_deflections(z_j: float, z_j_free: float) -> float:
    """Joint efficiency solved from both sides, W48 Eqs 22 and 23.

    Dividing Eq 23 by Eq 22 with z'_e = 0 gives j = 2R/(1+R), R = z'_j / z_j.
    Measuring j beats assuming it.
    """
    R = z_j_free / z_j
    return 2 * R / (1 + R)


def free_edge_defl(z_j: float, j: float) -> float:
    """W48 Eq 22 with the load entirely on one side, so z'_e = 0."""
    return z_j / (1 - 0.5 * j)


@dataclass
class EdgeResult:
    j: float
    z_e: float
    kl2_w26: float
    k_w26: float
    l_w26: float
    k_w48: float
    l_w48: float
    sigma_e: float
    sigma_j: float


def backcalculate_edge(P, E, h, mu, a, b, z_j, z_j_free=None, j=None,
                       y=0.0, k_lo=20.0, k_hi=20000.0) -> EdgeResult:
    """Both routes from a measured joint deflection.

    z_j and z_j_free in inches. Pass z_j_free to solve j, or pass j to assume it.
    """
    if j is None:
        if z_j_free is None:
            raise ValueError("give either z_j_free to solve j, or j itself")
        j = j_from_deflections(z_j, z_j_free)

    z_e = free_edge_defl(z_j, j)

    kl2 = kl2_from_edge_defl(P, z_e, mu)
    k26 = k_from_kl2(kl2, E, h, mu)
    l26 = radius_rel_stiffness(E, h, mu, k26)

    lo, hi = k_lo, k_hi
    for _ in range(200):                       # deflection falls with k
        mid = (lo + hi) / 2
        if edge_defl_w48(P, E, h, mu, mid, a, b, y) > z_e:
            lo = mid
        else:
            hi = mid
    k48 = (lo + hi) / 2
    l48 = radius_rel_stiffness(E, h, mu, k48)

    s_e = edge_stress_w48(P, E, h, mu, k48, a, b)
    return EdgeResult(j, z_e, kl2, k26, l26, k48, l48, s_e, (1 - 0.5 * j) * s_e)


# ---------------------------------------------------------------- forward mode

@dataclass
class ForwardResult:
    l: float
    z_e: float          # free-edge deflection, in
    z_j: float          # loaded side at the joint, in
    z_j_free: float     # free side at the joint, in
    sigma_e: float
    sigma_j: float
    sigma_j_free: float
    lte: float          # predicted, percent


def forward(P, E, h, mu, a, b, k, j, y=0.0) -> ForwardResult:
    """Mode A. Assume k and j, predict what the joint should do.

    No measured deflection enters, so comparing the output against the lab
    stays a genuine test rather than a circular one.
    """
    l = radius_rel_stiffness(E, h, mu, k)
    z_e = edge_defl_w48(P, E, h, mu, k, a, b, y)
    s_e = edge_stress_w48(P, E, h, mu, k, a, b)
    return ForwardResult(
        l=l, z_e=z_e,
        z_j=(1 - j / 2) * z_e,              # W48 Eq 22, z'_e = 0
        z_j_free=(j / 2) * z_e,             # W48 Eq 23
        sigma_e=s_e,
        sigma_j=(1 - j / 2) * s_e,          # W48 Eq 20
        sigma_j_free=(j / 2) * s_e,         # W48 Eq 21
        lte=100 * (j / 2) / (1 - j / 2),    # depends on j only, never on k
    )


CAVEATS = [
    "Panel short side over l is about 2.2. Westergaard assumes each panel is "
    "large with the other edges negligible (1948 p.427). Report k as an "
    "equivalent value for this geometry, not a soil property.",
    "Datum is the slab bottom and the value is composite, aggregate plus soil. "
    "Not comparable to a DCP or T307 subgrade value without that label.",
    "Eq 19 assumes j constant over some distance (1948 p.431), so j is approximate.",
    "Case 3 places the load centre at b from the joint; the real plate centre "
    "is at 5.5 in.",
    "Winkler foundation: reaction vertical and proportional to deflection "
    "(1926 p.25). No shear transfer in the foundation.",
    "Uncracked panel assumed (1948 p.427).",
    "No plate load test was run on the pit, so no independently measured k "
    "exists to check any of this against.",
]


def record(mode, primary, secondary=None, j=None, j_source=None,
           derived=None, inputs=None):
    """The shape every method in the app returns.

    datum is the field that stops a subgrade k landing in the same column as a
    composite one.
    """
    return {
        "method": "westergaard_edge_joint",
        "mode": mode,
        "datum": "slab_bottom_composite",
        "primary": primary,
        "secondary": secondary,
        "j": {"value": j, "source": j_source},
        "derived": derived or {},
        "inputs_used": inputs or {},
        "references": ["W26 Eq 1,15,16,18", "W48 Eq 13,14,20,21,22,23"],
        "caveats": CAVEATS,
    }

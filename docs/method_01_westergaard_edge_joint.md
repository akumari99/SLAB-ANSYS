# Method 1 — Westergaard edge and joint

**Status:** approved, ready to implement
**Sections:** 1 (forward prediction) and 2 (inversion for k)
**Depends on:** nothing. Runs on manual input alone.

---

## 1. What it computes

Two modes off the same equations.

**Mode A, forward.** Assume k and j, predict deflection and stress at the joint.
Goes in Section 1 next to ILLI-SLAB and the lab measurement. No lab deflection
enters, so the comparison against measured deflection stays independent.

**Mode B, inversion.** Take the measured deflections on both sides of the joint,
solve j from them, and invert for k. Goes in Section 2.

**Datum for k: bottom of the slab.** Westergaard's k is the reaction pressure per
unit deflection at the slab–foundation interface, so it lumps the aggregate and
the soil together. Tag every result `slab_bottom_composite`. It is not the same
quantity as a DCP subgrade k and the two must never share a column unlabelled.

---

## 2. Inputs

All editable. Defaults are the FAA slab 2 static configuration.

| Field | Default | Unit | Where it comes from |
|---|---|---|---|
| `P` | 16000 | lb | applied load at the static step |
| `E` | 4,100,000 | psi | concrete cylinders |
| `h` | 8.0 | in | measured slab thickness |
| `mu` | 0.15 | — | assumed, per W26 p. 25 |
| `MOR` | 550 | psi | flexural strength |
| `a` | 6.206 | in | ellipse semiaxis parallel to the joint |
| `b` | 6.206 | in | ellipse semiaxis across the joint |
| `y` | 0.0 | in | observation point offset from the joint |
| `k_assumed` | 430 | pci | Mode A only |
| `j_assumed` | 0.90 | — | Mode A; Mode B when `j_mode = assumed` |
| `z_j` | 7.40 | mils | Mode B. Loaded side, `Right_B2` |
| `z_j_free` | 6.28 | mils | Mode B. Free side, `Left_B2` |
| `j_mode` | `measured` | — | Mode B: `measured` or `assumed` |

### Notes on a, b and y

`a` and `b` default to the equal-area circle of the 11 x 11 in steel plate:
r = 11*sqrt(pi)/2 = 6.206 in, area 121.0 in². The inscribed circle (r = 5.5)
used in the original workbook is 95 in², 21 % short.

`y` is the **observation point**, not the load position. W48 Eq 14 gives the
deflection at distance y from the joint along the axis of symmetry. The DCDT sits
at the joint, so y = 0. Case 3 tangency is built in by construction — Eq 11 puts
the ellipse centre at distance b from the joint.

---

## 3. Equations

| Tag | Equation | Source |
|---|---|---|
| W26-1 | l = [E h³ / (12(1−μ²) k)]^¼ | Westergaard 1926, p. 25 |
| W26-15 | z_e = (1/√6)(1 + 0.4μ) P / (k l²) | 1926, p. 33 |
| W26-16 | z_e = 0.433 P / (k l²), at μ = 0.15 | 1926, p. 33 |
| W26-18 | k = 12(1−μ²)(k l²)² / (E h³) | 1926, p. 33 |
| W48-13 | σ_e, Case 3 | Westergaard 1948, p. 429 |
| W48-14 | z_e, Case 3, footprint corrected | 1948, p. 429 |
| W48-20 | σ_j = (1 − j/2) σ_e + (j/2) σ'_e | 1948, p. 431 |
| W48-21 | σ'_j = (j/2) σ_e + (1 − j/2) σ'_e | 1948, p. 431 |
| W48-22 | z_j = (1 − j/2) z_e + (j/2) z'_e | 1948, p. 431 |
| W48-23 | z'_j = (j/2) z_e + (1 − j/2) z'_e | 1948, p. 431 |

Written out, the two that carry the work:

```
W48-14   z_e = P sqrt(2 + 1.2 mu) / sqrt(E h^3 k)
               * [1 - (0.76 + 0.4 mu) b/l]
               * [1 - (0.76 + 0.4 mu) y/l]

W48-13   sigma_e = 2.2 (1+mu) P / ((3+mu) h^2) * log10( E h^3 / (100 k ((a+b)/2)^4) )
                 + 3 (1+mu) P / (pi (3+mu) h^2)
                   * [ 1.84 - 4 mu/3 + (1+mu)(a-b)/(a+b)
                       + 2 (1-mu) a b/(a+b)^2 + 1.18 (1+2 mu) b/l ]
```

### Why Case 3 equations apply to a doweled joint

There is no Case 6 deflection formula. Case 6 supplies only the superposition
rules, Eqs 19 to 23, which convert between the joint deflection you measure and
the free-edge deflection a jointless slab would have. Both k routes then invert
that free-edge value, and both W26-16 and W48-14 are Case 3 equations. The dowels
enter once, through j, at the Eq 22 step. Everything downstream of that point is
operating on a Case 3 quantity by construction.

### Solving j instead of assuming it

With the load entirely on one panel, z'_e = 0. Dividing Eq 23 by Eq 22 then
cancels z_e:

```
R = z'_j / z_j        j = 2R / (1 + R)
```

Mode A must not use this — predicting the measured deflections from a j derived
from those same deflections is circular. Mode A assumes j; the measured value is
reported alongside as an independent check.

---

## 4. Step sequence

### Mode A, forward

```
1  l   = (E h^3 / (12 (1 - mu^2) k_assumed))^0.25            W26-1
2  z_e = W48-14 at k_assumed
3  s_e = W48-13 at k_assumed
4  j   = j_assumed
5  z_j   = (1 - j/2) z_e        z_j_free  = (j/2) z_e        W48-22, 23
6  s_j   = (1 - j/2) s_e        s_j_free  = (j/2) s_e        W48-20, 21
7  LTE_predicted = z_j_free / z_j = (j/2)/(1 - j/2)
8  return all of the above plus s_j / MOR
```

`LTE_predicted` depends only on j, never on k. It is therefore a clean
independent check on the joint alone.

### Mode B, inversion

```
1  if j_mode == "measured":  R = z_j_free / z_j ;  j = 2R/(1+R)
   else:                     j = j_assumed
2  z_e = z_j / (1 - j/2)                                     W48-22, z'_e = 0
3  route W26:  kl2 = (1/sqrt(6))(1 + 0.4 mu) P / z_e         W26-15
               k26 = 12 (1 - mu^2) kl2^2 / (E h^3)           W26-18
4  route W48:  bisect k in [20, 20000] pci until W48-14 returns z_e
               (iterative: b/l and y/l both depend on k)
5  s_e = W48-13 at k48 ;  s_j = (1 - j/2) s_e                W48-13, 20
6  return both k. primary = k48. never average them.
```

Bisection is safe because z_e falls monotonically with k over the whole bracket.
Converge to 1e-6 relative or 300 iterations.

---

## 5. Return record

Every method in the app returns this shape. It is what makes the Section 2
comparison table honest.

```python
{
  "method": "westergaard_edge_joint",
  "mode": "forward" | "inverse",
  "datum": "slab_bottom_composite",
  "primary": {"k_pci": 829.0, "route": "W48_Eq14"},
  "secondary": {"k_pci": 1431.4, "route": "W26_Eq16_Eq18"},
  "j": {"value": 0.9181, "source": "measured"},
  "derived": {"z_e_mils": 13.68, "l_in": 21.555, "kl2": 506132,
              "sigma_e_psi": 465.9, "sigma_j_psi": 252.0,
              "stress_ratio": 0.458},
  "inputs_used": {...},
  "references": ["W26 Eq 1,15,16,18", "W48 Eq 13,14,20,22,23"],
  "caveats": [...]
}
```

---

## 6. Caveats attached to every result

1. **Panel size.** Short side / l = 2.23. Westergaard assumes each panel is large
   with the other edges far enough away to have negligible influence (1948,
   p. 427). That does not hold here. Report k as an equivalent value for this
   geometry, not as a soil property.
2. **Datum.** Composite, at the slab bottom. Not comparable to a DCP or T307
   subgrade value without that label. Westergaard's own reply (1948, p. 444)
   states k depends on the subgrade, the pavement, and the position of the load
   together, and that an edge k may exceed an interior k by a factor of one to two.
3. **j is approximate.** Eq 19 assumes j constant over some distance (1948, p. 431).
4. **Footprint idealisation.** Case 3 places the load centre at b = 6.206 in from
   the joint. The real plate centre is at 5.5 in.
5. **Winkler.** Subgrade reaction vertical and proportional to deflection
   (1926, p. 25). No shear transfer in the foundation.
6. **Uncracked panel** assumed (1948, p. 427). Revisit past the cracking cycle count.
7. **No independent k exists.** No plate load test was run on the pit, so every k
   in Section 2 is an inference, not a measurement against a reference.

---

## 7. Worked example — FAA slab 2, 15.86 kip static

Inputs as the defaults in §2.

### Mode A, k = 430 pci, j = 0.90

| Quantity | Value |
|---|---|
| l | 25.399 in |
| z_e | 19.883 mils |
| z_j predicted | 10.936 mils |
| z_j_free predicted | 8.947 mils |
| LTE predicted | 81.82 % |
| σ_e | 517.3 psi |
| σ_j | 284.5 psi |
| σ_j / MOR | 0.517 |

Against measured z_j = 7.40 mils, Mode A over-predicts by **+48 %**. Measured
LTE 84.9 % against predicted 81.8 %, a 3.1 point gap. The pit is stiffer than the
assumed 430 pci, which Section 2 confirms independently.

### Mode B, measured j

| Quantity | Value |
|---|---|
| R | 0.848649 |
| j measured | 0.918129 |
| z_e | 13.680 mils |
| k l² | 506,132 lb/in |
| k, W26 Eq 16+18 | 1431.4 pci, l = 18.804 in |
| **k, W48 Eq 14 (primary)** | **829.0 pci, l = 21.555 in** |
| σ_e | 465.9 psi |
| σ_j | 252.0 psi |
| σ_j / MOR | 0.458 |
| b / l | 0.288 |

The 1431 against 829 gap is the footprint correction. b/l = 0.288 makes the
Eq 14 bracket 0.764, so Eq 16 treating a 121 in² plate as a point load inflates k
by about 70 %.

---

## 8. Acceptance tests

```
test_reproduces_workbook
    j = 0.90 assumed, a = b = 5.5, W26 route  ->  k = 1482 pci  (+/- 0.5 %)
    confirms the implementation matches the original Excel before the changes

test_j_solved_from_both_sides
    z_j = 7.40, z_j_free = 6.28  ->  j = 0.9181  (+/- 1e-4)

test_mode_b_primary
    defaults, j measured  ->  k48 = 829.0 pci  (+/- 0.5 %)
                              k26 = 1431.4 pci (+/- 0.5 %)

test_mode_a_forward
    k = 430, j = 0.90  ->  z_j = 10.936 mils, LTE = 81.82 %,
                           sigma_j = 284.5 psi   (all +/- 0.5 %)

test_lte_independent_of_k
    LTE predicted must be identical at k = 100 and k = 2000

test_radius_against_westergaard_table_1
    E = 3e6, mu = 0.15, h = 8, k = 100  ->  l = 33.83 in  (W26 Table 1, p. 26)

test_round_trip
    Mode A at k, then Mode B on its own z_j with the same j, recovers k
```

---

## 9. Changes from the original workbook

| | Workbook | This spec |
|---|---|---|
| j | assumed 0.90 | measured 0.918 (Mode B), assumed (Mode A) |
| a = b | 5.5 in, 95 in² | 6.206 in, 121 in² |
| Final inversion | W26 Eq 16 | W48 Eq 14 primary, Eq 16 secondary |
| E | 410,000 psi in the cell | 4,100,000 psi |
| k reported | 1482 pci | 829 pci primary, 1431 secondary |

The E value in the workbook cell was short by a factor of ten and gave
k = 14,816 pci. Corrected to 4.1e6 it gives 1482, which is the figure this spec
reproduces in `test_reproduces_workbook`.

---

## 10. Out of scope

- **Cyclic data.** Mode B needs deflection on both sides of the joint at the load.
  The cyclic configuration has no LVDT on the loaded side at B2, and the actuator
  head was not recorded. Method 1 runs on static configurations only.
- **Corner and interior cases.** Separate methods, separate specs.
- **Curling and temperature.** Not in Westergaard's formulation (1926, p. 35 lists
  it as excluded). The measured corner deflections suggest built-in curl is
  present and material.

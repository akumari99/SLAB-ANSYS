# Slab Pit

Analysis front end for the FAA slab 2 fatigue test: Westergaard edge and joint,
subgrade stiffness backcalculation, Newmark and Boussinesq stress, DCP, and a
side by side comparison against ILLI-SLAB and FAARFIELD.

One self contained HTML file. No build step, no dependencies to install.

## Run it

    python3 -m http.server 8000

then open <http://localhost:8000> in Chrome.

Opening `index.html` straight from the file manager also works, but Chrome is
fussier about storage and about loading the spreadsheet reader from a
`file://` page, so the local server is the safer habit.

## Where the data lives

| How you opened it | Where your inputs are saved |
|---|---|
| local server or `file://` | that browser's local storage, that machine only |
| the claude.ai artifact link | the artifact store, follows your account |
| GitHub Pages | that browser's local storage, per visitor |

These do not sync. Save / export writes a JSON file that moves between them.

## Publishing

Push this folder to a GitHub repo with the file named `index.html`, then turn on
Pages in Settings → Pages → Deploy from a branch → main → / (root).

## Structure

Everything is in `index.html`:

- design tokens and CSS in the `<style>` block
- page markup, one `<section class="page">` per left nav item
- the script at the bottom, in labelled blocks:
  `state` → `persistence` → `chart` → `physics` → `nav` → per page renderers
  → `Westergaard 1926/1948` → `Newmark` → `DCP` → `master render` → `boot`

`renderAll()` redraws every panel. Anything that changes state calls it.

## Conventions worth keeping

- deflections in mils in the UI, converted to inches inside the physics
- pressure in psi, stress in psi, k in pci, moduli in psi
- `S` is the whole application state and is what gets exported to JSON
- `LASTK.*` collects one k per method for the summary table
- every equation carries its source in a `<details>` block next to it

## Sources

- Westergaard, H. M., "Stresses in Concrete Pavements Computed by Theoretical
  Analysis," Public Roads 7(2), 1926, pp. 25–35. Eqs 1, 13–18.
- Westergaard, H. M., "New Formulas for Stresses in Concrete Pavements of
  Airfields," ASCE Transactions 113, 1948, Paper 2340, pp. 425–444.
  Cases 3 and 6, Eqs 12–14 and 19–23.
- Newmark, N. M., "Influence Charts for Computation of Stresses in Elastic
  Foundations," Univ. of Illinois EES Bulletin 338, 1942.
- ASTM D6951/D6951M-18, DCP in shallow pavement applications.
- FAA AC 150/5320-6G and AC 150/5370-11B.
- AASHTO Guide for Design of Pavement Structures, 1993, Part III.

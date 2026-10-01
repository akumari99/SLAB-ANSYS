# Slab Pit

Analysis tooling for the FAA slab 2 fatigue test. Westergaard forward and
inverse, ILLI-SLAB output, DCP, consolidation, and the cross-checks between
measured pressure and modelled stress.

Runs locally. Nothing is published and no data leaves the machine.

---

## Install

Fifteen minutes, once per computer.

### 1. Software

| What | Where |
|---|---|
| Python 3.12 | <https://python.org/downloads> |
| VS Code | <https://code.visualstudio.com> |
| Git | <https://git-scm.com/download/win> |

When the Python installer opens, **tick "Add python.exe to PATH"** on the first
screen. Easy to miss, and nothing works without it.

Check both installed. Open VS Code, press `Ctrl` + `` ` `` for a terminal:

    python --version
    git --version

### 2. Clone

Keep the repo out of OneDrive. OneDrive syncs the hidden `.git` folder and
corrupts it, and GitHub is already the backup.

    mkdir C:\dev
    cd C:\dev
    git clone https://github.com/akumari99/SLAB-ANSYS.git
    cd SLAB-ANSYS

Then File → Open Folder → `C:\dev\SLAB-ANSYS`. If a banner mentions Restricted
Mode, click Manage → Trust.

### 3. Environment

    cd python
    python -m venv .venv
    .venv\Scripts\activate

The prompt should now start with `(.venv)`. If PowerShell refuses with an
execution policy error, run this once and try again:

    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

### 4. Dependencies

    pip install -r requirements.txt

Two or three minutes. numpy, pandas, scipy, pyarrow, streamlit, pytest.

### 5. Check it

    python -m pytest tests -q

Expect `12 passed, 1 skipped`. The skip is an ILLI-SLAB fixture that only runs
if a sample `.out` is sitting in `tests/data/`, which is optional.

If anything **fails**, stop and read which test. They are pinned to measured
numbers, so a failure means a formula is wrong, not that the setup is off.

### 6. Run

    streamlit run app.py

Opens at <http://localhost:8501>. To stop it, click the terminal and press
`Ctrl` and `C` together.

Every session after this one is just:

    cd C:\dev\SLAB-ANSYS\python
    .venv\Scripts\activate
    streamlit run app.py

---

## Using it

Pick a section in the left sidebar. The sidebar also lists what is built and
what is still waiting on a spec, so you can see the gaps.

### Section 1 — pavement response

Westergaard forward. Put in an assumed k and an assumed j, get back the
predicted deflection each side of the joint, the stresses, and the predicted
load transfer.

Nothing measured goes in, which is the point: comparing the output against the
lab is then a real test rather than a circular one. Expand *Compare against a
measurement* to type your measured deflections and see the error.

Predicted LTE depends on j alone and never moves with k, so it is an
independent check on the joint by itself.

### Section 2 — stiffness and modulus

Westergaard inversion. Put in the measured deflection on both sides of the
joint and it solves j from them, then returns k two ways:

- **W48 Eq 14** is the primary. It corrects for the size of the loaded area.
- **W26 Eq 16** is the legacy check. It treats the load as a point at the edge,
  which for a 121 in² plate reads roughly 70 % high.

Both are shown. They are never averaged. Open *Caveats that travel with this
number* before quoting either one — in particular, this k sits at the bottom of
the slab and lumps aggregate and soil together, so it is not the same quantity
as a DCP or T307 subgrade value.

### ILLI-SLAB results

At the bottom of any section. Drag `.out` files onto the uploader.

**One file** gives you the run summary and deflection at all twelve DCDT
locations. There is an editable column for your measured values, which fills in
a model-over-lab ratio per sensor.

**Several files** gives you a k sweep: deflection at every sensor against k, as
a table, a chart and a CSV. That table is the response surface — fit a measured
basin against it and you have a finite element backcalculation without rerunning
the Fortran.

k is always recovered from subgrade stress ÷ deflection. The title line in these
files is frequently stale — the sample run is headed `WINKLER K=200` and is in
fact k = 580 on a two slab doweled model — so it is ignored. The app also checks
that reactions balance the applied load and warns if a run did not converge.

### Where to keep data

Raw files stay out of the repo. GitHub rejects anything over 100 MB and the
history would bloat permanently.

    C:\Users\<you>\OneDrive\SlabPit-Data\
        illislab\     *.out
        faarfield\    *.pdf
        static\       *.csv  *.xlsx
        cyclic\       *.csv

OneDrive is fine for the data. It is only the repo that must stay out of it.

---

## Editing

    cd python
    .venv\Scripts\activate
    streamlit run app.py

Streamlit reloads when you save, so edit and watch the browser.

After any change to a formula:

    python -m pytest tests -q

Then commit. Source Control panel in VS Code, write a real message, Commit,
Sync Changes. Commit after every working change, not at the end of the day — if
a number moves you want to land on the one commit that moved it.

On a second computer: clone once, then `git pull` before you start and push when
you finish.

---

## How a method gets added

Spec first, in `docs/`. Inputs with units and provenance, equations with page
references, the step sequence, the caveats, and acceptance tests. Approve the
spec, then write the code, then make the tests pass. Not the other way round.

Every method returns the same record:

    {"method": ..., "mode": ..., "datum": ...,
     "primary": {...}, "secondary": {...},
     "j": {"value": ..., "source": ...},
     "derived": {...}, "inputs_used": {...},
     "references": [...], "caveats": [...]}

`datum` is the field that matters. It is what stops a subgrade k landing in the
same column as a composite one.

---

## Layout

    python/app.py              Streamlit UI. No physics lives here.
    python/slabkit/
      westergaard.py           W26 Eq 1,15,16,18 and W48 Eq 13,14,20-23
      illislab.py              .out reader, accepts a path or an upload
      dcp.py                   ASTM D6951, FAA and AASHTO k routes
      daq.py                   raw DAQ to cycle peaks to decimated
      export.py                JSON and Parquet writers
    python/build_data.py       batch runner for bulk files
    python/tests/              pinned to measured numbers from the workbooks
    python/.streamlit/         upload limit raised to 1 GB
    docs/                      one spec per method, approved before coding
    _archive/                  the old browser app. Not maintained, and three
                               of its methods are wrong. Do not copy from it.

`slabkit/westergaard.py` touches no files at all — numbers in, numbers out. That
is deliberate. It means the tests can check it directly and it cannot break
because a file format changed.

---

## What the tests pin

- k = 1482 pci from the original Excel chain, so the port can be checked against
  the spreadsheet it replaced
- j = 0.918 solved from the two joint deflections
- k = 829 pci (Eq 14) and 1431 pci (Eq 16) from the 15.86 kip static step
- the DCP chain against three rows of the workbook
- Newmark influence factors against the Vertical Stresses sheet
- ℓ = 33.83 in against Westergaard 1926 Table 1
- a round trip: predict a deflection at a known k, invert it, recover k

---

## Sources

- Westergaard, H. M. "Stresses in Concrete Pavements Computed by Theoretical
  Analysis." *Public Roads* 7(2), 1926, pp. 25–35. Eqs 1, 13–18.
- Westergaard, H. M. "New Formulas for Stresses in Concrete Pavements of
  Airfields." *ASCE Transactions* 113, 1948, Paper 2340, pp. 425–444.
  Cases 3 and 6, Eqs 12–14, 19–23.
- Newmark, N. M. "Influence Charts for Computation of Stresses in Elastic
  Foundations." Univ. of Illinois EES Bulletin 338, 1942.
- ASTM D6951/D6951M-18, dynamic cone penetrometer.
- FAA AC 150/5320-6G and AC 150/5370-11B.
- AASHTO Guide for Design of Pavement Structures, 1993, Part III.

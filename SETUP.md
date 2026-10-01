# Setup

One-time, about fifteen minutes. Repeat on each laptop.

## 1. Clone

Keep the repo **out of OneDrive**. OneDrive syncs the hidden `.git` folder and
corrupts it. GitHub is already the backup.

    cd C:\dev
    git clone https://github.com/akumari99/SLAB-ANSYS.git
    cd SLAB-ANSYS

## 2. Python environment

    cd python
    python -m venv .venv
    .venv\Scripts\activate          # Windows
    pip install -r requirements.txt

## 3. Check the install

    python -m pytest tests/ -q

Thirteen tests. They pin the code to numbers from your own workbooks — k = 1482
from the original Excel chain, j = 0.918 from the two joint deflections, the DCP
chain against three rows, the Newmark factors against your Vertical Stresses
sheet, and the ILLI-SLAB reader against the sample .out. If any fail, stop and
read which one.

## 4. Run

    streamlit run app.py

Opens at <http://localhost:8501>. Ctrl+C in the terminal to stop.

## 5. Point it at your data

Keep raw files outside the repo, in OneDrive if you want them synced:

    C:\Users\<you>\OneDrive\SlabPit-Data\
        illislab\     *.out
        faarfield\    *.pdf
        static\       *.csv  *.xlsx
        cyclic\       *.csv

Set that path in the app sidebar. `raw/` is gitignored, and GitHub rejects files
over 100 MB anyway, so nothing large ever enters the repo.

## Editing

Claude Code in VS Code, or type directly. After any change to a formula:

    python -m pytest tests/ -q

then commit. Source Control panel, write a real message, Commit, Sync.

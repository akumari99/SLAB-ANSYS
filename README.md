# Slab Pit

Local analysis tooling for the FAA slab 2 fatigue test: Westergaard forward and
inverse, ILLI-SLAB output, DCP, consolidation, and the cross-checks between
measured pressure and modelled stress.

Runs on your own machine. Nothing is published and nothing is uploaded.

    cd python && streamlit run app.py

See `SETUP.md` to install, `docs/` for the method specifications.

## Layout

    python/app.py            Streamlit UI
    python/slabkit/          the analysis
      westergaard.py         W26 Eq 1,15,16,18 and W48 Eq 13,14,20-23
      illislab.py            .out reader, nodes to DataFrame or Parquet
      dcp.py                 ASTM D6951, FAA and AASHTO k routes
      daq.py                 raw DAQ to cycle peaks to decimated
      export.py              JSON writers
    python/tests/            pins the code to your own measured numbers
    docs/                    one spec per method, approved before coding
    _archive/                the old browser app, not maintained

## How a method gets added

Spec first, in `docs/`, with inputs, equations and page references, step
sequence, caveats and acceptance tests. Approve it, then write the code, then
make the tests pass. Not the other way round.

Every method returns the same record: value, datum, j source, inputs used,
references, caveats. The `datum` field is what keeps a subgrade k out of the
same column as a composite one.

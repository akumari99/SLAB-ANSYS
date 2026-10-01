# Archive

`legacy_browser_app.html` is the original JavaScript app that ran on GitHub
Pages. Kept for reference, not maintained. Do not copy formulas out of it
without checking them against `docs/`.

Known wrong in that file:

- strain inversion for k assumed gauges on the slab bottom. They are on the
  dowels at mid-depth, which is the slab's neutral axis.
- ellipse semiaxes were 5.5 in, the inscribed circle of the 11 x 11 plate,
  which is 95 in² against the real 121 in².
- the edge inversion used W26 Eq 16 with no footprint correction, reading
  roughly 70 % high.

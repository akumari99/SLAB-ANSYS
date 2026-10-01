"""Slab Pit analysis kit.

Python side of the FAA slab 2 tooling. Handles the parts a browser cannot:
large DAQ files, the ILLI-SLAB Fortran sweep, and anything that needs scipy.

Outputs land in ../web/data as small JSON the page reads directly.
"""
__all__ = ["westergaard", "dcp", "daq", "export"]

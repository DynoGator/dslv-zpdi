"""SPEC-022 — C2 command adapter implementations.

Each adapter translates a typed C2 capability into a bounded interaction
with the local system.  No arbitrary shell execution occurs here.
"""

from .hdf5_query import Hdf5Adapter
from .pipeline import PipelineAdapter
from .sdr import SdrAdapter

__all__ = ["PipelineAdapter", "SdrAdapter", "Hdf5Adapter"]

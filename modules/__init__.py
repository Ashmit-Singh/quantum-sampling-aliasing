"""Quantum-Enhanced Sampling & Aliasing — DSP backend.

Public API:
    SampledSignal   — pipeline result container
    Waveform        — waveform type enum
    RMSEQuality     — reconstruction quality tier
    classify_rmse   — RMSE → quality classifier
    process_signal  — full pipeline entry point
"""

from .models import RMSEQuality, SampledSignal, Waveform, classify_rmse
from .pipeline import process_signal

__all__ = [
    "SampledSignal",
    "Waveform",
    "RMSEQuality",
    "classify_rmse",
    "process_signal",
]

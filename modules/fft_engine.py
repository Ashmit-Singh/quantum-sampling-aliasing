"""Robust FFT analysis engine.

Computes the one-sided amplitude spectrum of a discrete signal and
identifies the dominant spectral component.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
from numpy.typing import NDArray


def compute_fft(
    x_samples: NDArray[np.float64],
    fs: float,
) -> Tuple[NDArray[np.float64], NDArray[np.float64], float]:
    """Compute the one-sided amplitude spectrum via real FFT.

    Uses ``numpy.fft.rfft`` with 2/N magnitude normalization (single-sided).
    The DC component is normalized by 1/N.

    Args:
        x_samples: Discrete sample amplitudes (≥ 2 samples required).
        fs: Sampling frequency in Hz.

    Returns:
        (freqs, magnitude, dominant_freq):
            freqs — frequency bins in Hz.
            magnitude — normalized amplitude at each bin.
            dominant_freq — frequency of the largest spectral peak.

    Raises:
        ValueError: If fewer than 2 samples are provided or fs ≤ 0.
    """
    if x_samples.size < 2:
        raise ValueError(
            f"FFT requires at least 2 samples, got {x_samples.size}"
        )
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError(f"Sampling rate must be positive and finite, got {fs}")

    n = x_samples.size
    spectrum = np.fft.rfft(x_samples)
    magnitude = np.abs(spectrum) * (2.0 / n)
    # DC component should only be scaled by 1/N
    magnitude[0] *= 0.5

    freqs = np.fft.rfftfreq(n, d=1.0 / fs).astype(np.float64)

    # Dominant frequency: largest magnitude (skip DC for tonal signals)
    if magnitude.size > 1:
        search_mag = magnitude[1:]
        dominant_idx = int(np.argmax(search_mag)) + 1
    else:
        dominant_idx = 0
    dominant_freq = float(freqs[dominant_idx])

    return freqs, magnitude, dominant_freq

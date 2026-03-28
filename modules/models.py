"""Strongly-typed data contracts for the DSP pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from numpy.typing import NDArray


class Waveform(Enum):
    """Supported waveform types."""
    SINE = "sine"
    SQUARE = "square"
    TRIANGLE = "triangle"


class RMSEQuality(Enum):
    """Reconstruction quality classification."""
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"


def classify_rmse(rmse: float) -> RMSEQuality:
    """Classify reconstruction quality by RMSE threshold.

    Thresholds:
        < 0.01  → GOOD
        < 0.1   → MODERATE
        ≥ 0.1   → POOR
    """
    if rmse < 0.01:
        return RMSEQuality.GOOD
    if rmse < 0.1:
        return RMSEQuality.MODERATE
    return RMSEQuality.POOR


@dataclass(slots=True, frozen=True)
class SampledSignal:
    """Immutable result container for the full DSP pipeline.

    Groups continuous-domain, sampled-domain, frequency-domain,
    and reconstruction outputs into a single strongly-typed record.
    """

    # Continuous domain
    t_cont: NDArray[np.float64]
    x_cont: NDArray[np.float64]

    # Sampled domain
    t_samples: NDArray[np.float64]
    x_samples: NDArray[np.float64]

    # Metadata
    fs: float
    f_signal: float
    aliased_freq: float
    nyquist_satisfied: bool

    # Frequency domain
    fft_freqs: NDArray[np.float64]
    fft_magnitude: NDArray[np.float64]
    dominant_freq: float

    # Reconstruction
    x_reconstructed: NDArray[np.float64]
    rmse: float

    @property
    def reconstruction_quality(self) -> RMSEQuality:
        """Classify reconstruction quality."""
        return classify_rmse(self.rmse)

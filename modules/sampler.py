"""Interpolation-based discrete-time sampling engine.

Samples a continuous-domain signal by interpolating at exact sample
instants rather than slicing the pre-computed array.  This preserves
correctness when the continuous resolution is not an integer multiple
of the sampling rate.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
from numpy.typing import NDArray


def _validate_params(fs: float, duration: float) -> None:
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError(f"Sampling rate must be positive and finite, got {fs}")
    if not np.isfinite(duration) or duration <= 0:
        raise ValueError(f"Duration must be positive and finite, got {duration}")


def sample_signal(
    t_cont: NDArray[np.float64],
    x_cont: NDArray[np.float64],
    fs: float,
    duration: float,
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Sample a continuous signal via linear interpolation.

    Constructs a uniform sample grid at rate *fs* over [0, duration]
    and evaluates the continuous signal at those instants using
    ``numpy.interp``.

    Args:
        t_cont: Continuous-domain time axis (monotonically increasing).
        x_cont: Continuous-domain amplitude values.
        fs: Desired sampling frequency in Hz.
        duration: Total signal duration in seconds.

    Returns:
        (t_samples, x_samples) — sample instants and interpolated values.

    Raises:
        ValueError: On non-positive or non-finite parameters.
    """
    _validate_params(fs, duration)

    n_samples = int(np.floor(fs * duration)) + 1
    # Guard: at least one sample
    n_samples = max(n_samples, 1)

    t_samples = np.linspace(0.0, (n_samples - 1) / fs, n_samples, dtype=np.float64)
    # Clamp to continuous domain to avoid extrapolation artifacts
    t_samples = np.clip(t_samples, t_cont[0], t_cont[-1])
    x_samples = np.interp(t_samples, t_cont, x_cont).astype(np.float64)

    return t_samples, x_samples

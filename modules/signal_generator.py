"""High-resolution continuous-time signal synthesis engine.

Generates densely-sampled waveforms suitable for interpolation-based
sampling and Whittaker–Shannon reconstruction benchmarks.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
from numpy.typing import NDArray
from scipy import signal as scipy_signal

from .models import Waveform

# Minimum continuous-domain resolution (samples per second)
_MIN_RESOLUTION: int = 10_000
# Resolution multiplier relative to signal frequency
_FREQ_MULTIPLIER: int = 100


def _validate_params(f: float, duration: float) -> None:
    """Raise ValueError on invalid generation parameters."""
    if not np.isfinite(f) or f <= 0:
        raise ValueError(f"Signal frequency must be positive and finite, got {f}")
    if not np.isfinite(duration) or duration <= 0:
        raise ValueError(f"Duration must be positive and finite, got {duration}")


def _compute_resolution(f: float, resolution: int | None) -> int:
    """Determine continuous-domain sample rate.

    Uses the greater of the explicit resolution, the minimum floor,
    or a frequency-adaptive multiplier to ensure adequate representation
    of the waveform.
    """
    adaptive = int(_FREQ_MULTIPLIER * f)
    base = max(_MIN_RESOLUTION, adaptive)
    if resolution is not None:
        if resolution <= 0:
            raise ValueError(f"Resolution must be positive, got {resolution}")
        return max(resolution, base)
    return base


def _generate_waveform(
    phase_vec: NDArray[np.float64],
    waveform: Waveform,
) -> NDArray[np.float64]:
    """Dispatch waveform generation by type.

    Args:
        phase_vec: Instantaneous phase array (radians).
        waveform: Target waveform shape.

    Returns:
        Signal amplitude array.
    """
    if waveform is Waveform.SINE:
        return np.sin(phase_vec)
    if waveform is Waveform.SQUARE:
        return scipy_signal.square(phase_vec).astype(np.float64)
    if waveform is Waveform.TRIANGLE:
        # sawtooth with width=0.5 produces symmetric triangle
        return scipy_signal.sawtooth(phase_vec, width=0.5).astype(np.float64)
    raise ValueError(f"Unsupported waveform type: {waveform}")


def generate_continuous_signal(
    f: float,
    duration: float,
    waveform: Waveform = Waveform.SINE,
    phase: float = 0.0,
    resolution: int | None = None,
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Synthesize a high-resolution continuous-time signal.

    Args:
        f: Signal frequency in Hz.
        duration: Signal duration in seconds.
        waveform: Waveform shape (sine, square, triangle).
        phase: Initial phase offset in radians.
        resolution: Override for continuous-domain sample rate.
            Clamped to at least max(10000, 100·f).

    Returns:
        (t_cont, x_cont) — time axis and amplitude arrays.

    Raises:
        ValueError: On non-positive or non-finite parameters.
    """
    _validate_params(f, duration)
    res = _compute_resolution(f, resolution)
    n_samples = int(np.ceil(res * duration)) + 1
    t = np.linspace(0.0, duration, n_samples, dtype=np.float64)
    phase_vec = 2.0 * np.pi * f * t + phase
    x = _generate_waveform(phase_vec, waveform)
    return t, x

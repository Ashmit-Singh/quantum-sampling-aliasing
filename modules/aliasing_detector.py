"""Analytically correct aliasing detection.

Computes the apparent (aliased) frequency observed when a signal of
frequency *f* is sampled at rate *fs*, using the standard folding formula.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

# Relative tolerance for borderline Nyquist comparison (fs ≈ 2f)
_NYQUIST_REL_EPS: float = 1e-9


def compute_alias_frequency(
    f_signal: float,
    fs: float,
) -> Tuple[float, bool]:
    """Compute the aliased frequency and Nyquist satisfaction flag.

    Uses the folding formula::

        f_alias = |f_signal − round(f_signal / fs) · fs|

    Numerical stability: when *fs* is very close to 2·f_signal the
    Nyquist flag is determined with a relative tolerance of 1e-9.

    Args:
        f_signal: True signal frequency in Hz (must be > 0).
        fs: Sampling frequency in Hz (must be > 0).

    Returns:
        (aliased_freq, nyquist_satisfied):
            aliased_freq — the observed frequency after sampling.
            nyquist_satisfied — True iff fs > 2·f_signal (within tolerance).

    Raises:
        ValueError: On non-positive or non-finite inputs.
    """
    if not np.isfinite(f_signal) or f_signal <= 0:
        raise ValueError(f"Signal frequency must be positive and finite, got {f_signal}")
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError(f"Sampling rate must be positive and finite, got {fs}")

    f_alias = float(np.abs(f_signal - np.round(f_signal / fs) * fs))

    nyquist_limit = 2.0 * f_signal
    nyquist_satisfied = bool(fs > nyquist_limit * (1.0 - _NYQUIST_REL_EPS))

    return f_alias, nyquist_satisfied

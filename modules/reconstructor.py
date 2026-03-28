"""Whittaker–Shannon sinc-interpolation reconstruction engine.

Reconstructs a continuous-time signal from its discrete samples using
the ideal interpolation formula, with optional Hann windowing to
suppress Gibbs-phenomenon ringing.

Memory-safe: large reconstructions are chunked to avoid allocating
huge intermediate matrices.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
from numpy.typing import NDArray

# Maximum rows per chunk in the sinc matrix (controls peak memory)
_DEFAULT_CHUNK_SIZE: int = 4096


def _sinc_matrix_chunked(
    t_cont: NDArray[np.float64],
    t_samples: NDArray[np.float64],
    fs: float,
    x_samples: NDArray[np.float64],
    apply_window: bool,
    chunk_size: int,
) -> NDArray[np.float64]:
    """Compute sinc-interpolation output in memory-safe chunks.

    For each chunk of *t_cont*, builds the (chunk, N_samples) sinc
    matrix, optionally applies a Hann window, and contracts against
    *x_samples* via matrix–vector product.
    """
    n_cont = t_cont.shape[0]
    n_samp = t_samples.shape[0]
    out = np.empty(n_cont, dtype=np.float64)

    # Pre-compute sample indices [0, 1, ..., N-1]
    indices = np.arange(n_samp, dtype=np.float64)

    # Optional Hann window applied to the sinc kernel
    if apply_window and n_samp > 1:
        window = np.hanning(n_samp).astype(np.float64)
    else:
        window = None

    for start in range(0, n_cont, chunk_size):
        end = min(start + chunk_size, n_cont)
        # (chunk, 1) - (1, N_samples)  →  (chunk, N_samples)
        arg = fs * t_cont[start:end, np.newaxis] - indices[np.newaxis, :]
        sinc_mat = np.sinc(arg)  # numpy sinc is sin(πx)/(πx)

        if window is not None:
            sinc_mat *= window[np.newaxis, :]

        # (chunk, N_samples) @ (N_samples,) → (chunk,)
        out[start:end] = sinc_mat @ x_samples

    return out


def reconstruct_signal(
    t_cont: NDArray[np.float64],
    t_samples: NDArray[np.float64],
    x_samples: NDArray[np.float64],
    fs: float,
    x_original: NDArray[np.float64],
    apply_window: bool = False,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> Tuple[NDArray[np.float64], float]:
    """Reconstruct a signal via Whittaker–Shannon interpolation.

    Implements::

        x_r(t) = Σ_n  x[n] · sinc(fs · t − n)

    with optional Hann-windowed sinc kernel.

    Args:
        t_cont: Continuous-domain time axis for reconstruction targets.
        t_samples: Discrete sample instants.
        x_samples: Discrete sample amplitudes.
        fs: Sampling frequency in Hz.
        x_original: Ground-truth continuous signal for RMSE computation.
        apply_window: If True, multiply each sinc kernel by a Hann window.
        chunk_size: Number of output points per vectorized chunk.

    Returns:
        (x_reconstructed, rmse):
            x_reconstructed — the reconstructed signal evaluated at *t_cont*.
            rmse — root-mean-square error vs. *x_original*.
    """
    if t_samples.size == 0 or x_samples.size == 0:
        x_reconstructed = np.zeros_like(t_cont)
        rmse = float(np.sqrt(np.mean(x_original ** 2)))
        return x_reconstructed, rmse

    x_reconstructed = _sinc_matrix_chunked(
        t_cont, t_samples, fs, x_samples, apply_window, chunk_size,
    )

    residual = x_original - x_reconstructed
    rmse = float(np.sqrt(np.mean(residual ** 2)))

    return x_reconstructed, rmse

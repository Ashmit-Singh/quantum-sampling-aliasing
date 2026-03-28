"""
qft_encoder — amplitude-encode a sampled signal into an n-qubit state.

The encoder normalises the input signal, pads/truncates it to length 2^n,
and uses Qiskit's ``initialize()`` to prepare the quantum state.

Hard cap: **8 qubits** maximum (256 amplitudes).  Any request above this
raises ``ValueError`` so the Aer simulation stays under ~2 s.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from qiskit import QuantumCircuit

# ── constants ────────────────────────────────────────────────────────
MAX_QUBITS = 8  # hard cap — keeps statevector sim fast


def encode_signal(
    signal: np.ndarray,
    n_qubits: Optional[int] = None,
) -> QuantumCircuit:
    """Amplitude-encode *signal* into an *n_qubits*-qubit quantum state.

    Parameters
    ----------
    signal : np.ndarray
        Real-valued 1-D array of samples.
    n_qubits : int, optional
        Number of qubits to use.  If *None* the smallest ``n`` with
        ``2**n >= len(signal)`` is chosen automatically.

    Returns
    -------
    QuantumCircuit
        A circuit whose initial state encodes the (normalised) signal.

    Raises
    ------
    ValueError
        If *n_qubits* > ``MAX_QUBITS`` (8) or *signal* is empty.
    """
    signal = np.asarray(signal, dtype=float).ravel()

    if signal.size == 0:
        raise ValueError("Signal must contain at least one sample.")

    # ── determine qubit count ────────────────────────────────────────
    if n_qubits is None:
        n_qubits = max(1, math.ceil(math.log2(signal.size)))
        # edge-case: exact power of two → log2 already exact
        if 2**n_qubits < signal.size:
            n_qubits += 1

    if n_qubits > MAX_QUBITS:
        raise ValueError(
            f"Requested {n_qubits} qubits — hard cap is {MAX_QUBITS}. "
            f"Reduce the signal length or explicitly pass n_qubits ≤ {MAX_QUBITS}."
        )

    dim = 2**n_qubits

    # ── pad or truncate to 2^n ───────────────────────────────────────
    if signal.size < dim:
        signal = np.pad(signal, (0, dim - signal.size), mode="constant")
    else:
        signal = signal[:dim]

    # ── L2-normalise (required for valid quantum state) ──────────────
    norm = np.linalg.norm(signal)
    if norm < 1e-12:
        raise ValueError("Signal is near-zero; cannot normalise to a valid quantum state.")
    signal = signal / norm

    # ── build circuit ────────────────────────────────────────────────
    qc = QuantumCircuit(n_qubits, name="signal_encode")
    qc.initialize(signal.tolist())

    return qc

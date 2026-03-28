"""
qft_runner — execute a QFT circuit on Aer's statevector simulator.

Returns the final ``Statevector`` so downstream code can extract
amplitudes, phases, and probabilities without re-running.
"""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


def run_qft(circuit: QuantumCircuit) -> Statevector:
    """Simulate *circuit* and return the output statevector.

    Parameters
    ----------
    circuit : QuantumCircuit
        A fully-composed circuit (encoding + QFT).  Must **not** contain
        measurement gates.

    Returns
    -------
    Statevector
        The final quantum state after simulation.

    Notes
    -----
    Uses ``Statevector.from_instruction`` which is the recommended
    lightweight approach for pure-state simulation in modern Qiskit
    (works without ``qiskit-aer`` being installed, but is Aer-accelerated
    when available).
    """
    # Decompose any high-level library gates so the statevector
    # simulator can handle everything.
    decomposed = circuit.decompose()
    sv = Statevector.from_instruction(decomposed)
    return sv

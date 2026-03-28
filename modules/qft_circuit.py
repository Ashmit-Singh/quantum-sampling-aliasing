"""
qft_circuit — build a QFT circuit on top of an already-encoded quantum state.

Uses ``qiskit.circuit.library.QFTGate`` (Qiskit ≥ 2.1) so we get the
canonical, gate-level decomposition for free.
"""

from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.circuit.library import QFTGate


def build_qft_circuit(encoded_circuit: QuantumCircuit) -> QuantumCircuit:
    """Append a QFT to *encoded_circuit* and return the composed circuit.

    Parameters
    ----------
    encoded_circuit : QuantumCircuit
        A circuit that already prepares the desired initial state
        (e.g. via ``initialize()``).

    Returns
    -------
    QuantumCircuit
        The full circuit: state-preparation ➜ QFT.
        No measurement gates are added (statevector simulation).
    """
    n = encoded_circuit.num_qubits

    # Build the QFT gate (modern Qiskit 2.1+ API)
    qft_gate = QFTGate(num_qubits=n)

    # Compose onto a copy so the caller's circuit stays untouched
    full = encoded_circuit.copy(name="signal_encode+QFT")
    full.append(qft_gate, qargs=range(n))

    return full

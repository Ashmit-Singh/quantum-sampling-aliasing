"""
qft_visualizer — extract frequency-domain data and export a circuit diagram.

Takes the composed circuit + statevector and packages everything into a
``QFTResult`` for the UI / analysis layer.
"""

from __future__ import annotations


from typing import Optional

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qft_result import QFTResult         # noqa: E402


def visualize_qft(
    circuit: QuantumCircuit,
    statevector: Statevector,
) -> QFTResult:
    """Build a ``QFTResult`` from a completed QFT simulation.

    Parameters
    ----------
    circuit : QuantumCircuit
        The full (encode + QFT) circuit to draw.
    statevector : Statevector
        Output statevector from the simulation.

    Returns
    -------
    QFTResult
        Populated result dataclass ready for the UI.
    """
    n_qubits = circuit.num_qubits
    amplitudes_complex = np.array(statevector.data)

    # ── frequency-domain representation ──────────────────────────────
    probabilities = (np.abs(amplitudes_complex) ** 2).tolist()
    phases = np.angle(amplitudes_complex).tolist()

    basis_states = [format(i, f"0{n_qubits}b") for i in range(2**n_qubits)]

    # ── generate text circuit diagram ────────────────────────────────
    text_diagram = str(circuit.draw("text"))

    return QFTResult(
        n_qubits=n_qubits,
        basis_states=basis_states,
        amplitudes=probabilities,
        phases=phases,
        circuit_diagram=text_diagram,
    )


def plot_frequency_spectrum(
    result: QFTResult,
    output_dir: str = ".",
    filename: str = "qft_spectrum.png",
) -> str:
    """Save a bar-chart of the frequency spectrum and return the file path.

    This is an optional convenience — the UI can also render from
    ``result.amplitudes`` directly.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)

    fig, ax = plt.subplots(figsize=(max(6, result.n_qubits * 1.2), 4))
    x = np.arange(len(result.basis_states))
    ax.bar(x, result.amplitudes, color="#6366f1", edgecolor="#4f46e5", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(result.basis_states, rotation=45, ha="right", fontsize=7)
    ax.set_xlabel("Basis state")
    ax.set_ylabel("|amplitude|²")
    ax.set_title("QFT Frequency Spectrum")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)

    return os.path.abspath(path)

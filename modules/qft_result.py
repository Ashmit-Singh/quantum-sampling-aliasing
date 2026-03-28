"""
QFTResult — shared output contract for the QFT pipeline.

Every stage of the pipeline produces or consumes this dataclass so that
downstream consumers (UI, analysis, export) have a stable interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class QFTResult:
    """Container for QFT analysis results.

    Attributes
    ----------
    n_qubits : int
        Number of qubits used in the circuit.
    basis_states : list[str]
        Binary labels for each computational basis state (e.g. ["000", …, "111"]).
    amplitudes : list[float]
        Squared magnitudes (|amplitude|²) per basis state — i.e. probabilities.
    phases : list[float]
        Phase angles (radians) of each complex amplitude.
    circuit_diagram: str
    """

    n_qubits: int
    basis_states: List[str] = field(default_factory=list)
    amplitudes: List[float] = field(default_factory=list)
    phases: List[float] = field(default_factory=list)
    circuit_diagram: str = ""

    # ── convenience helpers ──────────────────────────────────────────

    def dominant_frequencies(self, top_k: int = 3) -> List[tuple]:
        """Return the *top_k* basis states with the highest |amplitude|².

        Returns a list of ``(basis_state, amplitude²)`` tuples sorted
        descending by amplitude.
        """
        paired = list(zip(self.basis_states, self.amplitudes))
        paired.sort(key=lambda x: x[1], reverse=True)
        return paired[:top_k]

    def as_dict(self) -> dict:
        """Serialise to a plain dictionary (handy for JSON export)."""
        return {
            "n_qubits": self.n_qubits,
            "basis_states": self.basis_states,
            "amplitudes": self.amplitudes,
            "phases": self.phases,
            "circuit_diagram": self.circuit_diagram,
        }

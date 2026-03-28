"""
Integration test for the full QFT pipeline.

    encode_signal → build_qft_circuit → run_qft → visualize_qft

Run with:  python -m pytest test_qft_pipeline.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile

import numpy as np
import pytest

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(__file__))

from qft_encoder import encode_signal, MAX_QUBITS
from qft_circuit import build_qft_circuit
from qft_runner import run_qft
from qft_visualizer import visualize_qft, plot_frequency_spectrum
from qft_result import QFTResult


# ── helpers ──────────────────────────────────────────────────────────

def _sine_signal(freq: float = 2.0, n_samples: int = 16) -> np.ndarray:
    """Simple sine wave used as a reproducible test signal."""
    t = np.linspace(0, 1, n_samples, endpoint=False)
    return np.sin(2 * np.pi * freq * t)


# ── tests ────────────────────────────────────────────────────────────

class TestFullPipeline:
    """End-to-end smoke test."""

    def test_pipeline_returns_qft_result(self):
        signal = _sine_signal(freq=2.0, n_samples=16)

        with tempfile.TemporaryDirectory() as tmpdir:
            encoded = encode_signal(signal)
            circuit = build_qft_circuit(encoded)
            sv = run_qft(circuit)
            result = visualize_qft(circuit, sv, output_dir=tmpdir)

            assert isinstance(result, QFTResult)
            assert result.n_qubits == 4  # 16 samples → 4 qubits
            assert len(result.basis_states) == 16
            assert len(result.amplitudes) == 16
            assert len(result.phases) == 16

    def test_amplitudes_sum_to_one(self):
        signal = _sine_signal(freq=3.0, n_samples=8)

        encoded = encode_signal(signal)
        circuit = build_qft_circuit(encoded)
        sv = run_qft(circuit)
        result = visualize_qft(circuit, sv)

        total = sum(result.amplitudes)
        assert abs(total - 1.0) < 1e-6, f"Probabilities sum to {total}, expected ≈1.0"

    def test_circuit_image_saved(self):
        signal = _sine_signal(freq=1.0, n_samples=4)

        with tempfile.TemporaryDirectory() as tmpdir:
            encoded = encode_signal(signal)
            circuit = build_qft_circuit(encoded)
            sv = run_qft(circuit)
            result = visualize_qft(circuit, sv, output_dir=tmpdir)

            assert os.path.isfile(result.circuit_image)
            assert result.circuit_image.endswith(".png")

    def test_spectrum_plot_saved(self):
        signal = _sine_signal(freq=1.0, n_samples=4)

        with tempfile.TemporaryDirectory() as tmpdir:
            encoded = encode_signal(signal)
            circuit = build_qft_circuit(encoded)
            sv = run_qft(circuit)
            result = visualize_qft(circuit, sv, output_dir=tmpdir)
            spectrum_path = plot_frequency_spectrum(result, output_dir=tmpdir)

            assert os.path.isfile(spectrum_path)

    def test_dominant_frequencies_helper(self):
        signal = _sine_signal(freq=2.0, n_samples=16)

        encoded = encode_signal(signal)
        circuit = build_qft_circuit(encoded)
        sv = run_qft(circuit)
        result = visualize_qft(circuit, sv)

        top = result.dominant_frequencies(top_k=3)
        assert len(top) == 3
        assert top[0][1] >= top[1][1]  # sorted descending

    def test_as_dict_serialization(self):
        signal = _sine_signal(freq=1.0, n_samples=4)

        encoded = encode_signal(signal)
        circuit = build_qft_circuit(encoded)
        sv = run_qft(circuit)
        result = visualize_qft(circuit, sv)

        d = result.as_dict()
        assert set(d.keys()) == {"n_qubits", "basis_states", "amplitudes", "phases", "circuit_image"}


class TestQubitCap:
    """Ensure the hard 8-qubit cap is enforced."""

    def test_exceeding_cap_raises(self):
        big_signal = np.random.randn(2**9)  # would need 9 qubits
        with pytest.raises(ValueError, match="hard cap"):
            encode_signal(big_signal)

    def test_explicit_cap_violation(self):
        signal = np.array([1.0, 0.0, 0.0, 0.0])
        with pytest.raises(ValueError, match="hard cap"):
            encode_signal(signal, n_qubits=9)

    def test_max_allowed_qubits(self):
        signal = np.random.randn(2**MAX_QUBITS)
        qc = encode_signal(signal, n_qubits=MAX_QUBITS)
        assert qc.num_qubits == MAX_QUBITS


class TestEdgeCases:
    """Encoder edge cases."""

    def test_empty_signal_raises(self):
        with pytest.raises(ValueError, match="at least one sample"):
            encode_signal(np.array([]))

    def test_zero_signal_raises(self):
        with pytest.raises(ValueError, match="near-zero"):
            encode_signal(np.zeros(8))

    def test_single_sample(self):
        qc = encode_signal(np.array([1.0]))
        assert qc.num_qubits == 1

    def test_non_power_of_two_pads(self):
        signal = np.array([1.0, 2.0, 3.0])  # 3 → pad to 4 → 2 qubits
        qc = encode_signal(signal)
        assert qc.num_qubits == 2

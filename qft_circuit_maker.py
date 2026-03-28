"""
main.py — Person 3 (Quantum Module) Standalone Test
Now includes QFT circuit diagram export
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import warnings
warnings.filterwarnings("ignore")

from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────

@dataclass
class SampledSignal:
    time: np.ndarray
    samples: np.ndarray
    fs: float
    f: float
    aliased_freq: Optional[float]
    fft_freqs: np.ndarray
    fft_mags: np.ndarray

@dataclass
class QFTResult:
    n_qubits: int
    basis_states: list
    amplitudes: np.ndarray
    phases: np.ndarray
    circuit_image: object


# ─────────────────────────────────────────────
# Signal generation + sampling
# ─────────────────────────────────────────────

def generate_signal(f, amplitude=1.0, phase=0.0, duration=1.0, oversample=1000):
    t = np.linspace(0, duration, int(duration * oversample), endpoint=False)
    signal = amplitude * np.sin(2 * np.pi * f * t + phase)
    return t, signal


def sample_signal(f, fs, amplitude=1.0, phase=0.0, duration=1.0):
    t_samples = np.arange(0, duration, 1.0 / fs)
    samples = amplitude * np.sin(2 * np.pi * f * t_samples + phase)

    nyquist = fs / 2.0
    aliased_freq = abs(f - round(f / fs) * fs) if f > nyquist else None

    N = len(samples)
    fft_mags = np.abs(np.fft.rfft(samples)) / N
    fft_freqs = np.fft.rfftfreq(N, d=1.0 / fs)

    return SampledSignal(t_samples, samples, fs, f, aliased_freq, fft_freqs, fft_mags)


# ─────────────────────────────────────────────
# QFT Encoding + Circuit
# ─────────────────────────────────────────────

def compute_n_qubits(n_samples, max_qubits=8):
    return min(int(np.ceil(np.log2(max(n_samples, 2)))), max_qubits)


def encode_signal(samples, n_qubits):
    n_states = 2 ** n_qubits
    padded = np.zeros(n_states)
    padded[:min(len(samples), n_states)] = samples[:n_states]

    norm = np.linalg.norm(padded)
    if norm < 1e-10:
        padded[0] = 1.0
        norm = 1.0

    return (padded / norm).astype(complex)


def build_qft_circuit(statevector, n_qubits):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import QFT

    qc = QuantumCircuit(n_qubits)
    qc.initialize(statevector.tolist(), range(n_qubits))
    qc.append(QFT(n_qubits, do_swaps=True), range(n_qubits))
    return qc.decompose(reps=3)


# ─────────────────────────────────────────────
# QFT Runner
# ─────────────────────────────────────────────

def run_qft(circuit):
    from qiskit_aer import AerSimulator

    sim = AerSimulator(method="statevector")
    circuit.save_statevector()
    result = sim.run(circuit).result()
    return np.array(result.get_statevector())


def extract_frequency_data(statevector):
    return np.abs(statevector), np.angle(statevector)


def draw_circuit(circuit):
    return circuit.draw("mpl", fold=-1)


def get_basis_state_labels(n):
    return [format(i, f"0{n}b") for i in range(2 ** n)]


# ─────────────────────────────────────────────
# Scenarios
# ─────────────────────────────────────────────

SCENARIOS = {
    "aliasing": {"label": "Aliasing", "f": 45.0, "fs": 40.0},
    "normal": {"label": "Normal", "f": 5.0, "fs": 100.0},
    "nyquist": {"label": "Nyquist", "f": 10.0, "fs": 20.0},
    "oversample": {"label": "Oversample", "f": 3.0, "fs": 200.0},
}


# ─────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────

def run_pipeline(name, scenario):
    print(f"\n--- {scenario['label']} ---")

    sig = sample_signal(scenario["f"], scenario["fs"])

    n_qubits = compute_n_qubits(len(sig.samples))
    statevector = encode_signal(sig.samples, n_qubits)

    circuit = build_qft_circuit(statevector, n_qubits)

    # 🔥 SAVE CIRCUIT DIAGRAM
    circuit_img = draw_circuit(circuit)
    circuit_path = f"qft_circuit_{name}.png"
    circuit_img.savefig(circuit_path, dpi=120, bbox_inches="tight")
    print(f"QFT circuit saved → {circuit_path}")

    statevector_out = run_qft(circuit)
    amps, phases = extract_frequency_data(statevector_out)

    return sig, QFTResult(
        n_qubits,
        get_basis_state_labels(n_qubits),
        amps,
        phases,
        circuit_img
    )


# ─────────────────────────────────────────────
# Plot
# ─────────────────────────────────────────────

def plot_results(sig, qft, name):
    fig = plt.figure(figsize=(12, 6))

    # FFT
    plt.subplot(1, 2, 1)
    plt.title("FFT")
    plt.bar(sig.fft_freqs, sig.fft_mags)

    # QFT
    plt.subplot(1, 2, 2)
    plt.title("QFT")
    plt.bar(range(len(qft.amplitudes)), qft.amplitudes**2)

    out_path = f"output_{name}.png"
    plt.savefig(out_path)
    plt.close()

    print(f"Plot saved → {out_path}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="aliasing", choices=SCENARIOS.keys())
    args = parser.parse_args()

    name = args.scenario
    sig, qft = run_pipeline(name, SCENARIOS[name])
    plot_results(sig, qft, name)

    print("\nDone. Check images.\n")


if __name__ == "__main__":
    main()
from dataclasses import dataclass
import numpy as np

@dataclass
class SampledSignal:
    time: np.ndarray
    signal: np.ndarray
    samples_t: np.ndarray
    samples_a: np.ndarray
    fs: float
    f: float
    aliased_freq: float
    fft_freqs: np.ndarray
    fft_mags: np.ndarray

@dataclass
class QFTResult:
    n_qubits: int
    basis_states: list
    amplitudes: np.ndarray
    phases: np.ndarray
    circuit_image: object
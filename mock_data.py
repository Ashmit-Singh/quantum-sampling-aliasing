import numpy as np
from shared_types import SampledSignal, QFTResult

def get_mock_signal(f=5.0, fs=20.0, signal_type="sine") -> SampledSignal:
    t = np.linspace(0, 1, 1000)

    if signal_type == "sine":
        signal = np.sin(2 * np.pi * f * t)
    elif signal_type == "square":
        signal = np.sign(np.sin(2 * np.pi * f * t))
    else:
        signal = 2 * np.abs(2 * (t * f - np.floor(t * f + 0.5))) - 1

    samples_t = np.arange(0, 1, 1 / fs)
    samples_a = np.sin(2 * np.pi * f * samples_t)

    aliased_freq = abs(f - round(f / fs) * fs) if fs < 2 * f else 0.0

    fft_result = np.abs(np.fft.rfft(signal))
    fft_freqs = np.fft.rfftfreq(len(t), d=1 / 1000)

    return SampledSignal(
        time=t, signal=signal,
        samples_t=samples_t, samples_a=samples_a,
        fs=fs, f=f, aliased_freq=aliased_freq,
        fft_freqs=fft_freqs, fft_mags=fft_result
    )

def get_mock_qft(n_qubits=3) -> QFTResult:
    n = 2 ** n_qubits
    amps = np.random.dirichlet(np.ones(n))
    phases = np.random.uniform(0, 2 * np.pi, n)
    states = [format(i, f'0{n_qubits}b') for i in range(n)]

    return QFTResult(
        n_qubits=n_qubits,
        basis_states=states,
        amplitudes=amps,
        phases=phases,
        circuit_image=None
    )
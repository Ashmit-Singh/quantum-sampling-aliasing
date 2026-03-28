import numpy as np
from scipy import signal as scipy_signal
from dataclasses import dataclass
from typing import Literal

@dataclass
class SignalResult:
    t: list[float]
    s: list[float]
    fs: float

@dataclass  
class SamplingResult:
    sample_indices: list[int]
    sample_values: list[float]
    is_aliased: bool
    alias_frequency: float
    nyquist_frequency: float

@dataclass
class QuantizationResult:
    quantized: list[float]
    error: list[float]
    snr_theoretical: float
    snr_simulated: float
    lsb_size: float
    levels: int

@dataclass
class OversamplingResult:
    snr_gain_db: float
    enob: float
    noise_floor_reduction: float
    effective_snr: float

class DSPEngine:
    N_SAMPLES = 512

    def generate_signal(
        self,
        signal_type: Literal["sine","square","chirp","multi"],
        frequency: float,
        amplitude: float,
        noise_level: float = 0.0
    ) -> SignalResult:
        t = np.linspace(0, 1, self.N_SAMPLES, endpoint=False)
        if signal_type == "sine":
            s = np.sin(2 * np.pi * frequency * t)
        elif signal_type == "square":
            s = np.sign(np.sin(2 * np.pi * frequency * t))
        elif signal_type == "chirp":
            f0 = frequency
            f1 = frequency * 3.0
            k = (f1 - f0)
            s = np.sin(2 * np.pi * (f0 * t + 0.5 * k * t ** 2))
        elif signal_type == "multi":
            s = np.sin(2 * np.pi * frequency * t) * 0.6 + np.sin(2 * np.pi * frequency * 3.1 * t) * 0.4
        else:
            s = np.zeros_like(t)

        s = s * amplitude
        if noise_level > 0:
            noise = (np.random.rand(self.N_SAMPLES) - 0.5) * 2 * (noise_level) * amplitude
            s += noise

        return SignalResult(t=t.tolist(), s=s.tolist(), fs=float(self.N_SAMPLES))

    def sample_signal(
        self,
        signal: SignalResult,
        sampling_rate_ratio: float,
        signal_frequency: float,
        signal_type: str = "sine"
    ) -> SamplingResult:
        step = max(1, round(self.N_SAMPLES / (sampling_rate_ratio * 10)))
        indices = list(range(0, self.N_SAMPLES, step))
        vals = [signal.s[i] for i in indices]
        
        fs_effective = signal_frequency * sampling_rate_ratio
        nyq = fs_effective / 2
        
        max_freq = signal_frequency
        if signal_type == "multi":
            max_freq = signal_frequency * 3.1
        elif signal_type == "chirp":
            max_freq = signal_frequency * 3.0
            
        is_aliased = max_freq > nyq
        alias_freq = abs(max_freq - round(max_freq / fs_effective) * fs_effective) if fs_effective > 0 else 0

        return SamplingResult(
            sample_indices=indices,
            sample_values=vals,
            is_aliased=is_aliased,
            alias_frequency=alias_freq,
            nyquist_frequency=nyq
        )

    def quantize(
        self,
        signal: SignalResult,
        bits: int
    ) -> QuantizationResult:
        levels = 2 ** bits
        amp = max(abs(v) for v in signal.s) if any(signal.s) else 1.0
        lsb = (2 * amp) / levels
        
        q = [round(v / lsb) * lsb for v in signal.s]
        err = [signal.s[i] - q[i] for i in range(len(signal.s))]
        
        sp = sum(v*v for v in signal.s) / len(signal.s)
        np_pow = sum(e*e for e in err) / len(err)
        snr_sim = 999.0 if np_pow < 1e-12 else 10 * np.log10(sp / np_pow)
        snr_theory = 6.02 * bits + 1.76

        return QuantizationResult(
            quantized=q,
            error=err,
            snr_theoretical=snr_theory,
            snr_simulated=snr_sim,
            lsb_size=lsb,
            levels=levels
        )

    def oversample(
        self,
        signal: SignalResult,
        bits: int,
        osr: int
    ) -> OversamplingResult:
        quant = self.quantize(signal, bits)
        q_arr = np.array(quant.quantized)
        
        if osr > 1:
            cutoff = 1.0 / osr
            b, a = scipy_signal.butter(4, cutoff, btype='low')
            filtered = scipy_signal.filtfilt(b, a, q_arr)
        else:
            filtered = q_arr
            
        s_arr = np.array(signal.s)
        noise = s_arr - filtered
        signal_power = float(np.mean(s_arr ** 2))
        noise_power = float(np.mean(noise ** 2))
        eff_snr = 999.0 if noise_power < 1e-12 else 10 * np.log10(signal_power / noise_power)
        
        gain = 10 * np.log10(osr) if osr > 1 else 0.0
        enob = (eff_snr - 1.76) / 6.02

        return OversamplingResult(
            snr_gain_db=gain,
            enob=enob,
            noise_floor_reduction=gain,
            effective_snr=eff_snr
        )

    def compute_fft(
        self,
        signal: SignalResult,
        window: bool = True
    ) -> dict:
        N = len(signal.s)
        s = np.array(signal.s[:N])
        if window:
            win = np.hanning(N)
            s = s * win
            
        fft_res = np.fft.fft(s)
        freqs = np.fft.fftfreq(N, d=1.0/signal.fs)
        
        mag = np.abs(fft_res[:N//2]) / (N/2)
        mag_db = 20 * np.log10(np.maximum(mag, 1e-10))
        
        return {
            "frequencies": freqs[:N//2].tolist(),
            "magnitudes_db": mag_db.tolist()
        }

    def sinc_reconstruct(
        self,
        samples: list[float],
        sample_indices: list[int],
        fs_continuous: float
    ) -> dict:
        t_cont = np.linspace(0, 1, self.N_SAMPLES, endpoint=False)
        T = 1 / fs_continuous
        reconstructed = np.zeros_like(t_cont)
        components = []

        max_components_to_send = 25
        stride = max(1, len(samples) // max_components_to_send)

        for i, (idx, xn) in enumerate(zip(sample_indices, samples)):
            # T is the period of the sampling rate
            # n*T is the time of the sample
            t_samp = idx / self.N_SAMPLES
            sinc_pulse = xn * np.sinc((t_cont - t_samp) / T)
            reconstructed += sinc_pulse
            if i % stride == 0 and len(components) < max_components_to_send:
                components.append(sinc_pulse.tolist())

        return {
            "reconstructed": reconstructed.tolist(),
            "sinc_components": components
        }

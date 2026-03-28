"""Stateless DSP pipeline orchestrator.

Composes signal generation → sampling → aliasing detection →
reconstruction → FFT analysis into a single deterministic call
that returns a fully populated ``SampledSignal``.
"""

from __future__ import annotations

from .aliasing_detector import compute_alias_frequency
from .fft_engine import compute_fft
from .models import SampledSignal, Waveform
from .reconstructor import reconstruct_signal
from .sampler import sample_signal
from .signal_generator import generate_continuous_signal


def process_signal(
    f: float,
    fs: float,
    duration: float = 1.0,
    waveform: Waveform = Waveform.SINE,
    phase: float = 0.0,
    apply_window: bool = False,
) -> SampledSignal:
    """Execute the full DSP pipeline and return a packed result.

    Pipeline stages:
        1. Generate high-resolution continuous-time signal
        2. Sample via interpolation at rate *fs*
        3. Compute analytical aliased frequency
        4. Reconstruct signal via Whittaker–Shannon interpolation
        5. Compute one-sided FFT spectrum
        6. Package all outputs into ``SampledSignal``

    Args:
        f: Signal frequency in Hz.
        fs: Sampling frequency in Hz.
        duration: Signal duration in seconds (default 1.0).
        waveform: Waveform shape.
        phase: Initial phase offset in radians.
        apply_window: Apply Hann window during reconstruction.

    Returns:
        Fully populated ``SampledSignal`` instance.
    """
    # 1. Continuous-time synthesis
    t_cont, x_cont = generate_continuous_signal(
        f=f, duration=duration, waveform=waveform, phase=phase,
    )

    # 2. Discrete-time sampling
    t_samples, x_samples = sample_signal(
        t_cont=t_cont, x_cont=x_cont, fs=fs, duration=duration,
    )

    # 3. Aliasing detection
    aliased_freq, nyquist_satisfied = compute_alias_frequency(
        f_signal=f, fs=fs,
    )

    # 4. Signal reconstruction
    x_reconstructed, rmse = reconstruct_signal(
        t_cont=t_cont,
        t_samples=t_samples,
        x_samples=x_samples,
        fs=fs,
        x_original=x_cont,
        apply_window=apply_window,
    )

    # 5. Frequency-domain analysis
    fft_freqs, fft_magnitude, dominant_freq = compute_fft(
        x_samples=x_samples, fs=fs,
    )

    # 6. Pack result
    return SampledSignal(
        t_cont=t_cont,
        x_cont=x_cont,
        t_samples=t_samples,
        x_samples=x_samples,
        fs=fs,
        f_signal=f,
        aliased_freq=aliased_freq,
        nyquist_satisfied=nyquist_satisfied,
        fft_freqs=fft_freqs,
        fft_magnitude=fft_magnitude,
        dominant_freq=dominant_freq,
        x_reconstructed=x_reconstructed,
        rmse=rmse,
    )

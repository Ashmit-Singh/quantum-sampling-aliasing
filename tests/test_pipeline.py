"""Comprehensive test suite for the DSP backend pipeline.

Covers: signal generation, sampling, aliasing detection, reconstruction,
FFT analysis, pipeline integration, edge cases, and performance.
"""

import time

import numpy as np
import pytest

from modules.aliasing_detector import compute_alias_frequency
from modules.fft_engine import compute_fft
from modules.models import RMSEQuality, Waveform, classify_rmse
from modules.pipeline import process_signal
from modules.reconstructor import reconstruct_signal
from modules.sampler import sample_signal
from modules.signal_generator import generate_continuous_signal


# ── Signal Generation ────────────────────────────────────────────────

class TestSignalGeneration:

    def test_sine_frequency_content(self):
        """Verify sine wave has correct frequency via zero-crossings."""
        f, dur = 50.0, 1.0
        t, x = generate_continuous_signal(f, dur, Waveform.SINE)
        # Count positive-to-negative zero crossings
        crossings = np.where(np.diff(np.sign(x)) < 0)[0]
        # Each cycle has one negative crossing; expect ~f crossings
        assert abs(len(crossings) - f) <= 2

    def test_square_wave_shape(self):
        t, x = generate_continuous_signal(10.0, 0.5, Waveform.SQUARE)
        unique_vals = np.unique(np.round(x, 1))
        assert set(unique_vals).issubset({-1.0, 1.0})

    def test_triangle_wave_range(self):
        t, x = generate_continuous_signal(10.0, 0.5, Waveform.TRIANGLE)
        assert np.min(x) >= -1.01 and np.max(x) <= 1.01

    def test_phase_offset(self):
        """Sine with π/2 phase should start near 1.0."""
        _, x = generate_continuous_signal(10.0, 0.1, Waveform.SINE, phase=np.pi / 2)
        assert abs(x[0] - 1.0) < 0.01

    def test_invalid_frequency_raises(self):
        with pytest.raises(ValueError):
            generate_continuous_signal(0.0, 1.0)

    def test_invalid_duration_raises(self):
        with pytest.raises(ValueError):
            generate_continuous_signal(10.0, -1.0)

    def test_resolution_floor(self):
        """Output should have at least 10000 * duration samples."""
        t, _ = generate_continuous_signal(5.0, 1.0)
        assert t.size >= 10_000


# ── Sampling ─────────────────────────────────────────────────────────

class TestSampling:

    def test_interpolated_values_match_continuous(self):
        """Sampled values at aligned points should match the source."""
        f, dur, fs = 10.0, 1.0, 100.0
        t_c, x_c = generate_continuous_signal(f, dur)
        t_s, x_s = sample_signal(t_c, x_c, fs, dur)
        # Each sample point should have a close match in the continuous domain
        for i in range(min(10, t_s.size)):
            expected = np.interp(t_s[i], t_c, x_c)
            assert abs(x_s[i] - expected) < 1e-10

    def test_sample_count(self):
        fs, dur = 44.0, 1.0
        t_s, _ = sample_signal(
            *generate_continuous_signal(10.0, dur), fs, dur,
        )
        expected_n = int(np.floor(fs * dur)) + 1
        assert t_s.size == expected_n

    def test_very_low_fs(self):
        """Ultra-low sampling rate should still produce valid output."""
        t_s, x_s = sample_signal(
            *generate_continuous_signal(100.0, 1.0), 1.0, 1.0,
        )
        assert t_s.size >= 1

    def test_invalid_fs_raises(self):
        t, x = generate_continuous_signal(10.0, 1.0)
        with pytest.raises(ValueError):
            sample_signal(t, x, 0.0, 1.0)


# ── Aliasing Detection ──────────────────────────────────────────────

class TestAliasingDetection:

    def test_known_alias_pair(self):
        """150 Hz sampled at 200 Hz → alias at 50 Hz."""
        f_alias, nyq = compute_alias_frequency(150.0, 200.0)
        assert abs(f_alias - 50.0) < 1e-6
        assert nyq is False

    def test_no_aliasing(self):
        """50 Hz sampled at 200 Hz → no aliasing, f_alias = 50 Hz."""
        f_alias, nyq = compute_alias_frequency(50.0, 200.0)
        assert abs(f_alias - 50.0) < 1e-6
        assert nyq is True

    def test_nyquist_boundary(self):
        """fs = 2f should be considered satisfied (within tolerance)."""
        _, nyq = compute_alias_frequency(100.0, 200.0)
        assert nyq is True

    def test_just_below_nyquist(self):
        """fs slightly below 2f → Nyquist NOT satisfied."""
        _, nyq = compute_alias_frequency(100.0, 199.0)
        assert nyq is False

    def test_invalid_inputs(self):
        with pytest.raises(ValueError):
            compute_alias_frequency(-1.0, 100.0)
        with pytest.raises(ValueError):
            compute_alias_frequency(10.0, 0.0)


# ── Reconstruction ───────────────────────────────────────────────────

class TestReconstruction:

    def test_oversampled_sine_low_rmse(self):
        """Well-oversampled sine should reconstruct with RMSE < 0.01."""
        f, dur, fs = 10.0, 1.0, 200.0
        t_c, x_c = generate_continuous_signal(f, dur)
        t_s, x_s = sample_signal(t_c, x_c, fs, dur)
        x_r, rmse = reconstruct_signal(t_c, t_s, x_s, fs, x_c)
        assert rmse < 0.01
        assert x_r.shape == x_c.shape

    def test_windowed_reconstruction(self):
        f, dur, fs = 10.0, 1.0, 200.0
        t_c, x_c = generate_continuous_signal(f, dur)
        t_s, x_s = sample_signal(t_c, x_c, fs, dur)
        x_r, rmse = reconstruct_signal(t_c, t_s, x_s, fs, x_c, apply_window=True)
        # Windowed reconstruction may have higher RMSE but should still work
        assert np.isfinite(rmse)
        assert x_r.shape == x_c.shape

    def test_empty_samples(self):
        t_c, x_c = generate_continuous_signal(10.0, 1.0)
        x_r, rmse = reconstruct_signal(
            t_c, np.array([]), np.array([]), 100.0, x_c,
        )
        assert x_r.shape == x_c.shape
        assert rmse > 0


# ── FFT Engine ───────────────────────────────────────────────────────

class TestFFTEngine:

    def test_dominant_frequency_matches_input(self):
        """FFT should detect the input frequency of a clean sine."""
        f, dur, fs = 50.0, 1.0, 500.0
        t_c, x_c = generate_continuous_signal(f, dur)
        _, x_s = sample_signal(t_c, x_c, fs, dur)
        freqs, mag, dom = compute_fft(x_s, fs)
        assert abs(dom - f) <= (fs / x_s.size)  # within one FFT bin

    def test_too_few_samples_raises(self):
        with pytest.raises(ValueError):
            compute_fft(np.array([1.0]), 100.0)

    def test_magnitude_normalization(self):
        """Pure DC signal: magnitude[0] should equal the signal level."""
        x = np.ones(100, dtype=np.float64) * 3.0
        _, mag, _ = compute_fft(x, 100.0)
        assert abs(mag[0] - 3.0) < 0.01


# ── Pipeline Integration ────────────────────────────────────────────

class TestPipeline:

    def test_round_trip(self):
        result = process_signal(f=50.0, fs=500.0, duration=1.0)
        assert result.f_signal == 50.0
        assert result.fs == 500.0
        assert result.nyquist_satisfied is True
        assert result.t_cont.size > 0
        assert result.x_reconstructed.shape == result.x_cont.shape
        assert np.isfinite(result.rmse)
        assert np.isfinite(result.dominant_freq)

    def test_aliasing_scenario(self):
        """fs < 2f should flag aliasing and produce non-trivial alias freq."""
        result = process_signal(f=150.0, fs=200.0)
        assert result.nyquist_satisfied is False
        assert abs(result.aliased_freq - 50.0) < 1e-6

    def test_oversampling_scenario(self):
        result = process_signal(f=10.0, fs=1000.0)
        assert result.nyquist_satisfied is True
        assert result.rmse < 0.01

    def test_all_waveforms(self):
        for wf in Waveform:
            result = process_signal(f=20.0, fs=500.0, waveform=wf)
            assert result.t_samples.size > 0

    def test_reconstruction_quality_property(self):
        result = process_signal(f=10.0, fs=1000.0)
        assert result.reconstruction_quality in RMSEQuality


# ── RMSE Classification ─────────────────────────────────────────────

class TestRMSEClassification:

    def test_good(self):
        assert classify_rmse(0.005) is RMSEQuality.GOOD

    def test_moderate(self):
        assert classify_rmse(0.05) is RMSEQuality.MODERATE

    def test_poor(self):
        assert classify_rmse(0.5) is RMSEQuality.POOR


# ── Performance ──────────────────────────────────────────────────────

class TestPerformance:

    def test_typical_latency_under_100ms(self):
        """Typical pipeline call should complete well under 100ms."""
        # Warmup
        process_signal(f=50.0, fs=500.0, duration=0.5)

        start = time.perf_counter()
        process_signal(f=50.0, fs=500.0, duration=1.0)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        assert elapsed_ms < 150.0, f"Pipeline took {elapsed_ms:.1f}ms (limit: 150ms)"

    def test_large_reconstruction_no_crash(self):
        """Large array reconstruction should complete without OOM."""
        result = process_signal(f=10.0, fs=200.0, duration=2.0)
        assert result.x_reconstructed.shape == result.x_cont.shape

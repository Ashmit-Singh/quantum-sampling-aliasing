"""Generate sample CSV datasets for the CSV pipeline integration."""
import numpy as np
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'sample_data')
os.makedirs(OUT_DIR, exist_ok=True)


def generate_ecg(n=2048):
    """Simulated ECG-like signal using superimposed Gaussians."""
    t = np.linspace(0, 4, n)
    ecg = np.zeros(n)
    # Heartbeat pattern every ~1 second
    for beat_t in [0.5, 1.5, 2.5, 3.5]:
        # P wave
        ecg += 0.15 * np.exp(-((t - (beat_t - 0.15)) ** 2) / (2 * 0.01 ** 2))
        # QRS complex
        ecg -= 0.1 * np.exp(-((t - (beat_t - 0.03)) ** 2) / (2 * 0.005 ** 2))
        ecg += 0.9 * np.exp(-((t - beat_t) ** 2) / (2 * 0.008 ** 2))
        ecg -= 0.2 * np.exp(-((t - (beat_t + 0.03)) ** 2) / (2 * 0.005 ** 2))
        # T wave
        ecg += 0.25 * np.exp(-((t - (beat_t + 0.2)) ** 2) / (2 * 0.02 ** 2))
    # Normalize to [-1, 1]
    ecg = ecg / (np.max(np.abs(ecg)) + 1e-9)
    # Add slight noise
    ecg += np.random.randn(n) * 0.02
    ecg = np.clip(ecg, -1, 1)
    path = os.path.join(OUT_DIR, 'ecg_signal.csv')
    np.savetxt(path, ecg, delimiter=',', header='voltage', comments='')
    print(f"  ✓ {path}  ({n} rows)")


def generate_sine_440(n=2048, sr=44100):
    """Clean 440 Hz sine at 44100 Hz sample rate."""
    t = np.arange(n) / sr
    s = np.sin(2 * np.pi * 440 * t)
    path = os.path.join(OUT_DIR, 'sine_440hz.csv')
    np.savetxt(path, s, delimiter=',', header='amplitude', comments='')
    print(f"  ✓ {path}  ({n} rows)")


def generate_noisy_sensor(n=2048):
    """Random walk simulating ADC noise from a sensor."""
    rng = np.random.default_rng(42)
    walk = np.cumsum(rng.normal(0, 0.01, n))
    walk = walk / (np.max(np.abs(walk)) + 1e-9)
    # Add high-frequency noise
    noise = rng.normal(0, 0.05, n)
    s = walk + noise
    s = s / (np.max(np.abs(s)) + 1e-9)
    path = os.path.join(OUT_DIR, 'noisy_sensor.csv')
    np.savetxt(path, s, delimiter=',', header='reading', comments='')
    print(f"  ✓ {path}  ({n} rows)")


if __name__ == '__main__':
    print("Generating sample data...")
    generate_ecg()
    generate_sine_440()
    generate_noisy_sensor()
    print("Done.")

# QSA Visualizer
### Quantum Sampling & Aliasing — 3D Simulator
*PS18 + PS19 Combined Simulator · QtHack04 · SRM Institute of Science and Technology*

---

## Overview

QSA Visualizer is an interactive 3D simulation environment for exploring classical and quantum signal processing concepts — specifically the relationship between sampling theory, quantization noise, aliasing artifacts, and Quantum Fourier Transform (QFT). Built for QtHack04, it bridges the gap between DSP fundamentals and quantum computation through real-time visual simulation.

---

## Quick Start

### Frontend Only *(no backend required)*
```bash
# Just open in Chrome — no install needed
open index.html
```

### Full Stack *(Python backend + API)*
```bash
pip install -r requirements.txt
cd backend
python main.py
```
Then visit `http://localhost:8000`

---

## Architecture

```
[Browser Frontend]
       │
       ▼
[FastAPI Backend]
       │
       ▼
[DSPEngine / QFTBridge]
       │
  ┌────┴────┐
  ▼         ▼
[DSP     [Quantum
modules] modules]
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/signal` | Generate input signal |
| `POST` | `/api/sample` | Apply sampling at given rate |
| `POST` | `/api/quantize` | Quantize signal to N bits |
| `POST` | `/api/oversample` | Apply oversampling at given OSR |
| `POST` | `/api/fft` | Compute classical FFT |
| `POST` | `/api/qft` | Compute Quantum Fourier Transform |
| `POST` | `/api/pipeline` | **Main endpoint** — run full DSP/QFT pipeline |

---

## Signal Math

| Formula | Description |
|---------|-------------|
| `SNR = 6.02 × N + 1.76 dB` | Signal-to-noise ratio for N-bit quantization |
| `OSR gain = 10 × log₁₀(OSR)` | SNR improvement from oversampling |
| `ENOB = (SNR − 1.76) / 6.02` | Effective number of bits |
| `f_alias = \|f − round(f/fs) × fs\|` | Alias frequency given signal freq f and sample rate fs |

---

## Features

- **3D waveform visualization** — real-time rendering of sampled and aliased signals
- **Quantum Fourier Transform** — side-by-side comparison with classical FFT
- **Aliasing detector** — visual alert when sampling rate violates Nyquist criterion
- **Oversampling simulation** — observe SNR improvements live
- **Quantization noise** — bit-depth sweep with ENOB readout
- **Pipeline mode** — chain signal → sample → quantize → FFT/QFT in one call

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML5 Canvas / WebGL, vanilla JS |
| Backend | Python 3, FastAPI, Uvicorn |
| DSP | NumPy, SciPy |
| Quantum | Custom QFTBridge module |

---

## Team

**QtHack04** — *Visual Simulation of Classical & Quantum Technologies*
SRM Institute of Science and Technology

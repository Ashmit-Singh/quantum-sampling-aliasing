# Quantum Sampling & Aliasing — 3D Visualizer

PS18 + PS19 combined simulator for QtHack04

## Quick start

### Frontend only (no backend needed)
Open index.html in Chrome directly.

### Full stack (with Python backend)
```bash
pip install -r requirements.txt
cd backend
python main.py
```
Open `http://localhost:8000`

## Architecture
[Frontend] → [FastAPI] → [DSPEngine / QFTBridge] → [modules/]

## API Reference
- `GET  /health`
- `POST /api/signal`
- `POST /api/sample`
- `POST /api/quantize`
- `POST /api/oversample`
- `POST /api/fft`
- `POST /api/pipeline`    ← main endpoint
- `POST /api/qft`

## Signal math
- SNR = 6.02 × N + 1.76 dB
- OSR gain = 10 × log10(OSR)
- ENOB = (SNR - 1.76) / 6.02
- Alias frequency = |f - round(f/fs) × fs|

## Team
QtHack04 — Visual Simulation of Classical & Quantum Technologies
SRM Institute of Science and Technology

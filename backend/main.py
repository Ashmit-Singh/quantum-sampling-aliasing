from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn
import sys
import os
import io
import numpy as np
from scipy import signal as scipy_signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

from backend.dsp_engine import DSPEngine, SignalResult
from backend.qft_bridge import QFTBridge
from backend.qft_bridge_real import QFTBridgeReal

app = FastAPI(title="Quantum Sampling & Aliasing API", version="2.0.0")

# CORS — allow the frontend to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://localhost:3000", 
        "https://quantum-sampling-aliasing.onrender.com",
        "https://quantum-sampling-aliasing.vercel.app"
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Serve index.html from root
static_dir = os.path.join(os.path.dirname(__file__), "..")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

dsp = DSPEngine()
qft = QFTBridge()
qft_real = QFTBridgeReal()

# ── Request models ──
class SignalRequest(BaseModel):
    signal_type: str = Field("sine", pattern="^(sine|square|chirp|multi)$")
    frequency: float = Field(5.0, ge=1, le=100)
    amplitude: float = Field(1.0, ge=0.01, le=10)
    noise_level: float = Field(0.0, ge=0, le=1)

class SamplingRequest(SignalRequest):
    sampling_rate_ratio: float = Field(2.5, ge=0.1, le=20)

class QuantizationRequest(SamplingRequest):
    bits: int = Field(8, ge=2, le=16)

class FullPipelineRequest(QuantizationRequest):
    osr: int = Field(1, ge=1, le=64)
    reconstruction_mode: str = Field("spline", pattern="^(spline|sinc)$")

class RealSignalRequest(BaseModel):
    samples: list[float]
    source_sample_rate: int
    bits: int = Field(8, ge=2, le=16)
    osr: int = Field(1, ge=1, le=64)
    sampling_rate_ratio: float = Field(2.5, ge=0.1, le=20)
    reconstruction_mode: str = Field("spline", pattern="^(spline|sinc)$")

# ── Helper: run full pipeline on a SignalResult ──
def _run_full_pipeline(sig: SignalResult, sampling_rate_ratio: float, bits: int, osr: int, reconstruction_mode: str = "spline", signal_frequency: float = 5.0, signal_type: str = "sine"):
    samp = dsp.sample_signal(sig, sampling_rate_ratio, signal_frequency, signal_type)
    quant = dsp.quantize(sig, bits)
    over = dsp.oversample(sig, bits, osr)
    fft_res = dsp.compute_fft(sig)

    fs_effective = signal_frequency * sampling_rate_ratio
    recon_res = None
    if reconstruction_mode == "sinc":
        recon_res = dsp.sinc_reconstruct(samp.sample_values, samp.sample_indices, fs_effective)

    sampled_vals = samp.sample_values[:256]
    try:
        qft_res = qft.run_qft_on_signal(sampled_vals)
    except Exception as e:
        qft_res = {
            "success": False,
            "error": str(e),
            "n_qubits": 0,
            "amplitudes": [],
            "phases": [],
            "circuit_diagram": "",
            "measurement_probabilities": []
        }

    return {
        "signal": sig.__dict__,
        "sampling": samp.__dict__,
        "quantization": quant.__dict__,
        "oversampling": over.__dict__,
        "fft": fft_res,
        "reconstruction": recon_res,
        "qft": qft_res.__dict__ if hasattr(qft_res, "__dict__") else qft_res,
    }

# ── Routes ──

@app.get("/ping")
def ping():
    return {"pong": True, "t": __import__('time').time()}

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}

@app.post("/api/signal")
def generate_signal(req: SignalRequest):
    return dsp.generate_signal(req.signal_type, req.frequency, req.amplitude, req.noise_level)

@app.post("/api/sample")
def sample_signal(req: SamplingRequest):
    sig = dsp.generate_signal(req.signal_type, req.frequency, req.amplitude, req.noise_level)
    return dsp.sample_signal(sig, req.sampling_rate_ratio, req.frequency, req.signal_type)

@app.post("/api/quantize")
def quantize_signal(req: QuantizationRequest):
    sig = dsp.generate_signal(req.signal_type, req.frequency, req.amplitude, req.noise_level)
    return dsp.quantize(sig, req.bits)

@app.post("/api/oversample")
def oversample_signal(req: FullPipelineRequest):
    sig = dsp.generate_signal(req.signal_type, req.frequency, req.amplitude, req.noise_level)
    return dsp.oversample(sig, req.bits, req.osr)

@app.post("/api/fft")
def compute_fft(req: SignalRequest):
    sig = dsp.generate_signal(req.signal_type, req.frequency, req.amplitude, req.noise_level)
    return dsp.compute_fft(sig)

@app.post("/api/pipeline")
def full_pipeline(req: FullPipelineRequest):
    sig = dsp.generate_signal(req.signal_type, req.frequency, req.amplitude, req.noise_level)
    result = _run_full_pipeline(sig, req.sampling_rate_ratio, req.bits, req.osr, req.reconstruction_mode, req.frequency, req.signal_type)
    return result

# ── Integration 1: Real Audio Pipeline ──

@app.post("/api/pipeline/audio")
def pipeline_audio(req: RealSignalRequest):
    if len(req.samples) < 2:
        raise HTTPException(400, "Need at least 2 samples")

    raw = np.array(req.samples, dtype=float)
    s = scipy_signal.resample(raw, 512)
    max_abs = np.max(np.abs(s))
    if max_abs > 1e-9:
        s = s / max_abs

    sig = SignalResult(
        t=np.linspace(0, 1, 512, endpoint=False).tolist(),
        s=s.tolist(),
        fs=float(req.source_sample_rate),
    )

    result = _run_full_pipeline(sig, req.sampling_rate_ratio, req.bits, req.osr, req.reconstruction_mode, 1.0, "sine")
    result["source"] = {
        "type": "audio",
        "original_samples": len(req.samples),
        "source_sample_rate": req.source_sample_rate,
    }
    return result

# ── Integration 2: CSV / Sensor Data Pipeline ──

@app.post("/api/pipeline/csv")
async def pipeline_csv(
    file: UploadFile = File(...),
    bits: int = 8,
    osr: int = 1,
    sampling_rate_ratio: float = 2.5,
    source_sample_rate: int = 1000,
):
    contents = await file.read()
    try:
        import pandas as pd
        df = pd.read_csv(io.StringIO(contents.decode()))
        raw = df.iloc[:, 0].dropna().to_numpy(dtype=float)
    except Exception as e:
        raise HTTPException(400, f"CSV parse error: {e}")

    if len(raw) < 2:
        raise HTTPException(400, "CSV must contain at least 2 numeric rows")

    s = scipy_signal.resample(raw, 512)
    max_abs = np.max(np.abs(s))
    if max_abs > 1e-9:
        s = s / max_abs

    sig = SignalResult(
        t=np.linspace(0, 1, 512, endpoint=False).tolist(),
        s=s.tolist(),
        fs=float(source_sample_rate),
    )

    result = _run_full_pipeline(sig, sampling_rate_ratio, bits, osr, "spline", 1.0, "sine")
    result["source"] = {
        "type": "csv",
        "filename": file.filename,
        "original_rows": len(raw),
        "source_sample_rate": source_sample_rate,
    }
    return result

# ── Integration 3: Hardware QFT ──

@app.post("/api/qft/hardware")
def run_qft_hardware(n_qubits: int = 4, force_fresh: bool = False):
    if n_qubits < 2 or n_qubits > 10:
        raise HTTPException(400, "n_qubits must be between 2 and 10")
    return qft_real.get_qft_result(n_qubits, force_fresh)

@app.get("/api/qft/hardware/status")
def qft_hardware_status():
    return {
        "ibm_token_set": qft_real.ibm_token is not None,
        "use_real_hardware": qft_real.use_real,
        "cache_keys": list(qft_real._cache.keys()),
    }

@app.post("/api/qft")
def run_qft_endpoint(req: SignalRequest):
    """Async QFT endpoint — called by frontend background fetch, never blocks UI."""
    sig = dsp.generate_signal(req.signal_type, req.frequency, req.amplitude, req.noise_level)
    # Use first 256 samples for QFT (max 8 qubits)
    samples = sig.s[:256]
    result = qft.run_qft_on_signal(samples)
    return result

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

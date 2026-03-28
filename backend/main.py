from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.dsp_engine import DSPEngine
from backend.qft_bridge import QFTBridge
import os

app = FastAPI(title="Quantum Sampling & Aliasing API", version="1.0.0")

# CORS — allow the frontend to call the backend
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve index.html from root
static_dir = os.path.join(os.path.dirname(__file__), "..")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

dsp = DSPEngine()
qft = QFTBridge()

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

# ── Routes ──

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.post("/api/signal")
def generate_signal(req: SignalRequest):
    return dsp.generate_signal(req.signal_type, req.frequency, req.amplitude, req.noise_level)

@app.post("/api/sample")
def sample_signal(req: SamplingRequest):
    sig = dsp.generate_signal(req.signal_type, req.frequency, req.amplitude, req.noise_level)
    return dsp.sample_signal(sig, req.sampling_rate_ratio)

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
    samp = dsp.sample_signal(sig, req.sampling_rate_ratio)
    quant = dsp.quantize(sig, req.bits)
    over = dsp.oversample(sig, req.bits, req.osr)
    fft_res = dsp.compute_fft(sig)
    
    fs_effective = (req.sampling_rate_ratio * 10) / 2 * req.sampling_rate_ratio
    recon_res = None
    if req.reconstruction_mode == "sinc":
        recon_res = dsp.sinc_reconstruct(samp.sample_values, samp.sample_indices, fs_effective)
    
    qft_res = None
    if req.bits <= 8:
        sampled_vals = samp.sample_values[:256] 
        try:
            qft_res = qft.run_qft_on_signal(sampled_vals)
        except Exception as e:
             qft_res = {"success": False, "error": str(e)}
             
    return {
        "signal": sig.__dict__,
        "sampling": samp.__dict__,
        "quantization": quant.__dict__,
        "oversampling": over.__dict__,
        "fft": fft_res,
        "reconstruction": recon_res,
        "qft": qft_res.__dict__ if hasattr(qft_res, "__dict__") else qft_res
    }

@app.post("/api/qft")
def run_qft(req: SignalRequest):
    sig = dsp.generate_signal(req.signal_type, req.frequency, req.amplitude, req.noise_level)
    return qft.run_qft_on_signal(sig.s)

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

import pytest
from backend.dsp_engine import DSPEngine

def test_generate_signal():
    dsp = DSPEngine()
    res = dsp.generate_signal("sine", 5.0, 1.0)
    assert len(res.s) == dsp.N_SAMPLES
    assert res.fs == dsp.N_SAMPLES
    assert max(res.s) <= 1.0 + 1e-5

def test_sample_signal():
    dsp = DSPEngine()
    sig = dsp.generate_signal("sine", 5.0, 1.0)
    res = dsp.sample_signal(sig, 2.5)
    assert not res.is_aliased
    
    res_aliased = dsp.sample_signal(sig, 1.5)
    assert res_aliased.is_aliased

def test_quantize():
    dsp = DSPEngine()
    sig = dsp.generate_signal("sine", 5.0, 1.0)
    res = dsp.quantize(sig, 8)
    assert res.levels == 256
    assert abs(res.snr_theoretical - (6.02 * 8 + 1.76)) < 1e-5

def test_oversample():
    dsp = DSPEngine()
    sig = dsp.generate_signal("sine", 5.0, 1.0)
    res = dsp.oversample(sig, 8, 4)
    assert res.snr_gain_db > 0

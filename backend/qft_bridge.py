import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'modules'))

from qft_encoder import encode_signal
from qft_circuit import build_qft_circuit
from qft_runner import run_qft
from qft_visualizer import visualize_qft

class QFTBridge:
    def run_qft_on_signal(self, signal_samples: list[float]) -> dict:
        try:
            enc = encode_signal(signal_samples)
            circ = build_qft_circuit(enc)
            sv = run_qft(circ)
            res = visualize_qft(circ, sv)
            res_dict = res.as_dict()
            res_dict["success"] = True
            res_dict["error"] = None
            res_dict["measurement_probabilities"] = [
                abs(a) ** 2 for a in res_dict["amplitudes"]
            ] if res_dict.get("amplitudes") else []

            # ── Circuit transparency metadata ──
            # Decompose to basis gates to get real depth/gate count
            try:
                decomposed = circ.decompose()
                res_dict["circuit_depth"] = decomposed.depth()
                res_dict["gate_count"] = sum(decomposed.count_ops().values())
                res_dict["encoding_method"] = "Amplitude encoding (O(2^n) initialization)"
                res_dict["gate_ops"] = dict(decomposed.count_ops())
            except Exception:
                res_dict["circuit_depth"] = circ.depth()
                res_dict["gate_count"] = circ.size()
                res_dict["encoding_method"] = "Amplitude encoding"

            return res_dict
        except Exception as e:
            return {
                "n_qubits": 0,
                "amplitudes": [],
                "phases": [],
                "circuit_diagram": "",
                "measurement_probabilities": [],
                "circuit_depth": 0,
                "gate_count": 0,
                "encoding_method": "",
                "success": False,
                "error": str(e)
            }


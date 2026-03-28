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
            res_dict["measurement_probabilities"] = res_dict["amplitudes"]
            return res_dict
        except Exception as e:
            return {
                "n_qubits": 0,
                "amplitudes": [],
                "phases": [],
                "circuit_diagram": "",
                "measurement_probabilities": [],
                "success": False,
                "error": str(e)
            }

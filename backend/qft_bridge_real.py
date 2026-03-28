import os
import json
import time
from pathlib import Path

CACHE_FILE = Path(__file__).parent / "qft_cache.json"


class QFTBridgeReal:
    def __init__(self):
        self.ibm_token = os.getenv("IBM_QUANTUM_TOKEN")
        self.use_real = self.ibm_token is not None
        self._cache = self._load_cache()

        if self.use_real:
            try:
                from qiskit_ibm_runtime import QiskitRuntimeService
                QiskitRuntimeService.save_account(
                    channel="ibm_quantum",
                    token=self.ibm_token,
                    overwrite=True,
                )
                self.service = QiskitRuntimeService(channel="ibm_quantum")
            except Exception as e:
                print(f"[QFTBridgeReal] IBM Runtime init failed: {e}")
                self.use_real = False
                self.service = None

    def _load_cache(self) -> dict:
        if CACHE_FILE.exists():
            try:
                return json.loads(CACHE_FILE.read_text())
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        try:
            CACHE_FILE.write_text(json.dumps(self._cache, indent=2))
        except Exception:
            pass

    def _cache_key(self, n_qubits: int) -> str:
        return f"qft_{n_qubits}q"

    def run_qft_real(self, n_qubits: int) -> dict:
        """Run QFT on real IBM hardware."""
        from qiskit import QuantumCircuit
        from qiskit.circuit.library import QFT
        from qiskit_ibm_runtime import SamplerV2

        backend = self.service.least_busy(
            operational=True,
            simulator=False,
            min_num_qubits=n_qubits,
        )

        qc = QuantumCircuit(n_qubits)
        qc.h(range(n_qubits))
        qc.append(QFT(n_qubits), range(n_qubits))
        qc.measure_all()

        sampler = SamplerV2(backend=backend)
        job = sampler.run([qc], shots=1024)
        result = job.result()
        counts = result[0].data.meas.get_counts()
        total = sum(counts.values())

        return {
            "counts": counts,
            "probabilities": {k: v / total for k, v in counts.items()},
            "backend_name": backend.name,
            "n_qubits": n_qubits,
            "shots": 1024,
            "ran_on_hardware": True,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def get_qft_result(self, n_qubits: int, force_fresh: bool = False) -> dict:
        """
        Returns cached hardware result if available, otherwise runs on
        hardware (if token set) or falls back to simulator.
        """
        cache_key = self._cache_key(n_qubits)

        if not force_fresh and cache_key in self._cache:
            result = dict(self._cache[cache_key])
            result["from_cache"] = True
            return result

        if self.use_real:
            try:
                result = self.run_qft_real(n_qubits)
                self._cache[cache_key] = result
                self._save_cache()
                result["from_cache"] = False
                return result
            except Exception as e:
                return {
                    "error": str(e),
                    "ran_on_hardware": False,
                    "fallback": "simulator",
                    "from_cache": False,
                }

        # Fallback: local statevector sim
        return self._run_simulator(n_qubits)

    def _run_simulator(self, n_qubits: int) -> dict:
        from qiskit import QuantumCircuit
        from qiskit.circuit.library import QFT
        from qiskit_aer import AerSimulator
        from qiskit.compiler import transpile

        qc = QuantumCircuit(n_qubits)
        qc.h(range(n_qubits))
        qc.append(QFT(n_qubits), range(n_qubits))
        qc.measure_all()

        sim = AerSimulator()
        compiled = transpile(qc, sim)
        job = sim.run(compiled, shots=1024)
        counts = job.result().get_counts()
        total = sum(counts.values())

        return {
            "counts": counts,
            "probabilities": {k: v / total for k, v in counts.items()},
            "backend_name": "aer_simulator (local)",
            "n_qubits": n_qubits,
            "shots": 1024,
            "ran_on_hardware": False,
            "from_cache": False,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

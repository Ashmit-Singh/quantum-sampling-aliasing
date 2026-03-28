// ══════════════════════════════════════════════════════════
// INTEGRATIONS — Real Audio, CSV Sensor Data, IBM Quantum HW
// ══════════════════════════════════════════════════════════

/* ── Shared: Toast Notification ── */
function showToast(message, duration) {
  duration = duration || 4000;
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, duration);
}

/* ── Shared: Source Badge ── */
function showSourceBadge(text) {
  const badge = document.getElementById('source-badge');
  badge.textContent = text;
  badge.style.display = 'block';
}
function hideSourceBadge() {
  document.getElementById('source-badge').style.display = 'none';
}

/* ── Shared: Button Loading State ── */
function setBtnLoading(btnId, loading, labelId) {
  const btn = document.getElementById(btnId);
  const label = document.getElementById(labelId);
  if (loading) {
    btn.disabled = true;
    label.dataset.origText = label.textContent;
    label.innerHTML = '<span class="spinner"></span> Processing…';
  } else {
    btn.disabled = false;
    label.textContent = label.dataset.origText || label.textContent;
  }
}

/* ── Shared: Get current UI control values ── */
function getCurrentPipelineParams() {
  return {
    bits: parseInt(document.getElementById('adc-bits').value),
    osr: parseInt(document.getElementById('osr-sel').value),
    sampling_rate_ratio: parseFloat(document.getElementById('samp-rate').value) / 10,
  };
}

/* ── Shared: Feed pipeline response into existing viz ── */
function handlePipelineResponse(data, sourceLabel) {
  const sampRate = data.quantization ? (getCurrentPipelineParams().sampling_rate_ratio) : 10;
  const freq = 5; // real signals don't have a single freq; use default for UI
  const bits = getCurrentPipelineParams().bits;
  const osr = getCurrentPipelineParams().osr;

  renderFromData(
    data.signal,
    data.quantization,
    data.oversampling,
    data.fft,
    freq, sampRate, bits, osr
  );

  if (sourceLabel) showSourceBadge(sourceLabel);
}

// ══════════════════════════════════════════════════════════
// INTEGRATION 1 — Real Audio (Microphone + File Upload)
// ══════════════════════════════════════════════════════════

let micRecording = false;
let micStream = null;

async function toggleMicRecording() {
  if (micRecording) return; // already in progress

  const btn = document.getElementById('btn-mic');
  const label = document.getElementById('mic-label');

  try {
    micRecording = true;
    btn.disabled = true;
    label.textContent = '🔴 Recording…';

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    micStream = stream;
    const micAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = micAudioCtx.createMediaStreamSource(stream);
    const analyser = micAudioCtx.createAnalyser();
    analyser.fftSize = 4096;
    source.connect(analyser);

    // Capture 2 seconds
    await new Promise(resolve => setTimeout(resolve, 2000));

    const buffer = new Float32Array(analyser.fftSize);
    analyser.getFloatTimeDomainData(buffer);

    stream.getTracks().forEach(t => t.stop());
    micStream = null;
    micAudioCtx.close();

    label.innerHTML = '<span class="spinner"></span> Sending…';
    await sendRealAudio(Array.from(buffer), 44100, '🎙️ Live Audio');

  } catch (e) {
    showToast('❌ Microphone: ' + e.message);
  } finally {
    micRecording = false;
    btn.disabled = false;
    label.textContent = 'Record 2s';
  }
}

async function handleAudioFile(input) {
  const file = input.files[0];
  if (!file) return;

  try {
    const decodeCtx = new (window.AudioContext || window.webkitAudioContext)();
    const arrayBuffer = await file.arrayBuffer();
    const audioBuffer = await decodeCtx.decodeAudioData(arrayBuffer);
    const samples = Array.from(audioBuffer.getChannelData(0));
    decodeCtx.close();

    await sendRealAudio(samples, audioBuffer.sampleRate, '📁 File: ' + file.name);
  } catch (e) {
    showToast('❌ Audio file: ' + e.message);
  }
  input.value = ''; // reset for re-upload
}

async function sendRealAudio(samples, sampleRate, sourceLabel) {
  const params = getCurrentPipelineParams();
  const payload = {
    samples: samples,
    source_sample_rate: sampleRate,
    bits: params.bits,
    osr: params.osr,
    sampling_rate_ratio: params.sampling_rate_ratio,
  };

  try {
    const res = await fetch(API_BASE + '/api/pipeline/audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    handlePipelineResponse(data, sourceLabel);
  } catch (e) {
    showToast('❌ /api/pipeline/audio: ' + e.message);
  }
}

// ══════════════════════════════════════════════════════════
// INTEGRATION 2 — CSV / Sensor Data
// ══════════════════════════════════════════════════════════

async function handleCSVFile(input) {
  const file = input.files[0];
  if (!file) return;

  const params = getCurrentPipelineParams();
  const formData = new FormData();
  formData.append('file', file);
  formData.append('bits', params.bits);
  formData.append('osr', params.osr);
  formData.append('sampling_rate_ratio', params.sampling_rate_ratio);

  try {
    const res = await fetch(API_BASE + '/api/pipeline/csv', {
      method: 'POST',
      body: formData, // no Content-Type — browser sets boundary
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    const rows = data.source ? data.source.original_rows : '?';
    handlePipelineResponse(data, '📊 CSV: ' + file.name + ' (' + rows + ' rows)');
  } catch (e) {
    showToast('❌ /api/pipeline/csv: ' + e.message);
  }
  input.value = '';
}

// ══════════════════════════════════════════════════════════
// INTEGRATION 3 — IBM Quantum Hardware QFT
// ══════════════════════════════════════════════════════════

async function checkQFTHardwareStatus() {
  try {
    const res = await fetch(API_BASE + '/api/qft/hardware/status');
    if (!res.ok) throw new Error(res.statusText);
    const data = await res.json();
    const dot = document.getElementById('qft-status-dot');
    const text = document.getElementById('qft-status-text');
    if (data.use_real_hardware) {
      dot.className = 'qft-status-dot green';
      text.textContent = 'IBM connected';
    } else if (data.ibm_token_set) {
      dot.className = 'qft-status-dot green';
      text.textContent = 'Token set (init pending)';
    } else {
      dot.className = 'qft-status-dot grey';
      text.textContent = 'Simulator only';
    }
    if (data.cache_keys && data.cache_keys.length > 0) {
      text.textContent += ' · ' + data.cache_keys.length + ' cached';
    }
  } catch (e) {
    const dot = document.getElementById('qft-status-dot');
    const text = document.getElementById('qft-status-text');
    dot.className = 'qft-status-dot grey';
    text.textContent = 'Backend offline';
  }
}

async function runHardwareQFT() {
  setBtnLoading('btn-qft-hw', true, 'qft-hw-label');
  try {
    const res = await fetch(API_BASE + '/api/qft/hardware?n_qubits=4', {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    renderQFTHardwareResult(data);
  } catch (e) {
    showToast('❌ /api/qft/hardware: ' + e.message);
  } finally {
    setBtnLoading('btn-qft-hw', false, 'qft-hw-label');
  }
}

function renderQFTHardwareResult(data) {
  const container = document.getElementById('qft-hw-result');

  // Badge
  let badges = '';
  if (data.ran_on_hardware) {
    badges += '<span class="qft-badge hw">🔴 Real Hardware</span>';
  } else {
    badges += '<span class="qft-badge sim">🟡 Simulator</span>';
  }
  if (data.from_cache) {
    badges += '<span class="qft-badge cache">cached</span>';
  }

  // Bar chart from probabilities
  let barChart = '';
  if (data.probabilities) {
    const entries = Object.entries(data.probabilities).sort((a, b) => a[0].localeCompare(b[0]));
    const maxProb = Math.max(...entries.map(e => e[1]));
    const bars = entries.map(([state, prob]) => {
      const pct = (prob / maxProb * 100).toFixed(0);
      return '<div class="qft-bar" style="height:' + pct + '%" title="' + state + ': ' + (prob * 100).toFixed(1) + '%"></div>';
    }).join('');
    barChart = '<div class="qft-bar-chart">' + bars + '</div>';
  }

  // Info
  let info = '<div style="margin-top:6px;color:var(--muted);line-height:1.8;">';
  info += '<div>Backend: <span style="color:var(--text)">' + (data.backend_name || 'unknown') + '</span></div>';
  info += '<div>Qubits: <span style="color:var(--text)">' + (data.n_qubits || '?') + '</span> · Shots: <span style="color:var(--text)">' + (data.shots || '?') + '</span></div>';
  if (data.timestamp) info += '<div>Time: <span style="color:var(--text)">' + data.timestamp + '</span></div>';
  if (data.error) info += '<div style="color:var(--red)">Error: ' + data.error + '</div>';
  info += '</div>';

  container.innerHTML = badges + barChart + info;
}

// ══════════════════════════════════════════════════════════
// CIRCUIT INSPECTOR MODAL — exposes Qiskit circuit diagrams
// ══════════════════════════════════════════════════════════

function openCircuitModal() {
  const modal = document.getElementById('circuit-modal');
  const pre = document.getElementById('circuit-diagram-pre');
  const meta = document.getElementById('circuit-meta');

  if (_lastQftData && _lastQftData.circuit_diagram) {
    pre.textContent = _lastQftData.circuit_diagram;
    let metaHtml = '';
    if (_lastQftData.n_qubits) metaHtml += 'Qubits: <span>' + _lastQftData.n_qubits + '</span>';
    if (_lastQftData.circuit_depth) metaHtml += ' · Circuit Depth: <span>' + _lastQftData.circuit_depth + '</span>';
    if (_lastQftData.gate_count) metaHtml += ' · Gate Count: <span>' + _lastQftData.gate_count + '</span>';
    if (_lastQftData.encoding_method) metaHtml += ' · Encoding: <span>' + _lastQftData.encoding_method + '</span>';
    meta.innerHTML = metaHtml || 'Amplitude encoding → QFT';
  } else {
    pre.textContent = 'No circuit data available.\n\nStart the Python backend to generate Qiskit quantum circuits.\nThe circuit shows:\n  1. Amplitude encoding of sampled signal into 2^n quantum amplitudes\n  2. Quantum Fourier Transform (QFT) gate decomposition\n  3. Full state preparation gate depth';
    meta.innerHTML = '';
  }

  modal.classList.add('visible');
}

function closeCircuitModal() {
  document.getElementById('circuit-modal').classList.remove('visible');
}

// Close modal on Escape key
window.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeCircuitModal();
});

// ── Init: check QFT status on page load ──
setTimeout(checkQFTHardwareStatus, 1500);


// ══════════════════════════════════════════════════════════
// APP — charts, API integration, stage management, animation, audio
// ══════════════════════════════════════════════════════════

/* ── Chart System ── */
let chartData = { sig: null, bits: 8, osr: 1, snrT: 0, snrS: 0, fftMag: [], err: [], freq: 5, sampRate: 10 };
let currentChartTab = 0;

function setChartTab(n) {
  currentChartTab = n;
  document.querySelectorAll('.chart-tab').forEach((t, i) => t.classList.toggle('active', i === n));
  for (let i = 0; i < 5; i++) {
    const el = document.getElementById('cwrap' + i);
    if (el) el.style.display = i === n ? '' : 'none';
  }
}

function updateCharts() {
  if (!chartData.sig) return;
  drawScope(); drawFFT(); drawSNR(); drawError();
}

function chartSetup(id) {
  const c = document.getElementById(id);
  const w = c.parentElement.clientWidth - 20;
  c.width = w; const h = c.height;
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, w, h);
  // Grid
  ctx.strokeStyle = 'rgba(68,136,255,0.08)'; ctx.lineWidth = 0.5;
  for (let i = 0; i <= 10; i++) { const x = i * w / 10; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let i = 0; i <= 4; i++) { const y = i * h / 4; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
  return { c, ctx, w, h };
}

function drawScope() {
  const { ctx, w, h } = chartSetup('c2d-scope');
  const sig = chartData.sig;
  // Original signal
  ctx.strokeStyle = '#4488ff'; ctx.lineWidth = 1.5; ctx.beginPath();
  for (let i = 0; i < sig.s.length; i++) {
    const x = i / sig.s.length * w, y = h / 2 - sig.s[i] * h * 0.4;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();
  // Quantized
  if (chartData.err) {
    const { q } = DSP.quantize(sig.s, chartData.bits);
    ctx.strokeStyle = '#ff4455'; ctx.lineWidth = 1; ctx.globalAlpha = 0.6; ctx.beginPath();
    for (let i = 0; i < q.length - 1; i++) {
      const x1 = i / q.length * w, x2 = (i + 1) / q.length * w, y = h / 2 - q[i] * h * 0.4;
      ctx.moveTo(x1, y); ctx.lineTo(x2, y);
    }
    ctx.stroke(); ctx.globalAlpha = 1;
  }
}

function drawFFT() {
  const { ctx, w, h } = chartSetup('c2d-fft');
  const fft = chartData.fftMag;
  if (!fft || fft.length === 0) return;
  const barW = w / fft.length;
  for (let i = 0; i < fft.length; i++) {
    const norm = Math.max(0, Math.min(1, (fft[i] + 80) / 80));
    const bh = norm * h * 0.9;
    // Color gradient
    const r = Math.floor(68 + norm * 187), g = Math.floor(136 - norm * 68), b = Math.floor(255 - norm * 200);
    ctx.fillStyle = `rgb(${r},${g},${b})`;
    ctx.fillRect(i * barW, h - bh, Math.max(barW - 1, 1), bh);
  }
  // Nyquist line
  ctx.strokeStyle = '#ff445580'; ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
  const nyqX = w * 0.5;
  ctx.beginPath(); ctx.moveTo(nyqX, 0); ctx.lineTo(nyqX, h); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = '#ff4455'; ctx.font = '9px "JetBrains Mono"'; ctx.fillText('Nyquist', nyqX + 4, 12);
}

function drawSNR() {
  const { ctx, w, h } = chartSetup('c2d-snr');
  const bars = [
    { label: 'Theory', val: chartData.snrT, color: '#ffcc44' },
    { label: 'Simulated', val: chartData.snrS, color: '#33ffaa' },
    { label: '+OSR', val: chartData.snrS + DSP.osrGain(chartData.osr), color: '#ff8833' }
  ];
  const maxVal = Math.max(...bars.map(b => b.val), 1);
  const barW = w / (bars.length * 2 + 1);
  bars.forEach((b, i) => {
    const bh = (b.val / maxVal) * h * 0.75;
    const x = (i * 2 + 1) * barW;
    ctx.fillStyle = b.color; ctx.globalAlpha = 0.8;
    ctx.fillRect(x, h - bh - 20, barW, bh);
    ctx.globalAlpha = 1; ctx.fillStyle = b.color;
    ctx.font = '10px "JetBrains Mono"'; ctx.textAlign = 'center';
    ctx.fillText(b.val.toFixed(1) + ' dB', x + barW / 2, h - bh - 24);
    ctx.fillStyle = '#5a6a8a'; ctx.font = '9px "JetBrains Mono"';
    ctx.fillText(b.label, x + barW / 2, h - 6);
  });
  ctx.textAlign = 'start';
}

function drawError() {
  const { ctx, w, h } = chartSetup('c2d-err');
  const err = chartData.err;
  if (!err || err.length === 0) return;
  const { LSB } = DSP.quantize(chartData.sig.s, chartData.bits);
  for (let x = 0; x < w; x++) {
    const idx = Math.floor(x / w * err.length);
    const norm = Math.min(Math.abs(err[idx]) / (LSB * 0.5), 1);
    const r = Math.floor(norm * 255), g = Math.floor((1 - norm) * 40), b = Math.floor((1 - norm) * 255);
    ctx.fillStyle = `rgb(${r},${g},${b})`;
    ctx.fillRect(x, 0, 1, h);
  }
}

/* ── API Integration ── */
const RENDER_URL = 'https://quantum-sampling-aliasing.onrender.com';
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000' : RENDER_URL;

// ══════════════════════════════════════════════════════════
// PRIMARY UPDATE PATH — 100% client-side, zero network latency
// Python backend is ONLY used for async QFT (Qiskit) calls
// ══════════════════════════════════════════════════════════
function updateAll() {
  const type = document.getElementById('sig-type').value;
  const freq = parseFloat(document.getElementById('sig-freq').value);
  const amp = parseFloat(document.getElementById('sig-amp').value) / 10;
  const noise = parseFloat(document.getElementById('sig-noise').value);
  const sampRate = parseFloat(document.getElementById('samp-rate').value) / 10;
  const bits = parseInt(document.getElementById('adc-bits').value);
  const osr = parseInt(document.getElementById('osr-sel').value);
  const fs = freq * sampRate;

  // Harmonic-aware aliasing detection (not just sampRate < 2)
  const isAliased = DSP.isAliased(freq, sampRate, type);

  document.getElementById('lbl-freq').textContent = freq + ' Hz';
  document.getElementById('lbl-amp').textContent = amp.toFixed(1);
  document.getElementById('lbl-noise').textContent = (noise / 100).toFixed(2);
  document.getElementById('lbl-fs').textContent = sampRate.toFixed(1) + '× Nyquist';
  document.getElementById('lbl-bits').textContent = bits + ' bits';
  document.getElementById('lbl-osr').textContent = osr + '×';

  const badge = document.getElementById('nyquist-badge');
  if (isAliased) {
    badge.className = 'aliased'; badge.textContent = '⚠ ALIASED — below Nyquist';
    document.getElementById('lbl-alias').textContent = DSP.aliasFreq(freq, fs).toFixed(2) + ' Hz';
    glitchT = 2.0;
    canvas3d.style.transition = 'filter 0.1s ease';
    canvas3d.style.filter = 'hue-rotate(18deg) contrast(1.08)';
    setTimeout(() => { canvas3d.style.filter = ''; }, 380);
    const tb = document.getElementById('topbar');
    tb.style.borderBottomColor = 'rgba(255,68,85,0.5)';
    setTimeout(() => tb.style.borderBottomColor = '', 250);
  } else {
    badge.className = 'safe'; badge.textContent = '✓ Above Nyquist';
    document.getElementById('lbl-alias').textContent = '—';
  }

  // ── Instant client-side DSP (< 1ms for N=512) ──
  updateAllJS(type, freq, amp, noise, sampRate, bits, osr);

  // ── Fire async QFT in background (debounced) ──
  triggerAsyncQFT(type, freq, amp, noise);
}

function updateAllJS(type, freq, amp, noise, sampRate, bits, osr) {
  const sig = DSP.generateSignal(type, freq, amp, noise);
  const { q, err, LSB } = DSP.quantize(sig.s, bits);
  const snrT = DSP.snrTheory(bits);
  const snrS = DSP.snrSimulated(sig.s, err);

  // ── REAL oversampling via 4th-order Butterworth IIR filter ──
  // (replaces the old arithmetic SNR hack: snrS + osrG)
  const osrRes = DSP.oversample(sig.s, bits, osr);

  const fftMag = DSP.fft(sig.s);
  renderFromData(
    sig,
    { q, error: err, lsb_size: LSB, snr_theoretical: snrT, snr_simulated: snrS, levels: Math.pow(2, bits) },
    { snr_gain_db: osrRes.snr_gain_db, enob: osrRes.enob, effective_snr: osrRes.effective_snr, filtered: osrRes.filtered },
    { magnitudes_db: fftMag },
    freq, sampRate, bits, osr
  );
}

function renderFromData(sig, quantization, oversampling, fftData, freq, sampRate, bits, osr) {
  const err = quantization.error || quantization.err;
  const LSB = quantization.lsb_size || quantization.LSB;
  const snrT = quantization.snr_theoretical;
  const snrS = quantization.snr_simulated;
  const osrG = oversampling.snr_gain_db;
  const enob = oversampling.enob;
  const effSnr = oversampling.effective_snr;

  document.getElementById('met-snr-t').textContent = snrT.toFixed(1) + ' dB';
  document.getElementById('met-snr-s').textContent = snrS.toFixed(1) + ' dB';
  document.getElementById('met-enob').textContent = enob.toFixed(2) + ' bits';
  document.getElementById('met-osrg').textContent = '+' + osrG.toFixed(1) + ' dB';
  document.getElementById('met-ratio').textContent = sampRate.toFixed(1) + '×';
  document.getElementById('lbl-lsb').textContent = LSB.toFixed(4);

  // Show effective SNR if available (real Butterworth filter result)
  if (effSnr !== undefined && effSnr !== null) {
    const effEl = document.getElementById('met-eff-snr');
    if (effEl) effEl.textContent = effSnr.toFixed(1) + ' dB';
  }

  const rms = Math.sqrt(sig.s.reduce((a, v) => a + v * v, 0) / sig.s.length);
  starMat.size = 0.04 + rms * 0.07;
  starMat.opacity = 0.28 + rms * 0.35;

  chartData = { sig, bits, osr, snrT, snrS, fftMag: fftData.magnitudes_db, err, freq, sampRate, osrFiltered: oversampling.filtered };
  updateCharts();

  clearScene();
  const prevOsrErrTo = osrErrTo;
  osrErrFrom = prevOsrErrTo ? new Float32Array(prevOsrErrTo) : null;
  osrErrTo = null; osrLerpT = 0;

  const amp = parseFloat(document.getElementById('sig-amp').value) / 10;
  switch (currentStage) {
    case 0: buildStage0(sig); break;
    case 1: buildStage1(sig, sampRate, freq, amp); break;
    case 2: buildStage2(sig, bits); break;
    case 3: buildStage3(sig, bits, osr); break;
    case 4: buildStage4(sig, bits, osr, sampRate); break;
  }
  if (currentStage === 3 && osrErrTo && osrErrFrom) { osrLerpT = 0; } else { osrLerpT = 1; }
  updateWaterfall(fftData.magnitudes_db);
  updateAudioBuffer();
}

/* ── Stage Management ── */
let currentStage = 0, animT = 0, glitchT = 0, isTransitioning = false;

const STAGE_LABELS = ['Stage 01 — Analog Signal', 'Stage 02 — Sampling & Aliasing', 'Stage 03 — ADC Quantization', 'Stage 04 — Oversampling', 'Stage 05 — Full Pipeline'];
const CALLOUTS = [
  'The continuous analog signal — infinite resolution. 8 history snapshots trail behind.',
  'Nyquist: sample ≥ 2× freq or aliases appear. Drag below 2× for the ghost signal + glitch effect.',
  'Each ADC bit = +6 dB SNR. 2-bit = 4 levels. Error terrain shows quantization noise magnitude.',
  'Oversampling spreads noise wider. 4× = +1 effective bit. Watch noise terrain flatten over 600ms.',
  'Full pipeline: original → sampled → quantized → oversampled. Particles flow along cleanest signal.'
];
const STAGE_RELEVANCE = {
  0: ['sec-signal'], 1: ['sec-signal', 'sec-samp'], 2: ['sec-signal', 'sec-adc'],
  3: ['sec-signal', 'sec-adc', 'sec-osr'], 4: ['sec-signal', 'sec-samp', 'sec-adc', 'sec-osr']
};

function updateSectionDimming(stage) {
  const rel = STAGE_RELEVANCE[stage] || [];
  ['sec-signal', 'sec-samp', 'sec-adc', 'sec-osr'].forEach(id =>
    document.getElementById(id).classList.toggle('dimmed', !rel.includes(id)));
}

function setStage(n) {
  if (isTransitioning) return;
  isTransitioning = true;
  const overlay = document.getElementById('fade-overlay');
  overlay.style.transition = 'opacity .2s'; overlay.style.opacity = '1'; overlay.style.pointerEvents = 'all';
  setTimeout(() => {
    currentStage = n;
    document.querySelectorAll('.stage-btn').forEach((b, i) => b.classList.toggle('active', i === n));
    document.getElementById('stage-label').textContent = STAGE_LABELS[n];
    document.getElementById('stage-callout').textContent = CALLOUTS[n];
    updateSectionDimming(n);
    updateAll();
    overlay.style.opacity = '0'; overlay.style.pointerEvents = 'none';
    setTimeout(() => isTransitioning = false, 220);
  }, 200);
}

/* ── Resize ── */
function onResize() {
  const sw = W(), sh = H();
  renderer.setSize(sw, sh);
  camera.aspect = sw / sh; camera.updateProjectionMatrix();
  canvas3d.style.marginLeft = isMobile() ? '0' : '260px';
  canvas3d.style.marginTop = '52px';
  matBloomH.uniforms.h.value = 1 / sw;
  matBloomV.uniforms.v.value = 1 / sh;
  buildRTs(); updateCharts();
}

/* ── FPS Counter ── */
const fpsBuf = new Float32Array(30); let fpsIdx = 0, fpsLast = performance.now();
function tickFPS() {
  const now = performance.now();
  fpsBuf[fpsIdx % 30] = 1000 / (now - fpsLast); fpsIdx++; fpsLast = now;
  if (fpsIdx % 10 === 0) document.getElementById('fps-counter').textContent = (fpsBuf.reduce((a, b) => a + b, 0) / 30).toFixed(0) + ' fps';
}

function easeOut(t) { return 1 - Math.pow(1 - t, 3); }
const dummyAnim = new THREE.Object3D();
let updateTimer = null;
function debouncedUpdate() { clearTimeout(updateTimer); updateTimer = setTimeout(updateAll, 60); }

// ══════════════════════════════════════════════════════════
// ASYNC QUANTUM ENGINE — background QFT, never blocks UI
// ══════════════════════════════════════════════════════════
let _qftTimer = null;
let _qftPending = false;
let _lastQftData = null;

function triggerAsyncQFT(type, freq, amp, noise) {
  clearTimeout(_qftTimer);
  _qftTimer = setTimeout(() => _fetchQFT(type, freq, amp, noise), 800);
}

async function _fetchQFT(type, freq, amp, noise) {
  if (_qftPending) return;
  _qftPending = true;

  const qftStatus = document.getElementById('qft-async-status');
  if (qftStatus) { qftStatus.textContent = '⏳ Computing QFT…'; qftStatus.style.opacity = '1'; }

  try {
    const payload = { signal_type: type, frequency: freq, amplitude: amp, noise_level: noise / 100 };
    const res = await fetch(`${API_BASE}/api/qft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    _lastQftData = data;
    renderQFTChart(data);
    if (qftStatus) { qftStatus.textContent = '✓ QFT ready'; setTimeout(() => { qftStatus.style.opacity = '0.5'; }, 1500); }
  } catch (e) {
    console.warn('QFT backend offline:', e.message);
    if (qftStatus) { qftStatus.textContent = '⚠ Backend offline'; qftStatus.style.opacity = '0.6'; }
  } finally {
    _qftPending = false;
  }
}

function renderQFTChart(data) {
  const canvas = document.getElementById('c2d-qft');
  if (!canvas) return;
  const w = canvas.parentElement.clientWidth - 20;
  canvas.width = w;
  const h = canvas.height;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, w, h);

  // Grid
  ctx.strokeStyle = 'rgba(119,102,255,0.08)'; ctx.lineWidth = 0.5;
  for (let i = 0; i <= 10; i++) { const x = i * w / 10; ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
  for (let i = 0; i <= 4; i++) { const y = i * h / 4; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }

  // Get probabilities
  const probs = data.measurement_probabilities || data.amplitudes || [];
  if (probs.length === 0) {
    ctx.fillStyle = '#5a6a8a'; ctx.font = '11px "JetBrains Mono"'; ctx.textAlign = 'center';
    ctx.fillText('No QFT data — start backend for quantum results', w / 2, h / 2);
    return;
  }

  const maxP = Math.max(...probs, 1e-10);
  const barW = w / probs.length;
  for (let i = 0; i < probs.length; i++) {
    const norm = probs[i] / maxP;
    const bh = norm * h * 0.85;
    // Purple gradient for quantum
    const r = Math.floor(119 + norm * 50);
    const g = Math.floor(102 - norm * 60);
    const b = Math.floor(255 - norm * 40);
    ctx.fillStyle = `rgb(${r},${g},${b})`;
    ctx.fillRect(i * barW, h - bh, Math.max(barW - 1, 1), bh);
  }

  // Labels
  ctx.fillStyle = '#7766ff'; ctx.font = '9px "JetBrains Mono"'; ctx.textAlign = 'left';
  ctx.fillText('|ψ|² distribution — ' + (data.n_qubits || '?') + ' qubits', 6, 12);

  // Show circuit info if available
  if (data.circuit_depth || data.gate_count) {
    ctx.fillStyle = '#5a6a8a'; ctx.textAlign = 'right';
    ctx.fillText('Depth: ' + (data.circuit_depth || '?') + ' · Gates: ' + (data.gate_count || '?'), w - 6, 12);
  }

  // Update inspect button state
  const inspBtn = document.getElementById('btn-inspect-circuit');
  if (inspBtn) inspBtn.disabled = !data.circuit_diagram;
}

/* ── Animation Loop ── */
function animate() {
  requestAnimationFrame(animate);
  animT += 0.005; tickFPS();
  if (glitchT > 0) glitchT = Math.max(0, glitchT - 0.016);

  // Energy shader time update
  sceneObjects.forEach(o => {
    if (o.material && o.material.uniforms && o.material.uniforms.time) o.material.uniforms.time.value = animT;
  });

  // Sinc pulse animation
  sceneObjects.forEach(o => {
    if (o.userData.isSincPulse) {
      const phase = (animT * 2.0 - o.userData.sincOffset) % 3.0;
      o.material.opacity = phase > 0 && phase < 1 ? phase * 0.4 : (phase >= 1 && phase < 2 ? (2 - phase) * 0.4 : 0);
    }
  });

  // Particle flow
  sceneObjects.forEach(o => {
    if (o.userData.isParticles && o.userData.curve) {
      const pos = o.geometry.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const t = ((animT * 0.3 + i / pos.count) % 1);
        const pt = o.userData.curve.getPoint(t);
        pos.setXYZ(i, pt.x, pt.y, pt.z);
      }
      pos.needsUpdate = true;
    }
  });

  // Error particle animation
  sceneObjects.forEach(o => {
    if (o.userData.isErrParticles) {
      const em = o.userData.errMags, bYs = o.userData.baseYs, xPs = o.userData.xPositions, zPs = o.userData.zPositions;
      if (!em) return;
      for (let i = 0; i < o.count; i++) {
        const y = bYs[i] + Math.sin(animT * 3 + i) * 0.4 * (em[i] || 0) * 6;
        dummyAnim.position.set(xPs[i], y, zPs[i]); dummyAnim.updateMatrix();
        o.setMatrixAt(i, dummyAnim.matrix);
      }
      o.instanceMatrix.needsUpdate = true;
    }
  });

  // OSR terrain lerp
  if (currentStage === 3 && osrMeshValid && osrTerrainRef && osrErrFrom && osrErrTo && osrLerpT < 1) {
    osrLerpT = Math.min(1, osrLerpT + 0.016 / 0.6);
    const lerped = easeOut(osrLerpT);
    const pos = osrTerrainRef.geo.attributes.position;
    for (let i = 0; i < osrTerrainRef.posCount; i++) pos.setY(i, osrErrFrom[i] + (osrErrTo[i] - osrErrFrom[i]) * lerped);
    pos.needsUpdate = true; osrTerrainRef.geo.computeVertexNormals();
  }

  stars.rotation.y = animT * 0.03;
  orbitCamera();

  // Bloom pipeline
  bloomScene.remove(quadH, quadV, quadC, quadF);
  renderer.setRenderTarget(rtMain); renderer.clear(); renderer.render(scene, camera);
  matBloomH.uniforms.tDiffuse.value = rtMain.texture;
  bloomScene.add(quadH); renderer.setRenderTarget(rtBloomH); renderer.clear(); renderer.render(bloomScene, bloomCam);
  bloomScene.remove(quadH);
  matBloomV.uniforms.tDiffuse.value = rtBloomH.texture;
  bloomScene.add(quadV); renderer.setRenderTarget(rtBloomV); renderer.clear(); renderer.render(bloomScene, bloomCam);
  bloomScene.remove(quadV);
  matComposite.uniforms.tBase.value = rtMain.texture; matComposite.uniforms.tBloom.value = rtBloomV.texture;
  bloomScene.add(quadC); renderer.setRenderTarget(rtComposite); renderer.clear(); renderer.render(bloomScene, bloomCam);
  bloomScene.remove(quadC);
  matFilm.uniforms.tDiffuse.value = rtComposite.texture; matFilm.uniforms.time.value = animT;
  matFilm.uniforms.glitch.value = glitchT > 0 ? Math.min(1, glitchT) : 0;
  bloomScene.add(quadF); renderer.setRenderTarget(null); renderer.clear(); renderer.render(bloomScene, bloomCam);
}

/* ── Web Audio Engine ── */
let audioCtx = null, activeSource = null, isAudioEnabled = false;

function toggleAudio() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  isAudioEnabled = !isAudioEnabled;
  const btn = document.getElementById('btn-audio');
  if (isAudioEnabled) {
    audioCtx.resume();
    btn.textContent = 'Stop Audio Engine'; btn.style.background = '#ff445522'; btn.style.borderColor = '#ff4455'; btn.style.color = '#ff4455';
    updateAudioBuffer();
  } else {
    audioCtx.suspend();
    btn.textContent = 'Start Audio Engine'; btn.style.background = '#4488ff22'; btn.style.borderColor = '#4488ffaa'; btn.style.color = '#c8d4f0';
    if (activeSource) { activeSource.stop(); activeSource = null; }
  }
}

function updateAudioBuffer() {
  if (!isAudioEnabled || !audioCtx || !chartData.sig) return;
  const modeEl = document.getElementById('audio-mode');
  if (!modeEl) return;
  const mode = modeEl.value;
  const freq = chartData.freq, sampRate = chartData.sampRate, bits = chartData.bits, osr = chartData.osr;
  const fs_hz = freq * sampRate;
  const type = document.getElementById('sig-type').value;
  const amp = parseFloat(document.getElementById('sig-amp').value) / 10;
  const sampleRate = audioCtx.sampleRate, duration = 1.0, length = sampleRate * duration;
  const buffer = audioCtx.createBuffer(1, length, sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate; let v = 0;
    let render_f = freq;
    if (mode === 'aliased' && fs_hz < 2 * freq) render_f = DSP.aliasFreq(freq, fs_hz);
    if (type === 'sine') v = Math.sin(2 * Math.PI * render_f * t);
    else if (type === 'square') v = Math.sign(Math.sin(2 * Math.PI * render_f * t));
    else if (type === 'chirp') v = Math.sin(2 * Math.PI * (render_f + render_f * 2 * t) * t);
    else if (type === 'multi') v = Math.sin(2 * Math.PI * render_f * t) * 0.6 + Math.sin(2 * Math.PI * render_f * 3.1 * t) * 0.4;
    v *= amp;
    if (mode === 'quantized') { const lsb = (2 * amp) / Math.pow(2, bits); v = Math.round(v / lsb) * lsb; }
    if (mode === 'oversampled') {
      const lsb = (2 * amp) / Math.pow(2, bits);
      const qv = Math.round((v + (Math.random() - 0.5) * lsb) / lsb) * lsb;
      v = v - (v - qv) / Math.sqrt(osr);
    }
    data[i] = v * 0.5;
  }
  if (activeSource) activeSource.stop();
  activeSource = audioCtx.createBufferSource();
  activeSource.buffer = buffer; activeSource.loop = true;
  activeSource.connect(audioCtx.destination); activeSource.start(0);
}

/* ── Keyboard Shortcuts ── */
window.addEventListener('keydown', e => {
  if (e.key >= '1' && e.key <= '5') setStage(parseInt(e.key) - 1);
  if (e.key === 'r' || e.key === 'R') { orb.theta = 0.5; orb.phi = 1.1; orb.r = 10; }
  if (e.key === 'g' || e.key === 'G') { glitchT = 2.0; }
});

/* ── Init ── */
window.addEventListener('resize', onResize);
onResize();
updateSectionDimming(0);
updateAll();
animate();

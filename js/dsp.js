// ══════════════════════════════════════════════════════════
// DSP MODULE — client-side math (parity with backend/dsp_engine.py)
// Fixes applied:
//   ✓ Linear chirp: phase = 2π(f₀t + 0.5·k·t²)
//   ✓ Full 512-point Cooley-Tukey FFT (no truncation)
//   ✓ Harmonic-aware aliasing detection (multi=3.1f, chirp=3f)
//   ✓ Real 4th-order Butterworth IIR filter for oversampling
// ══════════════════════════════════════════════════════════
const DSP = {
  N_SAMPLES: 512,

  // ── Signal Generation ─────────────────────────────────
  generateSignal(type, freq, amp, noise) {
    const N = this.N_SAMPLES;
    const t = new Float64Array(N);
    const s = new Float64Array(N);
    for (let i = 0; i < N; i++) {
      t[i] = i / N;
      const ti = t[i];
      if (type === 'sine')        s[i] = Math.sin(2 * Math.PI * freq * ti);
      else if (type === 'square') s[i] = Math.sign(Math.sin(2 * Math.PI * freq * ti));
      else if (type === 'chirp') {
        // Linear chirp: sweep from freq to 3*freq over 1 second
        const f0 = freq, k = freq * 2; // f1 = 3*freq, k = f1-f0
        s[i] = Math.sin(2 * Math.PI * (f0 * ti + 0.5 * k * ti * ti));
      }
      else if (type === 'multi')  s[i] = Math.sin(2 * Math.PI * freq * ti) * 0.6 +
                                         Math.sin(2 * Math.PI * freq * 3.1 * ti) * 0.4;
      s[i] *= amp;
      if (noise > 0) s[i] += (Math.random() - 0.5) * 2 * (noise / 100) * amp;
    }
    return { t: Array.from(t), s: Array.from(s) };
  },

  // ── Quantize ──────────────────────────────────────────
  quantize(samples, bits) {
    const levels = Math.pow(2, bits);
    let amp = 0;
    for (let i = 0; i < samples.length; i++) amp = Math.max(amp, Math.abs(samples[i]));
    if (amp === 0) amp = 1;
    const LSB = (2 * amp) / levels;
    const q = new Float64Array(samples.length);
    const err = new Float64Array(samples.length);
    for (let i = 0; i < samples.length; i++) {
      q[i] = Math.round(samples[i] / LSB) * LSB;
      err[i] = samples[i] - q[i];
    }
    return { q: Array.from(q), err: Array.from(err), LSB, levels };
  },

  // ── Full 512-point Cooley-Tukey FFT ───────────────────
  fft(samples) {
    const N = this.N_SAMPLES; // Use full 512 points
    const re = new Float64Array(N);
    const im = new Float64Array(N);
    // Hanning window + copy
    for (let i = 0; i < N; i++) {
      const w = 0.5 * (1 - Math.cos(2 * Math.PI * i / N));
      re[i] = (i < samples.length ? samples[i] : 0) * w;
    }
    // Bit-reversal permutation
    for (let i = 0, j = 0; i < N; i++) {
      if (i < j) {
        [re[i], re[j]] = [re[j], re[i]];
        [im[i], im[j]] = [im[j], im[i]];
      }
      let m = N >> 1;
      while (m >= 1 && j >= m) { j -= m; m >>= 1; }
      j += m;
    }
    // Butterfly passes
    for (let s = 1; s <= Math.log2(N); s++) {
      const m = 1 << s;
      const wRe = Math.cos(-2 * Math.PI / m);
      const wIm = Math.sin(-2 * Math.PI / m);
      for (let k = 0; k < N; k += m) {
        let curRe = 1, curIm = 0;
        for (let j = 0; j < m / 2; j++) {
          const tRe = curRe * re[k + j + m / 2] - curIm * im[k + j + m / 2];
          const tIm = curRe * im[k + j + m / 2] + curIm * re[k + j + m / 2];
          re[k + j + m / 2] = re[k + j] - tRe;
          im[k + j + m / 2] = im[k + j] - tIm;
          re[k + j] += tRe;
          im[k + j] += tIm;
          const newRe = curRe * wRe - curIm * wIm;
          curIm = curRe * wIm + curIm * wRe;
          curRe = newRe;
        }
      }
    }
    const mag = new Float64Array(N / 2);
    for (let i = 0; i < N / 2; i++) {
      const m = Math.sqrt(re[i] * re[i] + im[i] * im[i]) / (N / 2);
      mag[i] = 20 * Math.log10(Math.max(m, 1e-10));
    }
    return Array.from(mag);
  },

  // ── Alias Frequency (folding formula) ─────────────────
  aliasFreq(freq, fs) {
    return Math.abs(freq - Math.round(freq / fs) * fs);
  },

  // ── Harmonic-aware maximum frequency ──────────────────
  maxFreqForType(freq, type) {
    if (type === 'multi') return freq * 3.1;
    if (type === 'chirp') return freq * 3.0;
    return freq;
  },

  // ── Harmonic-aware aliasing check ─────────────────────
  isAliased(freq, sampRate, type) {
    const fs = freq * sampRate;
    const nyq = fs / 2;
    const maxF = this.maxFreqForType(freq, type || 'sine');
    return maxF > nyq;
  },

  // ── SNR Theory (ideal) ────────────────────────────────
  snrTheory(bits) {
    return 6.02 * bits + 1.76;
  },

  // ── SNR Simulated (measured) ──────────────────────────
  snrSimulated(signal, error) {
    let sp = 0, np = 0;
    for (let i = 0; i < signal.length; i++) {
      sp += signal[i] * signal[i];
      np += error[i] * error[i];
    }
    sp /= signal.length;
    np /= error.length;
    return np < 1e-12 ? 999.0 : 10 * Math.log10(sp / np);
  },

  // ══════════════════════════════════════════════════════
  // REAL OVERSAMPLING: 4th-order Butterworth IIR filter
  // This replaces the fraudulent arithmetic SNR hack.
  // ══════════════════════════════════════════════════════

  // Design 4th-order Butterworth lowpass coefficients
  // cutoff: normalized frequency (0-1, where 1 = Nyquist)
  _butterCoeffs(cutoff) {
    // Pre-warp
    const wc = Math.tan(Math.PI * cutoff / 2);
    const wc2 = wc * wc;
    const wc3 = wc2 * wc;
    const wc4 = wc2 * wc2;

    // 4th-order Butterworth analog prototype poles
    const k1 = Math.sqrt(2 + Math.sqrt(2)); // 2*cos(π/8)
    const k2 = Math.sqrt(2 - Math.sqrt(2)); // 2*cos(3π/8)

    // Two second-order sections via bilinear transform
    const sections = [];
    const alphas = [k1, k2]; // damping factors for each section

    for (const alpha of alphas) {
      const a0 = 1 + alpha * wc + wc2;
      sections.push({
        b: [wc2 / a0, 2 * wc2 / a0, wc2 / a0],
        a: [1, 2 * (wc2 - 1) / a0, (1 - alpha * wc + wc2) / a0]
      });
    }
    return sections;
  },

  // Apply cascaded second-order sections (filtfilt = forward+backward for zero-phase)
  _filtfilt(signal, sections) {
    let x = signal.slice(); // copy
    // Forward pass through each section
    for (const sec of sections) {
      const y = new Float64Array(x.length);
      y[0] = sec.b[0] * x[0];
      y[1] = sec.b[0] * x[1] + sec.b[1] * x[0] - sec.a[1] * y[0];
      for (let i = 2; i < x.length; i++) {
        y[i] = sec.b[0] * x[i] + sec.b[1] * x[i-1] + sec.b[2] * x[i-2]
             - sec.a[1] * y[i-1] - sec.a[2] * y[i-2];
      }
      x = y;
    }
    // Backward pass (reverse, filter, reverse)
    x.reverse();
    for (const sec of sections) {
      const y = new Float64Array(x.length);
      y[0] = sec.b[0] * x[0];
      y[1] = sec.b[0] * x[1] + sec.b[1] * x[0] - sec.a[1] * y[0];
      for (let i = 2; i < x.length; i++) {
        y[i] = sec.b[0] * x[i] + sec.b[1] * x[i-1] + sec.b[2] * x[i-2]
             - sec.a[1] * y[i-1] - sec.a[2] * y[i-2];
      }
      x = y;
    }
    x.reverse();
    return Array.from(x);
  },

  // Oversample with real decimation filter
  oversample(signal, bits, osr) {
    const { q, err } = this.quantize(signal, bits);
    if (osr <= 1) {
      const snrS = this.snrSimulated(signal, err);
      return { snr_gain_db: 0, effective_snr: snrS, enob: this.ENOB(snrS), filtered: q };
    }

    // Apply 4th-order Butterworth low-pass at cutoff = 1/osr of Nyquist
    const cutoff = Math.min(0.95, 1.0 / osr);
    const sections = this._butterCoeffs(cutoff);
    const filtered = this._filtfilt(q, sections);

    // Compute real post-filter SNR
    const noise = new Float64Array(signal.length);
    for (let i = 0; i < signal.length; i++) noise[i] = signal[i] - filtered[i];
    let sp = 0, np = 0;
    for (let i = 0; i < signal.length; i++) { sp += signal[i] * signal[i]; np += noise[i] * noise[i]; }
    sp /= signal.length; np /= signal.length;
    const effSnr = np < 1e-12 ? 999.0 : 10 * Math.log10(sp / np);
    const gain = 10 * Math.log10(osr);

    return { snr_gain_db: gain, effective_snr: effSnr, enob: this.ENOB(effSnr), filtered };
  },

  osrGain(osr) {
    return osr > 1 ? 10 * Math.log10(osr) : 0;
  },

  ENOB(snr) {
    return (snr - 1.76) / 6.02;
  }
};

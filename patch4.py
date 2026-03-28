import re

html = open('index.html', 'r', encoding='utf-8').read()

audio_js = '''
// ══════════════════════════════════════════════════════════
// WEB AUDIO ENGINE
// ══════════════════════════════════════════════════════════
let audioCtx = null;
let activeSource = null;
let isAudioEnabled = false;

function toggleAudio() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  isAudioEnabled = !isAudioEnabled;
  const btn = document.getElementById('btn-audio');
  
  if (isAudioEnabled) {
    audioCtx.resume();
    btn.textContent = 'Stop Audio Engine';
    btn.style.background = '#ff445522';
    btn.style.borderColor = '#ff4455';
    btn.style.color = '#ff4455';
    updateAudioBuffer(); // start playback immediately
  } else {
    audioCtx.suspend();
    btn.textContent = 'Start Audio Engine';
    btn.style.background = '#4488ff22';
    btn.style.borderColor = '#4488ffaa';
    btn.style.color = '#c8d4f0';
    if (activeSource) { activeSource.stop(); activeSource = null; }
  }
}

function updateAudioBuffer() {
  if (!isAudioEnabled || !audioCtx || !chartData.sig) return;
  
  const mode = document.getElementById('audio-mode').value;
  const freq = chartData.freq;
  const sampRate = chartData.sampRate;
  const bits = chartData.bits;
  const osr = chartData.osr;
  const fs_hz = freq * sampRate;
  const type = document.getElementById('sig-type').value;
  const amp = parseFloat(document.getElementById('sig-amp').value)/10;
  
  const sampleRate = audioCtx.sampleRate;
  const duration = 1.0; 
  const length = sampleRate * duration;
  const buffer = audioCtx.createBuffer(1, length, sampleRate);
  const data = buffer.getChannelData(0);

  // Generate math representation 
  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    let v = 0;
    
    // Base frequency representation (can alias!)
    let render_f = freq;
    let is_aliasing = false;
    
    if (mode === 'aliased' && fs_hz < 2*freq) {
        render_f = DSP.aliasFreq(freq, fs_hz);
        is_aliasing = true;
    }

    if (type === 'sine')   v = Math.sin(2*Math.PI*render_f*t);
    else if (type === 'square') v = Math.sign(Math.sin(2*Math.PI*render_f*t));
    else if (type === 'chirp')  v = Math.sin(2*Math.PI*(render_f+render_f*2*t)*t);
    else if (type === 'multi')  v = Math.sin(2*Math.PI*render_f*t)*.6 + Math.sin(2*Math.PI*render_f*3.1*t)*.4;
    
    v *= amp;

    if (mode === 'quantized') {
       const levels = Math.pow(2, bits);
       const lsb = (2 * amp) / levels;
       v = Math.round(v / lsb) * lsb;
    }
    
    if (mode === 'oversampled') {
       const levels = Math.pow(2, bits);
       const lsb = (2 * amp) / levels;
       // Add high freq noise mimicking dither then quantizing, then LPF (simulating OSR)
       const noise = (Math.random() - 0.5) * lsb;
       let q_val = Math.round((v + noise) / lsb) * lsb;
       // We fade OSR error by sqrt(OSR), simulating filter averaging
       const err = v - q_val;
       v = v - err / Math.sqrt(osr); 
    }
    
    data[i] = v * 0.5; // Scale volume down slightly
  }

  if (activeSource) {
    activeSource.stop();
  }

  activeSource = audioCtx.createBufferSource();
  activeSource.buffer = buffer;
  activeSource.loop = true;
  activeSource.connect(audioCtx.destination);
  activeSource.start(0);
}

const orig_render = _renderFromData;
_renderFromData = function() {
    orig_render.apply(this, arguments);
    updateAudioBuffer();
};

const orig_updateAllJS = updateAllJS;
updateAllJS = function() {
    orig_updateAllJS.apply(this, arguments);
    updateAudioBuffer();
};

'''

if "WEB AUDIO ENGINE" not in html:
    html = html.replace('</script>', audio_js + '\n</script>')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

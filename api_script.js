const API_BASE = 'http://localhost:8000';

async function updateAll() {
  const type=document.getElementById('sig-type').value;
  const freq=parseFloat(document.getElementById('sig-freq').value);
  const amp=parseFloat(document.getElementById('sig-amp').value)/10;
  const noise=parseFloat(document.getElementById('sig-noise').value);
  const sampRate=parseFloat(document.getElementById('samp-rate').value)/10;
  const bits=parseInt(document.getElementById('adc-bits').value);
  const osr=parseInt(document.getElementById('osr-sel').value);
  const fs=freq*sampRate;
  const isAliased=sampRate<2;

  document.getElementById('lbl-freq').textContent=freq+' Hz';
  document.getElementById('lbl-amp').textContent=amp.toFixed(1);
  document.getElementById('lbl-noise').textContent=(noise/100).toFixed(2);
  document.getElementById('lbl-fs').textContent=sampRate.toFixed(1)+'× Nyquist';
  document.getElementById('lbl-bits').textContent=bits+' bits';
  document.getElementById('lbl-osr').textContent=osr+'×';

  const badge=document.getElementById('nyquist-badge');
  if(isAliased){
    badge.className='aliased';badge.textContent='⚠ ALIASED — below Nyquist';
    document.getElementById('lbl-alias').textContent=DSP.aliasFreq(freq,fs).toFixed(2)+' Hz';
    glitchT=2.0;
    canvas3d.style.transition='filter 0.1s ease';
    canvas3d.style.filter='hue-rotate(18deg) contrast(1.08)';
    setTimeout(()=>{canvas3d.style.filter='';},380);
    const tb=document.getElementById('topbar');
    tb.style.borderBottomColor='rgba(255,68,85,0.5)';
    setTimeout(()=>tb.style.borderBottomColor='',250);
  } else {
    badge.className='safe';badge.textContent='✓ Above Nyquist';
    document.getElementById('lbl-alias').textContent='—';
  }

  const payload = {
    signal_type: type,
    frequency: freq,
    amplitude: amp,
    noise_level: noise / 100,
    sampling_rate_ratio: sampRate,
    bits: bits,
    osr: osr
  };

  try {
    const res = await fetch(`${API_BASE}/api/pipeline`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    _renderFromData(data.signal, data.quantization, data.oversampling, data.fft, freq, sampRate, bits, osr);
  } catch(e) {
    console.warn('Backend offline — using JS fallback math');
    updateAllJS(type, freq, amp, noise, sampRate, bits, osr);
  }
}

function updateAllJS(type, freq, amp, noise, sampRate, bits, osr) {
  const sig=DSP.generateSignal(type,freq,amp,noise);
  const {q,err,LSB}=DSP.quantize(sig.s,bits);
  const snrT=DSP.snrTheory(bits);
  const snrS=DSP.snrSimulated(sig.s,err);
  const osrG=DSP.osrGain(osr);
  const enob=DSP.ENOB(snrS+osrG);
  const fftMag=DSP.fft(sig.s);
  
  _renderFromData(
    sig, 
    {q: q, error: err, lsb_size: LSB, snr_theoretical: snrT, snr_simulated: snrS}, 
    {snr_gain_db: osrG, enob: enob}, 
    {magnitudes_db: fftMag}, 
    freq, sampRate, bits, osr
  );
}

function _renderFromData(sig, quantization, oversampling, fftData, freq, sampRate, bits, osr) {
  const err = quantization.error || quantization.err;
  const LSB = quantization.lsb_size || quantization.LSB;
  const snrT = quantization.snr_theoretical;
  const snrS = quantization.snr_simulated;
  const osrG = oversampling.snr_gain_db;
  const enob = oversampling.enob;

  document.getElementById('met-snr-t').textContent=snrT.toFixed(1)+' dB';
  document.getElementById('met-snr-s').textContent=snrS.toFixed(1)+' dB';
  document.getElementById('met-enob').textContent=enob.toFixed(2)+' bits';
  document.getElementById('met-osrg').textContent='+'+osrG.toFixed(1)+' dB';
  document.getElementById('met-ratio').textContent=sampRate.toFixed(1)+'×';
  document.getElementById('lbl-lsb').textContent=LSB.toFixed(4);

  const rms=Math.sqrt(sig.s.reduce((a,v)=>a+v*v,0)/sig.s.length);
  starMat.size=0.04+rms*0.07;
  starMat.opacity=0.28+rms*0.35;

  chartData={sig,bits,osr,snrT,snrS,fftMag:fftData.magnitudes_db,err,freq,sampRate};
  DSP.quantize = function(s, b) { return {q: quantization.q || quantization.quantized, err: err, LSB: LSB, levels: quantization.levels} } // Mock for stage builds temporarily
  updateCharts();

  clearScene();
  const prevOsrErrTo=osrErrTo;
  osrErrFrom=prevOsrErrTo?new Float32Array(prevOsrErrTo):null;
  osrErrTo=null;osrLerpT=0;

  let amp = parseFloat(document.getElementById('sig-amp').value)/10;
  switch(currentStage){
    case 0:buildStage0(sig);break;
    case 1:buildStage1(sig,sampRate,freq,amp);break;
    case 2:buildStage2(sig,bits);break;
    case 3:buildStage3(sig,bits,osr);break;
    case 4:buildStage4(sig,bits,osr,sampRate);break;
  }
  if(currentStage===3&&osrErrTo&&osrErrFrom){osrLerpT=0;}else{osrLerpT=1;}
  updateWaterfall(fftData.magnitudes_db);
}

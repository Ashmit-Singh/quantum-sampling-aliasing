import re

html = open('index.html', 'r', encoding='utf-8').read()

fft_old = '''function drawFFTChart(sig,freq,sampRate,fftMag){
  const c=document.getElementById('c2d-fft');
  const pw=c.parentElement.clientWidth-20;
  if(pw<=0)return;
  c.width=pw;c.height=140;
  const ctx=c.getContext('2d');
  const padL=30,padB=16;
  ctx.fillStyle='#020408';ctx.fillRect(0,0,pw,140);

  const N=fftMag.length;
  const bw=(pw-padL)/N;
  const midY=64;
  const fs_hz=freq*sampRate;

  fftMag.forEach((db,i)=>{
    const norm=Math.max(0,(db+80)/80);
    const h=norm*52;
    const x=padL+i*bw;
    const grad=ctx.createLinearGradient(0,midY-h,0,midY);
    grad.addColorStop(0,'rgba(255,255,255,.9)');
    grad.addColorStop(.3,'rgba(255,140,40,.8)');
    grad.addColorStop(.7,'rgba(140,60,255,.6)');
    grad.addColorStop(1,'rgba(40,80,255,.3)');
    ctx.fillStyle=grad;
    ctx.fillRect(x,midY-h,Math.max(1,bw-.5),h);
    const grad2=ctx.createLinearGradient(0,midY,0,midY+h*.4);
    grad2.addColorStop(0,'rgba(40,80,255,.18)');
    grad2.addColorStop(1,'rgba(40,80,255,0)');
    ctx.fillStyle=grad2;
    ctx.fillRect(x,midY,Math.max(1,bw-.5),h*.4);
  });

  const peaks=[];
  for(let i=1;i<fftMag.length-1;i++){
    if(fftMag[i]>fftMag[i-1]&&fftMag[i]>fftMag[i+1]&&fftMag[i]>-30)peaks.push({i,db:fftMag[i]});
  }
  peaks.sort((a,b)=>b.db-a.db);
  peaks.slice(0,3).forEach(pk=>{
    const x=padL+pk.i*bw+bw/2;
    const norm=Math.max(0,(pk.db+80)/80);
    const y=midY-norm*52;
    const hz_value=pk.i/N*(fs_hz/2);
    const hzStr=hz_value<10?hz_value.toFixed(2)+'Hz':hz_value<100?hz_value.toFixed(1)+'Hz':hz_value.toFixed(0)+'Hz';
    ctx.setLineDash([3,3]);
    ctx.strokeStyle='rgba(255,204,68,.55)';ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(x,midY);ctx.lineTo(x,y);ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle='#ffcc44';
    ctx.beginPath();ctx.arc(x,y,2.5,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='rgba(255,204,68,.9)';
    ctx.font='9px \"JetBrains Mono\",monospace';
    ctx.textAlign='center';
    ctx.fillText(hzStr,x,y-7);
  });

  drawAxisLabels(ctx,pw,140,{
    yLabels:['-80','-40','0'],
    yPositions:[midY,midY-26,midY-52],
    xLabels:['0','fs/4','fs/2'],
    xUnit:'',
    padLeft:padL,padBottom:padB,
    yUnit:'dB'
  });
}'''

fft_new = '''function drawFFTChart(sig,freq,sampRate,fftMag){
  const c=document.getElementById('c2d-fft');
  const pw=c.parentElement.clientWidth-20;
  if(pw<=0)return;
  c.width=pw;c.height=140;
  const ctx=c.getContext('2d');
  const padL=30,padB=16;
  ctx.fillStyle='#020408';ctx.fillRect(0,0,pw,140);

  const N=fftMag.length;
  // Let the domain be up to 100Hz (or max frequency involved)
  const max_hz = Math.max(freq * 1.5, freq * sampRate * 0.75, 100); 
  const fs_hz = freq * sampRate;
  const nyq_hz = fs_hz / 2;

  // Since fftMag represents 0 to fs/2, the bin width in Hz is:
  const hz_per_bin = nyq_hz / N;
  
  // Custom drawing domain from 0 to max_hz
  const scaleX = (pw-padL)/max_hz;
  const midY=64;

  const type = document.getElementById('sig-type').value;
  const freqsToDraw = [];
  if (type === 'sine' || type === 'square') { freqsToDraw.push(freq); }
  else if (type === 'multi') { freqsToDraw.push(freq, freq*3.1); }
  else if (type === 'chirp') { freqsToDraw.push(freq); }

  // Draw True frequency components (faded if beyond nyquist)
  freqsToDraw.forEach(f => {
      const isAliased = f > nyq_hz;
      const x = padL + f * scaleX;
      if (x > pw) return;
      ctx.fillStyle = isAliased ? 'rgba(255,68,85,0.4)' : 'rgba(140,60,255,.8)';
      ctx.beginPath(); ctx.moveTo(x-2, midY); ctx.lineTo(x, midY-45); ctx.lineTo(x+2, midY); ctx.fill();
      
      if (isAliased) {
          // Draw Alias Fold
          const fold_f = DSP.aliasFreq(f, fs_hz);
          const fold_x = padL + fold_f * scaleX;
          ctx.fillStyle = 'rgba(255,136,51,0.9)';
          ctx.beginPath(); ctx.moveTo(fold_x-1.5, midY); ctx.lineTo(fold_x, midY-40); ctx.lineTo(fold_x+1.5, midY); ctx.fill();
          
          // Draw folding arrow
          ctx.beginPath();
          ctx.strokeStyle = 'rgba(255,68,85,0.4)'; ctx.setLineDash([2,2]); ctx.lineWidth = 1;
          ctx.moveTo(x, midY-20);
          ctx.quadraticCurveTo((x+fold_x)/2, midY-50, fold_x, midY-20);
          ctx.stroke(); ctx.setLineDash([]);
      }
  });

  // Draw Nyquist Wall
  const nyq_x = padL + nyq_hz * scaleX;
  if (nyq_x < pw) {
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(51,255,170,0.8)';
      ctx.lineWidth = 2;
      ctx.setLineDash([4,4]);
      ctx.moveTo(nyq_x, 0); ctx.lineTo(nyq_x, 140-padB);
      ctx.stroke(); ctx.setLineDash([]);
      
      ctx.fillStyle = 'rgba(51,255,170,0.8)';
      ctx.font = '9px "JetBrains Mono", monospace';
      ctx.textAlign = 'right';
      ctx.fillText("Nyquist fs/2", nyq_x - 4, 15);
      
      // Shade the invalid region
      ctx.fillStyle = 'rgba(255,68,85,0.08)';
      ctx.fillRect(nyq_x, 0, pw - nyq_x, 140-padB);
  }

  // Draw actual FFT magnitudes
  fftMag.forEach((db,i)=>{
    const norm=Math.max(0,(db+80)/80);
    const h=norm*30;
    const bin_hz = i * hz_per_bin;
    const x = padL + bin_hz * scaleX;
    if (x > pw) return;
    const bw = Math.max(1, scaleX * hz_per_bin);

    ctx.fillStyle='rgba(68,136,255,.6)';
    ctx.fillRect(x,midY-h,bw,h);
  });

  drawAxisLabels(ctx,pw,140,{
    yLabels:['-80','0'],
    yPositions:[midY,midY-52],
    xLabels:['0 Hz', (max_hz/2).toFixed(0)+' Hz', max_hz.toFixed(0)+' Hz'],
    xUnit:'',
    padLeft:padL,padBottom:padB,
    yUnit:'Mag dB'
  });
}'''

html = html.replace(fft_old, fft_new)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

import re

html = open('index.html', 'r', encoding='utf-8').read()

stage4_old = '''function buildStage4(sig,bits,osr,sampRate){
  const {q,err}=DSP.quantize(sig.s,bits);
  const step=Math.max(1,Math.round(DSP.N_SAMPLES/(sampRate*10)));
  const layers=[
    {z:4.5,color:0x4488ff,pts:sig.t.map((t,i)=>new THREE.Vector3(t*14-7,sig.s[i]*.7,4.5))},
    {z:1.5,color:0xff8833,pts:null},
    {z:-1.5,color:0xff4455,pts:sig.t.map((t,i)=>new THREE.Vector3(t*14-7,q[i]*.7,-1.5))},
    {z:-4.5,color:0x33ffaa,pts:sig.t.map((t,i)=>new THREE.Vector3(t*14-7,(sig.s[i]-err[i]/Math.sqrt(osr))*.7,-4.5))}
  ];
  const sampPts3=[];
  for(let i=0;i<DSP.N_SAMPLES;i+=step)sampPts3.push(new THREE.Vector3(sig.t[i]*14-7,sig.s[i]*.7,1.5));
  layers[1].pts=sampPts3;
  const labels=['Original','Sampled','Quantized','Oversampled'];
  layers.forEach((l,li)=>{
    if(l.pts&&l.pts.length>1){
      makeTube(l.pts,l.color,li===2?.025:.04,6);
      const lbl=makeLabel(labels[li],#);
      lbl.position.set(-8.5,.8,l.z);addObj(lbl);
    }
  });
  const connGeo=new THREE.BufferGeometry();
  const connPts=[];
  const conStep=Math.round(DSP.N_SAMPLES/20);
  for(let i=0;i<DSP.N_SAMPLES;i+=conStep){
    connPts.push(new THREE.Vector3(sig.t[i]*14-7,sig.s[i]*.7,4.5));
    connPts.push(new THREE.Vector3(sig.t[i]*14-7,q[i]*.7,-1.5));
  }
  connGeo.setFromPoints(connPts);
  addObj(new THREE.LineSegments(connGeo,new THREE.LineBasicMaterial({color:0x223355,transparent:true,opacity:.25})));
  if(layers[3].pts&&layers[3].pts.length>1){
    const pGeo2=new THREE.BufferGeometry();
    const pPos=new Float32Array(150*3);
    pGeo2.setAttribute('position',new THREE.BufferAttribute(pPos,3));
    const particles=new THREE.Points(pGeo2,new THREE.PointsMaterial({color:0x33ffaa,size:.12,transparent:true,opacity:.9}));
    particles.userData.curve=new THREE.CatmullRomCurve3(layers[3].pts);
    particles.userData.isParticles=true;
    addObj(particles);
  }
  orb={...orb,theta:.4,phi:.9,r:16};
}'''

stage4_new = '''function buildStage4(sig,bits,osr,sampRate,recon_data=null){
  const {q,err}=DSP.quantize(sig.s,bits);
  const step=Math.max(1,Math.round(DSP.N_SAMPLES/(sampRate*10)));
  const rMode = document.getElementById('recon-mode').value;
  
  let reconLinePts = [];
  if(rMode === 'sinc' && recon_data) {
     reconLinePts = sig.t.map((t,i)=>new THREE.Vector3(t*14-7,recon_data.reconstructed[i]*.7,-4.5));
  } else {
     reconLinePts = sig.t.map((t,i)=>new THREE.Vector3(t*14-7,(sig.s[i]-err[i]/Math.sqrt(osr))*.7,-4.5));
  }

  const layers=[
    {z:4.5,color:0x4488ff,pts:sig.t.map((t,i)=>new THREE.Vector3(t*14-7,sig.s[i]*.7,4.5))},
    {z:1.5,color:0xff8833,pts:null},
    {z:-1.5,color:0xff4455,pts:sig.t.map((t,i)=>new THREE.Vector3(t*14-7,q[i]*.7,-1.5))},
    {z:-4.5,color:0x33ffaa,pts:reconLinePts}
  ];
  const sampPts3=[];
  for(let i=0;i<DSP.N_SAMPLES;i+=step)sampPts3.push(new THREE.Vector3(sig.t[i]*14-7,sig.s[i]*.7,1.5));
  layers[1].pts=sampPts3;
  const labels=['Original','Sampled','Quantized',rMode==='sinc'?'Sinc Recon':'Oversampled'];
  
  layers.forEach((l,li)=>{
    if(l.pts&&l.pts.length>1){
      makeTube(l.pts,l.color,li===2?.025:.04,6);
      const lbl=makeLabel(labels[li],#);
      lbl.position.set(-8.5,.8,l.z);addObj(lbl);
    }
  });

  if(rMode === 'sinc' && recon_data) {
    recon_data.sinc_components.forEach((comp, idx) => {
       const cpt = comp.map((v,i) => new THREE.Vector3(sig.t[i]*14-7, v*.7, -4.5));
       const tube = makeTube(cpt, 0x33ffaa, 0.015, 3);
       if(tube) {
         tube.material.opacity = 0.15;
         tube.userData.isSincPulse = true;
         tube.userData.sincOffset = idx * 0.15;
       }
    });
  }

  const connGeo=new THREE.BufferGeometry();
  const connPts=[];
  const conStep=Math.round(DSP.N_SAMPLES/20);
  for(let i=0;i<DSP.N_SAMPLES;i+=conStep){
    connPts.push(new THREE.Vector3(sig.t[i]*14-7,sig.s[i]*.7,4.5));
    connPts.push(new THREE.Vector3(sig.t[i]*14-7,q[i]*.7,-1.5));
  }
  connGeo.setFromPoints(connPts);
  addObj(new THREE.LineSegments(connGeo,new THREE.LineBasicMaterial({color:0x223355,transparent:true,opacity:.25})));

  if(layers[3].pts&&layers[3].pts.length>1 && rMode!=='sinc'){
    const pGeo2=new THREE.BufferGeometry();
    const pPos=new Float32Array(150*3);
    pGeo2.setAttribute('position',new THREE.BufferAttribute(pPos,3));
    const particles=new THREE.Points(pGeo2,new THREE.PointsMaterial({color:0x33ffaa,size:.12,transparent:true,opacity:.9}));
    particles.userData.curve=new THREE.CatmullRomCurve3(layers[3].pts);
    particles.userData.isParticles=true;
    addObj(particles);
  }

  orb={...orb,theta:.4,phi:.9,r:16};
}'''

html = html.replace(stage4_old, stage4_new)

# Add animate logic for Sinc Pulses
anim_tgt = '''  sceneObjects.forEach(o=>{
    if(o.userData.isParticles&&o.userData.curve){'''

anim_repl = '''  sceneObjects.forEach(o=>{
    if(o.userData.isSincPulse){
       const phase = (animT * 2.0 - o.userData.sincOffset) % 3.0;
       const alpha = phase > 0 && phase < 1.0 ? phase * 0.4 : (phase >= 1.0 && phase < 2.0 ? (2.0 - phase) * 0.4 : 0);
       o.material.opacity = alpha;
    }
  });
  
  sceneObjects.forEach(o=>{
    if(o.userData.isParticles&&o.userData.curve){'''

html = html.replace(anim_tgt, anim_repl)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

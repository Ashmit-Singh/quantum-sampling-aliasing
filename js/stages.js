// ══════════════════════════════════════════════════════════
// STAGES — waterfall, history ribbon, stage builders 0–4
// ══════════════════════════════════════════════════════════

/* ── Waterfall Spectrogram ── */
const WATERFALL_W = 64, WATERFALL_D = 80;
const wfData = new Uint8Array(WATERFALL_W * WATERFALL_D * 3);
const wfTex = new THREE.DataTexture(wfData, WATERFALL_W, WATERFALL_D, THREE.RGBFormat);
wfTex.needsUpdate = true;
const wfGeo = new THREE.PlaneGeometry(8, 4);
const wfMat = new THREE.MeshBasicMaterial({ map: wfTex, transparent: true, opacity: 0.85, side: THREE.DoubleSide });
const wfMesh = new THREE.Mesh(wfGeo, wfMat);
wfMesh.rotation.x = -Math.PI / 2; wfMesh.position.set(0, -2.1, -3);
scene.add(wfMesh);

function dbToRGB(db) {
  const norm = Math.max(0, Math.min(1, (db + 80) / 80));
  let r, g, b;
  if (norm < 0.25)      { r = 0; g = 0; b = Math.floor(norm * 4 * 255); }
  else if (norm < 0.5)  { const t = (norm - 0.25) * 4; r = Math.floor(t * 180); g = 0; b = 255; }
  else if (norm < 0.75) { const t = (norm - 0.5) * 4; r = Math.floor(180 + t * 75); g = Math.floor(t * 140); b = Math.floor(255 * (1 - t)); }
  else                  { const t = (norm - 0.75) * 4; r = 255; g = Math.floor(140 + t * 115); b = Math.floor(t * 255); }
  return [r, g, b];
}

function updateWaterfall(fftMag) {
  wfData.copyWithin(WATERFALL_W * 3, 0, WATERFALL_W * (WATERFALL_D - 1) * 3);
  for (let x = 0; x < WATERFALL_W; x++) {
    const fi = Math.floor(x * fftMag.length / WATERFALL_W);
    const [r, g, b] = dbToRGB(fftMag[fi] || -80);
    wfData[x * 3] = r; wfData[x * 3 + 1] = g; wfData[x * 3 + 2] = b;
  }
  wfTex.needsUpdate = true;
}

/* ── History Ribbon ── */
const historyGroup = new THREE.Group();
scene.add(historyGroup);
const signalHistory = [];
const MAX_HISTORY = 8;
let historyTubes = [];

function updateHistoryRibbon(sig) {
  signalHistory.push([...sig.s]);
  if (signalHistory.length > MAX_HISTORY) signalHistory.shift();
  historyTubes.forEach(t => { t.geometry.dispose(); if (t.material) t.material.dispose(); historyGroup.remove(t); });
  historyTubes = [];
  signalHistory.forEach((snap, hi) => {
    const age = signalHistory.length - 1 - hi;
    if (age === 0) return;
    const opacity = 0.8 * (1 - age / (MAX_HISTORY - 1)) * 0.8 + 0.05;
    const zOff = -(age + 1) * 0.4;
    const pts = snap.map((v, i) => new THREE.Vector3(i / DSP.N_SAMPLES * 16 - 8, v * 0.8, zOff));
    if (pts.length < 2) return;
    const curve = new THREE.CatmullRomCurve3(pts);
    const geo = new THREE.TubeGeometry(curve, Math.min(pts.length, 200), 0.02, 4, false);
    const mat = new THREE.MeshPhongMaterial({ color: 0x4488ff, emissive: 0x4488ff, emissiveIntensity: opacity * 0.6, transparent: true, opacity });
    const mesh = new THREE.Mesh(geo, mat);
    historyGroup.add(mesh); historyTubes.push(mesh);
  });
}

/* ── OSR terrain lerp state ── */
let osrTerrainRef = null;
let osrErrFrom = null, osrErrTo = null;
let osrLerpT = 1;

/* ── buildStage0 — Analog Signal ── */
function buildStage0(sig) {
  updateHistoryRibbon(sig);
  const pts = sig.t.map((t, i) => new THREE.Vector3(t * 16 - 8, sig.s[i] * 0.8, 0));
  makeTube(pts, 0x4488ff, 0.06, 8);
  const axGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-8.5, 0, 0), new THREE.Vector3(8.5, 0, 0)]);
  addObj(new THREE.Line(axGeo, new THREE.LineBasicMaterial({ color: 0x112244, transparent: true, opacity: 0.35 })));
  orb = { ...orb, theta: 0.2, phi: 1.3, r: 10 };
}

/* ── buildStage1 — Sampling & Aliasing ── */
function buildStage1(sig, sampRate, freq, amp) {
  const fs = freq * sampRate;
  const isAliased = sampRate < 2;
  const pts = sig.t.map((t, i) => new THREE.Vector3(t * 16 - 8, sig.s[i] * 0.8, 0));
  makeTube(pts, 0x224488, 0.03, 4, false);
  const step = Math.max(1, Math.round(DSP.N_SAMPLES / (sampRate * 10)));
  const sampleCount = Math.max(1, Math.floor(DSP.N_SAMPLES / step));
  const pillarColor = isAliased ? 0xff4455 : 0x33ffaa;
  const cylGeo = new THREE.CylinderGeometry(0.06, 0.06, 1, 6);
  const sphGeo = new THREE.SphereGeometry(0.08, 8, 8);
  const pillarMat = new THREE.MeshPhongMaterial({ color: pillarColor, emissive: pillarColor, emissiveIntensity: 0.7 });
  const sphereMat = new THREE.MeshPhongMaterial({ color: pillarColor, emissive: pillarColor, emissiveIntensity: 0.9 });
  const instPillar = new THREE.InstancedMesh(cylGeo, pillarMat, sampleCount);
  const instSphere = new THREE.InstancedMesh(sphGeo, sphereMat, sampleCount);
  const dummy = new THREE.Object3D();
  let idx = 0;
  for (let i = 0; i < DSP.N_SAMPLES && idx < sampleCount; i += step, idx++) {
    const x = sig.t[i] * 16 - 8, y = sig.s[i] * 0.8;
    dummy.position.set(x, y / 2, 0); dummy.scale.set(1, Math.abs(y) + 0.01, 1); dummy.updateMatrix();
    instPillar.setMatrixAt(idx, dummy.matrix);
    dummy.position.set(x, y, 0); dummy.scale.set(1, 1, 1); dummy.updateMatrix();
    instSphere.setMatrixAt(idx, dummy.matrix);
  }
  instPillar.instanceMatrix.needsUpdate = true; instSphere.instanceMatrix.needsUpdate = true;
  addObj(instPillar); addObj(instSphere);

  if (isAliased) {
    const aliasFreq = DSP.aliasFreq(freq, fs);
    const blend = Math.min(1, (2 - sampRate) / 2);
    const aliasPts = sig.t.map((t, i) => {
      const origY = sig.s[i] * 0.8;
      const aliasY = Math.sin(2 * Math.PI * aliasFreq * t) * amp * 0.8;
      return new THREE.Vector3(t * 16 - 8, origY * (1 - blend) + aliasY * blend, 0.5);
    });
    makeTube(aliasPts, 0xff8833, 0.04, 6);
    const ghostLbl = makeLabel('alias ghost', '#ff8833');
    ghostLbl.position.set(0, 1.2, 0.5); addObj(ghostLbl);
  }
  const nyqLbl = makeLabel('fs/2', isAliased ? '#ff4455' : '#33ffaa');
  nyqLbl.position.set(0, 2.4, 0); addObj(nyqLbl);
  orb = { ...orb, theta: 0.3, phi: 1.2, r: 11 };
}

/* ── buildStage2 — ADC Quantization ── */
function buildStage2(sig, bits) {
  const { q, err, LSB, levels } = DSP.quantize(sig.s, bits);
  const amp = Math.max(...sig.s.map(Math.abs)) || 1;

  // Original signal
  const origPts = sig.t.map((t, i) => new THREE.Vector3(t * 16 - 8, sig.s[i] * 0.8, 0.3));
  makeTube(origPts, 0x4488ff, 0.03, 6);

  // Comparison bit depths
  [2, 4].forEach((cb, li) => {
    if (cb === bits) return;
    const { q: qc } = DSP.quantize(sig.s, cb);
    const zOff = (li + 1) * 1.2;
    const stairPts = [];
    for (let i = 0; i < DSP.N_SAMPLES - 1; i++) {
      stairPts.push(new THREE.Vector3(sig.t[i] * 16 - 8, qc[i] * 0.8, zOff));
      stairPts.push(new THREE.Vector3(sig.t[i + 1] * 16 - 8, qc[i] * 0.8, zOff));
    }
    if (stairPts.length > 1) {
      const g = new THREE.BufferGeometry().setFromPoints(stairPts);
      addObj(new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0x445566, transparent: true, opacity: 0.5 })));
    }
    const lbl = makeLabel(cb + '-bit', '#445566');
    lbl.position.set(8, qc[0] * 0.8 + 0.5, zOff); addObj(lbl);
  });

  // Quantization level planes
  const numVisible = Math.min(levels, 48);
  const levelStep = (2 * amp) / numVisible;
  const planeGeo = new THREE.PlaneGeometry(16, 0.002);
  const planeMat = new THREE.MeshBasicMaterial({ color: 0x334455, transparent: true, opacity: 0.3, side: THREE.DoubleSide });
  const instPlane = new THREE.InstancedMesh(planeGeo, planeMat, numVisible + 1);
  const dummy2 = new THREE.Object3D();
  for (let i = 0; i <= numVisible; i++) {
    dummy2.position.set(0, (-amp + i * levelStep) * 0.8, -0.1); dummy2.updateMatrix();
    instPlane.setMatrixAt(i, dummy2.matrix);
  }
  instPlane.instanceMatrix.needsUpdate = true; addObj(instPlane);

  // Extruded staircase
  const stairShape = new THREE.Shape();
  stairShape.moveTo(sig.t[0] * 16 - 8, q[0] * 0.8);
  for (let i = 0; i < DSP.N_SAMPLES - 1; i++) {
    stairShape.lineTo(sig.t[i + 1] * 16 - 8, q[i] * 0.8);
    stairShape.lineTo(sig.t[i + 1] * 16 - 8, q[i + 1] * 0.8);
  }
  for (let i = DSP.N_SAMPLES - 2; i >= 0; i--) {
    stairShape.lineTo(sig.t[i + 1] * 16 - 8, q[i] * 0.8 - 0.02);
    stairShape.lineTo(sig.t[i] * 16 - 8, q[i] * 0.8 - 0.02);
  }
  const extGeo = new THREE.ExtrudeGeometry(stairShape, { depth: 0.04, bevelEnabled: false });
  addObj(new THREE.Mesh(extGeo, new THREE.MeshPhongMaterial({ color: 0xff4455, emissive: 0x881122, emissiveIntensity: 0.4, shininess: 60 })));

  // Error terrain
  const tW = 100, tH = 20;
  const tGeo = new THREE.PlaneGeometry(16, 2, tW - 1, tH - 1);
  tGeo.rotateX(-Math.PI / 2);
  const pos = tGeo.attributes.position;
  const cols = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const xi = Math.floor((i % tW));
    const ei = Math.floor(xi * DSP.N_SAMPLES / tW);
    pos.setY(i, -1.6 + err[ei] * 0.8 * 2);
    const norm = Math.min(Math.abs(err[ei]) / (LSB * 0.5), 1);
    cols[i * 3] = norm; cols[i * 3 + 1] = 0.15 * (1 - norm); cols[i * 3 + 2] = 1 - norm;
  }
  tGeo.computeVertexNormals();
  tGeo.setAttribute('color', new THREE.BufferAttribute(cols, 3));
  addObj(new THREE.Mesh(tGeo, new THREE.MeshPhongMaterial({ vertexColors: true, shininess: 20 })));
  orb = { ...orb, theta: 0.5, phi: 1.0, r: 12 };
}

/* ── buildStage3 — Oversampling ── */
function buildStage3(sig, bits, osr) {
  const { q, err } = DSP.quantize(sig.s, bits);
  const gain = DSP.osrGain(osr);
  const groups = [
    { z: -2.5, label: 'Baseline (1×)', color: 0xff4455, noiseScale: 1 },
    { z: 2.5, label: osr + '× Oversampled', color: 0x33ffaa, noiseScale: 1 / Math.sqrt(osr) }
  ];

  groups.forEach((g, gi) => {
    const pts = sig.t.map((t, i) => new THREE.Vector3(t * 12 - 6, sig.s[i] * 0.7, g.z));
    makeTube(pts, 0x4488ff, 0.03, 4);
    const qPts = sig.t.map((t, i) => new THREE.Vector3(t * 12 - 6, q[i] * 0.7, g.z));
    makeTube(qPts, g.color, 0.04, 4);

    // Noise terrain
    const nW = 80, nH = 8;
    const nGeo = new THREE.PlaneGeometry(12, 1.5, nW - 1, nH - 1);
    nGeo.rotateX(-Math.PI / 2);
    const nPos = nGeo.attributes.position;
    const yPositions = new Float32Array(nPos.count);
    for (let i = 0; i < nPos.count; i++) {
      const xi = Math.floor(i % nW * DSP.N_SAMPLES / nW);
      const y = -1.3 + err[xi] * g.noiseScale * 1.5;
      nPos.setY(i, y);
      nPos.setZ(i, g.z + (Math.floor(i / nW) / (nH - 1) - 0.5) * 1.5);
      yPositions[i] = y;
    }
    nGeo.computeVertexNormals();
    const nMesh = new THREE.Mesh(nGeo, new THREE.MeshPhongMaterial({ color: g.color, transparent: true, opacity: 0.6, shininess: 40 }));
    addObj(nMesh);
    if (gi === 1) {
      osrTerrainRef = { mesh: nMesh, geo: nGeo, posCount: nPos.count, nW, nH };
      const fromPositions = new Float32Array(nPos.count);
      for (let i = 0; i < nPos.count; i++) {
        const xi = Math.floor(i % nW * DSP.N_SAMPLES / nW);
        fromPositions[i] = -1.3 + err[xi] * 1.0 * 1.5;
      }
      osrErrFrom = fromPositions; osrErrTo = yPositions; osrMeshValid = true;
    }

    // SNR bar
    const snrBase = DSP.snrTheory(bits);
    const snrVal = snrBase + (g.noiseScale < 1 ? gain : 0);
    const tH2 = snrVal * 0.04;
    const tGeo2 = new THREE.BoxGeometry(0.4, tH2, 0.4);
    const tMesh = new THREE.Mesh(tGeo2, new THREE.MeshPhongMaterial({ color: g.color, emissive: g.color, emissiveIntensity: 0.4 }));
    tMesh.position.set(7, tH2 / 2, g.z); addObj(tMesh);

    if (gi === 1) {
      const enob = DSP.ENOB(snrVal);
      const eGeo = new THREE.CylinderGeometry(0.05, 0.05, enob * 0.3, 8);
      const eMesh = new THREE.Mesh(eGeo, new THREE.MeshPhongMaterial({ color: 0xffcc44, emissive: 0xffcc44, emissiveIntensity: 0.8, transparent: true, opacity: 0.7 }));
      eMesh.position.set(8, enob * 0.15, g.z); addObj(eMesh);
      const eLabel = makeLabel('ENOB: ' + enob.toFixed(2) + ' bits', '#ffcc44');
      eLabel.position.set(8, enob * 0.3 + 0.4, g.z); addObj(eLabel);
    }
    const lbl = makeLabel(g.label, '#' + g.color.toString(16).padStart(6, '0'));
    lbl.position.set(0, 1.8, g.z); addObj(lbl);
  });
  orb = { ...orb, theta: 0.6, phi: 0.9, r: 14 };
}

/* ── buildStage4 — Full Pipeline ── */
function buildStage4(sig, bits, osr, sampRate) {
  const freq = parseFloat(document.getElementById('sig-freq').value);
  const amp = parseFloat(document.getElementById('sig-amp').value) / 10;
  const { q, err } = DSP.quantize(sig.s, bits);
  const isAliased = sampRate < 2;

  // Original analog (dim)
  const origPts = sig.t.map((t, i) => new THREE.Vector3(t * 16 - 8, sig.s[i] * 0.8, -1.5));
  makeTube(origPts, 0x224466, 0.02, 4, false);
  const oLbl = makeLabel('analog', '#224466'); oLbl.position.set(-7, 1.5, -1.5); addObj(oLbl);

  // Sampled points (z=0)
  const step = Math.max(1, Math.round(DSP.N_SAMPLES / (sampRate * 10)));
  const sCount = Math.max(1, Math.floor(DSP.N_SAMPLES / step));
  const pColor = isAliased ? 0xff4455 : 0x33ffaa;
  const cylGeo = new THREE.CylinderGeometry(0.04, 0.04, 1, 6);
  const sphGeo = new THREE.SphereGeometry(0.06, 8, 8);
  const pMat = new THREE.MeshPhongMaterial({ color: pColor, emissive: pColor, emissiveIntensity: 0.6 });
  const iP = new THREE.InstancedMesh(cylGeo, pMat, sCount);
  const iS = new THREE.InstancedMesh(sphGeo, pMat, sCount);
  const dm = new THREE.Object3D(); let idx = 0;
  for (let i = 0; i < DSP.N_SAMPLES && idx < sCount; i += step, idx++) {
    const x = sig.t[i] * 16 - 8, y = sig.s[i] * 0.8;
    dm.position.set(x, y / 2, 0); dm.scale.set(1, Math.abs(y) + 0.01, 1); dm.updateMatrix(); iP.setMatrixAt(idx, dm.matrix);
    dm.position.set(x, y, 0); dm.scale.set(1, 1, 1); dm.updateMatrix(); iS.setMatrixAt(idx, dm.matrix);
  }
  iP.instanceMatrix.needsUpdate = true; iS.instanceMatrix.needsUpdate = true;
  addObj(iP); addObj(iS);
  const sLbl = makeLabel('sampled', isAliased ? '#ff4455' : '#33ffaa'); sLbl.position.set(-7, 1.5, 0); addObj(sLbl);

  // Quantized staircase (z=1.5)
  const qStair = [];
  for (let i = 0; i < DSP.N_SAMPLES - 1; i++) {
    qStair.push(new THREE.Vector3(sig.t[i] * 16 - 8, q[i] * 0.8, 1.5));
    qStair.push(new THREE.Vector3(sig.t[i + 1] * 16 - 8, q[i] * 0.8, 1.5));
  }
  if (qStair.length > 1) addObj(new THREE.Line(new THREE.BufferGeometry().setFromPoints(qStair), new THREE.LineBasicMaterial({ color: 0xff4455, transparent: true, opacity: 0.8 })));
  const qLbl = makeLabel('quantized', '#ff4455'); qLbl.position.set(-7, 1.5, 1.5); addObj(qLbl);

  // Oversampled improved (z=3)
  const gf = 1 / Math.sqrt(osr);
  const osrPts = sig.t.map((t, i) => new THREE.Vector3(t * 16 - 8, (q[i] + err[i] * (1 - gf)) * 0.8, 3));
  makeTube(osrPts, 0x33ffaa, 0.05, 6);
  const osLbl = makeLabel(osr + '× oversampled', '#33ffaa'); osLbl.position.set(-7, 1.5, 3); addObj(osLbl);

  // Particles flowing along oversampled signal
  if (osrPts.length >= 2) {
    const curve = new THREE.CatmullRomCurve3(osrPts);
    const pCount = 60;
    const pGeo = new THREE.BufferGeometry();
    pGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pCount * 3), 3));
    const pts = new THREE.Points(pGeo, new THREE.PointsMaterial({ color: 0x33ffaa, size: 0.1, transparent: true, opacity: 0.8, sizeAttenuation: true }));
    pts.userData.isParticles = true; pts.userData.curve = curve;
    addObj(pts);
  }
  orb = { ...orb, theta: 0.4, phi: 1.1, r: 14 };
}

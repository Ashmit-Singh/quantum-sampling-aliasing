// ══════════════════════════════════════════════════════════
// THREE.JS SCENE — setup, bloom pipeline, orbit camera, stars, utilities
// ══════════════════════════════════════════════════════════

/* ── Helpers ── */
function isMobile() { return window.innerWidth < 900; }
function W() { return window.innerWidth - (isMobile() ? 0 : 260); }
function H() { return window.innerHeight - 52; }

/* ── Scene, Camera, Renderer ── */
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(60, W() / H(), 0.1, 200);
camera.position.set(0, 2, 10);
const canvas3d = document.getElementById('webgl-canvas');
const renderer = new THREE.WebGLRenderer({ canvas: canvas3d, antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x04050f, 1);
renderer.autoClear = false;

/* ── Lights ── */
scene.add(new THREE.AmbientLight(0x334466, 0.6));
const dirLight = new THREE.DirectionalLight(0x4488ff, 0.8);
dirLight.position.set(5, 8, 5); scene.add(dirLight);
const ptLight = new THREE.PointLight(0x7766ff, 0.5, 30);
ptLight.position.set(-5, 3, -3); scene.add(ptLight);

/* ── Stars ── */
const starGeo = new THREE.BufferGeometry();
const starPos = new Float32Array(2000 * 3);
for (let i = 0; i < 2000; i++) {
  starPos[i * 3]     = (Math.random() - 0.5) * 80;
  starPos[i * 3 + 1] = (Math.random() - 0.5) * 80;
  starPos[i * 3 + 2] = (Math.random() - 0.5) * 80;
}
starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
const starMat = new THREE.PointsMaterial({ color: 0x6688cc, size: 0.04, transparent: true, opacity: 0.4, sizeAttenuation: true });
const stars = new THREE.Points(starGeo, starMat);
scene.add(stars);

/* ── Orbit Camera ── */
let orb = { theta: 0.5, phi: 1.1, r: 10 };
let isDragging = false, lastMouse = { x: 0, y: 0 };

canvas3d.addEventListener('mousedown', e => { isDragging = true; lastMouse = { x: e.clientX, y: e.clientY }; });
canvas3d.addEventListener('mousemove', e => {
  if (!isDragging) return;
  orb.theta += (e.clientX - lastMouse.x) * 0.005;
  orb.phi = Math.max(0.2, Math.min(Math.PI - 0.2, orb.phi - (e.clientY - lastMouse.y) * 0.005));
  lastMouse = { x: e.clientX, y: e.clientY };
});
window.addEventListener('mouseup', () => isDragging = false);
canvas3d.addEventListener('wheel', e => { orb.r = Math.max(3, Math.min(25, orb.r + e.deltaY * 0.01)); e.preventDefault(); }, { passive: false });
// Touch
canvas3d.addEventListener('touchstart', e => { if (e.touches.length === 1) { isDragging = true; lastMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY }; } }, { passive: false });
canvas3d.addEventListener('touchmove', e => {
  if (!isDragging || e.touches.length !== 1) return; e.preventDefault();
  orb.theta += (e.touches[0].clientX - lastMouse.x) * 0.005;
  orb.phi = Math.max(0.2, Math.min(Math.PI - 0.2, orb.phi - (e.touches[0].clientY - lastMouse.y) * 0.005));
  lastMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
}, { passive: false });
canvas3d.addEventListener('touchend', () => isDragging = false);

function orbitCamera() {
  camera.position.x = orb.r * Math.sin(orb.phi) * Math.sin(orb.theta);
  camera.position.y = orb.r * Math.cos(orb.phi);
  camera.position.z = orb.r * Math.sin(orb.phi) * Math.cos(orb.theta);
  camera.lookAt(0, 0, 0);
}

/* ── Bloom Post-Processing ── */
const VS_QUAD = `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`;

const matBloomH = new THREE.ShaderMaterial({
  uniforms: { tDiffuse: { value: null }, h: { value: 1 / 512 } },
  vertexShader: VS_QUAD,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float h; varying vec2 vUv;
    void main(){
      vec4 s=vec4(0.0);
      s+=texture2D(tDiffuse,vec2(vUv.x-4.0*h,vUv.y))*0.051;
      s+=texture2D(tDiffuse,vec2(vUv.x-3.0*h,vUv.y))*0.0918;
      s+=texture2D(tDiffuse,vec2(vUv.x-2.0*h,vUv.y))*0.12;
      s+=texture2D(tDiffuse,vec2(vUv.x-1.0*h,vUv.y))*0.1531;
      s+=texture2D(tDiffuse,vUv)*0.1633;
      s+=texture2D(tDiffuse,vec2(vUv.x+1.0*h,vUv.y))*0.1531;
      s+=texture2D(tDiffuse,vec2(vUv.x+2.0*h,vUv.y))*0.12;
      s+=texture2D(tDiffuse,vec2(vUv.x+3.0*h,vUv.y))*0.0918;
      s+=texture2D(tDiffuse,vec2(vUv.x+4.0*h,vUv.y))*0.051;
      gl_FragColor=s;
    }`
});
const matBloomV = new THREE.ShaderMaterial({
  uniforms: { tDiffuse: { value: null }, v: { value: 1 / 512 } },
  vertexShader: VS_QUAD,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float v; varying vec2 vUv;
    void main(){
      vec4 s=vec4(0.0);
      s+=texture2D(tDiffuse,vec2(vUv.x,vUv.y-4.0*v))*0.051;
      s+=texture2D(tDiffuse,vec2(vUv.x,vUv.y-3.0*v))*0.0918;
      s+=texture2D(tDiffuse,vec2(vUv.x,vUv.y-2.0*v))*0.12;
      s+=texture2D(tDiffuse,vec2(vUv.x,vUv.y-1.0*v))*0.1531;
      s+=texture2D(tDiffuse,vUv)*0.1633;
      s+=texture2D(tDiffuse,vec2(vUv.x,vUv.y+1.0*v))*0.1531;
      s+=texture2D(tDiffuse,vec2(vUv.x,vUv.y+2.0*v))*0.12;
      s+=texture2D(tDiffuse,vec2(vUv.x,vUv.y+3.0*v))*0.0918;
      s+=texture2D(tDiffuse,vec2(vUv.x,vUv.y+4.0*v))*0.051;
      gl_FragColor=s;
    }`
});
const matComposite = new THREE.ShaderMaterial({
  uniforms: { tBase: { value: null }, tBloom: { value: null } },
  vertexShader: VS_QUAD,
  fragmentShader: `uniform sampler2D tBase; uniform sampler2D tBloom; varying vec2 vUv;
    void main(){ gl_FragColor = texture2D(tBase,vUv) + texture2D(tBloom,vUv)*0.55; }`
});
const matFilm = new THREE.ShaderMaterial({
  uniforms: { tDiffuse: { value: null }, time: { value: 0 }, glitch: { value: 0 } },
  vertexShader: VS_QUAD,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float time; uniform float glitch; varying vec2 vUv;
    float rand(vec2 c){ return fract(sin(dot(c,vec2(12.9898,78.233)))*43758.5453); }
    void main(){
      vec2 uv=vUv;
      if(glitch>0.0){ uv.x+=glitch*(rand(vec2(floor(uv.y*20.0),time))-0.5)*0.06; }
      vec4 c=texture2D(tDiffuse,uv);
      c.rgb+=rand(vUv+fract(time))*0.03-0.015;
      float vig=1.0-distance(vUv,vec2(0.5))*0.7;
      c.rgb*=vig;
      c.r=texture2D(tDiffuse,uv+vec2(0.001,0.0)).r;
      c.b=texture2D(tDiffuse,uv-vec2(0.001,0.0)).b;
      gl_FragColor=c;
    }`
});

const bloomScene = new THREE.Scene();
const bloomCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
const fsGeo = new THREE.PlaneGeometry(2, 2);
const quadH = new THREE.Mesh(fsGeo, matBloomH);
const quadV = new THREE.Mesh(fsGeo, matBloomV);
const quadC = new THREE.Mesh(fsGeo, matComposite);
const quadF = new THREE.Mesh(fsGeo, matFilm);

let rtMain, rtBloomH, rtBloomV, rtComposite;
function buildRTs() {
  const dpr = Math.min(window.devicePixelRatio, 2);
  const w = W() * dpr, h = H() * dpr;
  [rtMain, rtBloomH, rtBloomV, rtComposite].forEach(rt => { if (rt) rt.dispose(); });
  rtMain = new THREE.WebGLRenderTarget(w, h);
  rtBloomH = new THREE.WebGLRenderTarget(Math.floor(w / 2), Math.floor(h / 2));
  rtBloomV = new THREE.WebGLRenderTarget(Math.floor(w / 2), Math.floor(h / 2));
  rtComposite = new THREE.WebGLRenderTarget(w, h);
}
buildRTs();

/* ── Scene Object Management ── */
let sceneObjects = [];
function addObj(o) { scene.add(o); sceneObjects.push(o); return o; }
function clearScene() {
  sceneObjects.forEach(o => {
    scene.remove(o);
    if (o.geometry) o.geometry.dispose();
    if (o.material) {
      if (o.material.map) o.material.map.dispose();
      o.material.dispose();
    }
  });
  sceneObjects = [];
  osrMeshValid = false;
}
let osrMeshValid = false;

/* ── Energy Shader Material ── */
function energyMat(color) {
  const c = new THREE.Color(color);
  return new THREE.ShaderMaterial({
    uniforms: { time: { value: 0 }, color: { value: c } },
    vertexShader: `varying vec3 vPos; varying vec3 vNormal;
      void main(){ vPos=position; vNormal=normalMatrix*normal; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `uniform float time; uniform vec3 color; varying vec3 vPos; varying vec3 vNormal;
      void main(){
        float pulse=sin(vPos.x*2.0+time*4.0)*0.5+0.5;
        float edge=pow(1.0-abs(dot(normalize(vNormal),vec3(0.0,0.0,1.0))),2.0);
        vec3 glow=color*(0.6+pulse*0.4+edge*0.8);
        gl_FragColor=vec4(glow,1.0);
      }`
  });
}

/* ── Shared Utilities ── */
function makeLabel(text, color) {
  color = color || '#4488ff';
  const c = document.createElement('canvas'); c.height = 48;
  const ctx = c.getContext('2d');
  ctx.font = '500 14px "Sora", sans-serif';
  c.width = Math.ceil(ctx.measureText(text).width) + 24;
  ctx.clearRect(0, 0, c.width, 48);
  ctx.fillStyle = color; ctx.font = '500 14px "Sora", sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(text, c.width / 2, 24);
  const tex = new THREE.CanvasTexture(c);
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false });
  const spr = new THREE.Sprite(mat);
  spr.scale.set((c.width / 48) * 0.4, 0.4, 1);
  return spr;
}

function makeTube(pts3, color, radius, segments, useShader) {
  radius = radius || 0.04; segments = segments || 6;
  if (useShader === undefined) useShader = true;
  if (pts3.length < 2) return null;
  const curve = new THREE.CatmullRomCurve3(pts3);
  const geo = new THREE.TubeGeometry(curve, Math.min(pts3.length * 2, 300), radius, segments, false);
  const mat = useShader ? energyMat(color) : new THREE.MeshPhongMaterial({ color, emissive: color, emissiveIntensity: 0.5, shininess: 30 });
  return addObj(new THREE.Mesh(geo, mat));
}

function syncSlider(el) {
  const pct = ((el.value - el.min) / (el.max - el.min)) * 100;
  el.style.setProperty('--fill', pct + '%');
}
// Init all sliders
document.querySelectorAll('input[type=range]').forEach(syncSlider);

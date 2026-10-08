/* Take the gloves off! – Bildeffekte mit three.js
 * biegen(el, video):    Das Videobild biegt sich in einem senkrechten Band wie der Stab im Zeichen.
 * nachbild(el, video):  Bewegung hinterlässt ein rotes Nachbild, wie eine Langzeitbelichtung.
 * Fällt WebGL aus, bleibt das normale Video sichtbar.
 */
(function () {
  'use strict';
  if (!window.THREE) return;
  var T = window.THREE;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var VERT = 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }';

  // gemeinsame Funktionen: Bild formatfüllend einpassen, Körnung
  var COMMON = [
    'uniform vec2 uRes; uniform vec2 uVid; uniform float uTime;',
    'vec2 cover(vec2 uv){ float ra = uRes.x/uRes.y, rv = uVid.x/uVid.y;',
    '  vec2 s = ra > rv ? vec2(1.0, rv/ra) : vec2(ra/rv, 1.0); return (uv - 0.5) * s + 0.5; }',
    'float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }',
    'float luma(vec3 c){ return dot(c, vec3(0.299, 0.587, 0.114)); }'
  ].join('\n');

  function setup(el, video, frag, extraUniforms, feedback) {
    var canvas = document.createElement('canvas');
    canvas.className = 'fx';
    canvas.setAttribute('aria-hidden', 'true');
    var renderer;
    try {
      renderer = new T.WebGLRenderer({ canvas: canvas, antialias: false, alpha: false, powerPreference: 'high-performance' });
    } catch (e) { return null; }
    renderer.setPixelRatio(1);   // das Bild ist ohnehin weich, volle Auflösung kostet nur Rechenzeit
    var tex = new T.VideoTexture(video);
    tex.minFilter = T.LinearFilter; tex.magFilter = T.LinearFilter;

    var uniforms = {
      tVid: { value: tex }, uRes: { value: new T.Vector2(1, 1) }, uVid: { value: new T.Vector2(16, 9) },
      uTime: { value: 0 }
    };
    for (var k in extraUniforms) uniforms[k] = extraUniforms[k];
    var scene = new T.Scene();
    var cam = new T.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    var mat = new T.ShaderMaterial({ vertexShader: VERT, fragmentShader: COMMON + '\n' + frag, uniforms: uniforms });
    scene.add(new T.Mesh(new T.PlaneGeometry(2, 2), mat));

    // für das Nachbild: zwei Puffer im Wechsel
    var rtA, rtB, copyScene, copyMat;
    if (feedback) {
      var opt = { minFilter: T.LinearFilter, magFilter: T.LinearFilter, type: T.HalfFloatType };
      rtA = new T.WebGLRenderTarget(4, 4, opt); rtB = new T.WebGLRenderTarget(4, 4, opt);
      copyMat = new T.ShaderMaterial({ vertexShader: VERT, fragmentShader: feedback.display, uniforms: { tBuf: { value: null }, tVid: uniforms.tVid, uRes: uniforms.uRes, uVid: uniforms.uVid, uTime: uniforms.uTime } });
      copyMat.fragmentShader = COMMON + '\n' + feedback.display;
      copyScene = new T.Scene(); copyScene.add(new T.Mesh(new T.PlaneGeometry(2, 2), copyMat));
    }

    function resize() {
      var w = el.clientWidth, h = el.clientHeight;
      renderer.setSize(w, h, false);
      var pr = renderer.getPixelRatio();
      uniforms.uRes.value.set(w * pr, h * pr);
      if (feedback) { rtA.setSize(w * pr * .6, h * pr * .6); rtB.setSize(w * pr * .6, h * pr * .6); }
    }
    el.appendChild(canvas);
    resize();
    window.addEventListener('resize', resize);

    var visible = false, t0 = performance.now(), ok = true;
    new IntersectionObserver(function (es) { visible = es[0].isIntersecting; }, { rootMargin: '100px' }).observe(el);
    video.addEventListener('loadedmetadata', function () { uniforms.uVid.value.set(video.videoWidth, video.videoHeight); });
    if (video.videoWidth) uniforms.uVid.value.set(video.videoWidth, video.videoHeight);

    // Darf der Effekt das Video lesen? Sonst bleibt das normale Video sichtbar statt einer schwarzen Fläche.
    var probed = false;
    function readable() {
      try {
        var c = document.createElement('canvas'); c.width = c.height = 2;
        var x = c.getContext('2d'); x.drawImage(video, 0, 0, 2, 2); x.getImageData(0, 0, 1, 1);
        return true;
      } catch (e) { return false; }
    }

    var api = { uniforms: uniforms, onFrame: null };
    function loop() {
      if (!ok) return;
      requestAnimationFrame(loop);
      if (!visible || video.readyState < 2) return;
      if (!probed) { probed = true; if (!readable()) { ok = false; canvas.remove(); return; } }
      uniforms.uTime.value = (performance.now() - t0) / 1000;
      if (api.onFrame) api.onFrame(uniforms.uTime.value);
      try {
        if (feedback) {
          uniforms.tPrev.value = rtA.texture;
          renderer.setRenderTarget(rtB); renderer.render(scene, cam);
          renderer.setRenderTarget(null);
          copyMat.uniforms.tBuf.value = rtB.texture;
          renderer.render(copyScene, cam);
          var t = rtA; rtA = rtB; rtB = t;
        } else {
          renderer.render(scene, cam);
        }
        if (!el.classList.contains('fx-on')) el.classList.add('fx-on');
      } catch (e) { ok = false; el.classList.remove('fx-on'); }
    }
    loop();
    return api;
  }

  /* 1 · Biegen: ein senkrechtes Band in der Bildmitte verschiebt das Bild in einer S-Kurve */
  var BEND = [
    'uniform sampler2D tVid; uniform float uBend; uniform float uCenter; uniform float uGlitch; varying vec2 vUv;',
    'float s(float y){ float u = clamp((0.7 - y) / 0.48, 0.0, 1.0); return u*u*(3.0-2.0*u); }',  // y von oben
    'void main(){',
    '  vec2 uv = vUv; float y = 1.0 - uv.y;',
    '  float fr = floor(uTime * 30.0);',                               // Störung: Streifen reißen seitlich weg
    '  float tear = step(0.62, hash(vec2(floor(y * 9.0), fr + 3.0))) * (hash(vec2(floor(y * 23.0), fr)) - 0.5);',
    '  uv.x += tear * 0.09 * uGlitch;',
    '  float aspect = uRes.x / uRes.y;',
    '  float d = (uv.x - uCenter) * aspect;',
    '  float band = exp(-d*d / 0.09);',
    '  float off = s(y) * uBend * 0.075 * band;',
    '  vec2 c = cover(vec2(uv.x - off, uv.y));',
    '  float r = luma(texture2D(tVid, cover(vec2(uv.x - off * 1.25, uv.y))).rgb);',
    '  float g = luma(texture2D(tVid, c).rgb);',
    '  vec3 col = vec3(g);',
    '  col.r = mix(g, max(g, r * 1.15), band * uBend * 0.9);',   // an der Biegung wird es rötlich
    '  float sp = 0.011 * uGlitch;',                                   // Rot und Cyan laufen auseinander
    '  float rS = luma(texture2D(tVid, cover(vec2(uv.x - off + sp, uv.y))).rgb);',
    '  float cS = luma(texture2D(tVid, cover(vec2(uv.x - off - sp, uv.y))).rgb);',
    '  col = mix(col, vec3(rS, cS, cS), min(uGlitch * 1.5, 1.0));',
    '  col *= 1.0 - uGlitch * 0.18 * step(0.5, fract(vUv.y * uRes.y * 0.25));',  // Zeilen
    '  col = (col - 0.5) * 1.12 + 0.47;',
    '  col += (hash(uv * uRes + uTime) - 0.5) * 0.07;',            // Körnung
    '  float vig = smoothstep(1.25, 0.35, length((uv - 0.5) * vec2(aspect, 1.0)));',
    '  gl_FragColor = vec4(col * mix(0.35, 1.0, vig), 1.0);',
    '}'
  ].join('\n');

  window.TTGOfx = window.TTGOfx || {};
  window.TTGOfx.biegen = function (el, video, opts) {
    opts = opts || {};
    var u = { uBend: { value: 0 }, uCenter: { value: 0.5 }, uGlitch: { value: 0 } };
    var api = setup(el, video, BEND, u);
    if (!api) return null;
    var target = 0.8, mx = 0.5;
    el.addEventListener('pointermove', function (e) {
      var r = el.getBoundingClientRect();
      mx = (e.clientX - r.left) / r.width;
    });
    api.onFrame = function (t) {
      // langsam atmende Biegung, die Maus zieht das Band leicht mit.
      // Mit opts.drive folgt das Bild einem äußeren Takt (im Kopf: dem Stab im Zeichen).
      var b = opts.drive ? opts.drive() : (reduce ? 0.7 : 0.55 + 0.4 * Math.sin(t * 0.45));
      u.uBend.value += (b - u.uBend.value) * (opts.drive ? 0.14 : 0.05);
      u.uCenter.value += ((0.5 + (mx - 0.5) * 0.5) - u.uCenter.value) * 0.03;
      u.uGlitch.value = opts.glitch ? opts.glitch() : 0;
    };
    return api;
  };

  /* 2 · Nachbild: was sich bewegt, hinterlässt eine rote Spur */
  var TRAIL = [
    'uniform sampler2D tVid; uniform sampler2D tPrev; uniform float uDecay; varying vec2 vUv;',
    'void main(){',
    '  float cur = luma(texture2D(tVid, cover(vUv)).rgb);',
    '  vec2 drift = vec2(0.0, 0.0006);',                                   // Spuren sinken leicht ab
    '  float prev = texture2D(tPrev, vUv + drift).r;',
    '  gl_FragColor = vec4(max(cur, prev * uDecay), cur, 0.0, 1.0);',
    '}'
  ].join('\n');
  var TRAIL_DISPLAY = [
    'uniform sampler2D tBuf; varying vec2 vUv;',
    'void main(){',
    '  vec4 b = texture2D(tBuf, vUv);',
    '  float cur = b.g, ghost = max(b.r - cur, 0.0);',
    '  vec3 col = vec3(cur) + vec3(0.82, 0.17, 0.12) * ghost * 1.7;',
    '  col = (col - 0.5) * 1.1 + 0.48;',
    '  col += (hash(vUv * uRes + uTime) - 0.5) * 0.06;',
    '  gl_FragColor = vec4(col, 1.0);',
    '}'
  ].join('\n');
  window.TTGOfx.nachbild = function (el, video, decay) {
    var u = { tPrev: { value: null }, uDecay: { value: reduce ? 0 : (decay || 0.965) } };
    return setup(el, video, TRAIL, u, { display: TRAIL_DISPLAY });
  };
})();

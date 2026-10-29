/* Take the gloves off! – Zeichen im Styleguide (Bewegung, Box, Story)
 * Spielt dieselbe Partitur wie der Kopf (kopf.js) auf einzelnen Zeichen ab:
 * die drei Stäbe werden eingezählt, der mittlere biegt sich und wird rot, dann der Kreislauf
 * (Auftakt, Steigerung, Ausbruch, Höhepunkt, Ruhe), danach von vorn.
 * Aufruf: TTGOlauf(svg, { ink: '#efebe3', red: '#d22b1f', stoerung: true })
 * Programmierschnittstelle: TTGOlauf.LOOP (Zykluslänge in s), TTGOlauf.zustand(u), TTGOlauf.stoerungen,
 * TTGOlauf.zeige(Z, u): Zeichen Z (aus TTGOzeichen) zur Zeit u des Kreislaufs zeichnen.
 * Die Partitur ist eine Kopie aus kopf.js; wird sie dort geändert, hier angleichen.
 */
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function clamp(u) { return u < 0 ? 0 : u > 1 ? 1 : u; }
  function seg(t, a, d) { return clamp((t - a) / d); }
  function expoOut(u) { return u >= 1 ? 1 : 1 - Math.pow(2, -10 * u); }
  function inOut(u) { return u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; }
  function ease3(u) { return u * u * (3 - 2 * u); }

  // ---------- Partitur (wie in kopf.js) ----------
  var BPM = 128, BEAT = 60 / BPM;
  function b(n) { return n * BEAT; }
  var SCORE = [
    { was: 'stab', halt: b(0.75), aus: 0.06 },
    { was: 'pose', pose: 0, dunkel: b(0.25),  halt: b(1.25), weiss: 0.05, rot: 0.12, glow: 0.06, schein: 1, fade: 0.24 },
    { was: 'pose', pose: 1, dunkel: b(0.20),  halt: b(1.00), weiss: 0.05, rot: 0.12, glow: 0.06, schein: 1, fade: 0.20 },
    { was: 'pose', pose: 2, dunkel: b(0.18),  halt: b(0.90), weiss: 0.05, rot: 0.11, glow: 0.06, schein: 1, fade: 0.18 },
    { was: 'pose', pose: 3, dunkel: b(0.15),  halt: b(0.80), weiss: 0.05, rot: 0.10, glow: 0.06, schein: 1, fade: 0.16 },
    { was: 'pose', pose: 4, dunkel: b(0.125), halt: b(0.75), weiss: 0.05, rot: 0.09, glow: 0.07, schein: 1.2, fade: 0.14 },
    { was: 'pose', pose: 2, dunkel: b(0.125), halt: b(0.625), weiss: 0.05, rot: 0.08, glow: 0.08, schein: 1.5, fade: 0.10 },
    { was: 'pose', pose: 0, dunkel: b(0.125), halt: b(0.625), weiss: 0.05, rot: 0.08, glow: 0.08, schein: 1.5, fade: 0.10 },
    { was: 'pose', pose: 3, dunkel: b(0.125), halt: b(0.625), weiss: 0.05, rot: 0.08, glow: 0.08, schein: 1.6, fade: 0.10, stoerung: [0.0, 0.16, 0.7, 'mv'] },
    { was: 'pose', pose: 1, dunkel: b(0.125), halt: b(0.625), weiss: 0.05, rot: 0.08, glow: 0.08, schein: 1.6, fade: 0.10 },
    { was: 'pose', pose: 3, dunkel: b(0.25),  halt: b(3.75),  weiss: 0.10, rot: 0.22, glow: 0.18, schein: 3, radius: 1.3, fade: 0.60 },
    { was: 'stab', dunkel: b(1.0), halt: b(8.0), ein: 0.7, atmen: true, stoerung: [b(5.0), 0.14, 0.3, 'm'] }
  ];
  var TL = [], LOOP = 0, GLSCORE = [];
  (function () {
    var t = 0;
    SCORE.forEach(function (e, i) {
      var ev = { e: e, i: i, t0: t, ts: t + (e.dunkel || 0), te: t + (e.dunkel || 0) + e.halt };
      TL.push(ev); t = ev.te;
      if (e.stoerung) GLSCORE.push([ev.ts + e.stoerung[0], e.stoerung[1], e.stoerung[2], e.stoerung[3]]);
    });
    LOOP = t;
  })();
  function zustand(u) {
    var r = { bend: 1, hold: -1, tt: 0, dur: 1, fx: null, dark: false, stab: 1, env: 0 };
    for (var i = 0; i < TL.length; i++) {
      var v = TL[i], e = v.e;
      if (u < v.t0 || u >= v.te) continue;
      if (u < v.ts) { r.dark = true; break; }
      var d = u - v.ts;
      if (e.was === 'pose') { r.hold = e.pose; r.tt = d; r.dur = e.halt; r.fx = e; }
      else {
        r.stab = e.ein ? ease3(seg(d, 0, e.ein)) : 1 - (e.aus ? seg(d, e.halt - e.aus, e.aus) : 0);
        if (e.atmen) r.env = seg(d, 0.4, 1.0) * (1 - seg(d, e.halt - 0.8, 0.8));
        r.bend = 1 + 0.035 * r.env * Math.sin(u * Math.PI * 2 / 4.6);
      }
      break;
    }
    return r;
  }
  function zeige(Z, u) {
    var st = zustand(u);
    if (st.dark) Z.dunkel();
    else if (st.hold >= 0) Z.halte(st.hold, st.tt, st.dur, st.fx);
    else Z.set(st.bend, 1, st.stab);
  }

  // ---------- Signalstörung (wie in kopf.js) ----------
  function el(tag, attrs) { var n = document.createElementNS(NS, tag); for (var k in attrs) n.setAttribute(k, attrs[k]); return n; }
  var nGl = 0;
  function stoerungFor(svg) {
    if (!svg || !svg.viewBox || !svg.viewBox.baseVal || !svg.viewBox.baseVal.width) return function () {};
    var vb = svg.viewBox.baseVal, id = 'lauf' + (nGl++);
    var defs = svg.querySelector(':scope > defs') || svg.insertBefore(el('defs', {}), svg.firstChild);
    var f = el('filter', { id: id, x: '-10%', y: '-10%', width: '120%', height: '120%', 'color-interpolation-filters': 'sRGB' });
    var turb = el('feTurbulence', { type: 'fractalNoise', baseFrequency: '0.0001 ' + (7 / vb.height).toFixed(4), numOctaves: 1, seed: 1, result: 'n' });
    var ct = el('feComponentTransfer', { in: 'n', result: 'b' });
    ct.appendChild(el('feFuncR', { type: 'discrete', tableValues: '0.5 0.5 0.5 0.12 0.5 0.5 0.5 0.88 0.5 0.5 0.3 0.5' }));
    ct.appendChild(el('feFuncG', { type: 'linear', slope: 0, intercept: 0.5 }));
    ct.appendChild(el('feFuncA', { type: 'linear', slope: 0, intercept: 1 }));
    var disp = el('feDisplacementMap', { in: 'SourceGraphic', in2: 'b', scale: 0, xChannelSelector: 'R', yChannelSelector: 'G', result: 'd' });
    var ro = el('feOffset', { in: 'r', dx: 0, result: 'ro' }), co = el('feOffset', { in: 'c', dx: 0, result: 'co' });
    var merge = el('feMerge', {});
    ['co', 'ro', 'd'].forEach(function (k) { merge.appendChild(el('feMergeNode', { in: k })); });
    [turb, ct, disp,
      el('feColorMatrix', { in: 'd', type: 'matrix', values: '1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .85 0', result: 'r' }), ro,
      el('feColorMatrix', { in: 'd', type: 'matrix', values: '0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 .7 0', result: 'c' }), co,
      merge].forEach(function (n) { f.appendChild(n); });
    defs.appendChild(f);
    var g = el('g', {});
    Array.prototype.slice.call(svg.childNodes).forEach(function (n) { if (n !== defs) g.appendChild(n); });
    svg.appendChild(g);
    var on = false, w = vb.width;
    return function (a, seed) {
      if (a <= 0.01) { if (on) { g.removeAttribute('filter'); on = false; } return; }
      if (!on) { g.setAttribute('filter', 'url(#' + id + ')'); on = true; }
      turb.setAttribute('seed', seed);
      disp.setAttribute('scale', (a * w * 0.09).toFixed(2));
      ro.setAttribute('dx', (a * w * 0.012).toFixed(2));
      co.setAttribute('dx', (-a * w * 0.012).toFixed(2));
    };
  }
  function rnd(n) { var x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
  function glAt(t, list, who) {
    var a = 0, seed = 1;
    for (var i = 0; i < list.length; i++) {
      var e = list[i];
      if (e[3].indexOf(who) < 0) continue;
      var p = (t - e[0]) / e[1];
      if (p < 0 || p >= 1) continue;
      var step = Math.floor(t * 28);
      var k = e[2] * (1 - p * 0.6) * (rnd(step + i * 7) < 0.25 ? 0.15 : 0.6 + 0.4 * rnd(step * 3.1));
      if (k > a) { a = k; seed = 1 + (step % 97); }
    }
    return [a, seed];
  }

  // ---------- Ablauf auf einem Zeichen ----------
  // Einzählen und Biegen wie im Kopf, danach der Kreislauf
  var T = { bars: [0.3, 0.7, 1.1], barDur: 0.32, bend: 1.5, bendDur: 0.85, loop: 2.45 };
  function scaleY(e, k) {
    e.setAttribute('transform', k >= 1 ? '' : 'translate(0 8) scale(1 ' + Math.max(k, 0.0001) + ') translate(0 -8)');
  }

  function TTGOlauf(svg, opts) {
    opts = opts || {};
    var Z = TTGOzeichen(svg, { ink: opts.ink || '#efebe3', red: opts.red || '#d22b1f', manual: true });
    var stab = svg.querySelector('.z-stab');
    var bars = Array.prototype.slice.call(svg.querySelectorAll(':scope > rect'));
    if (reduce || opts.still) { Z.set(1, 1); return { still: true }; }
    var gl = opts.stoerung === false ? function () {} : stoerungFor(svg);
    var visible = true, printing = false, last = null, t = 0;
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) { visible = es[es.length - 1].isIntersecting; }, { rootMargin: '80px' }).observe(svg);
    }
    window.addEventListener('beforeprint', function () {
      printing = true; gl(0); Z.set(1, 1);
      bars.forEach(function (r) { r.removeAttribute('transform'); r.style.opacity = 1; });
    });
    window.addEventListener('afterprint', function () { printing = false; });

    function frame(now) {
      requestAnimationFrame(frame);
      if (last === null) last = now;
      var dt = Math.min((now - last) / 1000, 0.1); last = now;
      if (!visible || printing) return;
      t += dt;
      if (bars.length === 2 && stab) {
        [bars[0], stab, bars[1]].forEach(function (r, i) {
          var k = seg(t, T.bars[i], T.barDur);
          scaleY(r, expoOut(k));
          r.style.opacity = Math.min(1, k * 2.5);
        });
      }
      if (t < T.loop) {
        Z.set(inOut(seg(t, T.bend, T.bendDur)), clamp((t - T.bend - 0.35) / (T.bendDur - 0.35)), 1);
        gl(0);
      } else {
        var u = (t - T.loop) % LOOP;
        zeige(Z, u);
        var g = glAt(u, GLSCORE, 'm');
        gl(g[0], g[1]);
      }
    }
    requestAnimationFrame(frame);
    return { still: false };
  }
  TTGOlauf.LOOP = LOOP; TTGOlauf.zustand = zustand; TTGOlauf.zeige = zeige; TTGOlauf.stoerungen = GLSCORE;
  TTGOlauf.TL = TL; TTGOlauf.glAt = glAt; TTGOlauf.stoerungFor = stoerungFor; TTGOlauf.T = T;
  window.TTGOlauf = TTGOlauf;
})();

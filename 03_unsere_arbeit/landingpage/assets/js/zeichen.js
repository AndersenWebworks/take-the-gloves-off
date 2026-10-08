/* Take the gloves off! – animierte Bildmarke
 * Der mittlere Stab steht gerade in der Farbe der anderen Stäbe, biegt sich, wird rot,
 * geht in Überblendungen durch die Figuren (Daumenkino) und wird wieder zum geraden Stab.
 * Aufruf: TTGOzeichen(svg, { ink: '#efebe3', red: '#d22b1f' })
 * Im svg: <path class="z-stab">, optional <g class="z-figuren"> mit einem <path> je Figur.
 */
(function () {
  'use strict';
  var BAR = { x: 45.5, top: 8, bottom: 92, w: 9, bend: 12 };

  function bentBar(off) {
    var t0 = .3, t1 = .78, n = 56, L = BAR.bottom - BAR.top, x = BAR.x, w = BAR.w;
    function cx(t) { if (t <= t0) return 0; if (t >= t1) return off; var u = (t - t0) / (t1 - t0); return off * (3 * u * u - 2 * u * u * u); }
    function sl(t) { if (t <= t0 || t >= t1) return 0; var u = (t - t0) / (t1 - t0); return off * (6 * u - 6 * u * u) / (t1 - t0) / L; }
    var ts = [0, t0], i; for (i = 1; i < n; i++) ts.push(t0 + (t1 - t0) * i / n); ts.push(t1, 1);
    var l = [], r = [];
    ts.forEach(function (t) {
      var y = BAR.top + L * t, c = x + w / 2 + cx(t), s = sl(t), k = Math.sqrt(1 + s * s), nx = 1 / k, ny = -s / k;
      l.push([c - nx * w / 2, y - ny * w / 2]); r.push([c + nx * w / 2, y + ny * w / 2]);
    });
    l[0][1] = r[0][1] = BAR.top; l[l.length - 1][1] = r[r.length - 1][1] = BAR.bottom;
    var p = l.concat(r.reverse());
    return 'M' + p.map(function (q) { return q[0].toFixed(2) + ' ' + q[1].toFixed(2); }).join(' L') + ' Z';
  }

  function hex(c) { c = c.replace('#', ''); return [0, 2, 4].map(function (i) { return parseInt(c.substr(i, 2), 16); }); }
  function mix(a, b, t) { return 'rgb(' + a.map(function (v, i) { return Math.round(v + (b[i] - v) * t); }).join(',') + ')'; }
  function ease(u) { u = Math.max(0, Math.min(1, u)); return u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; }
  function lin(u) { return Math.max(0, Math.min(1, u)); }

  window.TTGOzeichen = function (svg, opts) {
    opts = opts || {};
    var stab = svg.querySelector('.z-stab');
    var g = svg.querySelector('.z-figuren');
    if (g && !g.children.length && window.TTGO_FIGUREN) {
      window.TTGO_FIGUREN.forEach(function (d) {
        var p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        p.setAttribute('d', d); g.appendChild(p);
      });
    }
    // Figuren liegen hinter den äußeren Stäben: was breiter ist als die Zelle, verschwindet hinter dem Gitter
    if (g && g !== svg.firstElementChild) svg.insertBefore(g, svg.firstElementChild);
    var figs = Array.prototype.slice.call(svg.querySelectorAll('.z-figuren path:not(.z-morph)'));
    var ink = hex(opts.ink || '#efebe3'), red = hex(opts.red || '#d22b1f');
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    figs.forEach(function (f) { f.style.opacity = 0; f.setAttribute('fill', opts.red || '#d22b1f'); });

    // Der Stab verformt sich zur ersten Figur und die letzte Figur zurück zum Stab (Morph über gleich viele Umrisspunkte).
    // Zwischen zwei Figuren liegt eine Doppelbelichtung.
    var M = window.TTGO_MORPH, mp = null;
    if (g && M) {
      mp = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      mp.setAttribute('class', 'z-morph'); mp.style.opacity = 0;
      g.insertBefore(mp, g.firstChild);
    }
    figs.forEach(function (f) { f.removeAttribute('transform'); });
    function smooth(u) { u = Math.max(0, Math.min(1, u)); return u * u * (3 - 2 * u); }
    function morphD(i, t) {
      var a = M.bar, b = M.figs[i], d = 'M';
      for (var k = 0; k < a.length; k += 2) {
        d += (k ? ' L' : '') + (a[k] + (b[k] - a[k]) * t).toFixed(2) + ' ' + (a[k + 1] + (b[k + 1] - a[k + 1]) * t).toFixed(2);
      }
      return d + ' Z';
    }
    function state(bend, col, figOp) {
      stab.setAttribute('d', bentBar(BAR.bend * bend));
      var fill = mix(ink, red, col);
      stab.setAttribute('fill', fill);
      var open = 0, top = 0;
      figs.forEach(function (f, i) { var v = figOp[i] || 0; open += v; if (v > (figOp[top] || 0)) top = i; });
      if (open > 0.999) {                               // Figuren, auch während der Doppelbelichtung
        stab.style.opacity = 0;
        if (mp) mp.style.opacity = 0;
        figs.forEach(function (f, i) { f.style.opacity = smooth(figOp[i] || 0); });
      } else if (open > 0.001 && mp && M.figs[top]) { // Stab und Figur verformen sich ineinander
        stab.style.opacity = 0;
        mp.setAttribute('d', morphD(top, smooth(open)));
        mp.setAttribute('fill', fill);
        mp.style.opacity = 1;
        figs.forEach(function (f) { f.style.opacity = 0; });
      } else {
        stab.style.opacity = 1;
        if (mp) mp.style.opacity = 0;
        figs.forEach(function (f) { f.style.opacity = 0; });
      }
    }
    var api = { set: state, figuren: figs.length };
    if (opts.manual) return api;                      // Ablauf kommt von außen (Kopf der Seite)
    if (reduce || opts.still) { state(1, 1, []); return api; }

    // Zeitplan in Sekunden
    var nf = figs.length, hold = 0.6, fade = 0.3, morph = 0.5;
    var tBend0 = 0.5, tBend1 = 1.4;
    var tFig0 = tBend1 + 0.35;                        // der Stab beginnt sich zur Figur zu verformen
    var figEnd = nf ? tFig0 + morph + nf * hold + (nf - 1) * fade : tBend1 + 1.2;
    var tBack1 = figEnd + morph;                      // wieder der gebogene Stab
    var tUn0 = tBack1 + 1.2, tUn1 = tUn0 + 0.8;
    var total = tUn1 + 1.0;
    var start = null;

    function frame(now) {
      if (start === null) start = now;
      var s = ((now - start) / 1000) % total;
      var bend, col, op = [];
      if (s < tBend0) { bend = 0; col = 0; }
      else if (s < tBend1) { var u = ease((s - tBend0) / (tBend1 - tBend0)); bend = u; col = lin((s - tBend0 - .3) / (tBend1 - tBend0 - .3)); }
      else if (s < tUn0) { bend = 1; col = 1; }
      else if (s < tUn1) { var v = ease((s - tUn0) / (tUn1 - tUn0)); bend = 1 - v; col = 1 - lin(v * 1.3); }
      else { bend = 0; col = 0; }
      for (var i = 0, a = tFig0; i < nf; i++) {
        var inD = i ? fade : morph, outD = i < nf - 1 ? fade : morph;
        var b = a + inD + hold;                        // Ausblenden beginnt (nächste kommt)
        var o = 0;
        if (s >= a && s < a + inD) o = (s - a) / inD;
        else if (s >= a + inD && s < b) o = 1;
        else if (s >= b && s < b + outD) o = 1 - (s - b) / outD;
        op.push(o);
        a = b;
      }
      state(bend, col, op);
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    return api;
  };
})();

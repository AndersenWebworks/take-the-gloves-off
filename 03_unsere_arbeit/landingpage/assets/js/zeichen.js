/* Take the gloves off! – animierte Bildmarke
 * Der mittlere Stab biegt sich, wird rot und wechselt per Flash (kein Morph) zwischen hängenden Luftartistik-Figuren.
 * Die Umrisse der fünf Figuren stehen in morph.js (je Figur ein Bild p0..p4).
 * Aufruf: TTGOzeichen(svg, { ink: '#efebe3', red: '#d22b1f', manual: true })
 * Im svg: <path class="z-stab">, <g class="z-figuren"> (nimmt den Figuren-Pfad auf).
 * Programmierschnittstelle: set(bend, col) Stab zeichnen; halte(figur, sway, glow) Figur 0..4 stehend (sway wird ignoriert, die Figur steht still;
 * glow > 0: einziger kurzer Impuls in heißerem Rot, nur Füllfarbe); dunkel() alles aus.
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
    if (g && g !== svg.firstElementChild) svg.insertBefore(g, svg.firstElementChild);   // Figuren hinter den äußeren Stäben
    var ink = hex(opts.ink || '#efebe3'), red = hex(opts.red || '#d22b1f');
    var M = window.TTGO_MORPH, mp = null, S = null;
    if (g && M) {
      mp = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      mp.setAttribute('class', 'z-morph'); mp.setAttribute('fill-rule', 'evenodd'); mp.style.opacity = 0;
      g.appendChild(mp);
      // Stützformen entpacken: je Bild Liste von Umrissen { id, p: Float32Array(x0,y0,x1,y1,...) }
      S = {};
      Object.keys(M.seq).forEach(function (name) {
        S[name] = M.seq[name].map(function (row) {
          var i = 1, fr = [];
          for (var c = 0; c < row[0]; c++) {
            var id = row[i], n = row[i + 1], p = new Float32Array(2 * n), x = row[i + 2], y = row[i + 3];
            p[0] = x / M.q; p[1] = y / M.q;
            for (var k = 1; k < n; k++) { x += row[i + 2 + 2 * k]; y += row[i + 3 + 2 * k]; p[2 * k] = x / M.q; p[2 * k + 1] = y / M.q; }
            fr.push({ id: id, p: p }); i += 2 + 2 * n;
          }
          return fr;
        });
      });
    }
    var HOLD = ['p0', 'p1', 'p2', 'p3', 'p4'];                         // Figur i = einziges Bild der Folge p<i>
    var HOT = [240, 62, 46];                                           // heißeres Rot für das Nachglühen

    function pathOf(a) {
      var d = '';
      for (var c = 0; c < a.length; c++) {
        var p = a[c].p;
        d += 'M';
        for (var k = 0; k < p.length; k += 2) d += (k ? 'L' : '') + p[k].toFixed(2) + ' ' + p[k + 1].toFixed(2);
        d += 'Z';
      }
      return d;
    }
    function showMorph(d, col, sway) {
      stab.style.opacity = 0;
      mp.setAttribute('d', d);
      mp.setAttribute('fill', mix(ink, red, col));
      if (sway) mp.setAttribute('transform', 'rotate(' + sway.toFixed(3) + ' 50 8)'); else mp.removeAttribute('transform');
      mp.style.opacity = 1; mp.style.filter = '';
    }
    function set(bend, col) {                           // der gebogene Stab (gerade, gebogen, weiß, rot)
      stab.setAttribute('d', bentBar(BAR.bend * bend));
      stab.setAttribute('fill', mix(ink, red, col));
      stab.style.opacity = 1;
      if (mp) mp.style.opacity = 0;
    }
    // Figur i = einziges Bild der Folge p<i>
    var HOT = [240, 62, 46];                                           // heißeres Rot für das Nachglühen

    function pathOf(a) {
      var d = '';
      for (var c = 0; c < a.length; c++) {
        var p = a[c].p;
        d += 'M';
        for (var k = 0; k < p.length; k += 2) d += (k ? 'L' : '') + p[k].toFixed(2) + ' ' + p[k + 1].toFixed(2);
        d += 'Z';
      }
      return d;
    }
    function showMorph(d, col, sway) {
      stab.style.opacity = 0;
      mp.setAttribute('d', d);
      mp.setAttribute('fill', mix(ink, red, col));
      if (sway) mp.setAttribute('transform', 'rotate(' + sway.toFixed(3) + ' 50 8)'); else mp.removeAttribute('transform');
      mp.style.opacity = 1; mp.style.filter = '';
    }
    function set(bend, col) {                           // der gebogene Stab (gerade, gebogen, weiß, rot)
      stab.setAttribute('d', bentBar(BAR.bend * bend));
      stab.setAttribute('fill', mix(ink, red, col));
      stab.style.opacity = 1;
      if (mp) mp.style.opacity = 0;
    }
    function morph(name, u, rev, col) {
      if (!mp || !S[name]) return;
      var last = S[name].length - 1;
      showMorph(frameD(name, (rev ? 1 - u : u) * last), col == null ? 1 : col, 0);
    }
    // Figur i (0..4) steht vollständig da. glow > 0: kurzer Impuls nach dem Flash (heißeres Rot, nur Füllfarbe,
    // nie Weiß, kein Filter); 0 = Normalzustand.
    function halte(i, sway, glow) {
      if (!mp) return;
      showMorph(pathOf(S[HOLD[i]][0]), 1, 0);          // nie Drehung, nie Filter: die Figur steht absolut still
      if (glow > 0) mp.setAttribute('fill', mix(red, HOT, 0.8));   // kurzer harter Impuls, nur Füllfarbe
    }
    function dunkel() {                                 // Figur aus (Dunkelphase des Flash): weder Stab noch Figur
      if (!mp) return;
      stab.style.opacity = 0; mp.style.opacity = 0; mp.style.filter = '';
    }
    return { set: set, halte: halte, dunkel: dunkel, figuren: 5 };
  };
})();

/* Take the gloves off! – Titelsequenz im Kopf der Seite
 * Ein Takt für alles: Dunkel, die Stäbe fallen, das Licht kommt, der Stab bricht
 * (und mit ihm das Bild), dann der Titel Zeile für Zeile, das Ausrufezeichen,
 * die Unterzeile unter einem Balken hervor, zuletzt die Bedienelemente.
 * Danach ruht das Zeichen gebogen und verwandelt sich in Abständen in hängende Luftartistik-Figuren.
 */
(function () {
  'use strict';
  var hero = document.querySelector('.hero');
  if (!hero) return;
  var NS = 'http://www.w3.org/2000/svg';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var root = document.documentElement;

  var mark = hero.querySelector('svg.zeichen-kopf');
  var bars = mark ? mark.querySelectorAll(':scope > rect') : [];
  var stab = mark ? mark.querySelector('.z-stab') : null;
  var Z = mark ? TTGOzeichen(mark, { ink: mark.getAttribute('data-ink') || '#efebe3', red: '#d22b1f', manual: true }) : null;
  var word = hero.querySelector('svg.wordmark');
  var fxwrap = document.getElementById('heroFx');
  var video = document.getElementById('heroVid');
  var inner = hero.querySelector('.in');

  // ---------- Hilfen ----------
  function clamp(u) { return u < 0 ? 0 : u > 1 ? 1 : u; }
  function seg(t, a, d) { return clamp((t - a) / d); }
  function expoOut(u) { return u >= 1 ? 1 : 1 - Math.pow(2, -10 * u); }
  function inOut(u) { return u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; }
  function backOut(u) { var c = 1.6; u -= 1; return 1 + (c + 1) * u * u * u + c * u * u; }

  // Bewegliche Teile des Schriftzugs: drei Zeilen, Ausrufezeichen (Stab, Punkt), Unterzeile
  var W = null;
  function prepWord() {
    if (!word) return;
    var els = word.querySelectorAll(':scope > path, :scope > rect');
    if (els.length < 6) return;
    W = { lines: [], bang: els[3], dot: els[4], sub: els[5] };
    var defs = document.createElementNS(NS, 'defs');
    word.insertBefore(defs, word.firstChild);
    for (var i = 0; i < 3; i++) {
      var el = els[i], bb = el.getBBox();
      // jede Zeile bekommt ein eigenes Fenster, aus dem sie von unten heraufsteigt
      var cp = document.createElementNS(NS, 'clipPath'); cp.id = 'kopfZeile' + i;
      var r = document.createElementNS(NS, 'rect');
      r.setAttribute('x', bb.x - 20); r.setAttribute('y', bb.y - 4);
      r.setAttribute('width', bb.width + 40); r.setAttribute('height', bb.height + 8);
      cp.appendChild(r); defs.appendChild(cp);
      var g = document.createElementNS(NS, 'g'); g.setAttribute('clip-path', 'url(#kopfZeile' + i + ')');
      el.parentNode.insertBefore(g, el); g.appendChild(el);
      W.lines.push({ el: el, h: bb.height + 8 });
    }
    var bb2 = W.bang.getBBox(); W.bangTop = bb2.y;
    var bd = W.dot.getBBox(); W.dotC = [bd.x + bd.width / 2, bd.y + bd.height / 2];
    var bs = W.sub.getBBox();
    // Balken über der Unterzeile, wie eine Schwärzung, die abgezogen wird
    W.bar = document.createElementNS(NS, 'rect');
    W.bar.setAttribute('x', bs.x - 3); W.bar.setAttribute('y', bs.y - 3);
    W.bar.setAttribute('width', bs.width + 6); W.bar.setAttribute('height', bs.height + 6);
    W.bar.setAttribute('fill', '#efebe3');
    word.appendChild(W.bar);
    W.subBox = [bs.x - 3, bs.width + 6];
  }

  function scaleY(el, k, top) {
    el.setAttribute('transform', k >= 1 ? '' : 'translate(0 ' + top + ') scale(1 ' + Math.max(k, 0.0001) + ') translate(0 ' + (-top) + ')');
  }

  // ---------- Zeitplan (Sekunden ab Seitenaufruf) ----------
  var T = {
    bars: [0.3, 0.7, 1.1], barDur: 0.32,    // eingezählt: eins, zwei, drei, von links nach rechts
    light: 1.3,                              // das Bild blendet auf (CSS-Übergang 1,5 s)
    bend: 1.5, bendDur: 0.85,                // auf die Vier bricht der mittlere, das Bild biegt sich mit
    move: 2.45, moveDur: 0.9,                // das Zeichen rückt aus der Mitte an seinen Platz
    lines: [2.7, 2.83, 2.96], lineDur: 0.8,  // Titel Zeile für Zeile
    bang: 3.4, bangDur: 0.4, dot: 3.7,       // das Ausrufezeichen fällt, der Punkt schlägt ein
    cover: 3.85, coverDur: 0.25, uncover: 4.1, uncoverDur: 0.55,
    ui: 4.55,                                // Bedienelemente
    loop: 4.75                               // ab hier der Kreislauf
  };
  // Signalstörungen: kurz, an den Schnittpunkten der Sequenz (Zeit, Dauer, Stärke, Ziel)
  // m = Zeichen, w = Schriftzug, v = Videobild
  var GL = [
    [0.36, 0.07, 0.2, 'm'], [0.76, 0.07, 0.2, 'm'], [1.16, 0.08, 0.25, 'm'],
    [1.7, 0.2, 0.75, 'mv'],
    [2.77, 0.13, 0.45, 'w'], [2.9, 0.11, 0.3, 'w'], [3.03, 0.14, 0.5, 'w'],
    [3.7, 0.12, 0.45, 'wv'],
    [4.13, 0.1, 0.3, 'w']
  ];
  // ---------- Partitur des Kreislaufs ----------
  // Alles, was im Kreislauf geschieht, steht hier als Daten; der Ablauf wird daraus abgespielt. Zeiten in Schlägen (BEAT = 1 Viertel).
  // Bogen: Auftakt -> Steigerung (accelerando) -> Ausbruch (hektisch) -> Höhepunkt (langes Rot, Ausglimmen) -> Ruhe -> neu.
  // Figuren stehen absolut still (kein Morph, keine Drehung/Skalierung/Versatz); jede Figur blitzt: schlagartig warmes Weiß mit
  // kleinem Schein -> Rot -> Ausglimmen. Sicherheit (WCAG 2.3.1): Abstand zweier Blitzstarts mindestens MIN_ABSTAND (< 3 Blitze je Sekunde).
  var BPM = 128;
  var BEAT = 60 / BPM;                                  // s je Schlag (0,469 s)
  var MIN_ABSTAND = 0.34;                               // s, kleinster erlaubter Abstand zweier Blitzstarts
  function b(n) { return n * BEAT; }
  //  was: 'stab' (Stab, gebogen und rot) oder 'pose' (pose 0..4 = Figur 1..5)
  //  dunkel: Dunkelphase davor; halt: Dauer der Sichtbarkeit nach der Dunkelphase (inkl. Aus-/Einblenden)
  //  Pose: weiss/rot = Sekunden warmes Weiß / Weiß->Rot, glow = Dauer des Scheins (s), schein = Stärke/Helligkeit des Scheins (1 = normal), radius = Weichzeichner-Faktor des Scheins (Standard = schein; kleiner = enger am Umriss), fade = Ausglimmen am Ende (s)
  //  Stab: ein = sanftes Einblenden (s), aus = hartes Ausfaden am Ende (s), atmen = leichtes Atmen der Biegung
  //  stoerung: [Beginn nach Start der Sichtbarkeit (s), Dauer (s), Stärke, Ziel 'm' Zeichen / 'v' Videobild / 'w' Schriftzug]
  var SCORE = [
    { was: 'stab', halt: b(0.75), aus: 0.06 },                                                                                  // Auftakt: Stab kurz, hartes Aus
    // Steigerung: Haltezeiten 0,59 -> 0,35 s, Dunkelphasen 0,12 -> 0,06 s
    { was: 'pose', pose: 0, dunkel: b(0.25),  halt: b(1.25), weiss: 0.05, rot: 0.12, glow: 0.06, schein: 1, fade: 0.24 },
    { was: 'pose', pose: 1, dunkel: b(0.20),  halt: b(1.00), weiss: 0.05, rot: 0.12, glow: 0.06, schein: 1, fade: 0.20 },
    { was: 'pose', pose: 2, dunkel: b(0.18),  halt: b(0.90), weiss: 0.05, rot: 0.11, glow: 0.06, schein: 1, fade: 0.18 },
    { was: 'pose', pose: 3, dunkel: b(0.15),  halt: b(0.80), weiss: 0.05, rot: 0.10, glow: 0.06, schein: 1, fade: 0.16 },
    { was: 'pose', pose: 4, dunkel: b(0.125), halt: b(0.75), weiss: 0.05, rot: 0.09, glow: 0.07, schein: 1.2, fade: 0.14 },
    // Ausbruch: vier Blitze im Mindestabstand (Figuren 3, 1, 4, 2), stärkerer Schein; einmalige Signalstörung auf dem dritten Blitz
    { was: 'pose', pose: 2, dunkel: b(0.125), halt: b(0.625), weiss: 0.05, rot: 0.08, glow: 0.08, schein: 1.5, fade: 0.10 },
    { was: 'pose', pose: 0, dunkel: b(0.125), halt: b(0.625), weiss: 0.05, rot: 0.08, glow: 0.08, schein: 1.5, fade: 0.10 },
    { was: 'pose', pose: 3, dunkel: b(0.125), halt: b(0.625), weiss: 0.05, rot: 0.08, glow: 0.08, schein: 1.6, fade: 0.10, stoerung: [0.0, 0.16, 0.7, 'mv'] },
    { was: 'pose', pose: 1, dunkel: b(0.125), halt: b(0.625), weiss: 0.05, rot: 0.08, glow: 0.08, schein: 1.6, fade: 0.10 },
    // Höhepunkt: Figur 4 (zusammengekrümmt in der Schlaufe), stärkster Blitz, steht lange rot, glimmt dann langsam aus
    { was: 'pose', pose: 3, dunkel: b(0.25),  halt: b(3.75),  weiss: 0.10, rot: 0.22, glow: 0.18, schein: 3, radius: 1.3, fade: 0.60 },
    // Ruhe (2 Takte statt 1): Dunkel, dann erscheint der Stab sanft und atmet; auf Schlag 5 der Sichtbarkeit ein kurzes, leises Nachbeben (Störung nur am Zeichen, kein Blitz)
    { was: 'stab', dunkel: b(1.0), halt: b(8.0), ein: 0.7, atmen: true, stoerung: [b(5.0), 0.14, 0.3, 'm'] }
  ];
  var FIGUREN = 5;                                      // Anzahl der Figuren (morph.js: p0 bis p4)
  var TL = [], LOOP = 0, GLSCORE = [], BLITZE = [];     // Zeitplan, Zykluslänge, Störungen, Blitzstarts (aus SCORE errechnet)
  (function () {
    var t = 0;
    SCORE.forEach(function (e, i) {
      var ev = { e: e, i: i, t0: t, ts: t + (e.dunkel || 0), te: t + (e.dunkel || 0) + e.halt };
      TL.push(ev); t = ev.te;
      if (e.was === 'pose') BLITZE.push({ t: ev.ts, i: i, pose: e.pose });
      if (e.stoerung) GLSCORE.push([ev.ts + e.stoerung[0], e.stoerung[1], e.stoerung[2], e.stoerung[3]]);
    });
    LOOP = t;
  })();
  function loopState(u) {
    var r = { bend: 1, hold: -1, tt: 0, dur: 1, fx: null, dark: false, stab: 1, env: 0 };
    for (var i = 0; i < TL.length; i++) {
      var v = TL[i], e = v.e;
      if (u < v.t0 || u >= v.te) continue;
      if (u < v.ts) { r.dark = true; break; }
      var d = u - v.ts;
      if (e.was === 'pose') { r.hold = e.pose; r.tt = d; r.dur = e.halt; r.fx = e; }
      else {
        r.stab = e.ein ? ease3(seg(d, 0, e.ein)) : 1 - (e.aus ? seg(d, e.halt - e.aus, e.aus) : 0);
        // Atmen nur in der Ruhe, an Anfang und Ende auf null gezogen (kein Sprung)
        if (e.atmen) r.env = seg(d, 0.4, 1.0) * (1 - seg(d, e.halt - 0.8, 0.8));
        r.bend = 1 + 0.035 * r.env * Math.sin(u * Math.PI * 2 / 4.6);
      }
      break;
    }
    return r;
  }
  function ease3(u) { return u * u * (3 - 2 * u); }

  var cur = { bend: 0 };
  function drive() { return cur.bend * 0.95; }

  // ---------- Signalstörung ----------
  // Ein SVG-Filter schiebt waagerechte Streifen gegeneinander und spaltet Rot und Cyan ab,
  // wie eine gestörte Videoeinblendung. Er hängt nur während einer Störung am Element.
  function el(tag, attrs) { var n = document.createElementNS(NS, tag); for (var k in attrs) n.setAttribute(k, attrs[k]); return n; }
  var nGl = 0;
  function stoerung(svg) {
    if (!svg || !svg.viewBox || !svg.viewBox.baseVal || !svg.viewBox.baseVal.width) return function () {};
    var vb = svg.viewBox.baseVal, id = 'kopfStoer' + (nGl++);
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
    // alles Sichtbare in eine Gruppe, die den Filter trägt
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
  // Stärke der Störung für ein Ziel zu einem Zeitpunkt; sie ruckelt in Bildern statt fließend
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
  // im Kreislauf: genau die Störungen der Partitur (einmaliger Akzent im Ausbruch)
  function loopGL() { return GLSCORE; }
  var glV = 0;

  // ---------- Endzustand ohne Bewegung ----------
  if (reduce) {
    if (Z) Z.set(1, 1);
    root.classList.remove('intro');
    hero.classList.add('lit', 'ui-on');
    if (window.TTGOfx && fxwrap && video) try { TTGOfx.biegen(fxwrap, video, { drive: function () { return 0.6; } }); } catch (e) {}
    return;
  }

  prepWord();
  if (window.TTGOfx && fxwrap && video) try { TTGOfx.biegen(fxwrap, video, { drive: drive, glitch: function () { return glV; } }); } catch (e) {}
  var stM = stoerung(mark), stW = stoerung(word);

  // Abstand des Zeichens zur Bildmitte, solange es allein steht
  var off = [0, 0];
  function measure() {
    if (!mark || !inner) return;
    var keep = mark.style.transform; mark.style.transform = '';
    var a = mark.getBoundingClientRect(), b = inner.getBoundingClientRect();
    off = [b.left + b.width / 2 - (a.left + a.width / 2), b.top + b.height / 2 - (a.top + a.height / 2)];
    mark.style.transform = keep;
  }
  window.addEventListener('resize', measure);

  // Wer scrollt, klickt oder eine Taste drückt, muss nicht warten: die Sequenz läuft dann im Zeitraffer
  var speed = 1;
  function hurry() { speed = 5; }
  ['wheel', 'touchstart', 'pointerdown', 'keydown'].forEach(function (e) { window.addEventListener(e, hurry, { passive: true }); });
  if (window.scrollY > 40) speed = 50;

  var last = null, t = 0;
  function frame(now) {
    if (last === null) { last = now; root.classList.remove('intro'); measure(); }
    var dt = Math.min((now - last) / 1000, 0.1); last = now;
    t += dt * (t < T.loop ? speed : 1);

    // Stäbe
    if (bars.length === 2 && stab) {
      [bars[0], stab, bars[1]].forEach(function (b, i) {
        var k = seg(t, T.bars[i], T.barDur);
        scaleY(b, expoOut(k), 8);
        b.style.opacity = Math.min(1, k * 2.5);
      });
    }
    // Zeichen
    var st;
    if (t < T.loop) {
      var b = inOut(seg(t, T.bend, T.bendDur));
      st = { bend: b, col: clamp((t - T.bend - 0.35) / (T.bendDur - 0.35)), hold: -1, stab: 1 };
    } else {
      st = loopState((t - T.loop) % LOOP);
    }
    cur.bend = st.bend;
    if (Z) {
      if (st.dark) Z.dunkel();
      else if (st.hold >= 0) Z.halte(st.hold, st.tt, st.dur, st.fx);
      else Z.set(st.bend, st.col == null ? 1 : st.col, st.stab);
    }

    // Signalstörungen
    var gt = t, gl = GL;
    if (t >= T.loop) { gt = (t - T.loop) % LOOP; gl = loopGL(); }
    var gm = glAt(gt, gl, 'm'), gw = glAt(gt, gl, 'w');
    stM(gm[0], gm[1]); stW(gw[0], gw[1]);
    glV = glAt(gt, gl, 'v')[0];

    // Zeichen erst in der Mitte, dann an seinem Platz neben dem Titel
    if (mark) {
      var m = 1 - inOut(seg(t, T.move, T.moveDur));
      mark.style.transform = m > 0 ? 'translate3d(' + (off[0] * m).toFixed(1) + 'px,' + (off[1] * m).toFixed(1) + 'px,0)' : '';
    }

    // Licht
    if (t >= T.light && !hero.classList.contains('lit')) {
      if (speed > 1 && fxwrap) fxwrap.style.transitionDuration = '0.8s';
      hero.classList.add('lit');
    }

    // Titel
    if (W) {
      W.lines.forEach(function (ln, i) {
        var k = expoOut(seg(t, T.lines[i], T.lineDur));
        ln.el.setAttribute('transform', k >= 1 ? '' : 'translate(0 ' + (ln.h * (1 - k)).toFixed(2) + ')');
      });
      scaleY(W.bang, expoOut(seg(t, T.bang, T.bangDur)), W.bangTop);
      W.bang.style.opacity = t >= T.bang ? 1 : 0;
      var d = seg(t, T.dot, 0.28), s = 1 + 0.9 * (1 - expoOut(d));
      W.dot.style.opacity = d > 0 ? Math.min(1, d * 3) : 0;
      W.dot.setAttribute('transform', d >= 1 ? '' : 'translate(' + W.dotC[0] + ' ' + W.dotC[1] + ') scale(' + s.toFixed(3) + ') translate(' + (-W.dotC[0]) + ' ' + (-W.dotC[1]) + ')');
      var c1 = expoOut(seg(t, T.cover, T.coverDur)), c2 = inOut(seg(t, T.uncover, T.uncoverDur));
      var x = W.subBox[0], bw = W.subBox[1];
      W.sub.style.opacity = t >= T.uncover ? 1 : 0;
      W.bar.setAttribute('x', (x + bw * c2).toFixed(2));
      W.bar.setAttribute('width', Math.max(0, bw * (c2 > 0 ? 1 - c2 : c1)).toFixed(2));
    }

    // Bedienelemente
    if (t >= T.ui && !hero.classList.contains('ui-on')) hero.classList.add('ui-on');

    // Kamera: langsame Fahrt ins Bild, beim Scrollen Parallaxe und Abblenden
    var y = Math.min(window.scrollY, hero.offsetHeight), h = hero.offsetHeight || 1;
    if (fxwrap) {
      var push = 1.12 - 0.12 * (1 - Math.pow(1 - clamp(t / 18), 3));
      fxwrap.style.transform = 'translate3d(0,' + (y * 0.35).toFixed(1) + 'px,0) scale(' + push.toFixed(4) + ')';
    }
    if (inner) {
      inner.style.transform = y > 0 ? 'translate3d(0,' + (y * 0.22).toFixed(1) + 'px,0)' : '';
      inner.style.opacity = y > 0 ? clamp(1 - y / (h * 0.7)).toFixed(3) : '';
    }
    hero.style.setProperty('--dim', clamp(y / (h * 0.8)).toFixed(3));

    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // Druck: alles im Endzustand
  window.addEventListener('beforeprint', function () {
    stM(0); stW(0);
    if (Z) Z.set(1, 1);
    if (mark) mark.style.transform = '';
    if (W) {
      W.lines.forEach(function (ln) { ln.el.setAttribute('transform', ''); });
      [W.bang, W.dot, W.sub].forEach(function (el) { el.style.opacity = 1; el.setAttribute('transform', ''); });
      W.bar.setAttribute('width', 0);
    }
  });
})();

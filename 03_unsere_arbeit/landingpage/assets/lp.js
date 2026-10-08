/* Take the gloves off! – Landingpage: Sprache, Effekte, Schwärzung, Demos, Galerie */
(function () {
  'use strict';
  var root = document.documentElement;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var TITLE = { de: 'Take the gloves off! – Musiktheater mit zeitgenössischem Zirkus', en: 'Take the gloves off! – A musical with contemporary circus' };

  // Sprache
  function setLang(l) {
    root.lang = l;
    document.title = TITLE[l];
    document.querySelectorAll('img[data-alt-en]').forEach(function (im) {
      if (!im.hasAttribute('data-alt-de')) im.setAttribute('data-alt-de', im.alt);
      im.alt = im.getAttribute('data-alt-' + l);
    });
    try { localStorage.setItem('ttgo-lang', l); } catch (e) {}
  }
  document.querySelectorAll('.lang button').forEach(function (b) {
    b.addEventListener('click', function () { setLang(b.getAttribute('data-set')); });
  });
  setLang(root.lang === 'en' ? 'en' : 'de');

  // Videoeffekte
  if (window.TTGOfx) {
    [['bendFx', 'bendVid', 'biegen'], ['fullFx', 'fullVid', 'nachbild']].forEach(function (f) {
      var el = document.getElementById(f[0]), v = document.getElementById(f[1]);
      if (el && v) try { TTGOfx[f[2]](el, v); } catch (e) {}
    });
  }

  // Stumme Hintergrundvideos laufen nur, solange sie im Bild sind
  var loops = Array.prototype.slice.call(document.querySelectorAll('video[muted], video[aria-hidden]'));
  if ('IntersectionObserver' in window) {
    var vio = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        var v = e.target;
        if (e.isIntersecting) { if (v.paused) { var p = v.play(); if (p && p.catch) p.catch(function () {}); } }
        else if (!v.paused) v.pause();
      });
    }, { rootMargin: '150px 0px' });
    loops.forEach(function (v) { vio.observe(v); });
  }

  // Schwärzung zum Antippen
  var bars = Array.prototype.slice.call(document.querySelectorAll('.rd'));
  var hints = document.querySelectorAll('.hint');
  var lastUser = 0, silenceOver = false;
  function set(el, open, ms) {
    el.classList.toggle('open', open);
    el.setAttribute('aria-pressed', open ? 'true' : 'false');
    clearTimeout(el._t);
    if (open && ms && !silenceOver) el._t = setTimeout(function () { set(el, false); }, ms);
  }
  bars.forEach(function (el) {
    var act = function () {
      lastUser = Date.now();
      hints.forEach(function (h) { h.classList.add('gone'); });
      set(el, !el.classList.contains('open'), 6000);
    };
    el.addEventListener('click', act);
    el.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); act(); } });
  });
  function inView(el) { var r = el.getBoundingClientRect(); return r.bottom > 0 && r.top < window.innerHeight && el.offsetParent; }
  if (!reduce) {
    setInterval(function () {
      if (silenceOver || Date.now() - lastUser < 9000 || document.hidden) return;
      var c = bars.filter(function (el) { return !el.classList.contains('open') && inView(el); });
      if (c.length) set(c[Math.floor(Math.random() * c.length)], true, 1400);
    }, 4200);
  }
  // Beim letzten Song fallen alle Balken: Don't stay silent
  var fin = document.getElementById('final');
  if (fin && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (es, o) {
      if (!es[0].isIntersecting) return;
      silenceOver = true; o.disconnect();
      bars.forEach(function (el, i) { setTimeout(function () { set(el, true); }, reduce ? 0 : 90 * i); });
    }, { threshold: 0.9 }).observe(fin);
  }

  // Demos: immer nur eine spielt
  var audio = new Audio(), cur = null;
  audio.preload = 'none';
  function fmt(s) { s = Math.max(0, Math.floor(s || 0)); return Math.floor(s / 60) + ':' + ('0' + s % 60).slice(-2); }
  document.querySelectorAll('.track').forEach(function (tr) {
    var btn = tr.querySelector('.play'), bar = tr.querySelector('.prog'), time = tr.querySelector('.time');
    btn.addEventListener('click', function () {
      if (cur === tr) { if (audio.paused) audio.play(); else audio.pause(); return; }
      if (cur) { cur.classList.remove('on'); }
      cur = tr; audio.src = tr.getAttribute('data-src'); audio.play();
    });
    bar.addEventListener('click', function (e) {
      if (cur !== tr || !audio.duration) return;
      var r = bar.getBoundingClientRect();
      audio.currentTime = audio.duration * (e.clientX - r.left) / r.width;
    });
    tr._time = time; tr._bar = bar.querySelector('span');
  });
  audio.addEventListener('play', function () { if (cur) { cur.classList.add('on'); cur.querySelector('.play').setAttribute('aria-label', 'Pause'); } });
  audio.addEventListener('pause', function () { if (cur) { cur.classList.remove('on'); cur.querySelector('.play').setAttribute('aria-label', 'Play'); } });
  audio.addEventListener('timeupdate', function () {
    if (!cur) return;
    cur._time.textContent = fmt(audio.currentTime);
    cur._bar.style.width = (audio.duration ? 100 * audio.currentTime / audio.duration : 0) + '%';
  });
  audio.addEventListener('ended', function () { if (cur) { cur._bar.style.width = '0%'; cur._time.textContent = cur._time.getAttribute('data-total'); } });

  // Probenvideo: eigenes Startbild, danach die normalen Bedienelemente
  var pl = document.getElementById('player');
  if (pl) {
    var pv = pl.querySelector('video');
    pl.querySelector('.pl-start').addEventListener('click', function () {
      if (cur && !audio.paused) audio.pause();
      pl.classList.add('on'); pv.controls = true;
      var pr = pv.play(); if (pr && pr.catch) pr.catch(function () {});
    });
    pv.addEventListener('play', function () { if (cur && !audio.paused) audio.pause(); });
    audio.addEventListener('play', function () { if (!pv.paused) pv.pause(); });
    pv.addEventListener('ended', function () { pl.classList.remove('on'); pv.controls = false; pv.currentTime = 0; });
  }

  // Filmstreifen: ziehen, Pfeile, Zähler, Fortschritt
  var strip = document.getElementById('galerie');
  var links = Array.prototype.slice.call(strip.querySelectorAll('a'));
  var film = strip.closest('.film'), cnt = film.querySelector('.count'), prev = film.querySelector('.prev'), next = film.querySelector('.next'), prog = film.querySelector('.film-prog span');
  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function padLeft() { return parseFloat(getComputedStyle(strip).paddingLeft) || 0; }
  function current() {
    var x = strip.scrollLeft, best = 0, d = Infinity;
    links.forEach(function (a, i) { var dd = Math.abs(a.offsetLeft - padLeft() - x); if (dd < d) { d = dd; best = i; } });
    return best;
  }
  function ui() {
    var max = strip.scrollWidth - strip.clientWidth;
    var i = current();
    if (max > 0 && strip.scrollLeft >= max - 4) i = links.length - 1;
    cnt.textContent = pad2(i + 1) + ' / ' + pad2(links.length);
    prev.disabled = strip.scrollLeft <= 4;
    next.disabled = strip.scrollLeft >= max - 4;
    var vis = max > 0 ? strip.clientWidth / strip.scrollWidth : 1;
    prog.style.width = (vis * 100) + '%';
    prog.style.left = (max > 0 ? (strip.scrollLeft / max) * (100 - vis * 100) : 0) + '%';
  }
  // Blättert eine ganze Ansicht weiter, damit schmale Hochformate nicht nur ein kleines Stück schieben
  function go(dir) {
    var L = padLeft(), x = strip.scrollLeft, view = strip.clientWidth - 2 * L, i = current(), t = i;
    if (dir > 0) {
      t = links.length - 1;
      for (var k = i + 1; k < links.length; k++) {
        if (links[k].offsetLeft + links[k].offsetWidth > x + L + view + 1) { t = k; break; }
      }
      if (t <= i) t = Math.min(links.length - 1, i + 1);
    } else {
      t = 0;
      for (var j = i - 1; j >= 0; j--) {
        if (links[i].offsetLeft - links[j].offsetLeft > view + 1) { t = j + 1; break; }
      }
      if (t >= i) t = Math.max(0, i - 1);
    }
    strip.scrollTo({ left: links[t].offsetLeft - L, behavior: reduce ? 'auto' : 'smooth' });
  }
  prev.addEventListener('click', function () { go(-1); });
  next.addEventListener('click', function () { go(1); });
  strip.addEventListener('scroll', ui, { passive: true });
  window.addEventListener('resize', ui);
  strip.querySelectorAll('img').forEach(function (im) { im.addEventListener('load', ui); });
  ui();
  var dragX = null, dragS = 0, moved = false;
  strip.addEventListener('pointerdown', function (e) {
    if (e.pointerType !== 'mouse' || e.button !== 0) return;
    dragX = e.clientX; dragS = strip.scrollLeft; moved = false;
  });
  window.addEventListener('pointermove', function (e) {
    if (dragX === null) return;
    var dx = e.clientX - dragX;
    if (!moved && Math.abs(dx) > 6) { moved = true; strip.classList.add('drag'); }
    if (moved) strip.scrollLeft = dragS - dx;
  });
  window.addEventListener('pointerup', function () {
    if (dragX === null) return;
    dragX = null;
    if (moved) { strip.classList.remove('drag'); var i = current(); strip.scrollTo({ left: links[i].offsetLeft - padLeft(), behavior: 'smooth' }); }
  });
  strip.addEventListener('keydown', function (e) {
    if (e.target !== strip) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); go(1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); go(-1); }
  });

  // Lightbox mit Zähler und Bildunterschrift
  var lb = document.getElementById('lightbox'), lbImg = lb.querySelector('img'), lbNum = lb.querySelector('.lb-n-c'), lbCap = lb.querySelector('.lb-cap'), idx = 0, opener = null;
  function show(i) {
    idx = (i + links.length) % links.length;
    var a = links[idx], l = root.lang === 'en' ? 'en' : 'de';
    lbImg.classList.add('load');
    lbImg.onload = function () { lbImg.classList.remove('load'); };
    lbImg.src = a.getAttribute('href');
    lbImg.alt = a.querySelector('img').alt;
    lbNum.textContent = pad2(idx + 1) + ' / ' + pad2(links.length);
    lbCap.textContent = a.getAttribute('data-cap-' + l);
    [idx - 1, idx + 1].forEach(function (k) { var n = links[(k + links.length) % links.length]; (new Image()).src = n.getAttribute('href'); });
  }
  function close() { lb.hidden = true; document.body.style.overflow = ''; if (opener) opener.focus(); }
  links.forEach(function (a, i) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      if (moved) return;
      opener = a; show(i); lb.hidden = false; document.body.style.overflow = 'hidden'; lb.querySelector('.lb-x').focus();
    });
  });
  lb.querySelector('.lb-x').addEventListener('click', close);
  lb.querySelector('.lb-p').addEventListener('click', function () { show(idx - 1); });
  lb.querySelector('.lb-n').addEventListener('click', function () { show(idx + 1); });
  lb.addEventListener('click', function (e) { if (e.target === lb || e.target.tagName === 'FIGURE') close(); });
  document.addEventListener('keydown', function (e) {
    if (lb.hidden) return;
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowLeft') show(idx - 1);
    else if (e.key === 'ArrowRight') show(idx + 1);
  });
  var tx = null;
  lb.addEventListener('touchstart', function (e) { tx = e.touches[0].clientX; }, { passive: true });
  lb.addEventListener('touchend', function (e) {
    if (tx === null) return;
    var d = e.changedTouches[0].clientX - tx; tx = null;
    if (Math.abs(d) > 40) show(idx + (d < 0 ? 1 : -1));
  });

  // Blocksatz: jede Zeile auf die Breite des Kastens ziehen
  function fitAll() {
    document.querySelectorAll('.fitbox').forEach(function (box) {
      var W = box.clientWidth; if (!W) return;
      box.querySelectorAll('.fit').forEach(function (el) {
        el.style.fontSize = '100px'; el.style.display = 'inline-block';
        var w = el.getBoundingClientRect().width;
        el.style.fontSize = (100 * W / w) + 'px'; el.style.display = 'block';
      });
    });
  }

  // Gestaucht und gedehnt: die Breite wandert, jede Zeile füllt trotzdem die ganze Breite
  var STEPS = [62, 72, 82, 92, 102, 112, 125], sq = [], sqOn = false;
  function sqMeasure() {
    sq = [];
    document.querySelectorAll('.squeeze').forEach(function (box) {
      box.querySelectorAll('span').forEach(function (el, i) {
        el.style.display = 'inline-block'; el.style.fontSize = '100px';
        var ws = STEPS.map(function (w) { el.style.fontVariationSettings = '"wdth" ' + w; return el.getBoundingClientRect().width; });
        el.style.display = '';
        sq.push({ el: el, box: box, ws: ws, ph: i * 0.5 });
      });
    });
  }
  function sqSet(it, w) {
    var W = it.box.clientWidth; if (!W) return;
    var j = 0; while (j < STEPS.length - 2 && w > STEPS[j + 1]) j++;
    var r = (w - STEPS[j]) / (STEPS[j + 1] - STEPS[j]);
    var px = it.ws[j] + (it.ws[j + 1] - it.ws[j]) * r;
    it.el.style.fontVariationSettings = '"wdth" ' + w.toFixed(1);
    it.el.style.fontSize = (100 * W / px).toFixed(2) + 'px';
  }
  function sqFrame(now) {
    if (!sqOn) return;
    sq.forEach(function (it) {
      var u = 0.5 - 0.5 * Math.cos((now / 9000 + it.ph) * Math.PI * 2);
      u = u * u * (3 - 2 * u);
      sqSet(it, 62 + 63 * u);
    });
    requestAnimationFrame(sqFrame);
  }
  function sqStatic() { sq.forEach(function (it) { sqSet(it, 90); }); }
  function typeStart() {
    fitAll(); sqMeasure(); sqStatic();
    if (reduce) return;
    var boxes = document.querySelectorAll('.squeeze');
    if (!boxes.length || !('IntersectionObserver' in window)) return;
    new IntersectionObserver(function (es) {
      var vis = es.some(function (e) { return e.isIntersecting; });
      if (vis && !sqOn) { sqOn = true; requestAnimationFrame(sqFrame); } else if (!vis) sqOn = false;
    }).observe(boxes[0]);
  }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(typeStart); else typeStart();
  window.addEventListener('resize', function () { fitAll(); if (!sqOn) sqStatic(); });

  // Verblassend: in den Wiederholungen gehen Buchstaben verloren und kommen wieder
  document.querySelectorAll('.echo').forEach(function (box) {
    var lines = Array.prototype.slice.call(box.querySelectorAll('span')).slice(1);
    var letters = lines.map(function (ln) {
      var t = ln.textContent; ln.textContent = '';
      return t.split('').map(function (c) { var i = document.createElement('i'); i.textContent = c; ln.appendChild(i); return i; });
    });
    var LOSS = [0.08, 0.2, 0.36, 0.55];
    function tick() {
      if (document.hidden) return;
      letters.forEach(function (ls, k) {
        ls.forEach(function (i) { if (Math.random() < 0.18) i.classList.toggle('weg', Math.random() < LOSS[k]); });
      });
    }
    if (!reduce) { tick(); setInterval(tick, 1400); }
  });
})();

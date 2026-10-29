/* Take the gloves off! – Impressum und Datenschutz: Sprachumschaltung */
(function () {
  'use strict';
  var root = document.documentElement;
  function setLang(l) {
    root.lang = l;
    if (window.TTGO_TITLES) document.title = window.TTGO_TITLES[l];
    try { localStorage.setItem('ttgo-lang', l); } catch (e) {}
  }
  document.querySelectorAll('.lang button').forEach(function (b) {
    b.addEventListener('click', function () { setLang(b.getAttribute('data-set')); });
  });
  setLang(root.lang === 'en' ? 'en' : 'de');
})();

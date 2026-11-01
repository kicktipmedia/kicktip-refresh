/* Rootables (rootables-shared build): the home row template, ONE function (row) so the row layout can be swapped in one place. Option A only (no carousel).
   Same rows, order and numbers as the team page (rootables.js compute 'blend'); why text from assets/ktwhy.js. */
(function (root) {
  var NB = '\u00A0';
  function E(t) { return String(t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function row(o) {   /* rev f: live-tight two-line row (live .pt-r rhythm). L1 pill over opponent; L2 meta + Why on the right; panel below */
    var id = 'rvw-' + o.id;
    return '<li class="rv-rw' + (o.slug ? ' tc-' + o.slug : '') + '"' + (o.extra || '') + '>' +
      '<p class="rv-ro"><span class="vh">Root for </span><span class="rv-l1"><span class="rv-root">' + (o.root.logo || '') + '<b>' + E(o.root.name) + '</b></span> over</span> <span class="rv-tn">' + (o.other.logo || '') + '<span>' + E(o.other.name) + '</span></span></p>' +
      '<p class="rv-rt"><span class="rv-mt"><b>+' + o.gain + NB + 'pts</b> <span aria-hidden="true">\u00B7</span> ' + E(o.when) + '</span>' +
      '<button type="button" class="rv-wb" aria-expanded="false" aria-controls="' + id + '"><span class="rv-wl">Why<span class="vh"> root for ' + E(o.root.name) + ' over ' + E(o.other.name) + '</span></span></button></p>' +
      '<div class="rv-wp" id="' + id + '" hidden>' + (o.tag ? '<p class="rv-race rv-' + o.race + '">' + E(o.tag) + '</p>' : '') + '<p class="rv-why">' + E(o.why) + '</p></div></li>';
  }
  function bindRows(el) { (el || document).addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('.rv-wb'); if (!b) return; var x = b.getAttribute('aria-expanded') === 'true', p = document.getElementById(b.getAttribute('aria-controls')); b.setAttribute('aria-expanded', String(!x)); if (p) p.hidden = x; }); }
  var api = { row: row, bindRows: bindRows };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.KTRvHome = api;
})(this);

/* KickTip logo helper. Generated map of which teams/conferences have a cached ESPN logo (from assets-cache at build time).
   Same tile markup as the server-rendered pages; no network requests of its own; no inline handlers (strict CSP).
   If a logo image fails to load, the tile switches to its initials/abbreviation fallback. */
(function () {
  'use strict';
  var MAP = __LOGO_MAP__, PAD = MAP.pad, D = document;
  function fbsz(t, size) { var inner = size - 2 * PAD[size] - 2; return Math.max(9, Math.min(Math.floor(size * 0.6), Math.floor(inner / (0.5 * Math.max(2, t.length))))); }
  function tile(base, fid, size, label, lazy) {
    var pad = PAD[size], im = size - 2 * pad - 2, fb = '<b class="fb f' + fbsz(label, size) + '">' + label + '</b>';
    if (!fid) return '<span class="lg s' + size + ' nf" aria-hidden="true">' + fb + '</span>';
    var src, ss = '', p = '/assets/logos/' + base;
    if (size <= 32) { src = p + '32/' + fid + '.png'; ss = ' srcset="' + p + '32/' + fid + '.png 1x, ' + p + '64/' + fid + '.png 2x"'; }
    else if (size <= 40) { src = p + '64/' + fid + '.png'; ss = ' srcset="' + p + '64/' + fid + '.png 1x, ' + p + '500/' + fid + '.png 2x"'; }
    else src = p + '500/' + fid + '.png';
    return '<span class="lg s' + size + '" aria-hidden="true"><img src="' + src + '"' + ss + ' alt="" width="' + im + '" height="' + im + '" decoding="async"' + (lazy ? ' loading="lazy"' : '') + '>' + fb + '</span>';
  }
  window.KTLogo = {
    team: function (slug, size, lazy) { var m = MAP.t[slug]; return m ? tile('', m[0], size, m[1], lazy) : ''; },
    conf: function (slug, size, lazy) { var m = MAP.c[slug]; return m ? tile('conf/', m[0], size, m[1], lazy) : ''; }
  };
  function fail(img) { var s = img.parentNode; if (s && s.classList && s.classList.contains('lg')) { s.classList.add('nf'); img.remove(); } }
  D.addEventListener('error', function (e) { var t = e.target; if (t && t.tagName === 'IMG' && t.parentNode && t.parentNode.classList && t.parentNode.classList.contains('lg')) fail(t); }, true);
  function sweep() { [].forEach.call(D.querySelectorAll('.lg img'), function (i) { if (i.complete && i.naturalWidth === 0) fail(i); }); }
  if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', sweep); else sweep();
  window.addEventListener('load', sweep);
})();

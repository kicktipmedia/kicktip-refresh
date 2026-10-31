// nojs1 stamp rules (Creative Oct 30): 3 = nbsp inside 'Oct 30' and '9:41 PM MT' (only break after the comma); 4 = data time -> America/Denver across the Nov 1 DST change; 6 = missing/unparseable -> ''.
// usage: node nojs1_stamp.js <siteDir>
const K = require(require('path').resolve(process.argv[2] || '.', 'assets/stamp.js')); let n = 0, f = 0;
const eq = (a, b, m) => { n++; if (a !== b) { f++; console.log('FAIL', m, JSON.stringify(a), '!=', JSON.stringify(b)); } };
const N = '\u00a0';
eq(K.fmt('2026-10-30 21:41'), 'Oct' + N + '30, 9:41' + N + 'PM' + N + 'MT', 'placeholder');
eq(K.fmt('2026-10-29 22:13 MT'), 'Oct' + N + '29, 10:13' + N + 'PM' + N + 'MT', 'pipeline form with MT');
// rule 3: the only ordinary space is right after the comma
for (const s of ['2026-10-30 21:41', '2026-11-01 00:05', '2026-12-31 12:00']) { const o = K.fmt(s); eq((o.match(/ /g) || []).length, 1, 'one breakable space ' + s); eq(o.indexOf(', '), o.indexOf(' ') - 1, 'break only after comma ' + s); eq(/MDT|MST/.test(o), false, 'MT only ' + s); }
eq(K.fmt('2026-11-01 00:05'), 'Nov' + N + '1, 12:05' + N + 'AM' + N + 'MT', 'midnight hour 12, no leading zero');
eq(K.fmt('2026-10-30 09:05'), 'Oct' + N + '30, 9:05' + N + 'AM' + N + 'MT', 'no leading zero hour');
// rule 4: instants either side of the Nov 1 2026 DST change (08:00Z = 2:00 AM MDT -> 1:00 AM MST)
eq(K.fmt('2026-11-01T07:59Z'), 'Nov' + N + '1, 1:59' + N + 'AM' + N + 'MT', 'just before fall-back (MDT, UTC-6)');
eq(K.fmt('2026-11-01T08:01Z'), 'Nov' + N + '1, 1:01' + N + 'AM' + N + 'MT', 'just after fall-back (MST, UTC-7)');
eq(K.fmt('2026-10-31T21:41Z'), 'Oct' + N + '31, 3:41' + N + 'PM' + N + 'MT', 'Sat (MDT)');
eq(K.fmt('2026-11-02T04:41Z'), 'Nov' + N + '1, 9:41' + N + 'PM' + N + 'MT', 'Sun evening (MST)');
eq(K.fmt('2026-10-29T09:10:00-04:00'), 'Oct' + N + '29, 7:10' + N + 'AM' + N + 'MT', 'offset input (brag.json)');
eq(K.fmt('2026-11-01T01:30-07:00'), 'Nov' + N + '1, 1:30' + N + 'AM' + N + 'MT', 'explicit MST offset');
// rule 6
for (const s of [undefined, null, '', 'recently', '2026-10-30', '2026-13-01 10:00', '2026-10-30 25:00', 'Oct 30, 9:41 PM', 12345]) eq(K.fmt(s), '', 'hide on ' + JSON.stringify(s));
console.log(n + ' checks, ' + f + ' failed'); process.exit(f ? 1 : 0);

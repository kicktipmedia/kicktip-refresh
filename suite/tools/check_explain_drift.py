#!/usr/bin/env python3
"""Drift check for explain_site. Every snippet in assets/tb/explain_site.js (between /*SNIPS-BEGIN*/ and /*SNIPS-END*/) must be an exact substring of the plain text of its page:
page "method" = method/index.html, page "field" = index.html (the 12-team playoff field card and its "How the field is chosen" section).
Run on a site tree:  python3 tools/check_explain_drift.py <site-tree>      exit 0 = no drift, exit 1 = lists the snippets that no longer match.
Run this again whenever /method/ or the home page is regenerated (the accuracy numbers change when the replay is re-run)."""
import html, json, os, re, sys
def page_text(path):
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'<(script|style)\b.*?</\1>', '', s, flags=re.S)
    s = re.sub(r'</?(b|i|em|strong|a|span|small|code|u)\b[^>]*>', '', s)   # inline tags vanish
    s = re.sub(r'<[^>]+>', '\n', s)                                         # block tags separate text
    s = html.unescape(s)
    return '\n'.join(re.sub(r'\s+', ' ', l).strip() for l in s.split('\n'))
def load_snips(tree):
    js = open(os.path.join(tree, 'assets/tb/explain_site.js'), encoding='utf-8').read()
    m = re.search(r'/\*SNIPS-BEGIN\*/\s*var SNIP = (\{.*?\});\s*/\*SNIPS-END\*/', js, re.S); assert m, 'snippet block not found'
    return json.loads(m.group(1))
def check(tree):
    sn = load_snips(tree); pages = {'method': page_text(os.path.join(tree, 'method/index.html')), 'field': page_text(os.path.join(tree, 'index.html'))}
    bad = [k for k, v in sorted(sn.items()) if v['text'] not in pages[v['page']]]
    return sn, bad
if __name__ == '__main__':
    sn, bad = check(sys.argv[1])
    if bad: print('DRIFT: %d of %d snippets no longer match their page: %s' % (len(bad), len(sn), ', '.join(bad))); sys.exit(1)
    print('explain_site snippets: %d of %d match their page exactly' % (len(sn), len(sn)))

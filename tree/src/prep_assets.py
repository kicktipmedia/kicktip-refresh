"""One-off asset prep (re-run only to regenerate): vendors fonts (TTF sources + subset woff2), outlines the Tag Badge logo text to paths,
copies the hero image. Output goes to src/assets/ (committed); build.py copies src/assets/ into the site. Free tools only (fontTools, brotli, uharfbuzz, Pillow).
Logo swap (b3): src/assets/logo/ now holds the shippable Creative v3 final r2 brand files (kicktip-*.svg, favicon, png/); this script no longer runs and must not overwrite them."""
import os, re, shutil, subprocess, sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools import subset
import uharfbuzz as hb
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); A = f"{ROOT}/src/assets"
CV = "/workspace/hub/creative-v3"; GF = "/usr/share/fonts/truetype/sand-box/google/Barlow Condensed"
FONTS = {  # name -> source ttf
 "BarlowCondensed-Bold": f"{GF}/BarlowCondensed-Bold.ttf",
 "BarlowCondensed-BoldItalic": f"{GF}/BarlowCondensed-BoldItalic.ttf",
 "SourceSans3-400": f"{CV}/fonts/ttf/SourceSans3-static-400.ttf",
 "SourceSans3-600": f"{CV}/fonts/ttf/SourceSans3-static-600.ttf",
 "SourceSans3-700": f"{CV}/fonts/ttf/SourceSans3-static-700.ttf"}
UNI = "U+0020-007E,U+00A0-00FF,U+0131,U+0152-0153,U+2013-2014,U+2018-201D,U+2022,U+2026,U+2190-2193,U+2212,U+00B7"
def fonts():
    for n, p in FONTS.items():
        shutil.copy(p, f"{A}/fonts-src/{n}.ttf")
        opt = subset.Options(); opt.flavor = "woff2"; opt.layout_features = ["*"]; opt.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]; opt.notdef_outline = True
        f = subset.load_font(p, opt); s = subset.Subsetter(opt); s.populate(unicodes=subset.parse_unicodes(UNI)); s.subset(f)
        subset.save_font(f, f"{A}/fonts/{n}.woff2", opt)
        print(n, os.path.getsize(f"{A}/fonts/{n}.woff2"), "bytes")

def text_path(ttf, text, size, x, y, track=0.0):
    blob = hb.Blob.from_file_path(ttf); face = hb.Face(blob); font = hb.Font(face)
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties(); hb.shape(font, buf, {"kern": True, "liga": True})
    tt = TTFont(ttf); gs = tt.getGlyphSet(); order = tt.getGlyphOrder(); upm = tt["head"].unitsPerEm; k = size / upm
    pen = SVGPathPen(gs, ntos=lambda v: ("%.2f" % v).rstrip("0").rstrip(".")); cx = x
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        g = order[info.codepoint]
        tp = TransformPen(pen, (k, 0, 0, -k, cx + pos.x_offset * k, y - pos.y_offset * k)); gs[g].draw(tp)
        cx += pos.x_advance * k + track
    return pen.getCommands()

def logos():
    S = f"{CV}/logo-options/svg"; D = f"{A}/logo"
    BI = FONTS["BarlowCondensed-BoldItalic"]; SS = FONTS["SourceSans3-700"]
    for var in ("dark", "light", "mono"):
        s = open(f"{S}/badge-lockup-{var}.svg").read()
        def rep(m):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1))); txt = m.group(2)
            ttf = BI if "Barlow" in attrs["font-family"] else SS
            d = text_path(ttf, txt, float(attrs["font-size"]), float(attrs["x"]), float(attrs["y"]), float(attrs.get("letter-spacing", 0)))
            return f'<path d="{d}" fill="{attrs["fill"]}"/>'
        s = re.sub(r"<text ([^>]*)>([^<]*)</text>", rep, s)
        assert "<text" not in s
        s = re.sub(r'<rect width="270" height="72" fill="[^"]*"/>', "", s, count=1)  # transparent lockup (placed on any surface)
        s = s.replace("<svg ", '<svg role="img" aria-label="KickTip Media" ', 1)
        open(f"{D}/lockup-{var}.svg", "w").write(s)
        i = open(f"{S}/badge-icon-{var}.svg").read(); open(f"{D}/icon-{var}.svg", "w").write(i)
        i = open(f"{S}/badge-icon-small-{var}.svg").read(); open(f"{D}/icon-small-{var}.svg", "w").write(i)
    print(sorted(os.listdir(D)))

def hero():
    from PIL import Image
    im = Image.open(f"{CV}/ai/ai-4-mood-graphite-boost.jpg").convert("RGB"); print("hero", im.size)
    im.save(f"{A}/img/hero.jpg", quality=72, optimize=True, progressive=True); print(os.path.getsize(f"{A}/img/hero.jpg"), "bytes")
if __name__ == "__main__": fonts(); logos(); hero()

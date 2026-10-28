"""Generate superseded M-concept v01 assets, NOT the current storefront brand.

Current user-supplied artwork lives in assets/original; see docs/BRAND.md.

Wordmark outlines are produced from local Arial through fontTools.
The generated deliverables have no runtime font dependency.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
import cairosvg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)
FONT = Path("C:/Windows/Fonts/arial.ttf")


def text_path(text, size, x, baseline):
    font = TTFont(FONT)
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font["head"].unitsPerEm
    parts = []
    cursor = 0
    for c in text:
        name = cmap[ord(c)]
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        if pen.getCommands():
            parts.append(f'<path transform="translate({x + cursor * scale:.3f} {baseline}) scale({scale:.8f} {-scale:.8f})" d="{pen.getCommands()}"/>')
        cursor += font["hmtx"].metrics[name][0]
    return "".join(parts)


SYMBOL = "M12 84V16H28L50 47L72 16H88V84H72V44L50 75L28 44V84Z"


def svg(width, height, content):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="MisePort"><title>MisePort</title><desc>A single open M symbol beside the MisePort wordmark.</desc>{content}</svg>'


for variant, ink in [("light", "#133A35"), ("dark", "#EAF7F2")]:
    lockup = f'<g fill="{ink}"><path d="{SYMBOL}"/>{text_path("MisePort", 54, 116, 68)}</g>'
    (OUT / f"logo-{variant}.svg").write_text(svg(360, 100, lockup), encoding="utf-8")
    points = [(12,84),(12,16),(28,16),(50,47),(72,16),(88,16),(88,84),(72,84),(72,44),(50,75),(28,44),(28,84)]
    cairosvg.svg2png(url=str(OUT / f"logo-{variant}.svg"), write_to=str(OUT / f"logo-{variant}.png"), scale=4)
    image = Image.open(OUT / f"logo-{variant}.png")
    image.resize((360,100), Image.Resampling.LANCZOS).save(OUT / f"logo-{variant}-small.png")

(OUT / "favicon.svg").write_text(svg(100,100,f'<rect width="100" height="100" rx="20" fill="#133A35"/><path fill="#EAF7F2" d="{SYMBOL}"/>'),encoding="utf-8")
favicon = Image.new("RGB", (400,400), "#133A35")
ImageDraw.Draw(favicon).polygon([(x*4,y*4) for x,y in points],fill="#EAF7F2")
favicon.resize((32,32),Image.Resampling.LANCZOS).save(OUT / "favicon.png")
favicon.save(OUT / "favicon.ico", sizes=[(16,16),(32,32),(48,48)])
cover = Image.new("RGB", (1200,630),"#EAF7F2")
cover.paste(Image.open(OUT / "logo-light.png").resize((864,240)),(130,150),Image.open(OUT / "logo-light.png").resize((864,240)))
d = ImageDraw.Draw(cover)
d.text((150,430),"A clear port for your product catalog.",font=ImageFont.truetype(str(FONT),36),fill="#133A35")
d.text((150,495),"READ-ONLY / JAPAN / OPEN SOURCE",font=ImageFont.truetype(str(FONT),20),fill="#526D65")
cover.save(OUT / "social-cover.png")
(OUT / "geometry-v01.json").write_text(json.dumps({"candidate":"v01","approved":False,"viewBox":[0,0,100,100],"symbol_path":SYMBOL,"vertical_stem":16,"topology":"single closed M contour; open counters; no facets","wordmark":"Arial regular converted to SVG paths; PNG uses same local font","clear_space":12,"min_symbol_px":24},indent=2),encoding="utf-8")

# QA contact sheet: normal size, 4x source render, reverse and favicon.
sheet = Image.new("RGB", (1500,850), "#F5F5EE")
sheet.paste(Image.open(OUT / "logo-light-small.png"),(30,20),Image.open(OUT / "logo-light-small.png"))
dark_panel = Image.new("RGB",(740,150),"#172D32")
reverse = Image.open(OUT / "logo-dark.png").resize((540,150))
dark_panel.paste(reverse,(15,0),reverse)
sheet.paste(dark_panel,(740,0))
large = Image.open(OUT / "logo-light.png")
sheet.paste(large,(30,220),large)
sheet.paste(Image.open(OUT / "favicon.png"),(35,720))
sheet.save(OUT / "brand-v01-review.png")

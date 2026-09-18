"""Generate the GitHub profile's SVG masthead + venture cards (light & dark).

All text is converted to outlines (Fraunces / JetBrains Mono) so it renders the
same everywhere — GitHub serves README SVGs through <img>, which can't load fonts.
"""
import os
import uharfbuzz as hb

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.environ.get("FONTS_DIR", os.path.join(HERE, "fonts"))
OUT = os.path.join(HERE, "..", "assets")
os.makedirs(OUT, exist_ok=True)

THEMES = {
    "light": dict(bg="#F7F3EC", ink="#201B18", accent="#D93F1C", muted="#6F665F",
                  rule="#D9D2C8", card="#FBF8F3"),
    "dark": dict(bg="#0F0D0C", ink="#F1EBE1", accent="#F0603B", muted="#A0968C",
                 rule="#34302C", card="#171412"),
}

_fonts = {}


def font(file, **axes):
    key = (file, tuple(sorted(axes.items())))
    if key not in _fonts:
        blob = hb.Blob.from_file_path(os.path.join(FONTS, file))
        face = hb.Face(blob)
        f = hb.Font(face)
        if axes:
            f.set_variations(axes)
        _fonts[key] = (f, face.upem)
    return _fonts[key]


SERIF = lambda w=600, opsz=144, soft=0, wonk=0: font("Fraunces.ttf", wght=w, opsz=opsz, SOFT=soft, WONK=wonk)
ITALIC = lambda w=400, opsz=144: font("Fraunces-Italic.ttf", wght=w, opsz=opsz, SOFT=50, WONK=1)
MONO = lambda w=500: font("JBMono.ttf", wght=w)


class PathPen:
    """Records a glyph outline in raw font units (y-up)."""
    def __init__(self):
        self.d = []

    def _p(self, x, y):
        return f"{round(x)} {round(-y)}"

    def moveTo(self, p): self.d.append("M" + self._p(*p))
    def lineTo(self, p): self.d.append("L" + self._p(*p))
    def curveTo(self, a, b, c): self.d.append("C" + " ".join(self._p(*q) for q in (a, b, c)))
    def qCurveTo(self, *pts): self.d.append("Q" + " ".join(self._p(*q) for q in pts))
    def closePath(self): self.d.append("Z")


_defs = {}  # (font id, gid) -> (symbol id, path d); reset per SVG


def glyph_ref(fnt, gid):
    key = (id(fnt[0]), gid)
    if key not in _defs:
        pen = PathPen()
        fnt[0].draw_glyph_with_pen(gid, pen)
        _defs[key] = (f"g{len(_defs)}", "".join(pen.d))
    return _defs[key][0]


def shape(fnt, text):
    f, upem = fnt
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(f, buf, {"kern": True, "liga": True})
    return f, upem, buf.glyph_infos, buf.glyph_positions


def width(fnt, text, size, track=0.0):
    f, upem, infos, pos = shape(fnt, text)
    return sum(p.x_advance for p in pos) * size / upem + track * size * len(text)


def text(fnt, s, x, y, size, fill, track=0.0, anchor="start", extra=""):
    """Outline `s` at baseline y. track = letter-spacing in em."""
    f, upem, infos, pos = shape(fnt, s)
    sc = size / upem
    if anchor == "end":
        x -= width(fnt, s, size, track)
    elif anchor == "middle":
        x -= width(fnt, s, size, track) / 2
    pen_x, uses = x, []
    for info, p in zip(infos, pos):
        gx, gy = pen_x + p.x_offset * sc, y - p.y_offset * sc
        if p.x_advance == 0 and not info.codepoint:
            pass
        uses.append(f'<use href="#{glyph_ref(fnt, info.codepoint)}" x="{gx / sc:.0f}" y="{gy / sc:.0f}"/>')
        pen_x += p.x_advance * sc + track * size
    return f'<g fill="{fill}" transform="scale({sc:.5f})" {extra}>{"".join(uses)}</g>', pen_x


def svg(w, h, body, title, css=""):
    defs = "".join(f'<path id="{i}" d="{d}"/>' for i, d in _defs.values())
    _defs.clear()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{title}"><title>{title}</title>'
            f'<style>{css}</style><defs>{defs}</defs>{body}</svg>')


PULSE_CSS = """
.pulse{transform-origin:center;transform-box:fill-box;animation:p 2.4s ease-out infinite}
@keyframes p{0%{opacity:.55;transform:scale(1)}80%,100%{opacity:0;transform:scale(3.2)}}
@media (prefers-reduced-motion:reduce){.pulse{animation:none;opacity:0}}
"""


def masthead(t):
    W, H = 1200, 420
    b = [f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>']
    # faint baseline grid
    for gx in range(80, W, 80):
        b.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{H}" stroke="{t["rule"]}" stroke-opacity=".35" stroke-width="1"/>')
    L = 72
    # top masthead rule
    b.append(f'<g class="rise">')
    p, _ = text(MONO(500), "JAY GAUTAM — AI / ML NOTEBOOK", L, 64, 13, t["muted"], track=0.18)
    b.append(p)
    p, _ = text(MONO(500), "UPDATED SEPT 2026", W - L, 64, 13, t["muted"], track=0.18, anchor="end")
    b.append(p)
    b.append(f'<line x1="{L}" y1="84" x2="{W - L}" y2="84" stroke="{t["ink"]}" stroke-width="1.5"/>')
    b.append(f'<line x1="{L}" y1="89" x2="{W - L}" y2="89" stroke="{t["ink"]}" stroke-width=".6"/>')
    b.append('</g>')

    # name
    b.append('<g class="rise d1">')
    p, end = text(SERIF(560, 144, 0, 0), "Jay Gautam", L - 4, 214, 118, t["ink"], track=-0.025)
    b.append(p)
    b.append(f'<circle cx="{end + 14}" cy="202" r="11" fill="{t["accent"]}"/>')
    b.append('</g>')

    # statement: roman + italic accent
    b.append('<g class="rise d2">')
    y = 282
    p, x = text(SERIF(380, 36), "I build AI agents that act on ", L, y, 36, t["ink"], track=-0.01)
    b.append(p)
    p, x = text(ITALIC(420, 36), "evidence", x, y, 36, t["accent"], track=-0.005)
    b.append(p)
    p, x = text(SERIF(380, 36), " —", x, y, 36, t["ink"])
    b.append(p)
    p, x = text(SERIF(380, 36), "and the harnesses that prove where they fail.", L, y + 46, 36, t["ink"], track=-0.01)
    b.append(p)
    b.append('</g>')

    # footer strip
    b.append('<g class="rise d3">')
    b.append(f'<line x1="{L}" y1="366" x2="{W - L}" y2="366" stroke="{t["rule"]}" stroke-width="1"/>')
    p, x = text(MONO(500), "B.TECH CS (AI & ML)  ·  LLM AGENTS · EVALUATION · COMPUTER VISION", L, 396, 13, t["muted"], track=0.16)
    b.append(p)
    label = "COMPETING ON KAGGLE"
    lw = width(MONO(600), label, 13, 0.16)
    lx = W - L - lw
    p, _ = text(MONO(600), label, lx, 396, 13, t["accent"], track=0.16)
    b.append(p)
    cx, cy = lx - 18, 391.5
    b.append(f'<circle class="pulse" cx="{cx}" cy="{cy}" r="4.5" fill="{t["accent"]}"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="{t["accent"]}"/>')
    b.append('</g>')
    return svg(W, H, "".join(b), "Jay Gautam — I build AI agents that act on evidence, and the harnesses that prove where they fail.", PULSE_CSS)


def card(t, idx, name, kind, lines, tags, status, live):
    W, H = 600, 300
    b = [f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="14" fill="{t["card"]}" stroke="{t["rule"]}" stroke-width="1.5"/>']
    P = 36
    p, _ = text(MONO(500), f"{idx:02d}", P, 52, 13, t["accent"], track=0.12)
    b.append(p)
    p, _ = text(MONO(500), kind.upper(), P + 34, 52, 13, t["muted"], track=0.16)
    b.append(p)
    # status pill, top-right
    sw = width(MONO(600), status.upper(), 11, 0.14)
    px = W - P - sw - 36
    b.append(f'<rect x="{px}" y="33" width="{sw + 36}" height="26" rx="13" fill="none" stroke="{t["accent" if live else "rule"]}" stroke-width="1.2"/>')
    if live:
        b.append(f'<circle class="pulse" cx="{px + 14}" cy="46" r="3.5" fill="{t["accent"]}"/>')
    b.append(f'<circle cx="{px + 14}" cy="46" r="3.5" fill="{t["accent"] if live else t["muted"]}"/>')
    p, _ = text(MONO(600), status.upper(), px + 26, 50, 11, t["accent"] if live else t["muted"], track=0.14)
    b.append(p)

    p, x = text(SERIF(560, 96), name, P - 2, 128, 54, t["ink"], track=-0.02)
    b.append(p)
    b.append(f'<circle cx="{x + 7}" cy="122" r="5.5" fill="{t["accent"]}"/>')
    y = 174
    for ln in lines:
        p, _ = text(SERIF(380, 20), ln, P, y, 20, t["muted"])
        b.append(p)
        y += 29
    b.append(f'<line x1="{P}" y1="244" x2="{W - P}" y2="244" stroke="{t["rule"]}" stroke-width="1"/>')
    x = P
    for tag in tags:
        p, x = text(MONO(500), tag, x, 272, 12.5, t["ink"], track=0.04)
        b.append(p)
        x += 12
        b.append(f'<circle cx="{x}" cy="268" r="2" fill="{t["accent"]}"/>')
        x += 12
    b.pop()  # drop trailing separator
    return svg(W, H, "".join(b), f"{name} — {kind}", PULSE_CSS)


CARDS = [
    ("aletheia", "Aletheia", "LLM verification", ["Multi-agent RAG pipeline that checks whether",
     "an LLM's claim is supported by its sources —",
     "and cites the exact span, vs. a single-LLM baseline."],
     ["LangGraph", "pgvector", "RAG", "FastAPI"], "Live demo", True),
    ("rampbrain", "RampBrain", "Agentic AI", ["Compiles how a team works into governed skills",
     "an AI agent runs — every step sourced, every", "action gated on human approval."],
     ["Agents", "MCP", "RAG", "Gemini"], "Live · pilots", True),
    ("dobara", "Dobara", "Applied ML", ["Calibrated LightGBM models price every retry",
     "of a failed recurring payment against the risk",
     "of losing the mandate, evaluated with CIs."],
     ["LightGBM", "Calibration", "Simulation"], "Razorpay AI", False),
    ("river", "River", "LLM memory", ["Keeps the thread across conversations without",
     "taking control of it — consent-based memory",
     "with a precision / recall evaluation harness."],
     ["LLMs", "Memory", "Eval harness"], "Public beta", True),
]

for name, t in THEMES.items():
    open(os.path.join(OUT, f"masthead-{name}.svg"), "w").write(masthead(t))
    for i, (slug, *rest) in enumerate(CARDS, 1):
        open(os.path.join(OUT, f"card-{slug}-{name}.svg"), "w").write(card(t, i, *rest))
print(sorted(os.listdir(OUT)))

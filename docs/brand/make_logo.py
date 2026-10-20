"""Generates the Dealshape logo SVGs (frontend/public/brand/mark.svg, mark-small.svg, wordmark.svg) from geometry, not from the
concept raster (docs/brand/logo_concept.png).

The mark is a "D" cut into three pieces by gaps of one constant width: the contract terms (the full-height stem on the left), and
the curved part split into the sales promises (top) and the product capabilities (bottom). The outline is a flat-sided D whose right edge is one circular arc, with no notch. Every
piece is built from straight edges and that one arc, then its corners are rounded with exact fillets (an inset of the piece by the
corner radius, with a radius-r arc at each inset vertex), so the gaps stay even right up to the corners.

mark-small.svg uses a wider gap, a larger margin and a heavier fillet so it stays readable at 16px.
The wordmark sets "Dealshape" as outlines taken from Inter SemiBold (the app's font, @fontsource/inter 600), so it looks the same
wherever the SVG is used, including through <img>, where web fonts do not load.

Run:  python make_logo.py <path to inter-latin-600-normal.woff> <output folder>   (needs fontTools)
"""

import math
import sys
from pathlib import Path

INDIGO = "#4f46e5"
INK = "#0f172a"
INK_ON_DARK = "#f1f5f9"  # the deal page's --ink in a dark colour scheme
SLOPE, SPLIT = 1 / 14, 0.47  # the second gap tilts a touch downward to the right, as in the concept


def f(x):
    s = f"{x:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# --- tiny geometry on edges: a line is n.x = c with outward unit normal n; an arc is a circle (centre, R), outward = radial --------
def line(n, c, d):
    return {"k": "line", "n": n, "c": c, "d": d}


def arc(cx, cy, R):
    return {"k": "arc", "cx": cx, "cy": cy, "R": R}


def inset(e, r):
    if e["k"] == "line":
        return {**e, "c": e["c"] - r}
    return {**e, "R": e["R"] - r}


def intersect(a, b, near):
    """Intersection of two (inset) edges, the one closest to `near`."""
    pts = []
    if a["k"] == "line" and b["k"] == "line":
        (a1, a2), (b1, b2) = a["n"], b["n"]
        det = a1 * b2 - a2 * b1
        pts = [((a["c"] * b2 - a2 * b["c"]) / det, (a1 * b["c"] - a["c"] * b1) / det)]
    else:
        ln, ac = (a, b) if a["k"] == "line" else (b, a)
        n1, n2 = ln["n"]
        px, py = n1 * ln["c"], n2 * ln["c"]  # a point on the line
        dx, dy = -n2, n1  # its direction
        fx, fy = px - ac["cx"], py - ac["cy"]
        A, B, C = 1.0, 2 * (fx * dx + fy * dy), fx * fx + fy * fy - ac["R"] ** 2
        disc = math.sqrt(max(B * B - 4 * A * C, 0))
        pts = [(px + t * dx, py + t * dy) for t in ((-B + disc) / 2, (-B - disc) / 2)]
    return min(pts, key=lambda p: (p[0] - near[0]) ** 2 + (p[1] - near[1]) ** 2)


def normal_at(e, p):
    if e["k"] == "line":
        return e["n"]
    d = math.hypot(p[0] - e["cx"], p[1] - e["cy"])
    return ((p[0] - e["cx"]) / d, (p[1] - e["cy"]) / d)


def rounded(edges, nominal, r):
    """SVG path for the region bounded by `edges` (clockwise on screen) with every corner rounded to radius r.
    nominal[k] is the sharp vertex between edges[k] and edges[k+1]."""
    ins = [inset(e, r) for e in edges]
    n = len(edges)
    verts = [intersect(ins[k], ins[(k + 1) % n], nominal[k]) for k in range(n)]
    out = []
    for k, e in enumerate(edges):
        v0, v1 = verts[k - 1], verts[k]
        n0, n1 = normal_at(e, v0), normal_at(e, v1)
        s = (v0[0] + r * n0[0], v0[1] + r * n0[1])
        t = (v1[0] + r * n1[0], v1[1] + r * n1[1])
        if k == 0:
            out.append(f"M{f(s[0])} {f(s[1])}")
        if e["k"] == "line":
            out.append(f"L{f(t[0])} {f(t[1])}")
        else:
            out.append(f"A{f(e['R'])} {f(e['R'])} 0 0 1 {f(t[0])} {f(t[1])}")
        nx = edges[(k + 1) % n]
        n2 = normal_at(nx, v1)
        s2 = (v1[0] + r * n2[0], v1[1] + r * n2[1])
        if math.hypot(s2[0] - t[0], s2[1] - t[1]) > 1e-6:  # tangent joins (the top edge into the bowl) need no corner
            out.append(f"A{f(r)} {f(r)} 0 0 1 {f(s2[0])} {f(s2[1])}")
    return "".join(out) + "Z"


def mark_paths(margin=4.0, gap=4.0, radius=2.2, slope=SLOPE, split=SPLIT, block=0.34):
    """The three pieces of the D in a 64 x 64 box. The left piece is the D's full-height stem (flat left edge, top to bottom). A
    vertical gap of width `gap` separates it from the curved right part, which one more gap of the same width splits into a top
    piece and a bottom piece. `block`: how far across the D's width the stem's gap sits, as a fraction of its height. `split`:
    where the second gap's centre line crosses the vertical gap, as a fraction of the height. `slope`: its tilt (0 = level)."""
    top, bottom, left = margin, 64 - margin, margin
    R = (bottom - top) / 2
    cx, cy = left + R, 32.0  # the flat part is as long as the bowl's radius
    s = math.sqrt(1 + slope * slope)
    xg = left + block * 2 * R  # the vertical gap's centre line
    xl, xb = xg - gap / 2, xg + gap / 2  # the stem's right edge, the curved part's left edge
    y0 = top + split * (bottom - top)  # the second gap's centre line where it leaves the vertical gap
    h = gap / 2 * s  # vertical half-width of the second gap
    a_hi, a_lo = y0 - slope * xg + h, y0 - slope * xg - h  # y = a + slope*x for the lower and the upper edge of the gap
    n_up, n_dn = (slope / s, -1 / s), (-slope / s, 1 / s)  # outward normals: out of the piece below / out of the piece above

    def on_circle(a):  # right-hand intersection of y = a + slope*x with the bowl: (x-cx)^2 + (a+slope*x-cy)^2 = R^2
        A2 = 1 + slope * slope
        B2 = 2 * (-cx + slope * (a - cy))
        C2 = cx * cx + (a - cy) ** 2 - R * R
        x = (-B2 + math.sqrt(B2 * B2 - 4 * A2 * C2)) / (2 * A2)
        return x, a + slope * x

    Lt = lambda x: a_lo + slope * x  # lower edge of the top piece
    Ub = lambda x: a_hi + slope * x  # upper edge of the bottom piece

    # the stem: four straight edges, left to right across the top, down, back along the bottom, up the flat left edge
    p_stem = rounded(
        [line((0, -1), -top, (1, 0)), line((1, 0), xl, (0, 1)), line((0, 1), bottom, (-1, 0)), line((-1, 0), -left, (0, -1))],
        [(xl, top), (xl, bottom), (left, bottom), (left, top)], radius)
    # the top piece: top edge, the bowl's arc clockwise, back along the gap, up its own left edge
    p_top = rounded(
        [line((0, -1), -top, (1, 0)), arc(cx, cy, R), line(n_dn, n_dn[1] * a_lo, (-1, -slope)), line((-1, 0), -xb, (0, -1))],
        [(cx, top), on_circle(a_lo), (xb, Lt(xb)), (xb, top)], radius)
    # the bottom piece: along the gap, the bowl's arc clockwise, back along the bottom, up its own left edge
    p_bot = rounded(
        [line(n_up, n_up[1] * a_hi, (1, slope)), arc(cx, cy, R), line((0, 1), bottom, (-1, 0)), line((-1, 0), -xb, (0, -1))],
        [on_circle(a_hi), (cx, bottom), (xb, bottom), (xb, Ub(xb))], radius)
    return [p_top, p_stem, p_bot]


def mark_svg(small=False, size=64):
    kw = dict(margin=2.0, gap=8.0, radius=2.6, block=0.36) if small else dict()
    paths = mark_paths(**kw)
    body = "".join(f'<path d="{d}"/>' for d in paths)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}" role="img" '
            f'aria-label="Dealshape"><g fill="{INDIGO}">{body}</g></svg>\n')


def wordmark_svg(font_path, mark_height=64.0):
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    font = TTFont(font_path)
    upm = font["head"].unitsPerEm
    cmap, gs, hmtx = font.getBestCmap(), font.getGlyphSet(), font["hmtx"]
    cap = font["OS/2"].sCapHeight
    size = 0.60 * 56 / (cap / upm)  # cap height is 60% of the mark's 56-unit D, as in the concept
    scale = size / upm
    track = -0.012 * size  # a hair of tightening, as Inter's semibold wants at display sizes
    gap = 15.0
    x = 64 + gap
    base = 32 + cap * scale / 2  # cap height centred on the mark
    glyphs = []
    for ch in "Dealshape":
        name = cmap[ord(ch)]
        pen = SVGPathPen(gs, ntos=f)
        gs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, base)))
        glyphs.append(pen.getCommands())
        x += hmtx[name][0] * scale + track
    width = x - track
    marks = "".join(f'<path d="{d}"/>' for d in mark_paths())
    text = "".join(f'<path d="{d}"/>' for d in glyphs)
    # In a dark colour scheme the ink would vanish on the app's dark canvas, so the text (not the mark) takes the app's dark ink.
    style = f"<style>@media (prefers-color-scheme: dark){{.ink{{fill:{INK_ON_DARK}}}}}</style>"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(width)} 64" width="{f(width)}" height="64" role="img" '
            f'aria-label="Dealshape">{style}<g fill="{INDIGO}">{marks}</g><g class="ink" fill="{INK}">{text}</g></svg>\n')


if __name__ == "__main__":
    font, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    (out / "mark.svg").write_text(mark_svg(), encoding="utf-8")
    (out / "mark-small.svg").write_text(mark_svg(small=True), encoding="utf-8")
    (out / "wordmark.svg").write_text(wordmark_svg(font), encoding="utf-8")
    print("wrote", ", ".join(p.name for p in sorted(out.glob("*.svg"))))

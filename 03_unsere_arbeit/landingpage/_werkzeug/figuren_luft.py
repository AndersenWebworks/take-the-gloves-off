"""Luftartistik-Silhouetten für die Verwandlung der Bildmarke (Probefassung).
Grundlage: sieben Referenzfotos von Lilith (02_rohmaterial_medien/luftartistik_referenzen_lilith).
Person samt eigenem Gurt wird freigestellt (BiRefNet, rembg), von Kabeln, Masten und losen Gurtstummeln
befreit, geglättet und mit potrace nachgezeichnet. Die Figuren HÄNGEN: der Gurt endet oben bei y = 8
(Oberkante des Stabs), die Person baumelt darunter.
Aufruf: python figuren_luft.py   (schreibt assets/js/figuren.js, assets/js/morph.js, tmp/luft/figuren.json und Vorschaubilder)
Die Rohmasken (refN_rembg.png) liegen in styleguide/_werkzeug/tmp/luft und werden bei Bedarf erzeugt.
"""
import json, os, re, math
import numpy as np, cv2
from PIL import Image, ImageOps
import potrace

HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.dirname(HERE)
ROOT = os.path.dirname(LP)
TMP = os.path.join(ROOT, "styleguide", "_werkzeug", "tmp", "luft"); os.makedirs(TMP, exist_ok=True)
REF = "C:/Andersen/Webworks/GitHub/Webworks/take-the-gloves-off/02_rohmaterial_medien/luftartistik_referenzen_lilith/"
X0, X1, Y0, Y1 = 21.5, 78.5, 8.0, 92.0
MAXW = X1 - X0 - 1.0
AXIS = 50.0
WORK_H = 2400
TRACE_H = 800

# r: Öffnungsradius (px im Foto), der dünne Kabel entfernt; region: Auswahlrahmen; weg: Rechtecke, die gelöscht werden
# (lose Gurtstummel); ycut: Gurt oben auf diese Höhe kürzen; hoehe: Anteil der Zeichenhöhe; open/soft: Glättung
FIGUREN = [
    dict(ref="ref3.jpg", r=6, ycut=0,   hoehe=1.00, open=0.0015, soft=0.006),   # kopfüber, Füße im Gurt
    dict(ref="ref2.jpg", r=6, ycut=330, hoehe=1.00, open=0.0015, soft=0.006, weg=[(0, 0, 440, 720)]),  # waagerecht rückwärts
    dict(ref="ref5.jpg", r=2, ycut=0,   hoehe=1.00, open=0.0006, soft=0.006, region=(150, 0, 760, 1100)),  # Spagat
    dict(ref="ref4.jpg", r=6, ycut=0,   hoehe=1.00, open=0.0015, soft=0.006),   # kopfüber, ein Arm nach unten
    dict(ref="ref1.jpg", r=6, ycut=0, rot=20,   hoehe=1.00, open=0.0015, soft=0.006, weg=[(0, 0, 880, 310)]),
]


def disk(r):
    r = max(1, int(round(r)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def rohmaske(ref):
    out = os.path.join(TMP, os.path.splitext(ref)[0] + "_rembg.png")
    if not os.path.exists(out):
        from rembg import remove, new_session
        im = ImageOps.exif_transpose(Image.open(REF + ref)).convert("RGB")
        remove(im, session=new_session("birefnet-general"), only_mask=True).save(out)
    return (np.array(Image.open(out).convert("L")) > 128).astype(np.uint8)


def biggest(m):
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    return (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)


def prepare(p):
    m = rohmaske(p["ref"])
    if p.get("region"):
        x0, y0, x1, y1 = p["region"]; z = np.zeros_like(m); z[y0:y1, x0:x1] = 1; m = m * z
    for x0, y0, x1, y1 in p.get("weg", []): m[y0:y1, x0:x1] = 0
    core = biggest(cv2.morphologyEx(m, cv2.MORPH_OPEN, disk(p["r"])))
    m = biggest(cv2.dilate(core, disk(p["r"] * 1.5)) & m)    # Haare und Finger bleiben, lose Kabel nicht
    if p["ycut"]: m[:p["ycut"]] = 0
    if p.get("rot"):                                          # Gurt senkrecht stellen (Drehung um die Mitte, Leinwand wächst mit)
        h0, w0 = m.shape; c = (w0 / 2, h0 / 2)
        M = cv2.getRotationMatrix2D(c, p["rot"], 1.0)
        cos, sin = abs(M[0, 0]), abs(M[0, 1]); nw, nh = int(h0 * sin + w0 * cos), int(h0 * cos + w0 * sin)
        M[0, 2] += nw / 2 - c[0]; M[1, 2] += nh / 2 - c[1]
        m = (cv2.warpAffine(m * 255, M, (nw, nh), flags=cv2.INTER_LINEAR) > 127).astype(np.uint8)
    ys, xs = np.nonzero(m)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    k = WORK_H / m.shape[0]
    m = cv2.resize(m * 255, (int(m.shape[1] * k), WORK_H), interpolation=cv2.INTER_LINEAR)
    m = ((m > 127) * 255).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, disk(p["open"] * WORK_H))
    m = biggest(m > 127) * 255
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    # Kontur glätten (Gauß entlang der Kurve): beseitigt Wackeln, lässt dünne Gurte stehen
    c = max(cs, key=len)[:, 0, :].astype(float)
    sg = p.get("cs", 9.0); half = int(sg * 3); ker = np.exp(-0.5 * (np.arange(-half, half + 1) / sg) ** 2); ker /= ker.sum()
    ext = np.concatenate([c[-half:], c, c[:half]])
    sm = np.stack([np.convolve(ext[:, i], ker, mode="valid") for i in range(2)], 1)
    m = np.zeros_like(m); cv2.fillPoly(m, [np.round(sm).astype(np.int32)[:, None, :]], 255)
    return m > 127


def trace(mask, p):
    ys, xs = np.nonzero(mask)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    h = y1 - y0; w = x1 - x0
    s = (Y1 - Y0) * p["hoehe"] / h
    if w * s > MAXW: s = MAXW / w
    top = mask[y0: y0 + max(4, int(h * 0.03))]
    ax = x0 + np.nonzero(top)[1].mean()                 # Mitte des Gurtendes
    ox = AXIS - ax * s
    if x0 * s + ox < X0 + .5: ox += X0 + .5 - (x0 * s + ox)
    if x1 * s + ox > X1 - .5: ox -= x1 * s + ox - (X1 - .5)
    oy = Y0 - y0 * s                                    # Gurt schließt oben an der Stabkante an
    k = TRACE_H / mask.shape[0]
    small = cv2.resize(mask.astype(np.uint8) * 255, (max(1, int(mask.shape[1] * k)), TRACE_H), interpolation=cv2.INTER_AREA) > 127
    path = potrace.Bitmap(~small).trace(turdsize=int(200 * k * k) + 2, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                                        alphamax=1.2, opticurve=True, opttolerance=0.4)
    T = lambda q: (q.x / k * s + ox, q.y / k * s + oy)
    parts, pts = [], []
    for curve in path:
        x, y = T(curve.start_point); d = f"M{x:.2f} {y:.2f}"; pts.append((x, y))
        for sg in curve.segments:
            if sg.is_corner:
                a, b = T(sg.c), T(sg.end_point); d += f"L{a[0]:.2f} {a[1]:.2f}L{b[0]:.2f} {b[1]:.2f}"; pts += [a, b]
            else:
                a, b, c = T(sg.c1), T(sg.c2), T(sg.end_point)
                d += f"C{a[0]:.2f} {a[1]:.2f} {b[0]:.2f} {b[1]:.2f} {c[0]:.2f} {c[1]:.2f}"; pts.append(c)
        parts.append(d + "Z")
    bb = (min(q[0] for q in pts), min(q[1] for q in pts), max(q[0] for q in pts), max(q[1] for q in pts))
    return "".join(parts), bb, ax * s + ox


# ---- Morph (Punktfolgen gleich verteilt entlang des Umrisses, wie styleguide/_werkzeug/morph.py) ----
N = 240


def parse(d):
    toks = re.findall(r"[MLCZ]|-?\d*\.?\d+", d)
    pts, i, cmd, cur = [], 0, None, None
    while i < len(toks):
        t = toks[i]
        if t in "MLCZ":
            cmd = t; i += 1
            if cmd == "Z": continue
        if cmd in "ML":
            cur = (float(toks[i]), float(toks[i + 1])); i += 2; pts.append(cur)
        elif cmd == "C":
            c = [float(v) for v in toks[i:i + 6]]; i += 6
            p0, p1, p2, p3 = cur, (c[0], c[1]), (c[2], c[3]), (c[4], c[5])
            for q in range(1, 25):
                u = q / 24; a = 1 - u
                pts.append((a**3*p0[0]+3*a*a*u*p1[0]+3*a*u*u*p2[0]+u**3*p3[0], a**3*p0[1]+3*a*a*u*p1[1]+3*a*u*u*p2[1]+u**3*p3[1]))
            cur = p3
        else: i += 1
    if pts[0] == pts[-1]: pts.pop()
    return pts


def resample(pts, n):
    ring = pts + [pts[0]]; seg = [math.dist(ring[i], ring[i+1]) for i in range(len(pts))]; total = sum(seg)
    out, j, acc = [], 0, 0.0
    for k in range(n):
        target = total * k / n
        while acc + seg[j] < target: acc += seg[j]; j += 1
        u = (target - acc) / seg[j] if seg[j] else 0; a, b = ring[j], ring[j+1]
        out.append((a[0]+(b[0]-a[0])*u, a[1]+(b[1]-a[1])*u))
    return out


def area(p): return sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))/2


def align(bar, fig):
    if (area(bar) > 0) != (area(fig) > 0): fig = fig[::-1]
    best, off = None, 0
    for o in range(len(fig)):
        s = sum((bar[i][0]-fig[(i+o)%N][0])**2+(bar[i][1]-fig[(i+o)%N][1])**2 for i in range(N))
        if best is None or s < best: best, off = s, o
    return fig[off:] + fig[:off]


if __name__ == "__main__":
    out = []
    for p in FIGUREN:
        d, bb, anchor = trace(prepare(p), p)
        out.append(d)
        print(p["ref"], "Rahmen", tuple(round(v, 1) for v in bb), "Gurtende bei x =", round(anchor, 1), "Länge", len(d))
        assert bb[0] >= X0 and bb[2] <= X1 and bb[1] >= Y0 - .3 and bb[3] <= Y1 + .3, "ragt über das Zeichen"
    json.dump(out, open(os.path.join(TMP, "figuren.json"), "w"))
    with open(os.path.join(LP, "assets", "js", "figuren.js"), "w", encoding="utf-8") as fh:
        fh.write("/* Luftartistik-Silhouetten für die Verwandlung der Bildmarke (Probefassung), freigestellt aus Referenzfotos "
                 "(erzeugt mit _werkzeug/figuren_luft.py) */\nwindow.TTGO_FIGUREN = " + json.dumps(out) + ";\n")
    mj = os.path.join(LP, "assets", "js", "morph.js")
    old = open(mj, encoding="utf-8").read()
    bar = json.loads(old[old.index("{"):old.rindex("}") + 1])["bar"]
    barp = [(bar[i], bar[i + 1]) for i in range(0, len(bar), 2)]
    figs = [align(barp, resample(parse(d), N)) for d in out]
    flat = lambda pp: [round(v, 2) for q in pp for v in q]
    data = {"bar": bar, "figs": [flat(f) for f in figs]}
    with open(mj, "w", encoding="utf-8") as f:
        f.write("/* Punktfolgen für den Morph zwischen gebogenem Stab und Luftartistik-Figuren (erzeugt mit _werkzeug/figuren_luft.py) */\n")
        f.write("window.TTGO_MORPH = " + json.dumps(data, separators=(",", ":")) + ";\n")
    # Vorschau als SVG-Seite (Rendern per Browser, cairo ist hier nicht verfügbar)
    cells = "".join(f'<g transform="translate({i*70} 0)"><rect x="21.5" y="8" width="9" height="84" fill="#efebe3"/>'
                    f'<rect x="69.5" y="8" width="9" height="84" fill="#efebe3"/><path d="{d}" fill="#d22b1f" fill-rule="evenodd"/></g>'
                    for i, d in enumerate(out))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="14 0 {70*len(out)} 100" width="{len(out)*380}" height="{int(380*100/70)}">'
           f'<rect x="0" y="0" width="900" height="100" fill="#0e0e0e"/>{cells}</svg>')
    open(os.path.join(TMP, "silhouetten.svg"), "w", encoding="utf-8").write(svg)
    print("ok")

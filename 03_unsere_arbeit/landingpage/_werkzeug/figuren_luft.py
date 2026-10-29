"""Luftartistik-Silhouetten für die Verwandlung der Bildmarke (Probefassung, zweite Fassung).
Grundlage: Referenzfotos von Lilith (02_rohmaterial_medien/luftartistik_referenzen_lilith).
Die PERSON wird aus dem Foto freigestellt (BiRefNet, rembg), Gurte, Kabel und Masten werden entfernt, die Kontur
wird geglättet. Die GURTE werden neu gesetzt: gerade, gleich breite Bänder vom gemeinsamen Ansatzpunkt am Stab
(x = 50, y = 8) zu den Griff- bzw. Haltepunkten, die im Foto abgelesen sind. Alle Figuren haben dieselbe
Körpermasse (gleiche Fläche) und bleiben zwischen den äußeren Stäben.
Aufruf: python figuren_luft.py   (schreibt assets/js/figuren.js, assets/js/morph.js, tmp/luft/figuren.json, silhouetten.svg)
Die Rohmasken (refN_rembg.png) liegen in styleguide/_werkzeug/tmp/luft und werden bei Bedarf erzeugt.
"""
import json, os, re, math
import numpy as np, cv2
from PIL import Image, ImageOps
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import potrace

HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.dirname(HERE)
ROOT = os.path.dirname(LP)
TMP = os.path.join(ROOT, "styleguide", "_werkzeug", "tmp", "luft"); os.makedirs(TMP, exist_ok=True)
REF = "C:/Andersen/Webworks/GitHub/Webworks/take-the-gloves-off/02_rohmaterial_medien/luftartistik_referenzen_lilith/"
X0, X1, Y0, Y1 = 21.5, 78.5, 8.0, 92.0       # Zeichen
IN0, IN1 = 31.8, 68.2                        # Zwischenraum zwischen den Stäben (mit Luft)
ANCHOR = (50.0, 8.0)                         # Gurtansatz am Stab
BAND = 1.8                                   # Gurtbreite (Zeichen-Einheiten)
RES = 24                                     # Pixel je Einheit beim Zusammensetzen
TRACE = 9                                    # Pixel je Einheit beim Nachzeichnen
LMIN = 9.0                                   # kürzester Gurt (Abstand der Haltepunkte unter dem Ansatz)
BOTTOM = 89.0                                # tiefster Punkt aller drei Figuren (Stab-Unterkante liegt bei 92)
POSE_MASSSTAB = 0.90                         # frei entworfene Figuren gegenüber der vollen Füllung etwas kleiner, damit sie neben dem schlanken Spagat nicht massiger wirken

# zonen = [(x0,y0,x1,y1,modus,r)]: kill löscht, open behält nur dicke Teile (entfernt Gurte); Koordinaten im Foto
# straps = Haltepunkte im Foto, mit dem Ansatz durch gerade Bänder verbunden; extra = weitere Bänder (Start, Ende)
# L = Abstand der Haltepunkte unter dem Ansatz (Einheiten)
SPEC4 = [   # ref4: Gelenkpunkte im Foto (x, y, Radius); idealisierte Kontur nach der Pose im Foto
    ("ell", 452, 488, 44, 34),
    ("chain", [(440, 520, 28), (436, 600, 30), (432, 720, 37), (430, 820, 47), (425, 880, 58)]),
    ("chain", [(400, 935, 82), (440, 1010, 66), (478, 1085, 70), (498, 1135, 60)]),
    ("chain", [(345, 905, 52), (270, 892, 46), (190, 880, 36), (178, 935, 28), (190, 962, 22), (165, 1000, 18), (140, 1018, 12)]),
    ("ell", 436, 1262, 74, 76),
    ("chain", [(470, 1135, 34), (452, 1200, 30)]),
    ("chain", [(515, 1130, 44), (575, 1100, 34), (625, 1082, 25), (672, 1068, 18), (705, 1062, 12)]),
    ("ell", 705, 1062, 28, 12, -10),
    ("chain", [(430, 1230, 30), (412, 1300, 26), (410, 1400, 23), (411, 1500, 19), (413, 1545, 16), (414, 1585, 6)]),
]
SPEC1 = [   # ref1
    ("ell", 535, 642, 70, 76),
    ("chain", [(570, 700, 30), (590, 750, 36)]),
    ("chain", [(580, 770, 70), (650, 800, 92), (655, 885, 84), (650, 940, 78), (655, 1030, 98), (645, 1110, 88)]),
    ("chain", [(595, 625, 36), (640, 540, 30), (690, 450, 27), (720, 385, 24), (737, 345, 26)]),
    ("ell", 738, 335, 30, 36),
    ("chain", [(705, 735, 40), (765, 670, 34), (830, 572, 27), (885, 510, 21), (910, 465, 24)]),
    ("ell", 910, 462, 26, 32),
    ("chain", [(640, 1105, 76), (540, 1150, 64), (450, 1210, 56), (390, 1283, 34), (340, 1318, 24), (290, 1340, 14)]),
    ("chain", [(610, 1125, 70), (540, 1275, 52), (600, 1330, 40), (663, 1383, 34), (703, 1437, 26), (757, 1483, 12)]),
]

# zonen = [(x0,y0,x1,y1,modus,r)]: kill löscht, open behält nur dicke Teile (entfernt Gurte, Locken); Koordinaten im Foto
# bau = Körper aus Gelenkpunkten statt aus dem Foto (idealisiert); straps = Haltepunkte im Foto, mit dem Ansatz durch
# gerade Bänder verbunden; extra = weitere Bänder (Start, Ende)
FIGUREN = [
    dict(ref="ref5.jpg", zonen=[(150, 0, 760, 322, "kill", 0), (150, 345, 306, 425, "kill", 0), (190, 420, 306, 740, "kill", 0),
                               (468, 322, 760, 612, "kill", 0), (0, 1000, 1049, 1573, "kill", 0)],
         straps=[(318, 356), (462, 336)], extra=[((462, 336), (660, 638))], plus=[("ell", 372, 497, 46, 52), ("line", (376, 540), (385, 610), 56)], L=14, unten=True, close=0.007, open=0.006, blur=0.008),
    dict(pose="c"),     # einarmiges Hängen, Rumpf verdreht, ein Knie angezogen (frei entworfen)
    dict(pose="a"),     # Hängen an beiden Händen, Kopf sinkt zwischen die Arme
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


def person(p):
    """Person ohne Gurte, glatt, als Gleitkomma-Maske (0..1) im Foto-Maßstab"""
    if p.get("bau"):
        g = np.array(Image.open(REF + p["ref"]).convert("L")); m = np.zeros(g.shape, np.uint8)
        for kind, *a in p["bau"]:
            if kind == "chain":
                for (x0, y0, r0), (x1, y1, r1) in zip(a[0][:-1], a[0][1:]):
                    A, B = np.array([x0, y0], float), np.array([x1, y1], float); d = B - A; Ln = np.linalg.norm(d)
                    cv2.circle(m, (int(x0), int(y0)), int(r0), 255, -1); cv2.circle(m, (int(x1), int(y1)), int(r1), 255, -1)
                    if Ln:
                        n = np.array([-d[1], d[0]]) / Ln
                        cv2.fillPoly(m, [np.round(np.array([A + n * r0, B + n * r1, B - n * r1, A - n * r0])).astype(np.int32)], 255)
            else:
                cx, cy, rx, ry = a[:4]; ang = a[4] if len(a) > 4 else 0
                cv2.ellipse(m, (int(cx), int(cy)), (int(rx), int(ry)), ang, 0, 360, 255, -1)
        ys, xs = np.nonzero(m); H = ys.max() - ys.min()
        return cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), H * p.get("blur", 0.006))
    if p.get("thr"):                                  # Gegenlicht: Schwellwert ist hier sauberer als die KI-Freistellung
        g = np.array(Image.open(REF + p["ref"]).convert("L")).astype(int)
        x0, y0, x1, y1 = p["box"]
        m = np.zeros(g.shape, np.uint8); m[y0:y1, x0:x1] = (g[y0:y1, x0:x1] < p["thr"])
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, disk(5))   # Kabel weg
    else:
        m = rohmaske(p["ref"])
    for x0, y0, x1, y1, mode, r in p["zonen"]:
        if mode == "kill": m[y0:y1, x0:x1] = 0
        else:
            o = cv2.morphologyEx(m, cv2.MORPH_OPEN, disk(r))
            m[y0:y1, x0:x1] = o[y0:y1, x0:x1]
    m = biggest(m)
    ys, xs = np.nonzero(m); H = ys.max() - ys.min()
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, disk(H * p.get("close", 0.004)))      # Locken zu einer ruhigen Form
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, disk(H * p.get("open", 0.003)))
    m = biggest(m)
    cs, hi = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(m)
    for c, h in zip(cs, hi[0]):                                   # kleine Löcher füllen, große Lücken behalten
        if h[3] < 0: cv2.drawContours(out, [c], -1, 1, -1)
    for c, h in zip(cs, hi[0]):
        if h[3] >= 0 and cv2.contourArea(c) > (H * 0.05) ** 2: cv2.drawContours(out, [c], -1, 0, -1)
    for kind, *a in p.get("plus", []):                            # Nachbesserung: Kopf klar absetzen
        if kind == "ell": cv2.ellipse(out, (int(a[0]), int(a[1])), (int(a[2]), int(a[3])), 0, 0, 360, 1, -1)
        else: cv2.line(out, (int(a[0][0]), int(a[0][1])), (int(a[1][0]), int(a[1][1])), 1, int(a[2]))
    return cv2.GaussianBlur(out.astype(np.float32), (0, 0), H * p.get("blur", 0.004))


def band(canvas, a, b, w, ext=True):
    """gerades Band der Breite w (Pixel) von a nach b, flache Enden; nach oben über den Rand hinaus verlängert"""
    a = np.array(a, float); b = np.array(b, float); d = b - a; d /= np.linalg.norm(d)
    n = np.array([-d[1], d[0]]) * w / 2
    a2 = a - d * 3000 if ext else a
    cv2.fillPoly(canvas, [np.round(np.array([a2 + n, b + n, b - n, a2 - n])).astype(np.int32)], 255)


def fit(p, f):
    """Maßstab je Figur: so groß, dass sie den Zwischenraum füllt (Breite und Höhe), mit möglichst kurzem Gurt"""
    ys, xs = np.nonzero(f > .5)
    cy = np.mean([q[1] for q in p["straps"]])
    s = min((IN1 - IN0) / (xs.max() - xs.min()), (BOTTOM - ANCHOR[1] - p.get("L", LMIN)) / (ys.max() - cy))
    while True:
        L = max(p.get("L", LMIN), 4 - (ys.min() - cy) * s)                 # Körper beginnt frühestens 4 Einheiten unter dem Ansatz
        bottom = ANCHOR[1] + L + (ys.max() - cy) * s
        if bottom <= BOTTOM + 1e-6 and (xs.max() - xs.min()) * s <= IN1 - IN0 + 1e-6:
            if p.get("unten"): L = BOTTOM - ANCHOR[1] - (ys.max() - cy) * s       # Körper hängt bündig am unteren Rand, der Gurt trägt die Höhe
            return s, L
        s *= 0.99


def build(p, f, s, L, body=True):
    h, w = f.shape
    k = s * RES
    big = cv2.resize(f, (int(w * k), int(h * k)), interpolation=cv2.INTER_CUBIC)
    cx = np.mean([q[0] for q in p["straps"]]) * s
    cy = np.mean([q[1] for q in p["straps"]]) * s
    ys, xs = np.nonzero(f > .5)
    bx0, bx1 = xs.min() * s, xs.max() * s
    px = min(max(ANCHOR[0] - cx, IN0 - bx0), IN1 - bx1)            # Mitte der Haltepunkte unter den Ansatz, sonst nur so weit schieben wie nötig
    py = ANCHOR[1] + L - cy
    W, H = int((X1 - X0) * RES), int((Y1 - Y0) * RES)
    canvas = np.zeros((H, W), np.uint8)
    tx, ty = int(round((px - X0) * RES)), int(round((py - Y0) * RES))
    xa, ya = max(0, tx), max(0, ty); xb, yb = min(W, tx + big.shape[1]), min(H, ty + big.shape[0])
    sub = big[ya - ty:yb - ty, xa - tx:xb - tx]
    if body: canvas[ya:yb, xa:xb] = ((sub > .5) * 255).astype(np.uint8)
    P = lambda q: ((q[0] * s + px - X0) * RES, (q[1] * s + py - Y0) * RES)
    anchor = ((ANCHOR[0] - X0) * RES, (ANCHOR[1] - Y0) * RES)
    for q in p["straps"]: band(canvas, anchor, P(q), BAND * RES)
    for a, b in p["extra"]: band(canvas, P(a), P(b), BAND * RES, False)
    canvas = cv2.morphologyEx(canvas, cv2.MORPH_CLOSE, disk(0.55 * RES))               # spitze Keile und Haarrisse zu
    if not body: return canvas
    cs, hi = cv2.findContours(canvas, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)      # winzige Lücken schließen
    for c, h in zip(cs, hi[0]):
        if h[3] >= 0 and cv2.contourArea(c) < 6 * RES * RES: cv2.drawContours(canvas, [c], -1, 255, -1)
    return canvas


_POSEN_CACHE = {}


def pose_canvas(name, body=True):
    """frei entworfene Figur aus Körpersegmenten (figuren_koerper.py): Maske im Raster des Zeichens plus gerade Gurte"""
    from figuren_koerper import pose_skaliert
    W, H = int((X1 - X0) * RES), int((Y1 - Y0) * RES)
    if name not in _POSEN_CACHE:
        X, Y = np.meshgrid(X0 + (np.arange(W) + 0.5) / RES, Y0 + (np.arange(H) + 0.5) / RES)
        d, grips, Z = pose_skaliert(name, X, Y, unten=BOTTOM, q=POSE_MASSSTAB)
        print('   Pose', name, 'Vergrößerung', round(Z, 3))
        _POSEN_CACHE[name] = (((d < 0) * 255).astype(np.uint8), grips)
    mask, grips = _POSEN_CACHE[name]
    canvas = mask.copy() if body else np.zeros((H, W), np.uint8)
    anchor = ((ANCHOR[0] - X0) * RES, (ANCHOR[1] - Y0) * RES)
    for g in grips: band(canvas, anchor, ((g[0] - X0) * RES, (g[1] - Y0) * RES), BAND * RES)
    if body:
        canvas = cv2.morphologyEx(canvas, cv2.MORPH_CLOSE, disk(0.55 * RES))
        cs, hi = cv2.findContours(canvas, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        for c, h in zip(cs, hi[0]):
            if h[3] >= 0 and cv2.contourArea(c) < 4 * RES * RES: cv2.drawContours(canvas, [c], -1, 255, -1)
    return canvas


def smooth_contour(m, sigma):
    cs, _ = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(m)
    for c in cs:
        if len(c) < 20: continue
        c = c[:, 0, :].astype(float); half = int(sigma * 3)
        ker = np.exp(-0.5 * (np.arange(-half, half + 1) / sigma) ** 2); ker /= ker.sum()
        ext = np.concatenate([c[-half:], c, c[:half]])
        sm = np.stack([np.convolve(ext[:, i], ker, mode="valid") for i in range(2)], 1)
        cv2.fillPoly(out, [np.round(sm).astype(np.int32)[:, None, :]], 255)
    return out


def vectorise(canvas):
    k = TRACE / RES
    small = cv2.resize(canvas, (int(canvas.shape[1] * k), int(canvas.shape[0] * k)), interpolation=cv2.INTER_AREA) > 127
    pad = np.pad(small, 3)
    path = potrace.Bitmap(~pad).trace(turdsize=20, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                                      alphamax=1.15, opticurve=True, opttolerance=0.6)
    T = lambda q: ((q.x - 3) / TRACE + X0, (q.y - 3) / TRACE + Y0)
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
    return "".join(parts), bb


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


K = 20           # Zwischenbilder je Verwandlung (Stab -> Figur)
R2 = 12          # Pixel je Einheit für die Abstandsfelder


def zwischenbilder(barp, gurt, canvas):
    """Weiche Verwandlung in zwei Schritten: erst zieht sich der Stab zum Gurt zusammen, dann wächst der Körper aus den
    Haltepunkten (Abstandsfelder werden überblendet, keine verdrehten Umrisse). Ergebnis: K Pfade von t = 0 (Stab) bis t = 1."""
    W, H = int((X1 - X0) * R2), int((Y1 - Y0) * R2)
    rs = lambda c: (cv2.resize(c, (W, H), interpolation=cv2.INTER_AREA) > 127).astype(np.uint8)
    fig, gur = rs(canvas), rs(gurt)
    bar = np.zeros((H, W), np.uint8)
    cv2.fillPoly(bar, [np.round(np.array([((x - X0) * R2, (y - Y0) * R2) for x, y in barp])).astype(np.int32)], 1)
    sd = lambda m: cv2.distanceTransform(1 - m, cv2.DIST_L2, 5) - cv2.distanceTransform(m, cv2.DIST_L2, 5)
    cx = lambda m: np.nonzero(m)[1].mean()
    def shift(m, dx):
        return cv2.warpAffine(m, np.float32([[1, 0, dx], [0, 1, 0]]), (W, H), flags=cv2.INTER_NEAREST)
    SPLIT = 0.5
    frames = []
    for i in range(K):
        t = i / (K - 1)
        if t <= SPLIT:                                    # Stab -> Gurt (gemeinsame Mitte, Ansatz bleibt oben)
            u = t / SPLIT; u = u * u * (3 - 2 * u)
            c = (1 - u) * cx(bar) + u * cx(gur)
            f = (1 - u) * sd(shift(bar, c - cx(bar))) + u * sd(shift(gur, c - cx(gur)))
        else:                                             # Gurt -> ganze Figur (Körper wächst aus den Haltepunkten)
            u = (t - SPLIT) / (1 - SPLIT); u = u * u * (3 - 2 * u)
            f = (1 - u) * sd(gur) + u * sd(fig)
        up = cv2.resize(f, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        m = (up < 0).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, disk(2))
        cs, hi = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        d = ""
        for c_ in cs:
            if len(c_) < 12 or cv2.contourArea(c_) < 6: continue
            c_ = c_[:, 0, :].astype(float); sg = 3.5; half = int(sg * 3)
            ker = np.exp(-0.5 * (np.arange(-half, half + 1) / sg) ** 2); ker /= ker.sum()
            ext = np.concatenate([c_[-half:], c_, c_[:half]])
            sm = np.stack([np.convolve(ext[:, j], ker, mode="valid") for j in range(2)], 1)
            ap = cv2.approxPolyDP(sm.astype(np.float32)[:, None, :], 0.7, True)[:, 0, :]
            if len(ap) < 3: continue
            d += "M" + "L".join(f"{x / (2 * R2) + X0:.2f} {y / (2 * R2) + Y0:.2f}" for x, y in ap) + "Z"
        frames.append(d)
    return frames


if __name__ == "__main__":
    out, canvases, strapcv = [], [], []
    for p in FIGUREN:
        if p.get("pose"):
            canvas = pose_canvas(p["pose"]); canvases.append(canvas); strapcv.append(pose_canvas(p["pose"], body=False)); s, L = 1.0, 0
        else:
            f = person(p)
            s, L = fit(p, f)
            canvas = build(p, f, s, L); canvases.append(canvas); strapcv.append(build(p, f, s, L, body=False))
        d, bb = vectorise(canvas)
        out.append(d)
        print(p.get("ref", p.get("pose")), "Maßstab", round(s, 4), "L", round(L, 1), "Rahmen", tuple(round(float(v), 1) for v in bb), "Länge", len(d))
        assert bb[0] >= 31.0 and bb[2] <= 69.0 and bb[3] <= Y1 and bb[1] >= Y0 - .3, "ragt über den Zwischenraum"
    json.dump(out, open(os.path.join(TMP, "figuren.json"), "w"))
    with open(os.path.join(LP, "assets", "js", "figuren.js"), "w", encoding="utf-8") as fh:
        fh.write("/* Luftartistik-Silhouetten für die Verwandlung der Bildmarke (Probefassung), Personen aus Referenzfotos freigestellt, "
                 "Gurte neu gesetzt (erzeugt mit _werkzeug/figuren_luft.py) */\nwindow.TTGO_FIGUREN = " + json.dumps(out) + ";\n")
    mj = os.path.join(LP, "assets", "js", "morph.js")
    old = open(mj, encoding="utf-8").read()
    bar = json.loads(old[old.index("{"):old.rindex("}") + 1])["bar"]
    barp = [(bar[i], bar[i + 1]) for i in range(0, len(bar), 2)]
    figs = [align(barp, resample(parse(d), N)) for d in out]
    flat = lambda pp: [round(v, 2) for q in pp for v in q]
    data = {"bar": bar, "figs": [flat(f) for f in figs], "frames": [zwischenbilder(barp, strapcv[k], c) if k in (0, len(canvases) - 1) else None for k, c in enumerate(canvases)]}
    with open(mj, "w", encoding="utf-8") as f:
        f.write("/* Punktfolgen für den Morph zwischen gebogenem Stab und Luftartistik-Figuren (erzeugt mit _werkzeug/figuren_luft.py) */\n")
        f.write("window.TTGO_MORPH = " + json.dumps(data, separators=(",", ":")) + ";\n")
    cells = "".join(f'<g transform="translate({i*70} 0)"><rect x="21.5" y="8" width="9" height="84" fill="#efebe3"/>'
                    f'<rect x="69.5" y="8" width="9" height="84" fill="#efebe3"/><path d="{d}" fill="#d22b1f" fill-rule="evenodd"/></g>'
                    for i, d in enumerate(out))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="14 0 {70*len(out)} 100" width="{len(out)*480}" height="{int(480*100/70)}">'
           f'<rect x="0" y="0" width="900" height="100" fill="#0e0e0e"/>{cells}</svg>')
    open(os.path.join(TMP, "silhouetten.svg"), "w", encoding="utf-8").write(svg)
    print("ok")

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
    dict(pose2="E"),    # einarmiges Hängen, Rumpf verdreht, ein Knie angezogen (frei entworfen, figuren_posen2.py)
    dict(pose2="K"),    # kopfüber, ein Fuß im Gurt eingehakt, das andere Bein im Vierer, Arme hängen
    dict(pose2="G"),    # zusammengekrümmt in der Gurtschlaufe, Stirn auf den Knien
    dict(pose2="F"),    # an beiden Fäusten hängend, Kopf sinkt zwischen die Arme
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


def build(p, f, s, L, body=True, spec=False):
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
    if spec: return dict(anchor=anchor, bands=[(anchor, P(q)) for q in p["straps"]] + [(P(a), P(b)) for a, b in p["extra"]], close=True)
    for q in p["straps"]: band(canvas, anchor, P(q), BAND * RES)
    for a, b in p["extra"]: band(canvas, P(a), P(b), BAND * RES, False)
    canvas = cv2.morphologyEx(canvas, cv2.MORPH_CLOSE, disk(0.55 * RES))               # spitze Keile und Haarrisse zu
    if not body: return canvas
    cs, hi = cv2.findContours(canvas, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)      # winzige Lücken schließen
    for c, h in zip(cs, hi[0]):
        if h[3] >= 0 and cv2.contourArea(c) < 6 * RES * RES: cv2.drawContours(canvas, [c], -1, 255, -1)
    return canvas


_POSEN_CACHE = {}


def pose_canvas(name, body=True, spec=False):
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
    if spec: return dict(anchor=anchor, bands=[(anchor, ((g[0] - X0) * RES, (g[1] - Y0) * RES)) for g in grips], close=False)
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


K = 30           # Zwischenbilder je Verwandlung (Stab -> Figur)
KP = 36          # Zwischenbilder je Verwandlung Figur -> Figur
R2 = 12          # Pixel je Einheit für die Abstandsfelder


def pfad_aus_feld(f):
    """Abstandsfeld (negativ = innen) -> geglätteter Pfad mit einer einzigen deckenden Form"""
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
    return d


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
    body_ = cv2.morphologyEx(fig & (1 - gur), cv2.MORPH_OPEN, disk(4)); body_ = biggest(body_)
    ys_, xs_ = np.nonzero(body_); kk_ = ys_ < ys_.min() + 2 * R2
    px_, py_ = float(xs_[kk_].mean()), float(ys_.min() + 3 * R2)          # Handpunkt: oberer Rand des Körpers
    frames = []
    for i in range(K):
        t = i / (K - 1)
        if t <= SPLIT:                                    # Stab -> Gurt (gemeinsame Mitte, Ansatz bleibt oben)
            u = t / SPLIT; u = u * u * (3 - 2 * u)
            c = (1 - u) * cx(bar) + u * cx(gur)
            f = (1 - u) * sd(shift(bar, c - cx(bar))) + u * sd(shift(gur, c - cx(gur)))
        else:                                             # Gurt -> ganze Figur (Körper wächst aus den Haltepunkten)
            u = (t - SPLIT) / (1 - SPLIT); u = u * u * (3 - 2 * u)
            # der Körper wächst als verkleinerte Silhouette aus den Haltepunkten (Skalierung um den Handpunkt: keine Spitzen)
            k = max(u, 0.02)
            M_ = np.float32([[k, 0, px_ * (1 - k)], [0, k, py_ * (1 - k)]])
            kw = cv2.warpAffine(fig * 255, M_, (W, H), flags=cv2.INTER_LINEAR)
            f = sd(((kw > 127).astype(np.uint8)) | gur)
        d = pfad_aus_feld(f)
        frames.append(d)
    return frames


def paar_bilder(ca, cb, ga, gb):
    """Formmorph Figur A -> Figur B, zu jedem Zeitpunkt genau eine deckende Form.
    Körper und Gurt werden getrennt gemorpht und vereinigt:
    - Körper (ohne Gurt): Abstandsfelder werden überblendet, die Körpermitten laufen zusammen, die Fläche wächst linear
      (Flächenerhalt), das Feld wird leicht geglättet;
    - Gurt: A -> ein einzelnes Band vom Ansatz zu den (gemittelten) Händen -> B, ebenfalls flächentreu.
    Das Band hält Gurt und Körper in jedem Bild zusammen."""
    W, H = int((X1 - X0) * R2), int((Y1 - Y0) * R2)
    rs = lambda c: (cv2.resize(c, (W, H), interpolation=cv2.INTER_AREA) > 127).astype(np.uint8)
    A, B, GA, GB = rs(ca), rs(cb), rs(ga), rs(gb)
    sd = lambda m: cv2.distanceTransform(1 - m, cv2.DIST_L2, 5) - cv2.distanceTransform(m, cv2.DIST_L2, 5)
    sm = lambda u: u * u * (3 - 2 * u)
    def koerper(M, G):
        m = M & (1 - G)
        return biggest(cv2.morphologyEx(m, cv2.MORPH_OPEN, disk(4)))
    bA, bB = koerper(A, GA), koerper(B, GB)
    shift = lambda f, dx: cv2.warpAffine(f, np.float32([[1, 0, dx], [0, 1, 0]]), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    cen = lambda m: np.nonzero(m)[1].mean()
    def treu(f, ziel):
        lo, hi_ = -40.0, 60.0
        for _ in range(30):
            mid = (lo + hi_) / 2
            if (f < mid).sum() < ziel: lo = mid
            else: hi_ = mid
        return f - (lo + hi_) / 2
    def kopf(m):
        ys, xs = np.nonzero(m); k = ys < ys.min() + 2 * R2
        return xs[k].mean(), ys.min() + 6 * R2
    fbA, fbB, fgA, fgB = sd(bA), sd(bB), sd(GA), sd(GB)
    ca_, cb_ = cen(bA), cen(bB); ta, tb = kopf(bA), kopf(bB)
    out = []
    for i in range(KP):
        u = i / (KP - 1)
        c = (1 - u) * ca_ + u * cb_
        fb = treu((1 - u) * shift(fbA, c - ca_) + u * shift(fbB, c - cb_), (1 - u) * bA.sum() + u * bB.sum())
        sg = 9 * math.sin(math.pi * u)                    # in der Mitte der Verwandlung am weichsten, an den Enden unverändert
        if sg > 0.3: fb = treu(cv2.GaussianBlur(fb, (0, 0), sg), (1 - u) * bA.sum() + u * bB.sum())
        g = ((1 - u) * ta[0] + u * tb[0], (1 - u) * ta[1] + u * tb[1])
        link = np.zeros((H, W), np.uint8); band(link, ((ANCHOR[0] - X0) * R2, 0), g, BAND * R2)
        Lk = (link > 0).astype(np.uint8); fl = sd(Lk)
        if u < 0.5:
            v = sm(u / 0.5); fs = treu((1 - v) * fgA + v * fl, (1 - v) * GA.sum() + v * Lk.sum())
        else:
            v = sm((u - 0.5) / 0.5); fs = treu((1 - v) * fl + v * fgB, (1 - v) * Lk.sum() + v * GB.sum())
        out.append(pfad_aus_feld(np.minimum(fb, fs)))
    return out


def paar_ueber_gurt(ca, cb, ga, gb):
    """Verwandlung Figur A -> Figur B über den Gurt, nie mit einem Zwischenkörper aus beiden Posen:
    A schrumpft als verkleinerte Silhouette in die Hände, der Gurt morpht flächentreu vom Gurt A über ein Einzelband zum
    Gurt B, danach wächst B aus seinen Händen."""
    W, H = int((X1 - X0) * R2), int((Y1 - Y0) * R2)
    rs = lambda c: (cv2.resize(c, (W, H), interpolation=cv2.INTER_AREA) > 127).astype(np.uint8)
    A, B, GA, GB = rs(ca), rs(cb), rs(ga), rs(gb)
    sd = lambda m: cv2.distanceTransform(1 - m, cv2.DIST_L2, 5) - cv2.distanceTransform(m, cv2.DIST_L2, 5)
    sm = lambda u: u * u * (3 - 2 * u)
    def treu(f, ziel):
        lo, hi_ = -40.0, 60.0
        for _ in range(30):
            mid = (lo + hi_) / 2
            if (f < mid).sum() < ziel: lo = mid
            else: hi_ = mid
        return f - (lo + hi_) / 2
    def pivot(M, G):
        b = biggest(cv2.morphologyEx(M & (1 - G), cv2.MORPH_OPEN, disk(4)))
        ys, xs = np.nonzero(b); k = ys < ys.min() + 2 * R2
        return float(xs[k].mean()), float(ys.min() + 3 * R2)
    pA, pB = pivot(A, GA), pivot(B, GB)
    def skaliert(M, p, k):
        return (cv2.warpAffine(M * 255, np.float32([[k, 0, p[0] * (1 - k)], [0, k, p[1] * (1 - k)]]), (W, H), flags=cv2.INTER_LINEAR) > 127).astype(np.uint8)
    T = {"s0": 0.0, "s1": 0.42, "g0": 0.25, "g1": 0.75, "w0": 0.58, "w1": 1.0}
    fgA, fgB = sd(GA), sd(GB)
    out = []
    for i in range(KP):
        t = i / (KP - 1)
        # Körper: erst A schrumpft, dann wächst B (nie beide zugleich)
        if t <= T["s1"]: body = skaliert(A, pA, max(1 - sm(t / T["s1"]), 0.0))
        elif t < T["w0"]: body = np.zeros((H, W), np.uint8)
        else: body = skaliert(B, pB, max(sm((t - T["w0"]) / (T["w1"] - T["w0"])), 0.0))
        if body.sum() < 30: body[:] = 0
        # Gurt
        v = min(max((t - T["g0"]) / (T["g1"] - T["g0"]), 0), 1); vs = sm(v)
        g = ((1 - vs) * pA[0] + vs * pB[0], (1 - vs) * pA[1] + vs * pB[1])
        link = np.zeros((H, W), np.uint8); band(link, ((ANCHOR[0] - X0) * R2, 0), g, BAND * R2)
        Lk = (link > 0).astype(np.uint8); fl = sd(Lk)
        if v <= 0: gur = GA
        elif v >= 1: gur = GB
        elif vs < 0.5:
            w = vs / 0.5; gur = (treu((1 - w) * fgA + w * fl, (1 - w) * GA.sum() + w * Lk.sum()) < 0).astype(np.uint8)
        else:
            w = (vs - 0.5) / 0.5; gur = (treu((1 - w) * fl + w * fgB, (1 - w) * Lk.sum() + w * GB.sum()) < 0).astype(np.uint8)
        out.append(pfad_aus_feld(sd(body | gur)))
    return out


if __name__ == "__main__":
    out, canvases, strapcv, specs = [], [], [], []
    for p in FIGUREN:
        if p.get("pose2"):
            import figuren_posen2
            canvas = figuren_posen2.canvas(p["pose2"], X0, X1, Y0, Y1, RES); canvases.append(canvas); strapcv.append(figuren_posen2.canvas(p["pose2"], X0, X1, Y0, Y1, RES, body=False)); specs.append(None); s, L = 1.0, 0
        elif p.get("pose"):
            canvas = pose_canvas(p["pose"]); canvases.append(canvas); strapcv.append(pose_canvas(p["pose"], body=False)); specs.append(pose_canvas(p["pose"], spec=True)); s, L = 1.0, 0
        else:
            f = person(p)
            s, L = fit(p, f)
            canvas = build(p, f, s, L); canvases.append(canvas); strapcv.append(build(p, f, s, L, body=False)); specs.append(build(p, f, s, L, spec=True))
        d, bb = vectorise(canvas)
        out.append(d)
        print(p.get("ref", p.get("pose", p.get("pose2"))), "Maßstab", round(s, 4), "L", round(L, 1), "Rahmen", tuple(round(float(v), 1) for v in bb), "Länge", len(d))
        assert bb[0] >= 31.0 and bb[2] <= 69.0 and bb[3] <= Y1 and bb[1] >= Y0 - .3, "ragt über den Zwischenraum"
    json.dump(out, open(os.path.join(TMP, "figuren.json"), "w"))
    with open(os.path.join(LP, "assets", "js", "figuren.js"), "w", encoding="utf-8") as fh:
        fh.write("/* Luftartistik-Silhouetten für die Verwandlung der Bildmarke (Probefassung), Personen aus Referenzfotos freigestellt, "
                 "Gurte neu gesetzt (erzeugt mit _werkzeug/figuren_luft.py) */\nwindow.TTGO_FIGUREN = " + json.dumps(out) + ";\n")
    mj = os.path.join(LP, "assets", "js", "morph.js")
    import morph_dicht
    # v10: kein Morph mehr. Je Figur genau ein Bild (dichter, geglätteter Umriss); Wechsel zwischen den Figuren per Flash im Browser.
    seqs = {}
    for i, c in enumerate(canvases):
        fr = morph_dicht.folge_zu_formen([morph_dicht.sd(morph_dicht.pad(c))])
        seqs["p%d" % i] = morph_dicht.kodieren(fr)
    data = {"kt": 1, "q": 50, "seq": seqs}
    with open(mj, "w", encoding="utf-8") as f:
        f.write("/* Umrisse der fünf Figuren für die Bildmarke, je Figur ein Bild (erzeugt mit _werkzeug/figuren_luft.py und morph_dicht.py) */\n")
        f.write("window.TTGO_MORPH = " + json.dumps(data, separators=(",", ":")) + ";\n")
    cells = "".join(f'<g transform="translate({i*70} 0)"><rect x="21.5" y="8" width="9" height="84" fill="#efebe3"/>'
                    f'<rect x="69.5" y="8" width="9" height="84" fill="#efebe3"/><path d="{d}" fill="#d22b1f" fill-rule="evenodd"/></g>'
                    for i, d in enumerate(out))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="14 0 {70*len(out)} 100" width="{len(out)*480}" height="{int(480*100/70)}">'
           f'<rect x="0" y="0" width="900" height="100" fill="#0e0e0e"/>{cells}</svg>')
    open(os.path.join(TMP, "silhouetten.svg"), "w", encoding="utf-8").write(svg)
    print("ok")

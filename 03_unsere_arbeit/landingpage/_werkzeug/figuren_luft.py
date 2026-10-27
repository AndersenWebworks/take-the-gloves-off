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
import potrace

HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.dirname(HERE)
ROOT = os.path.dirname(LP)
TMP = os.path.join(ROOT, "styleguide", "_werkzeug", "tmp", "luft"); os.makedirs(TMP, exist_ok=True)
REF = "C:/Andersen/Webworks/GitHub/Webworks/take-the-gloves-off/02_rohmaterial_medien/luftartistik_referenzen_lilith/"
X0, X1, Y0, Y1 = 21.5, 78.5, 8.0, 92.0       # Zeichen
IN0, IN1 = 32.5, 67.5                        # Zwischenraum zwischen den Stäben (mit Luft)
ANCHOR = (50.0, 8.0)                         # Gurtansatz am Stab
BAND = 1.8                                   # Gurtbreite (Zeichen-Einheiten)
RES = 24                                     # Pixel je Einheit beim Zusammensetzen
TRACE = 9                                    # Pixel je Einheit beim Nachzeichnen
KOPF = 6.6                                   # Kopfhöhe (mit Haar) in Einheiten: bestimmt den Maßstab, alle Figuren gleich groß
                                # größter Maßstab (Foto-Pixel -> Einheiten), damit nichts übergroß wird
MITTE = 52.0                                 # Körper möglichst um diese Höhe zentrieren
BOTTOM = 89.5                                # tiefster erlaubter Punkt

# zonen = [(x0,y0,x1,y1,modus,r)]: kill löscht, open behält nur dicke Teile (entfernt Gurte); Koordinaten im Foto
# straps = Haltepunkte im Foto, mit dem Ansatz durch gerade Bänder verbunden; extra = weitere Bänder (Start, Ende)
# L = Abstand der Haltepunkte unter dem Ansatz (Einheiten)
FIGUREN = [
    dict(ref="ref5.jpg", zonen=[(150, 0, 760, 322, "kill", 0), (150, 345, 306, 425, "kill", 0), (190, 420, 306, 740, "kill", 0),
                               (468, 322, 760, 612, "kill", 0), (0, 1000, 1049, 1573, "kill", 0)],
         kopf=95, straps=[(318, 356), (462, 336)], extra=[((462, 336), (660, 638))], L=24, close=0.005, open=0.004, blur=0.005),
    dict(ref="ref2.jpg", zonen=[(0, 0, 1066, 725, "kill", 0), (560, 725, 640, 772, "kill", 0)],
         kopf=125, straps=[(300, 745), (597, 792)], extra=[], L=24, close=0.014, open=0.007, blur=0.007),
    dict(ref="ref4.jpg", zonen=[(0, 0, 1066, 446, "kill", 0), (492, 500, 560, 760, "open", 14)],
         kopf=120, straps=[(492, 478)], extra=[], L=18, close=0.008, open=0.006, blur=0.009),
    dict(ref="ref1.jpg", zonen=[(650, 0, 900, 330, "open", 16), (850, 0, 1067, 460, "open", 16)],
         kopf=140, straps=[(740, 340), (905, 450)], extra=[], L=24, close=0.008, open=0.005, blur=0.007),
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
    return cv2.GaussianBlur(out.astype(np.float32), (0, 0), H * p.get("blur", 0.004))


def band(canvas, a, b, w, ext=True):
    """gerades Band der Breite w (Pixel) von a nach b, flache Enden; nach oben über den Rand hinaus verlängert"""
    a = np.array(a, float); b = np.array(b, float); d = b - a; d /= np.linalg.norm(d)
    n = np.array([-d[1], d[0]]) * w / 2
    a2 = a - d * 3000 if ext else a
    cv2.fillPoly(canvas, [np.round(np.array([a2 + n, b + n, b - n, a2 - n])).astype(np.int32)], 255)


def fit(p, f):
    """Maßstab aus gleicher Körperfläche, verkleinert, bis die Figur zwischen die Stäbe und ins Zeichen passt"""
    area = (f > .5).sum()
    s = KOPF / p["kopf"]
    ys, xs = np.nonzero(f > .5)
    cx = np.mean([q[0] for q in p["straps"]]); cy = np.mean([q[1] for q in p["straps"]])
    while True:
        w = (xs.max() - xs.min()) * s
        top = (ys.min() - cy) * s; bot = (ys.max() - cy) * s
        L = MITTE - (top + bot) / 2 - ANCHOR[1]
        L = max(L, 14)
        bottom = ANCHOR[1] + L + (ys.max() - cy) * s
        if bottom > BOTTOM: L = max(12, L - (bottom - BOTTOM)); bottom = ANCHOR[1] + L + (ys.max() - cy) * s
        if w <= IN1 - IN0 and bottom <= BOTTOM + 1e-6: return s, L
        s *= 0.99


def build(p, f, s, L):
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
    canvas[ya:yb, xa:xb] = ((sub > .5) * 255).astype(np.uint8)
    P = lambda q: ((q[0] * s + px - X0) * RES, (q[1] * s + py - Y0) * RES)
    anchor = ((ANCHOR[0] - X0) * RES, (ANCHOR[1] - Y0) * RES)
    for q in p["straps"]: band(canvas, anchor, P(q), BAND * RES)
    for a, b in p["extra"]: band(canvas, P(a), P(b), BAND * RES, False)
    canvas = cv2.morphologyEx(canvas, cv2.MORPH_CLOSE, disk(0.55 * RES))               # spitze Keile und Haarrisse zu
    cs, hi = cv2.findContours(canvas, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)      # winzige Lücken schließen
    for c, h in zip(cs, hi[0]):
        if h[3] >= 0 and cv2.contourArea(c) < 6 * RES * RES: cv2.drawContours(canvas, [c], -1, 255, -1)
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


K = 14           # Zwischenbilder je Verwandlung (Stab -> Figur)
R2 = 12          # Pixel je Einheit für die Abstandsfelder


def zwischenbilder(barp, canvas):
    """Weiche Verwandlung: Abstandsfelder von Stab und Figur werden überblendet (keine verdrehten Umrisse wie bei
    Punkt-zu-Punkt-Morphs). Ergebnis: K Pfade von t = 0 (Stab) bis t = 1 (Figur)."""
    W, H = int((X1 - X0) * R2), int((Y1 - Y0) * R2)
    fig = (cv2.resize(canvas, (W, H), interpolation=cv2.INTER_AREA) > 127).astype(np.uint8)
    bar = np.zeros((H, W), np.uint8)
    cv2.fillPoly(bar, [np.round(np.array([((x - X0) * R2, (y - Y0) * R2) for x, y in barp])).astype(np.int32)], 1)
    sd = lambda m: cv2.distanceTransform(1 - m, cv2.DIST_L2, 5) - cv2.distanceTransform(m, cv2.DIST_L2, 5)
    # Schwerpunkte (nur waagerecht) auf eine Linie legen, damit sich die Formen beim Überblenden immer überlagern;
    # der überblendete Umriss wandert dann mit t vom Schwerpunkt des Stabs zu dem der Figur (Gurtansatz oben bleibt bei y = 8)
    cxa = np.nonzero(bar)[1].mean(); cxb = np.nonzero(fig)[1].mean()
    def shift(m, dx):
        M = np.float32([[1, 0, dx], [0, 1, 0]]); return cv2.warpAffine(m, M, (W, H), flags=cv2.INTER_NEAREST)
    frames = []
    for i in range(K):
        t = i / (K - 1)
        cx = (1 - t) * cxa + t * cxb                       # gemeinsame Mitte dieses Bildes
        sa = sd(shift(bar, cx - cxa)); sb = sd(shift(fig, cx - cxb))
        f = (1 - t) * sa + t * sb
        up = cv2.resize(f, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        m = (up < 0).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, disk(2))
        # Gurtansatz bleibt am Stab: ein Band von der Oberkante bis zur Form hält sie fest (Breite von Stab zu Gurt)
        n_, lab, st, _ = cv2.connectedComponentsWithStats((m > 0).astype(np.uint8))
        if n_ > 1:
            big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])); ytop = st[big, cv2.CC_STAT_TOP]
            wb = BAND + (9.0 - BAND) * (1 - t) ** 2
            xa, xb = int((ANCHOR[0] - wb / 2 - X0) * 2 * R2), int((ANCHOR[0] + wb / 2 - X0) * 2 * R2)
            m[0:ytop + 2 * R2, max(0, xa):xb] = 255
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, disk(10))
        cs, hi = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        d = ""
        for c in cs:
            if len(c) < 12 or cv2.contourArea(c) < 6: continue
            c = c[:, 0, :].astype(float); sg = 4.0; half = int(sg * 3)
            ker = np.exp(-0.5 * (np.arange(-half, half + 1) / sg) ** 2); ker /= ker.sum()
            ext = np.concatenate([c[-half:], c, c[:half]])
            sm = np.stack([np.convolve(ext[:, j], ker, mode="valid") for j in range(2)], 1)
            ap = cv2.approxPolyDP(sm.astype(np.float32)[:, None, :], 0.5, True)[:, 0, :]
            if len(ap) < 3: continue
            d += "M" + "L".join(f"{x / (2 * R2) + X0:.2f} {y / (2 * R2) + Y0:.2f}" for x, y in ap) + "Z"
        frames.append(d)
    return frames


if __name__ == "__main__":
    out, canvases = [], []
    for p in FIGUREN:
        f = person(p)
        s, L = fit(p, f)
        canvas = build(p, f, s, L); canvases.append(canvas)
        d, bb = vectorise(canvas)
        out.append(d)
        print(p["ref"], "Maßstab", round(s, 4), "L", round(L, 1), "Rahmen", tuple(round(float(v), 1) for v in bb), "Länge", len(d))
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
    data = {"bar": bar, "figs": [flat(f) for f in figs], "frames": [zwischenbilder(barp, c) if k in (0, len(canvases) - 1) else None for k, c in enumerate(canvases)]}
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

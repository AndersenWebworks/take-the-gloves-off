"""Körper aus anatomisch geformten Segmenten (Abstandsfelder mit weicher Vereinigung) für die Luftartistik-Figuren.
Koordinaten sind Zeichen-Einheiten (Bildmarke x 21.5-78.5, y 8-92; y wächst nach unten). Proportionen (Erwachsene,
Silhouette von vorn/seitlich): Kopf ca. 1/7,5 der Körperlänge, Schulterbreite ca. 0,25 H, Oberschenkel/Unterschenkel
je ca. 0,245 H, Oberarm 0,165 H, Unterarm 0,15 H. Glieder verjüngen sich mit Muskelbauch, Gelenke sind schmal.
"""
import numpy as np


HEAD = 1.2        # Kopf etwas größer (Körperlänge : Kopf etwa 1 : 6,5 wie bei den alten Figuren)
TORSO = 1.2       # Rumpfbreite
RUMPF_F = 1.0     # Faktor auf die Rumpfbreite (nur für einzelne Posen verändert)
OSCHENKEL_F = 1.0 # Faktor auf Oberschenkel und Hosenbein
GIRTH = 1.32      # Gliedmaßen und Rumpf etwas kräftiger als der Durchschnitt (Artistenkörper, Wucht wie die alten Figuren)


def smin(a, b, k):
    """weiches Minimum (polynomial): k ist der Mischradius"""
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def _S(u):
    u = np.clip(u, 0, 1)
    return u * u * (3 - 2 * u)


def limb(X, Y, A, B, r0, rb, r1, tb=0.35):
    """sich verjüngende Kapsel von A nach B: Radius r0 -> Muskelbauch rb bei tb -> r1"""
    A = np.array(A, float); B = np.array(B, float); d = B - A; L2 = float(d @ d)
    t = np.clip(((X - A[0]) * d[0] + (Y - A[1]) * d[1]) / L2, 0, 1)
    px, py = A[0] + t * d[0], A[1] + t * d[1]
    dist = np.hypot(X - px, Y - py)
    r = np.where(t < tb, r0 + (rb - r0) * _S(t / tb), rb + (r1 - rb) * _S((t - tb) / (1 - tb)))
    return dist - r * GIRTH


def ell(X, Y, c, rx, ry, ang=0.0):
    """Ellipse (Näherung des Abstandsfeldes), ang in Grad, im Uhrzeigersinn auf dem Bild"""
    a = np.deg2rad(ang); ca, sa = np.cos(a), np.sin(a)
    dx, dy = X - c[0], Y - c[1]
    u, v = dx * ca + dy * sa, -dx * sa + dy * ca
    k = np.sqrt((u / rx) ** 2 + (v / ry) ** 2)
    return (k - 1) * min(rx, ry) * 0.9 + np.minimum(0, 0)


def cut(X, Y, A, B, r):
    """Hosenbein: oben gerundet, am Saum flach"""
    A = np.array(A, float); B = np.array(B, float); d = B - A; L = float(np.hypot(*d)); n = d / L
    al = (X - A[0]) * n[0] + (Y - A[1]) * n[1]
    pe = np.abs(-(X - A[0]) * n[1] + (Y - A[1]) * n[0])
    dist = np.where(al < 0, np.hypot(X - A[0], Y - A[1]), pe)
    return np.maximum(dist - r * GIRTH, al - L)


def limbp(X, Y, A, B, prof):
    """Kapsel mit frei vorgegebenem Radiusverlauf prof = [(t, r), ...]; Verlauf wird geglättet"""
    A = np.array(A, float); B = np.array(B, float); d = B - A; L2 = float(d @ d)
    tt = np.linspace(0, 1, 201); rr = np.interp(tt, [p[0] for p in prof], [p[1] for p in prof])
    k = np.exp(-0.5 * (np.arange(-12, 13) / 6.0) ** 2); k /= k.sum()
    rr = np.convolve(np.pad(rr, 12, mode="edge"), k, mode="valid")
    t = np.clip(((X - A[0]) * d[0] + (Y - A[1]) * d[1]) / L2, 0, 1)
    dist = np.hypot(X - (A[0] + t * d[0]), Y - (A[1] + t * d[1]))
    return dist - np.interp(t, tt, rr) * GIRTH


def kopf(X, Y, c, ang=0.0, w=2.85, h=3.65, haar=1.0, haardir=1.0):
    """leicht ovaler Schädel mit Kiefer- und Hinterkopfandeutung, Haare als ruhige, etwas asymmetrische Masse"""
    a = np.deg2rad(ang); ca, sa = np.cos(a), np.sin(a)
    def P(dx, dy): return (c[0] + dx * ca - dy * sa, c[1] + dx * sa + dy * ca)   # Kopf-Koordinaten -> Bild
    sk = ell(X, Y, P(0, -0.25), w, h, ang)                       # Schädel
    kf = ell(X, Y, P(0.25 * haardir, 1.85), w * 0.74, h * 0.52, ang)   # Kiefer
    d = smin(sk, kf, 0.9)
    if haar:
        m1 = ell(X, Y, P(-0.35 * haardir, -1.05), w * 1.12, h * 0.78, ang)   # Haarmasse oben/hinten
        m2 = ell(X, Y, P(-1.45 * haardir, 0.3), w * 0.62, h * 0.62, ang)      # Nackenhaar
        m3 = ell(X, Y, P(0.9 * haardir, -2.3), w * 0.62, h * 0.38, ang)       # Stirnlocke
        hr = smin(smin(m1, m2, 0.8), m3, 0.6)
        d = smin(d, hr * 1.0 + 0.0, 0.9)
    return d


def hand_offen(X, Y, W, ang, laenge=5.2):
    """locker hängende Hand: Handgelenk, Handteller, auslaufende Finger als eine Form, Daumenandeutung"""
    a = np.deg2rad(ang); d = np.array([np.sin(a), np.cos(a)]); n = np.array([-d[1], d[0]])
    W = np.array(W, float)
    pal = limb(X, Y, W, W + d * laenge * 0.5, 0.78, 1.32, 1.25, 0.55)
    fing = limb(X, Y, W + d * laenge * 0.4, W + d * laenge, 1.2, 1.05, 0.38, 0.5)
    dau = limb(X, Y, W + d * laenge * 0.18 + n * 0.8, W + d * laenge * 0.62 + n * 1.5, 0.55, 0.52, 0.28, 0.5)
    return smin(smin(pal, fing, 0.55), dau, 0.35)


def faust(X, Y, G, ang=0.0, W=None):
    """geschlossene Hand am Gurt: Kapsel in Richtung des Unterarms, Daumenwulst"""
    G = np.array(G, float)
    d = np.array([0.0, -1.0]) if W is None else (G - np.array(W, float)) / max(1e-6, np.hypot(*(G - np.array(W, float))))
    n = np.array([-d[1], d[0]])
    f = limb(X, Y, G - d * 1.3, G + d * 1.15, 1.0, 1.35, 1.15, 0.5)
    th = ell(X, Y, tuple(G - d * 0.1 + n * 1.0), 0.62, 1.0, np.degrees(np.arctan2(-d[0], d[1])) if False else 0.0)
    return smin(f, th, 0.4)


def fuss_gestreckt(X, Y, K, ang, laenge=8.2):
    """gestreckter Fuß (Spann in Verlängerung des Beins), K = Knöchel, ang = Richtung des Fußes"""
    a = np.deg2rad(ang); d = np.array([np.sin(a), np.cos(a)]); n = np.array([-d[1], d[0]])
    K = np.array(K, float)
    ferse = ell(X, Y, tuple(K - d * 0.3 - n * 0.35), 1.35, 1.75, np.rad2deg(a))
    spann = limb(X, Y, K, K + d * laenge * 0.6, 1.2, 1.2, 0.95, 0.5)
    zehen = limb(X, Y, K + d * laenge * 0.5, K + d * laenge, 1.0, 0.8, 0.3, 0.5)
    return smin(smin(ferse, spann, 0.5), zehen, 0.45)


# ------------------------------------------------------------------ Bausteine für ganze Körper
def achse(P0, P1):
    t = np.array(P1, float) - np.array(P0, float); t /= np.hypot(*t)
    return float(np.degrees(np.arctan2(-t[0], t[1])))


def arm(X, Y, S, E, W, offen_ang=None, G=None, faust_ang=0.0, r=(2.05, 2.15, 1.25, 1.3, 1.5, 0.78)):
    d = smin(limb(X, Y, S, E, r[0], r[1], r[2], 0.32), limb(X, Y, E, W, r[3], r[4], r[5], 0.28), 0.5)
    if G is not None: d = smin(d, faust(X, Y, G, faust_ang, W=W), 0.4)
    else: d = smin(d, hand_offen(X, Y, W, offen_ang), 0.45)
    return smin(d, ell(X, Y, S, 2.2, 2.4), 1.0)             # Schulterkappe


def bein(X, Y, Hh, K, A, fuss_ang, hose=True, fuss=True):
    th = limb(X, Y, Hh, K, 3.35 * OSCHENKEL_F, 3.6 * OSCHENKEL_F, 2.0, 0.3)
    sh = limb(X, Y, K, A, 2.0, 2.3, 1.08, 0.3)
    d = smin(th, sh, 0.5)
    if hose:
        Hh_, K_ = np.array(Hh, float), np.array(K, float)
        end = Hh_ + (K_ - Hh_) * 0.42
        d = smin(d, cut(X, Y, Hh_, end, 3.5 * OSCHENKEL_F), 0.3)
    if fuss: d = smin(d, fuss_gestreckt(X, Y, A, fuss_ang), 0.45)
    return smin(d, ell(X, Y, Hh, 3.5 * OSCHENKEL_F, 3.5 * OSCHENKEL_F), 1.2)


def rumpf(X, Y, hals, SL, SR, brust, taille, becken, HL, HR, breit=5.1, tail=3.9, beck=4.7, tr=2.0, schulter=5.4):
    """Rumpf: V-förmig (breite Schulterpartie, Taille, Becken), Trapezius läuft breit in den Hals"""
    F = RUMPF_F
    d = limbp(X, Y, hals, becken, [(0, 2.6), (0.10, schulter * 0.92 * TORSO / GIRTH * F), (0.28, breit * TORSO / GIRTH * F), (0.55, tail * TORSO / GIRTH * F), (0.80, ((tail + beck) / 2 + .3) * TORSO / GIRTH * F), (1.0, beck * TORSO / GIRTH * F)])
    d = smin(d, limb(X, Y, hals, SL, tr + .3, tr * .95, 2.0, .5), 1.6)
    d = smin(d, limb(X, Y, hals, SR, tr + .3, tr * .95, 2.0, .5), 1.6)
    return d


def hals_kopf(X, Y, hals, kopfc, ang, haar=1.0, hd=1.0):
    n = limb(X, Y, hals, kopfc, 1.9, 1.5, 1.5, 0.5)
    return smin(n, kopf(X, Y, kopfc, ang, haar=haar, haardir=hd), 0.9)


def kopf_profil(X, Y, c, ang=0.0, f=1.0, haar=1.0, nase=1.0):
    """Kopf im Profil/Dreiviertelprofil: Schädel, Stirn, Nase, Lippen, Kinn, Kiefer; Haare als ruhige, leicht
    gewellte Masse hinten/oben (Locken wie in den Referenzen). ang in Grad (im Uhrzeigersinn), f = +1 Blick nach +x'."""
    a = np.deg2rad(ang); ca, sa = np.cos(a), np.sin(a)
    P = lambda dx, dy: (c[0] + (dx * ca - dy * sa) * HEAD, c[1] + (dx * sa + dy * ca) * HEAD)
    sk = ell(X, Y, P(-0.2 * f, -0.3), 2.85 * HEAD, 3.45 * HEAD, ang)
    stirn = ell(X, Y, P(1.35 * f, -0.7), 1.7 * HEAD, 2.0 * HEAD, ang)
    nase = limb(X, Y, P(2.3 * f, 0.15), P((2.3 + 1.85 * nase) * f, 0.15 + 1.2 * nase), 0.62 * HEAD, 0.5 * HEAD, 0.18, 0.4)
    lippe = ell(X, Y, P(2.45 * f, 2.05), 0.75 * HEAD, 0.6 * HEAD, ang)
    kinn = ell(X, Y, P(2.0 * f, 3.0), 1.25 * HEAD, 1.25 * HEAD, ang)
    kiefer = ell(X, Y, P(0.3 * f, 2.25), 2.2 * HEAD, 1.7 * HEAD, ang)
    d = smin(smin(sk, stirn, 0.7), smin(kiefer, kinn, 0.5), 0.7)
    d = smin(smin(d, nase, 0.3), lippe, 0.3)
    if haar:
        h1 = ell(X, Y, P(-1.0 * f, -1.5), 3.25 * HEAD * haar, 2.9 * HEAD * haar, ang)
        h2 = ell(X, Y, P(-2.5 * f, 0.9), 1.3 * HEAD * haar, 2.1 * HEAD * haar, ang)
        d = smin(d, smin(h1, h2, 0.8), 0.7)
        for lx, ly, lr in [(-3.2, -0.3, 1.25), (-2.9, -2.4, 1.35), (-1.0, -3.9, 1.35), (1.3, -3.6, 1.15), (-3.1, 2.0, 1.1), (-2.0, 3.3, 0.9)]:
            d = smin(d, ell(X, Y, P(lx * f * haar, ly * (1 if ly > 0 else haar)), lr * HEAD * haar, lr * HEAD * haar, 0), 0.55)               # Locken: sanfte Wellen im Umriss
    return d


# ------------------------------------------------------------------ Posen (Einheiten des Zeichens)
def hk(X, Y, hals, c, ang, f, haar=1.0, nase=1.0):
    n = limb(X, Y, hals, c, 2.0, 1.6, 1.55, 0.5)
    return smin(n, kopf_profil(X, Y, c, ang, f, haar, nase), 1.0)


def pose_c(X, Y, schlank=True):
    """einarmiges Hängen: ein Arm zieht (Ellbogen nach außen), Rumpf verdreht, ein Knie angezogen, freier Arm schwingt aus"""
    global RUMPF_F, OSCHENKEL_F, HEAD
    G = (50.0, 19.0)
    f0 = (RUMPF_F, OSCHENKEL_F, HEAD)
    if schlank: RUMPF_F, OSCHENKEL_F, HEAD = 0.91, 0.91, HEAD * 0.92   # v7: Rumpf und Oberschenkel 9 % schmaler, Kopf 8 % kleiner
    S1, S2 = (50.8, 33.2), (44.0, 36.4)
    d = arm(X, Y, S1, (57.0, 27.2), (50.3, 21.6), G=G, faust_ang=0)
    d = smin(d, arm(X, Y, S2, (38.4, 43.0), (35.4, 50.6), offen_ang=-16), 0.3)
    t = rumpf(X, Y, (47.4, 33.0), S2, S1, (47.8, 39.8), (47.9, 46.6), (48.3, 51.4), (46.3, 52.2), (50.4, 51.7), breit=4.5, tail=3.5, beck=4.4, schulter=4.6)
    d = smin(d, t, 1.0)
    d = smin(d, hk(X, Y, (47.4, 33.0), (44.6, 26.8), -22, -1, haar=0.78, nase=1.3), 1.0)
    d = smin(d, bein(X, Y, (50.4, 51.7), (53.4, 64.2), (55.0, 76.2), 6), 1.2)
    d = smin(d, bein(X, Y, (46.3, 52.2), (40.2, 60.4), (43.6, 72.8), 8), 1.2)
    RUMPF_F, OSCHENKEL_F, HEAD = f0
    return d, [G]


def pose_b(X, Y):
    """kopfüber, ein Fuß im Gurt eingehakt, das andere Bein angewinkelt, Arme hängen nach unten"""
    G = (50.2, 19.0)
    d = limb(X, Y, (50.2, 15.4), (50.2, 22.8), 1.15, 1.2, 1.1, 0.5)                    # Fuß im Gurt (Spann nach oben)
    d = smin(d, bein(X, Y, (52.0, 48.8), (50.9, 35.6), (50.2, 22.8), 180, hose=False, fuss=False), 1.0)
    t = rumpf(X, Y, (48.6, 69.0), (53.4, 68.0), (44.2, 67.0), (48.9, 64.2), (49.4, 58.2), (49.9, 52.5), (52.0, 48.8), (47.6, 49.8), breit=4.7, tail=3.6, beck=4.5, schulter=4.9)
    d = smin(d, t, 1.0)
    d = smin(d, hk(X, Y, (48.6, 69.0), (47.6, 75.2), 180 + 12, 1), 1.0)
    d = smin(d, arm(X, Y, (53.4, 68.0), (59.4, 75.0), (64.0, 82.0), offen_ang=32), 0.3)
    d = smin(d, arm(X, Y, (44.2, 67.0), (41.0, 76.0), (38.8, 83.4), offen_ang=-12), 0.3)
    d = smin(d, bein(X, Y, (47.6, 49.8), (36.6, 54.0), (36.0, 66.5), 4), 1.2)
    return d, [G]


def pose_a(X, Y):
    """Hängen an beiden Händen im Klimmzug, asymmetrisch: Ellbogen nach außen, Kopf zwischen den Fäusten, ein Knie leicht gebeugt"""
    G1, G2 = (43.4, 20.4), (56.8, 18.8)
    SL, SR = (45.8, 33.8), (54.2, 32.2)
    d = arm(X, Y, SL, (38.6, 29.6), (43.6, 23.0), G=G1, faust_ang=0)
    d = smin(d, arm(X, Y, SR, (61.2, 27.2), (56.6, 20.6), G=G2, faust_ang=0), 0.3)
    t = rumpf(X, Y, (50.0, 31.8), SL, SR, (50.0, 38.8), (50.4, 45.6), (50.8, 50.6), (48.4, 51.2), (52.9, 50.8), breit=4.7, tail=3.7, beck=4.5, schulter=4.9)
    d = smin(d, t, 1.0)
    d = smin(d, hk(X, Y, (50.0, 31.8), (49.4, 26.2), -8, 1), 1.0)
    d = smin(d, bein(X, Y, (48.4, 51.2), (46.0, 63.4), (47.6, 74.8), -3), 1.2)
    d = smin(d, bein(X, Y, (52.9, 50.8), (54.6, 63.0), (54.0, 75.4), 6), 1.2)
    return d, [G1, G2]


POSEN = {"a": pose_a, "b": pose_b, "c": pose_c}
POSEN_REF = {"c": lambda X, Y: pose_c(X, Y, schlank=False)}   # Maße für Maßstab und Lage stammen von der v6-Fassung, damit Höhe und Handposition gleich bleiben


def pose_skaliert(name, X, Y, unten=89.0, links=31.8, rechts=68.2, zentrum=(50.0, 19.0), q=1.0):
    """Pose um den Gurtpunkt vergrößern, bis sie den Zwischenraum füllt (nichts berührt einen Stab), mit Faktor q verkleinern
    und dann senkrecht so verschieben, dass der tiefste Punkt bei `unten` liegt. Die Gurte werden dadurch länger."""
    f = POSEN[name]
    xs, ys = np.meshgrid(np.arange(links - 12, rechts + 12, 0.25), np.arange(8, 120, 0.25))
    d0, _ = POSEN_REF.get(name, f)(xs, ys)
    m = d0 < 0
    cx, cy = zentrum
    Z = min((unten - cy) / (ys[m].max() - cy), (cx - links) / (cx - xs[m].min()), (rechts - cx) / (xs[m].max() - cx)) * q
    dy = unten - (cy + (ys[m].max() - cy) * Z)
    d, grips = f(cx + (X - cx) / Z, cy + (Y - dy - cy) / Z)
    return d * Z, [(cx + (g[0] - cx) * Z, cy + (g[1] - cy) * Z + dy) for g in grips], Z

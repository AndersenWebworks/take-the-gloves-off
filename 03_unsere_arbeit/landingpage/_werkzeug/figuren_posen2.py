"""Frei gezeichnete Luftartistik-Figuren (v10): schlanke, ruhige Silhouetten aus verjüngten Gliedern (Abstandsfelder).
Koordinaten in Zeichen-Einheiten (x 21.5-78.5, y 8-92, y nach unten), Gurtansatz (50, 8).
pose(name, X, Y) -> (d, bands): d < 0 ist Körper; bands = [(A, B, breite), ...] gerade Gurtbänder (der Ansatz oben wird verlängert).
"""
import numpy as np

def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.minimum(a, b) - h * h * k * 0.25

def cap(X, Y, A, B, ra, rb):
    A = np.array(A, float); B = np.array(B, float); d = B - A; L2 = float(d @ d)
    t = np.clip(((X - A[0]) * d[0] + (Y - A[1]) * d[1]) / L2, 0, 1)
    return np.hypot(X - (A[0] + t * d[0]), Y - (A[1] + t * d[1])) - (ra + (rb - ra) * t)

def chain(X, Y, pts, rs, k=0.7):
    """Glieder entlang pts mit Radien rs; Übergänge weich"""
    d = None
    for i in range(len(pts) - 1):
        c = cap(X, Y, pts[i], pts[i + 1], rs[i], rs[i + 1])
        d = c if d is None else smin(d, c, k)
    return d

def ell(X, Y, c, rx, ry, ang=0.0):
    a = np.deg2rad(ang); ca, sa = np.cos(a), np.sin(a)
    dx, dy = X - c[0], Y - c[1]
    u, v = dx * ca + dy * sa, -dx * sa + dy * ca
    return (np.sqrt((u / rx) ** 2 + (v / ry) ** 2) - 1) * min(rx, ry)

def kopf(X, Y, c, ang=0.0, s=1.0, dirn=1.0):
    """Kopf: Schädel (leicht oval), Kinn/Kiefer weicher, kleiner Haarknoten; dirn = Blickrichtung +1 rechts / -1 links (in Kopfkoordinaten, ang dreht)"""
    a = np.deg2rad(ang); ca, sa = np.cos(a), np.sin(a)
    P = lambda dx, dy: (c[0] + (dx * ca - dy * sa) * s, c[1] + (dx * sa + dy * ca) * s)
    sk = ell(X, Y, P(0, -0.2), 3.0 * s, 3.5 * s, ang)
    kf = ell(X, Y, P(0.5 * dirn, 1.7), 2.1 * s, 1.9 * s, ang)
    nase = cap(X, Y, P(2.5 * dirn, 0.3), P(3.3 * dirn, 0.9), 0.5 * s, 0.35 * s)
    kn = ell(X, Y, P(-1.9 * dirn, -1.9), 1.7 * s, 1.6 * s, ang)           # Haarknoten hinten oben
    d = smin(sk, kf, 0.9 * s)
    d = smin(d, nase, 0.5 * s)
    d = smin(d, kn, 0.7 * s)
    return d

def hals(X, Y, a, b, r=1.45):
    return cap(X, Y, a, b, r, r * 1.05)

def fuss(X, Y, knoechel, zeh, r=1.15):
    return smin(cap(X, Y, knoechel, zeh, r, r * 0.55), ell(X, Y, knoechel, r * 1.25, r * 1.45), 0.4)

def faust(X, Y, c, r=1.5):
    return ell(X, Y, c, r, r * 1.2)

def bein(X, Y, h, k, a, z, r_h=3.0, r_k=1.95, r_w=2.15, r_a=1.1, fr=1.15):
    """Hüfte h, Knie k, Knöchel a, Zeh z; Oberschenkel, Wade mit leichtem Bauch, Fuß"""
    th = cap(X, Y, h, k, r_h, r_k)
    km = (np.array(k) * 0.62 + np.array(a) * 0.38)
    wa = smin(cap(X, Y, k, km, r_k, r_w), cap(X, Y, km, a, r_w, r_a), 0.9)
    d = smin(th, wa, 0.6)
    return smin(d, fuss(X, Y, a, z, fr), 0.5)

def arm(X, Y, s, e, w, hand, r_s=1.9, r_e=1.35, r_w=1.0):
    d = smin(cap(X, Y, s, e, r_s, r_e), cap(X, Y, e, w, r_e * 1.04, r_w), 0.5)
    if hand is not None:
        h = np.array(hand, float); w_ = np.array(w, float)
        dd = h - w_; n = dd / np.hypot(*dd)
        d = smin(d, cap(X, Y, w_, w_ + dd * 0.55, r_w * 1.05, r_w * 1.35), 0.4)
        d = smin(d, cap(X, Y, w_ + dd * 0.4, h, r_w * 1.25, r_w * 0.5), 0.4)
    return d

def rumpf(X, Y, pts, rs, k=1.2):
    return chain(X, Y, pts, rs, k)

# ---------------------------------------------------------------------------------------------------------
def pose_K(X, Y):
    """kopfüber, ein Fuß im Gurt eingehakt, das andere Bein im Vierer angewinkelt, Arme hängen"""
    ank = (50.0, 26.5)
    d = bein(X, Y, (51.6, 55.5), (49.4, 41.0), ank, (50.0, 20.6), r_h=3.9, r_k=2.0, r_w=2.5, r_a=1.05)
    d = smin(d, ell(X, Y, (50.0, 24.2), 2.1, 1.5), 0.4)                     # Gurtwicklung um den Knöchel
    t = chain(X, Y, [(51.6, 55.0), (51.6, 61.0), (52.0, 65.5), (52.2, 70.0)], [4.4, 3.3, 3.8, 4.8], 1.6)
    d = smin(d, t, 1.2)
    d = smin(d, hals(X, Y, (52.6, 70.0), (54.2, 76.0), 1.65), 0.8)
    d = smin(d, kopf(X, Y, (55.8, 81.6), 180 - 20, 1.12, 1.0), 0.5)
    d = smin(d, bein(X, Y, (49.6, 54.0), (38.4, 52.4), (36.4, 63.5), (35.0, 69.2), r_h=3.5, r_k=2.0, r_w=2.3, r_a=1.1), 1.0)
    d = smin(d, arm(X, Y, (48.8, 68.6), (43.6, 76.0), (42.6, 83.4), (42.8, 88.4), r_s=2.0, r_e=1.5, r_w=1.1), 0.5)
    d = smin(d, arm(X, Y, (55.4, 68.4), (60.8, 71.6), (64.6, 73.8), (67.0, 74.8), r_s=2.0, r_e=1.5, r_w=1.1), 0.5)
    return d, [((50.0, 8.0), (50.0, 24.0), 1.8)]

def pose_G(X, Y):
    """zusammengekrümmt in der Gurtschlaufe: sitzend, Rumpf nach vorn gebeugt, Stirn auf den Knien, Arme um die Schienbeine"""
    H = (48.6, 65.6)
    d = chain(X, Y, [H, (50.2, 58.5), (53.6, 52.4), (55.6, 50.4)], [4.0, 3.5, 4.1, 3.6], 1.6)
    d = smin(d, hals(X, Y, (55.4, 50.6), (57.8, 52.6), 1.7), 0.8)
    d = smin(d, kopf(X, Y, (60.0, 56.2), 62, 1.05, 1.0), 0.4)
    d = smin(d, bein(X, Y, H, (61.6, 68.4), (59.8, 82.6), (63.8, 88.2), r_h=3.7, r_k=2.2, r_w=2.4, r_a=1.1), 0.9)
    d = smin(d, arm(X, Y, (52.8, 55.0), (54.6, 63.4), (60.4, 67.0), (63.2, 69.6), r_s=2.0, r_e=1.5, r_w=1.1), 0.4)
    d = smin(d, ell(X, Y, (45.3, 66.2), 1.7, 1.7), 0.6)                                # Schlaufenrand rund
    return d, [((50.0, 8.0), (45.0, 65.0), 1.8), ((50.0, 8.0), (56.4, 68.6), 1.8), ((45.0, 66.8), (56.4, 69.6), 1.8, False)]

def pose_F(X, Y):
    """an beiden Fäusten hängend, Ellbogen nach außen, Kopf sinkt nach vorn zwischen die Arme, schlank"""
    G1, G2 = (43.6, 23.0), (56.4, 23.0)
    d = arm(X, Y, (46.2, 40.4), (41.6, 33.4), (43.5, 24.6), None, r_s=2.3, r_e=1.65, r_w=1.2)
    d = smin(d, faust(X, Y, G1), 0.4)
    d = smin(d, arm(X, Y, (53.8, 40.4), (58.4, 33.4), (56.5, 24.6), None, r_s=2.3, r_e=1.65, r_w=1.2), 0.4)
    d = smin(d, faust(X, Y, G2), 0.4)
    d = smin(d, cap(X, Y, (46.2, 40.4), (53.8, 40.4), 2.7, 2.7), 0.8)                 # Schulterlinie
    t = chain(X, Y, [(50.0, 41.0), (50.0, 46.0), (50.1, 52.5), (50.2, 58.0)], [4.4, 3.6, 2.9, 3.4], 1.6)
    d = smin(d, t, 1.2)
    d = smin(d, hals(X, Y, (50.0, 39.8), (50.3, 36.6), 1.75), 0.6)
    d = smin(d, kopf(X, Y, (50.3, 33.8), 14, 1.1, 1.0), 0.5)
    d = smin(d, bein(X, Y, (48.6, 58.0), (47.0, 71.8), (46.4, 83.6), (46.0, 88.8), r_h=3.0, r_k=2.0, r_w=2.35, r_a=1.05), 0.8)
    d = smin(d, bein(X, Y, (51.6, 58.0), (55.6, 69.4), (51.4, 78.6), (51.0, 84.2), r_h=3.0, r_k=2.0, r_w=2.35, r_a=1.05), 0.8)
    return d, [((50.0, 8.0), G1, 1.8), ((50.0, 8.0), G2, 1.8)]

def pose_E(X, Y):
    """einarmig hängend: ein Arm zieht (Ellbogen nach außen), Rumpf verdreht, Kopf im Profil nach links gesenkt, ein Knie angezogen, freier Arm schwingt aus"""
    G = (50.2, 20.6)
    d = arm(X, Y, (52.0, 36.6), (56.8, 30.0), (51.4, 23.2), None, r_s=2.5, r_e=1.8, r_w=1.3)
    d = smin(d, faust(X, Y, G), 0.4)
    d = smin(d, arm(X, Y, (45.4, 38.0), (39.8, 44.2), (36.6, 51.4), (35.4, 55.8), r_s=2.5, r_e=1.8, r_w=1.3), 0.4)
    d = smin(d, cap(X, Y, (45.4, 38.0), (52.0, 36.6), 2.6, 2.6), 0.8)                  # Schulterlinie, gedreht
    t = chain(X, Y, [(49.0, 39.0), (48.6, 45.0), (48.6, 51.0), (48.8, 57.0)], [4.8, 3.9, 3.2, 3.7], 1.6)
    d = smin(d, t, 1.2)
    d = smin(d, hals(X, Y, (48.8, 38.4), (48.0, 34.6), 1.75), 0.6)
    d = smin(d, kopf(X, Y, (47.4, 31.2), -14, 1.1, -1.0), 0.5)
    d = smin(d, bein(X, Y, (47.0, 56.6), (41.6, 66.6), (46.4, 74.6), (47.8, 80.2), r_h=3.5, r_k=2.1, r_w=2.45, r_a=1.1), 0.8)
    d = smin(d, bein(X, Y, (50.2, 56.6), (51.8, 71.8), (51.2, 83.2), (50.8, 88.8), r_h=3.5, r_k=2.1, r_w=2.45, r_a=1.1), 0.8)
    return d, [((50.0, 8.0), G, 1.8)]

POSEN2 = {"E": pose_E, "K": pose_K, "G": pose_G, "F": pose_F}


def canvas(name, X0=21.5, X1=78.5, Y0=8.0, Y1=92.0, RES=24, body=True):
    """Maske (uint8, 0/255) im Raster des Zeichens: Körper plus Gurtbänder"""
    import cv2
    W, H = int((X1 - X0) * RES), int((Y1 - Y0) * RES)
    Xg, Yg = np.meshgrid(X0 + (np.arange(W) + .5) / RES, Y0 + (np.arange(H) + .5) / RES)
    d, bands = POSEN2[name](Xg.astype(np.float32), Yg.astype(np.float32))
    out = ((d < 0) * 255).astype(np.uint8) if body else np.zeros((H, W), np.uint8)
    for bb in bands:
        a, b, w = bb[:3]; ext = bb[3] if len(bb) > 3 else True
        A = np.array([(a[0] - X0) * RES, (a[1] - Y0) * RES]); B = np.array([(b[0] - X0) * RES, (b[1] - Y0) * RES])
        v = B - A; v /= np.linalg.norm(v); n = np.array([-v[1], v[0]]) * w * RES / 2
        A2 = A - v * 3000 if ext else A
        cv2.fillPoly(out, [np.round(np.array([A2 + n, B + n, B - n, A2 - n])).astype(np.int32)], 255)
    if body:
        cs, hi = cv2.findContours(out, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        for c, h in zip(cs, hi[0]):
            if h[3] >= 0 and cv2.contourArea(c) < 1.5 * RES * RES: cv2.drawContours(out, [c], -1, 255, -1)
    return out

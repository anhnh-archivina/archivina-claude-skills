#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Chinh hinh polyline phong / duong bo can theo cac loi nguoi dung sua tay (CT1 tang 5A-10, 08/10/2026).

Quy tac (references/quy-uoc-mat-bang-tang.md, quyet dinh 11-17):
 1-2 cat_kinh   : o mo / vach kinh / khung cua so dat NGOAI mat phang tuong -> ranh theo duong keo dai mat tuong
                  qua dau tuong (vuong goc), bo phan loi ra kinh (sau <= 400 mm).
 3   don_dinh   : bo gai / khac nho (<= 60 mm) va vat cheo ngan o goc tuong 90 do; doan thang khong gap khuc.
 4   op_wc      : phong WC tru lop op 10 mm (theo net op neu da ve, neu khong lui 10 mm tu mat trat).
 5   dau_tuong  : canh nam tren net loi tuong (A-Wall/S-Wall, khong co net trat) = dau tuong gach chua ve trat -> lui 15 mm.
 6   dai_tuong  : duong bo can chi lap dai tuong GIUA hai mat phong doi dien (tuong ngan, o cua); khong lap goc lom
                  -> khong an vao tuong bao ngoai.
 7   bau_lo_gia : lo gia / ban cong do toi mat trong bau BT / lan can (net bau gan nhat phia ngoai, <= 80 mm).
Chi xu ly canh truc giao (mat bang CT1 vuong goc); canh xien giu nguyen.
"""
import math

import shapely
from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import split, unary_union

TOL = 2.0
LOP = {
    "trat": {"a-vua trat"},
    "tuong": {"a-wall", "s-wall", "a-column"},
    "bau": {"a_wall bt", "a-line", "a-lancan"},
    # kinh / khung cua / do (CT1: kinh ve tren A-Door, do cua so 'thanh dung' tren layer 4)
    "kinh": {"a-door", "a-cửa", "a-cua", "a-window", "a-glaz", "a-glass", "玻璃层", "kính", "kinh", "a-wall-g",
             "a-window-g", "nhom", "4"},
}


class NetNen:
    """Doan thang truc giao cua nen kien truc, phan lop trat / tuong / bau."""

    def __init__(self, segs):
        self.ds = {k: [] for k in LOP}
        for x1, y1, x2, y2, lop in segs:
            if abs(x1 - x2) <= 0.5 or abs(y1 - y2) <= 0.5:
                self.ds[lop].append((x1, y1, x2, y2))
        self.tree = {k: (shapely.STRtree([LineString([(a, b), (c, d)]) for a, b, c, d in v]) if v else None, v)
                     for k, v in self.ds.items()}

    def _cands(self, lops, g):
        for k in lops:
            t, v = self.tree[k]
            if t is not None:
                for i in t.query(g):
                    yield k, v[i]

    def ho_tro(self, a, b, lops, tol=TOL):
        """Chieu dai doan a-b nam tren net thuoc cac lop 'lops' (cung phuong, lech <= tol)."""
        doc = abs(a[0] - b[0]) < abs(a[1] - b[1])
        k0, k1 = (1, 0) if doc else (0, 1)          # k0: truc doc theo canh, k1: truc vuong goc
        lo, hi = sorted((a[k0], b[k0]))
        c = (a[k1] + b[k1]) / 2
        iv = []
        for _, s in self._cands(lops, LineString([a, b]).buffer(tol)):
            p, q = (s[0], s[1]), (s[2], s[3])
            if abs(p[k1] - c) > tol or abs(q[k1] - c) > tol:
                continue
            s0, s1 = sorted((p[k0], q[k0]))
            x0, x1 = max(lo, s0), min(hi, s1)
            if x1 > x0:
                iv.append((x0, x1))
        iv.sort()
        tong, cur = 0.0, None
        for x0, x1 in iv:
            if cur is None or x0 > cur[1]:
                if cur:
                    tong += cur[1] - cur[0]
                cur = [x0, x1]
            else:
                cur[1] = max(cur[1], x1)
        if cur:
            tong += cur[1] - cur[0]
        return tong

    def song_song(self, a, b, n, lops, dmin, dmax, ti_le=0.5):
        """Khoang cach toi cac net song song phia huong n (vector don vi) trong (dmin, dmax], phu >= ti_le canh."""
        doc = abs(a[0] - b[0]) < abs(a[1] - b[1])
        k0, k1 = (1, 0) if doc else (0, 1)
        lo, hi = sorted((a[k0], b[k0]))
        L = hi - lo
        c = (a[k1] + b[k1]) / 2
        sg = n[k1]
        vung = box(*(lambda xs, ys: (min(xs), min(ys), max(xs), max(ys)))(
            [a[0], b[0], a[0] + n[0] * dmax, b[0] + n[0] * dmax], [a[1], b[1], a[1] + n[1] * dmax, b[1] + n[1] * dmax]))
        phu = {}
        for _, s in self._cands(lops, vung):
            p, q = (s[0], s[1]), (s[2], s[3])
            if abs(p[k1] - q[k1]) > 0.5:
                continue
            d = (p[k1] - c) * sg
            if not (dmin < d <= dmax):
                continue
            s0, s1 = sorted((p[k0], q[k0]))
            ov = min(hi, s1) - max(lo, s0)
            if ov > 0:
                phu[round(d, 1)] = phu.get(round(d, 1), 0.0) + ov
        return sorted(d for d, v in phu.items() if v >= ti_le * L)

    def diem_dau(self, lops, g):
        out = []
        for _, s in self._cands(lops, g):
            out += [(s[0], s[1]), (s[2], s[3])]
        return out


# ---------------------------------------------------------------------------------------------------------------------
def _vong(poly):
    p = orient(poly, 1.0)
    return [tuple(c) for c in p.exterior.coords[:-1]]


def _poly(pts, ho=()):
    try:
        g = Polygon(pts, ho)
    except Exception:
        return None
    return g if g.is_valid and g.area > 0 else None


def _truc(a, b, tol=0.5):
    return abs(a[0] - b[0]) <= tol or abs(a[1] - b[1]) <= tol


def _kc_duong(v, p, n):
    """Khoang cach diem v toi duong thang p-n."""
    L = math.dist(p, n)
    if L < 1e-9:
        return math.dist(v, p)
    return abs((n[0] - p[0]) * (p[1] - v[1]) - (p[0] - v[0]) * (n[1] - p[1])) / L


def lam_thang(pts, tol=1.5):
    """Canh lech truc <= tol mm -> nan thang (dat lai toa do dinh sau)."""
    pts = [list(p) for p in pts]
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        if 0 < abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) > 10 * tol:
            b[0] = a[0]
        elif 0 < abs(a[1] - b[1]) <= tol and abs(a[0] - b[0]) > 10 * tol:
            b[1] = a[1]
    return [tuple(p) for p in pts]


def vuong_goc(poly, net=None, lech_max=40.0):
    """Loi 1 (do cheo): canh gan truc nhung lech 1,5-lech_max mm (do lam gon / noi dinh) -> bac vuong goc 2 doan,
    goc chon theo net nen (doan dai nam tren net tuong/trat/bau). Sua tung canh, moi lan kiem tra hinh hop le.
    Tra ve (poly, so_canh_sua)."""
    if poly is None or poly.is_empty:
        return poly, 0
    ho = [list(h.coords) for h in poly.interiors]
    pts = lam_thang(_vong(poly))
    g0 = _poly(pts, ho)
    if g0 is None:
        return poly, 0
    sua = 0
    i = 0
    while i < len(pts):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
        nho, lon = min(dx, dy), max(dx, dy)
        if 1.5 < nho <= lech_max and lon >= 3 * nho:
            c1, c2 = (a[0], b[1]), (b[0], a[1])
            if net is not None:
                s1 = net.ho_tro(a, c1, ("trat", "tuong", "bau")) + net.ho_tro(c1, b, ("trat", "tuong", "bau"))
                s2 = net.ho_tro(a, c2, ("trat", "tuong", "bau")) + net.ho_tro(c2, b, ("trat", "tuong", "bau"))
                thu = [c1, c2] if s1 >= s2 else [c2, c1]
            else:
                thu = [c1, c2] if dx < dy else [c2, c1]
            for c in thu:
                cand = pts[:i + 1] + [c] + pts[i + 1:]
                if _poly(cand, ho) is not None:
                    pts = cand
                    sua += 1
                    i += 1
                    break
        i += 1
    if not sua:
        return (g0, 0)
    g = _poly(pts, ho)
    return (g, sua) if g is not None else (poly, 0)


def don_dinh(poly, net=None, tol=60.0, cheo=120.0):
    """Loi 3: bo dinh thua, gai/khac <= tol mm, vat cheo ngan o goc vuong. Tra ve (poly, so_dinh_bo)."""
    if poly is None or poly.is_empty:
        return poly, 0
    ho = [list(h.coords) for h in poly.interiors]
    pts = lam_thang(_vong(poly))
    bo = 0
    doi = True
    while doi and len(pts) > 4:
        doi = False
        n = len(pts)
        for i in range(n):
            p, v, q = pts[i - 1], pts[i], pts[(i + 1) % n]
            # dinh thang hang / trung
            if math.dist(p, v) < 0.5 or _kc_duong(v, p, q) < 0.5:
                cand = pts[:i] + pts[i + 1:]
            # gai / khac 1 dinh: hai dinh ben canh cung truc, dinh lech <= tol
            elif _truc(p, q) and _kc_duong(v, p, q) <= tol and math.dist(p, q) > 1:
                cand = pts[:i] + pts[i + 1:]
            else:
                cand = None
            if cand is not None:
                g, g0 = _poly(cand, ho), _poly(pts, ho)
                if g is not None and (g0 is None or abs(g.area - g0.area) < max(tol * 400, 0.02 * g.area)):
                    pts, doi, bo = cand, True, bo + 1
                    break
        if doi:
            continue
        n = len(pts)
        for i in range(n):
            p, a, b, q = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
            # khac 2 dinh: p, q cung truc, a, b sat duong p-q
            if n > 5 and _truc(p, q) and _kc_duong(a, p, q) <= tol and _kc_duong(b, p, q) <= tol and math.dist(a, b) <= 2.5 * tol:
                idx = {i % n, (i + 1) % n}
                cand = [pts[k] for k in range(n) if k not in idx]
            # vat cheo ngan a-b giua hai canh truc giao
            elif not _truc(a, b, 1.0) and math.dist(a, b) <= cheo and _truc(p, a, 1.0) and _truc(b, q, 1.0):
                ngang_pa = abs(p[1] - a[1]) <= 1.0
                ngang_bq = abs(b[1] - q[1]) <= 1.0
                if ngang_pa != ngang_bq:                      # vuong goc -> giao diem
                    c = (b[0], a[1]) if ngang_pa else (a[0], b[1])
                else:                                         # song song -> bac vuong, chon goc bam net
                    c1, c2 = (b[0], a[1]), (a[0], b[1])
                    if net is not None:
                        s1 = net.ho_tro(a, c1, ("trat", "tuong", "bau")) + net.ho_tro(c1, b, ("trat", "tuong", "bau"))
                        s2 = net.ho_tro(a, c2, ("trat", "tuong", "bau")) + net.ho_tro(c2, b, ("trat", "tuong", "bau"))
                        c = c1 if s1 >= s2 else c2
                    else:
                        c = c1
                cand = [pts[k] for k in range(n) if k not in {i % n, (i + 1) % n}]
                cand.insert(i % n if i % n < len(cand) + 1 else len(cand), c)
            else:
                continue
            g, g0 = _poly(cand, ho), _poly(pts, ho)
            if g is not None and (g0 is None or abs(g.area - g0.area) < max(cheo * cheo, 0.02 * g.area)):
                pts, doi, bo = cand, True, bo + 1
                break
    g = _poly(pts, ho)
    return (g if g is not None else poly), bo


def _khong_ho_tro(poly, net, lops=("trat", "tuong", "bau")):
    """Cac canh cua poly khong nam tren net tuong/trat/bau (kinh, khung cua, doan dong o mo)."""
    pts = _vong(poly)
    out = []
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        L = math.dist(a, b)
        if L > 1 and _truc(a, b) and net.ho_tro(a, b, lops) < 0.5 * L:
            out.append((a, b))
    return out


def cat_kinh(poly, net, sau=400.0, ti_le=0.6, ti_le_kinh=0.3, dt_max=3.0e6):
    """Loi 1-2: cat phan loi ra kinh/khung cua nam ngoai duong keo dai mat tuong qua dau tuong.

    Duong cat: duong truc giao qua dau mut net tuong/trat gan canh kinh. Phan bi cat: sau <= 'sau', bien (tru duong cat)
    >= ti_le khong bam tuong/trat/bau VA >= ti_le_kinh bam net kinh/khung cua (de khong cat nham doan dong o mo).
    Moi vong chon phan cat nho nhat; canh moi tao ra (tren duong cat) coi nhu da bam net.
    """
    if poly is None or poly.is_empty:
        return poly, 0
    bo = 0
    da_cat = []
    for _ in range(12):
        kh = [e for e in _khong_ho_tro(poly, net) if net.ho_tro(e[0], e[1], ("kinh",), tol=8) > 0.3 * math.dist(*e)]
        if not kh:
            break
        vung = unary_union([LineString(e).buffer(sau + 50) for e in kh])
        diem = {(round(x, 1), round(y, 1)) for x, y in net.diem_dau(("trat", "tuong"), vung)}
        minx, miny, maxx, maxy = poly.bounds
        duong = set()
        for x, y in diem:
            if minx + 0.5 < x < maxx - 0.5:
                duong.add(("x", x))
            if miny + 0.5 < y < maxy - 0.5:
                duong.add(("y", y))
        tot = None
        for k, v in sorted(duong):
            L = LineString([(v, miny - 10), (v, maxy + 10)]) if k == "x" else LineString([(minx - 10, v), (maxx + 10, v)])
            try:
                pcs = list(split(poly, L).geoms)
            except Exception:
                continue
            if len(pcs) < 2:
                continue
            lon = max(pcs, key=lambda q: q.area)
            for q in pcs:
                if q is lon or q.area > dt_max or q.area < 100 or (tot is not None and q.area >= tot.area):
                    continue
                cs = list(q.exterior.coords)
                if max(L.distance(shapely.Point(c)) for c in cs) > sau:
                    continue
                tong = kht = kinh = 0.0
                for a, b in zip(cs, cs[1:]):
                    ln = math.dist(a, b)
                    sg = LineString([a, b])
                    if ln < 0.5 or sg.within(L.buffer(0.5)) or any(sg.within(c_.buffer(0.5)) for c_ in da_cat):
                        continue
                    tong += ln
                    if _truc(a, b):
                        kht += ln - net.ho_tro(a, b, ("trat", "tuong", "bau"))
                        kinh += min(ln, net.ho_tro(a, b, ("kinh",), tol=8))
                    else:
                        kht += ln
                if tong > 0 and kht >= ti_le * tong and kinh >= ti_le_kinh * tong:
                    tot, tot_L = q, L
        if tot is None:
            break
        g = poly.difference(tot.buffer(0.01, join_style=2))
        g = max(g.geoms, key=lambda q: q.area) if isinstance(g, MultiPolygon) else g
        poly = g.buffer(0)
        da_cat.append(tot_L)
        bo += 1
    return poly, bo


def doi_canh(poly, dich):
    """Doi tung canh vao trong mot doan dich[i] (am = ra ngoai); dinh moi = giao cua hai canh ke da doi.
    Canh xien / cong giu nguyen (dich 0). Tra ve poly moi hoac None neu hinh moi khong hop le."""
    pts = _vong(poly)
    n = len(pts)
    L_ = []
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        L = math.dist(a, b)
        if L < 1e-9:
            return None
        nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L      # phap tuyen trong (CCW)
        d = dich[i]
        L_.append(((a[0] + nx * d, a[1] + ny * d), ((b[0] - a[0]) / L, (b[1] - a[1]) / L)))
    moi = []
    for i in range(n):
        (p0, u0), (p1, u1) = L_[i - 1], L_[i]
        cr = u0[0] * u1[1] - u0[1] * u1[0]
        if abs(cr) < 1e-9:                                 # hai canh thang hang: lay diem dau canh i da doi
            moi.append(p1)
            continue
        t = ((p1[0] - p0[0]) * u1[1] - (p1[1] - p0[1]) * u1[0]) / cr
        moi.append((p0[0] + u0[0] * t, p0[1] + u0[1] * t))
    g = _poly(moi, [list(h.coords) for h in poly.interiors])
    if g is None or abs(g.area - poly.area) > 0.05 * poly.area:
        return None
    return g


def _phap_tuyen(a, b):
    L = math.dist(a, b)
    return (-(b[1] - a[1]) / L, (b[0] - a[0]) / L)


def op_wc(poly, net, op=10.0):
    """Loi 4: WC tru lop op. Canh nam tren mat trat/tuong ma chua co net op (net trat song song cach 6-14 mm phia ngoai)."""
    pts = _vong(poly)
    d = []
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        L = math.dist(a, b)
        if L < 1 or not _truc(a, b) or net.ho_tro(a, b, ("trat", "tuong")) < 0.5 * L:
            d.append(0.0)
            continue
        nin = _phap_tuyen(a, b)
        ra = (-nin[0], -nin[1])
        d.append(0.0 if net.song_song(a, b, ra, ("trat",), op - 4, op + 4) else op)
    if not any(d):
        return poly, 0
    g = doi_canh(poly, d)
    return (g, sum(1 for x in d if x)) if g is not None else (poly, 0)


def dau_tuong(poly, net, trat=15.0, dai_max=350.0):
    """Loi 5: MAT DAU TUONG (canh ngan <= dai_max) nam tren net loi tuong, khong co net trat -> lui trat mm.
    Mat tuong dai khong ve trat thi giu nguyen (quy tac 05/10/2026: khong ve trat thi khong lui)."""
    pts = _vong(poly)
    d = []
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        L = math.dist(a, b)
        d.append(trat if (1 <= L <= dai_max and _truc(a, b) and net.ho_tro(a, b, ("tuong",)) >= 0.5 * L
                          and net.ho_tro(a, b, ("trat",)) < 0.5 * L) else 0.0)
    if not any(d):
        return poly, 0
    g = doi_canh(poly, d)
    return (g, sum(1 for x in d if x)) if g is not None else (poly, 0)


def bau_lo_gia(poly, net, dmax=80.0):
    """Loi 7: canh lo gia keo ra mat trong bau BT / lan can gan nhat phia ngoai (<= dmax)."""
    pts = _vong(poly)
    d = []
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        L = math.dist(a, b)
        if L < 100 or not _truc(a, b) or net.ho_tro(a, b, ("bau",)) >= 0.5 * L:
            d.append(0.0)
            continue
        nin = _phap_tuyen(a, b)
        ds = net.song_song(a, b, (-nin[0], -nin[1]), ("bau",), 0.5, dmax)
        d.append(-ds[0] if ds else 0.0)
    if not any(d):
        return poly, 0
    g = doi_canh(poly, d)
    return (g, sum(1 for x in d if x)) if g is not None else (poly, 0)


def dai_tuong(polys, dmax):
    """Loi 6: dai chu nhat giua hai canh doi dien song song (cach <= dmax) cua cac vung -> tuong ngan / o cua."""
    E = []
    for g in polys:
        pts = _vong(g)
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            if math.dist(a, b) < 1 or not _truc(a, b, 0.5):
                continue
            n = _phap_tuyen(a, b)
            E.append((a, b, (-n[0], -n[1])))                  # phap tuyen ngoai
    U = unary_union(polys)
    rects = []
    for i, (a, b, n) in enumerate(E):
        for c, d, m in E[i + 1:]:
            if abs(n[0] + m[0]) > 1e-6 or abs(n[1] + m[1]) > 1e-6:
                continue
            k1 = 1 if abs(n[1]) > 0.5 else 0                  # truc vuong goc canh
            k0 = 1 - k1
            gap = (c[k1] - a[k1]) * n[k1]
            if not (0.5 < gap <= dmax):
                continue
            lo = max(min(a[k0], b[k0]), min(c[k0], d[k0]))
            hi = min(max(a[k0], b[k0]), max(c[k0], d[k0]))
            if hi - lo < 1:
                continue
            r = box(lo, min(a[1], c[1]), hi, max(a[1], c[1])) if k1 == 1 else box(min(a[0], c[0]), lo, max(a[0], c[0]), hi)
            if r.intersection(U).area > 0.02 * r.area:
                r = r.difference(U)                           # phan dai bi vung khac chen vao: bo phan do
                if r.is_empty:
                    continue
            rects.append(r)
    return rects


def lap_lo_nho(g, dt_max=0.15e6):
    if isinstance(g, MultiPolygon):
        return MultiPolygon([lap_lo_nho(q, dt_max) for q in g.geoms])
    return Polygon(g.exterior, [h for h in g.interiors if Polygon(h).area > dt_max])

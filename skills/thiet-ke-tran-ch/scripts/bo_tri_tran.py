#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Bo tri MOI thiet bi tran can ho (Archivina) THEO TRUC - skill thiet-ke-tran-ch (nguyen tac nguoi dung chot 05/10/2026).

Phong thuong (khach, an, bep, ngu, da nang, hanh lang, chua ro):
  - TRUC = 1 HINH CHU NHAT KHEP KIN cach mep trong tuong va mat khoi tu (tu bep, tu ao) 500-600 mm moi huong.
    Hinh chu nhat lay theo TUONG CHINH (canh dai nhat cua phong) va la hinh chu nhat lon nhat nam trong phong
    (da tru tu) -> tu dong bo cac hoc (hoc vao PN, hoc bep, sanh can). Phong qua hep: truc giua.
  - Phan phong ngoai hinh chu nhat: sat khoi tu bep -> TRUC BEP (giua, song song chieu dai bep, den 2 dau + giua
    neu > 2400); con lai (hoc sanh can, hoc sanh PN) -> 1 DEN TAI TAM HOC.
  - DEN: DUNG 4 GOC hinh chu nhat (ke ca phia dau giuong); canh dai hon 2400 thi them den o giua (chia deu, tranh vung
    goi, cach nhau >= 1200). P. khach / an ("phong_den_deu"): moi canh chia DEU, khoang <= 1800 va > 1400 (du cho gio).
  - CUA GIO DIEU HOA (P. khach / an): tung cap gio hoi / gio cap DOI DIEN, THANG HANG (cung vi tri doc chieu dai) tren
    2 canh dai, o giua hai den; cac cap phan bo deu; co the nam tren noi that (tranh vung den tha).
  - LO THAM P. khach tai TAM hinh chu nhat truc.
  - Den tha: gan tam ban an nhat, CACH DEN DOWNLIGHT >= 200 (mep ky hieu), co the lech tim ban.
  - DAU BAO KHOI / NHIET: tren truc, tai DIEM GIUA hai den lien ke. PN: canh phia CHAN GIUONG; P. khach: khoang gan tam
    phong, cach gio cap >= 1000. NHIET: CHI trong bep, tren truc den bep, khoang gan bep nau.
  - Mieng gio hut bep tren bep nau.
WC: vuong -> hinh chu nhat truc cach mep trong tuong 450, DEN TAI 4 GOC, HUT MUI tai TAM phong; dai -> 1 truc theo chieu
    dai DI QUA TAM BON CAU, den tai tam bon cau va tam vung tam (chieu len truc), hut mui tren truc. Den D65 tai TAM
    CHAU RUA. LO THAM WC tren vung canh cua di mo (cach mat tuong 50); den vuong lo tham thi doi doc truc, ghi chu.
Lo gia: truc giua. Truc ve tren layer Defpoints, linetype HIDDEN. Sprinkler: tat theo cau hinh ("bo_tri_sprinkler").
Thong so: cau_hinh_tran.json -> "bo_tri_moi". PCCC / dieu hoa la PHUONG AN SO BO.

Gioi han den: WC <= 6 m2 toi da 3 den (khong tinh D65); PN < 15 m2 toi da 5 downlight (bo den giua canh / hoc truoc).

    python bo_tri_tran.py <file.dxf> --out-dir <thu muc> --truc-khach 600 --truc-ngu 600 --truc-wc 450
                          [--du-an ten] [--layer-ten A-Dimension]
    (khoang cach truc toi tuong P. khach / P. ngu / WC: HOI NGUOI DUNG XAC NHAN truoc moi can moi)
Xuat: bo_tri_tran.json (thiet bi + truc cho ve_com.py), BaoCaoBoTriTran.xlsx, xem_bo_tri_<can>.png, ve_bo_tri_tran.scr.
"""
import argparse
import io
import itertools
import json
import math
import os
import sys
import time

import ezdxf
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import nearest_points, unary_union
from shapely.prepared import prep

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import soat_tran as st  # noqa: E402

SKILL = os.path.dirname(HERE)
R_DEN = 55          # ban kinh ky hieu downlight D90 (Ø110)
DEN = ("LT-DL-D90", "LT-DL-WC-D90")


def fp_ky_hieu(c, x, y, rot):
    return affinity.rotate(box(x - c["rong"] / 2, y - c["cao"] / 2, x + c["rong"] / 2, y + c["cao"] / 2), rot, origin=(x, y))


def doc_cua_di(msp, cfg):
    """Cung quay canh cua di (WCS): (ban le H, ban kinh R, [2 dau mut cung]). Cung chen lat guong da quy ve WCS."""
    want = {st.tpp.layer_goc(x) for x in cfg["layer_cua"]}
    out = []
    for ents in st.tpp._nhom_cua(msp, want):
        for e in ents:
            if e.dxftype() != "ARC" or not 500 <= e.dxf.radius <= 1200:
                continue
            h = e.ocs().to_wcs(e.dxf.center)
            out.append(((h.x, h.y), e.dxf.radius, [(e.start_point.x, e.start_point.y), (e.end_point.x, e.end_point.y)]))
    return out


class BoTri:
    def __init__(self, catalog, cfg):
        self.cat = {c["ma"]: c for c in catalog["thiet_bi"]}
        self.ng = cfg["nguong"]
        self.b = cfg["bo_tri_moi"]
        self.ds = []
        self.truc = []             # (can, phong, (x1, y1), (x2, y2))
        self.ghi_chu = []          # (can, phong, noi dung)

    def them(self, ma, x, y, rot=0.0, ly_do="", r=None):
        c = self.cat[ma]
        fp = fp_ky_hieu(c, x, y, rot)
        d = dict(cat=c, ma=ma, x=x, y=y, fp=fp, rot=rot, block=ma,
                 layer=c["layer"], handle=f"MOI{len(self.ds) + 1:03d}", insert=(x, y), ly_do=ly_do,
                 phong_moi=r["ten"] if r else "", can_moi=r["can"] if r else "")
        self.ds.append(d)
        return d

    def note(self, r, s):
        self.ghi_chu.append((r["can"], r["ten"], s))


# ------------------------------------------------------------------------------------------------ hinh hoc truc
class Doan:
    """Mot doan truc: tham so t tu 0 (diem a) toi L (diem b)."""

    def __init__(self, a, b):
        self.a, self.b = (float(a[0]), float(a[1])), (float(b[0]), float(b[1]))
        self.L = math.dist(self.a, self.b)
        self.u = ((self.b[0] - self.a[0]) / self.L, (self.b[1] - self.a[1]) / self.L) if self.L else (1.0, 0.0)
        self.goc = math.degrees(math.atan2(self.u[1], self.u[0])) % 180.0

    def diem(self, t):
        return self.a[0] + self.u[0] * t, self.a[1] + self.u[1] * t

    def t(self, p):
        return (p[0] - self.a[0]) * self.u[0] + (p[1] - self.a[1]) * self.u[1]

    def kc(self, p):
        return LineString([self.a, self.b]).distance(Point(p))


def doan_vong(U, offs, rong_min=300):
    """Vong truc lui deu tu bien U (lan luot cac khoang lui); None neu phong qua hep."""
    for o in offs:
        R = U.buffer(-o, join_style=2, mitre_limit=5)
        if R.is_empty:
            continue
        R = max(getattr(R, "geoms", [R]), key=lambda g: g.area).simplify(10)
        xy = list(R.minimum_rotated_rectangle.exterior.coords)
        if min(math.dist(xy[0], xy[1]), math.dist(xy[1], xy[2])) < rong_min:
            continue
        c = list(R.exterior.coords)
        return [Doan(p, q) for p, q in zip(c, c[1:]) if math.dist(p, q) >= 1], o
    return None, None


def doan_giua(U, lui=300):
    """Truc giua theo chieu dai (hinh chu nhat bao nho nhat), lui `lui` o hai dau, cat trong U."""
    xy = list(U.minimum_rotated_rectangle.exterior.coords)[:4]
    if math.dist(xy[0], xy[1]) >= math.dist(xy[1], xy[2]):
        m1, m2 = ((xy[1][0] + xy[2][0]) / 2, (xy[1][1] + xy[2][1]) / 2), ((xy[3][0] + xy[0][0]) / 2, (xy[3][1] + xy[0][1]) / 2)
    else:
        m1, m2 = ((xy[0][0] + xy[1][0]) / 2, (xy[0][1] + xy[1][1]) / 2), ((xy[2][0] + xy[3][0]) / 2, (xy[2][1] + xy[3][1]) / 2)
    g = LineString([m1, m2]).intersection(U.buffer(-lui, join_style=2))
    g = max(getattr(g, "geoms", [g]), key=lambda q: q.length) if not g.is_empty else None
    if g is None or g.geom_type != "LineString" or g.length < 1:
        return []
    c = list(g.coords)
    return [Doan(c[0], c[-1])]


def goc_tuong_chinh(P):
    """Huong tuong chinh = canh dai nhat cua phong (do, 0-180)."""
    c = list(P.exterior.coords)
    a, b = max(zip(c, c[1:]), key=lambda s: math.dist(*s))
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0


def hcn_lon_nhat(U, goc):
    """Hinh chu nhat lon nhat nam trong U, canh song song tuong chinh (goc). Thu moi cap toa do dinh (dung voi phong
    truc giao) -> tu bo cac hoc / sanh hep. Tra ve polygon (toa do that) hoac None."""
    c = U.centroid
    V = affinity.rotate(U, -goc, origin=c).simplify(30)
    V = max(getattr(V, "geoms", [V]), key=lambda g: g.area)
    xs = sorted({round(x) for x, _ in V.exterior.coords})
    ys = sorted({round(y) for _, y in V.exterior.coords})
    pv = prep(V.buffer(5, join_style=2))
    best = None
    for i, x1 in enumerate(xs):
        for x2 in xs[i + 1:]:
            if x2 - x1 < 600:
                continue
            for j, y1 in enumerate(ys):
                for y2 in ys[j + 1:]:
                    if y2 - y1 < 600:
                        continue
                    a = (x2 - x1) * (y2 - y1)
                    if best is not None and a <= best[0]:
                        continue
                    if pv.contains(box(x1, y1, x2, y2)):
                        best = (a, box(x1, y1, x2, y2))
    return affinity.rotate(best[1], goc, origin=c) if best else None


def truc_thiet_bi(f, P):
    """Tuong gan noi that nhat -> (diem chieu tam len tuong, phap tuyen vao phong)."""
    c = f["fp"].centroid
    ext = list(P.exterior.coords)
    best = None
    for a, b in zip(ext, ext[1:]):
        seg = LineString([a, b])
        d = seg.distance(f["fp"])
        if seg.length > 300 and (best is None or d < best[0]):
            best = (d, seg)
    seg = best[1]
    q = seg.interpolate(seg.project(c))
    (ax, ay), (bx, by) = seg.coords
    L = math.dist((ax, ay), (bx, by))
    nx, ny = -(by - ay) / L, (bx - ax) / L
    if not P.contains(Point(q.x + nx * 50, q.y + ny * 50)):
        nx, ny = -nx, -ny
    return (q.x, q.y), (nx, ny)


def khoi_tu_bep(P, ds_bep, sau):
    """Khoi tu bep chinh: dai sau `sau` (hoac sau hon thiet bi) doc tuong cua bep nau, phu het bep nau / chau / may rua
    tren cung tuong (+300 hai dau)."""
    bep = ds_bep[0]
    (qx, qy), (nx, ny) = truc_thiet_bi(bep, P)
    wx, wy = -ny, nx
    ts, ds = [], [sau]
    for f in ds_bep:
        for x, y in list(f["fp"].exterior.coords):
            dn = (x - qx) * nx + (y - qy) * ny
            if dn < 1000:
                ts.append((x - qx) * wx + (y - qy) * wy)
                ds.append(dn)
    t0, t1, d = min(ts) - 300, max(ts) + 300, max(ds)
    pts = [(qx + wx * t0, qy + wy * t0), (qx + wx * t1, qy + wy * t1),
           (qx + wx * t1 + nx * d, qy + wy * t1 + ny * d), (qx + wx * t0 + nx * d, qy + wy * t0 + ny * d)]
    return Polygon(pts).buffer(0), dict(q=(qx, qy), n=(nx, ny), w=(wx, wy), t0=t0, t1=t1, sau=d)


def truc_bep(U, kh, lui_dau):
    """Truc bep: song song chieu dai khoi tu bep chinh, nam GIUA khong gian tu mat tu toi bien doi dien (tia phap tuyen
    tu giua mat tu trong U); dai theo vung bep (cat trong U, trong pham vi khoi tu), rut `lui_dau` o hai dau."""
    (qx, qy), (nx, ny), (wx, wy) = kh["q"], kh["n"], kh["w"]
    tm = (kh["t0"] + kh["t1"]) / 2
    fx, fy = qx + wx * tm + nx * (kh["sau"] + 1), qy + wy * tm + ny * (kh["sau"] + 1)
    tia = LineString([(fx, fy), (fx + nx * 20000, fy + ny * 20000)]).intersection(U)
    if tia.is_empty:
        return []
    seg = min(getattr(tia, "geoms", [tia]), key=lambda g: g.distance(Point(fx, fy)))
    c = list(seg.coords)
    D = max(math.dist((fx, fy), p) for p in c)
    cx, cy = fx + nx * D / 2, fy + ny * D / 2
    ln = LineString([(cx - wx * 20000, cy - wy * 20000), (cx + wx * 20000, cy + wy * 20000)]).intersection(U)
    ln = min(getattr(ln, "geoms", [ln]), key=lambda g: g.distance(Point(cx, cy))) if not ln.is_empty else None
    if ln is None or ln.geom_type != "LineString":
        return []
    c = list(ln.coords)
    d = Doan(c[0], c[-1])
    # gioi han trong pham vi khoi tu bep (chieu len truc)
    ta = sorted((d.t((qx + wx * kh["t0"], qy + wy * kh["t0"])), d.t((qx + wx * kh["t1"], qy + wy * kh["t1"]))))
    lo, hi = max(0.0, ta[0]) + lui_dau, min(d.L, ta[1]) - lui_dau
    if hi - lo < 1:
        return []
    return [Doan(d.diem(lo), d.diem(hi))]


def chia_theo_hcn(g, R0):
    """Cat phan du (phong tru hinh chu nhat truc) theo cac canh keo dai cua hinh chu nhat -> tung hoc rieng."""
    from shapely.ops import split
    xy = list(R0.exterior.coords)
    phan = [g]
    for a, b in zip(xy, xy[1:]):
        L = math.dist(a, b)
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        cat = LineString([(a[0] - ux * 50000, a[1] - uy * 50000), (b[0] + ux * 50000, b[1] + uy * 50000)])
        moi = []
        for p in phan:
            try:
                moi += [q for q in split(p, cat).geoms if q.area > 1]
            except Exception:
                moi.append(p)
        phan = moi
    return [p for p in phan if p.geom_type == "Polygon"]


def khe_tren_truc(doans, diem, rong_min):
    """Cac khoang trong giua 2 diem lien ke tren cung doan (hoac doan khong co diem): (diem giua, do dai khoang, doan)."""
    out = []
    for d in doans:
        ts = sorted(d.t((x, y)) for x, y in diem if d.kc((x, y)) < 2 and -2 <= d.t((x, y)) <= d.L + 2)
        if not ts:
            if d.L >= rong_min:
                out.append((d.diem(d.L / 2), d.L, d))
            continue
        for t0, t1 in zip(ts, ts[1:]):
            if t1 - t0 >= rong_min:
                out.append((d.diem((t0 + t1) / 2), t1 - t0, d))
    return out


def truc_qua_diem(U, c0, goc, lui):
    """Truc WC dai: duong theo huong `goc` di qua diem c0 (tam bon cau), cat trong U, rut `lui` o hai dau."""
    ux, uy = math.cos(math.radians(goc)), math.sin(math.radians(goc))
    g = LineString([(c0[0] - ux * 20000, c0[1] - uy * 20000), (c0[0] + ux * 20000, c0[1] + uy * 20000)]).intersection(U)
    g = min(getattr(g, "geoms", [g]), key=lambda q: q.distance(Point(c0))) if not g.is_empty else None
    if g is None or g.geom_type != "LineString":
        return None
    c = list(g.coords)
    d = Doan(c[0], c[-1])
    return Doan(d.diem(lui), d.diem(d.L - lui)) if d.L > 2 * lui + 1 else None


def lo_tham_cua(P, cua, cach_tuong):
    """Lo tham 600 ngay tren vung canh cua di WC mo: canh lo tham cach mat tuong co cua `cach_tuong`, giua be rong canh.
    Tra ve ((x, y), goc) hoac None (khong thay cua cua phong)."""
    ext = list(P.exterior.coords)
    best = None
    for H, R, ds in cua:
        # dau mut "dong" cua cung = dau nam doc tuong (o cua = doan H -> E1)
        for E1 in ds:
            m = Point((H[0] + E1[0]) / 2, (H[1] + E1[1]) / 2)
            dk = P.exterior.distance(m)
            if dk <= 300 and (best is None or dk < best[0]):
                best = (dk, H, R, E1, m)
    if best is None:
        return None
    _, H, R, E1, m = best
    a, b2 = min(zip(ext, ext[1:]), key=lambda s: LineString(s).distance(m))
    L = math.dist(a, b2)
    wx, wy = (b2[0] - a[0]) / L, (b2[1] - a[1]) / L
    if abs((E1[0] - H[0]) * wx + (E1[1] - H[1]) * wy) < 0.7 * R:      # cung khong nam doc canh nay
        return None
    s = 1 if (E1[0] - H[0]) * wx + (E1[1] - H[1]) * wy > 0 else -1
    t = (H[0] - a[0]) * wx + (H[1] - a[1]) * wy
    hx, hy = a[0] + wx * t, a[1] + wy * t
    nx, ny = -wy, wx
    if not P.contains(Point(hx + s * wx * R / 2 + nx * 50, hy + s * wy * R / 2 + ny * 50)):
        nx, ny = -nx, -ny
    k = 305 + cach_tuong
    c = (hx + s * wx * R / 2 + nx * k, hy + s * wy * R / 2 + ny * k)
    return c, math.degrees(math.atan2(wy, wx)) % 180.0


# ------------------------------------------------------------------------------------------------ bo tri mot phong
def bo_tri_phong(bt, r, nt_phong, can_poly, cua=()):
    P = r["poly"]
    P0 = P.buffer(-200, join_style=2).buffer(200, join_style=2)          # bo hoc cua / khung nho
    P0 = max(getattr(P0, "geoms", [P0]), key=lambda g: g.area) if not P0.is_empty else P
    loai = set(r["loai"])
    b, ng = bt.b, bt.ng
    khe = b["khe_ho_thiet_bi"]
    tu = [f for f in nt_phong if f["loai"] == "tu_ao"]
    giuong = next((f for f in nt_phong if f["loai"] == "giuong"), None)
    ban = [f for f in nt_phong if f["loai"] == "ban_an"]
    sofa = [f for f in nt_phong if f["loai"] == "sofa"]
    bep = [f for f in nt_phong if f["loai"] == "bep_nau"]
    bon_cau = [f for f in nt_phong if f["loai"] == "bon_cau"]
    chau = [f for f in nt_phong if f["loai"] == "chau_rua"]
    guong = [f for f in nt_phong if f["loai"] == "guong"]
    tam =[f for f in nt_phong if f["loai"] in ("sen_tam", "vach_tam")]
    vt = unary_union([f["fp"] for f in tam]) if tam else None
    wc, logia = "wc" in loai, "logia" in loai
    moi = []

    def them(ma, p, rot=0.0, ly_do=""):
        d = bt.them(ma, p[0], p[1], rot, ly_do, r)
        moi.append(d)
        return d

    def trong(p, cach_tb=khe + R_DEN):
        return all(d["fp"].distance(Point(p)) >= cach_tb for d in moi)

    def xoa(d):
        moi.remove(d)
        bt.ds.remove(d)

    def ho(ma, p, rot=0.0, cach=khe, bo=()):
        """Ky hieu `ma` dat tai p cach moi thiet bi da dat >= `cach` (mep - mep)."""
        fp = fp_ky_hieu(bt.cat[ma], p[0], p[1], rot)
        return all(x["fp"].distance(fp) >= cach for x in moi if x not in bo)

    def doc_truc(ma, p, ds_doan, cach=khe, toi_da=3000):
        """Diem tren truc gan p nhat (doi doc truc buoc 25) ma ky hieu khong vuong thiet bi khac."""
        d = min(ds_doan, key=lambda d: d.kc(p))
        t0 = min(max(d.t(p), 0.0), d.L)
        for s in range(0, toi_da, 25):
            for t in ((t0 + s, t0 - s) if s else (t0,)):
                if 0 <= t <= d.L and ho(ma, d.diem(t), 0, cach):
                    return d.diem(t)
        return None

    # ---- vung tran dung duoc (tru khoi tu bep, tu ao)
    tu_bep = None
    cam_nt = [f["fp"] for f in tu]
    if bep:
        ds_bep = bep + [f for f in nt_phong if f["loai"] == "chau_rua" and f["fp"].distance(bep[0]["fp"]) < 3000]
        tu_bep, kh_bep = khoi_tu_bep(P0, ds_bep, b["tu_bep_sau"])
        cam_nt.append(tu_bep)
    U = P0.difference(unary_union(cam_nt)) if cam_nt else P0
    U = max(getattr(U, "geoms", [U]), key=lambda g: g.area)

    # ---- truc
    hcn, doans, doan_bep, hoc, wc_dai, hcn_wc = None, [], [], [], False, None
    if wc:
        xy = list(U.minimum_rotated_rectangle.exterior.coords)
        dai, ngan = sorted((math.dist(xy[0], xy[1]), math.dist(xy[1], xy[2])), reverse=True)
        if dai / max(ngan, 1) >= b["wc_ty_le_dai"]:
            # WC dai: truc theo chieu dai DI QUA TAM BON CAU (khong co bon cau: truc giua), 2 dau cach tuong 450
            wc_dai = True
            i = 0 if math.dist(xy[0], xy[1]) >= math.dist(xy[1], xy[2]) else 1
            goc_dai = math.degrees(math.atan2(xy[i + 1][1] - xy[i][1], xy[i + 1][0] - xy[i][0])) % 180.0
            d = truc_qua_diem(U, (bon_cau[0]["x"], bon_cau[0]["y"]), goc_dai, b["den_wc_dai_cach_tuong"]) if bon_cau else None
            if d:                    # keo truc toi den tam bon cau / tam vung tam neu nam ngoai doan cach tuong 450
                ts = [d.t((bon_cau[0]["x"], bon_cau[0]["y"]))] + ([d.t((vt.centroid.x, vt.centroid.y))] if vt is not None else [])
                d = Doan(d.diem(min(0.0, *ts)), d.diem(max(d.L, *ts)))
            doans = [d] if d else doan_giua(U, b["den_wc_dai_cach_tuong"])
        else:
            # WC vuong: hinh chu nhat truc cach mep trong tuong 450, den tai 4 goc
            o = b["truc_wc_vuong_cach_tuong"]
            R0 = hcn_lon_nhat(U, goc_tuong_chinh(P0))
            R = R0.buffer(-o, join_style=2) if R0 is not None else None
            if R is not None and not R.is_empty and R.geom_type == "Polygon":
                xy = list(R.exterior.coords)
                hcn_wc = xy[:4]
                doans = [Doan(p, q) for p, q in zip(xy, xy[1:])]
            else:
                doans = doan_vong(U, [o], 100)[0] or doan_giua(U, o)
    elif logia:
        doans = doan_giua(U, 300)
    else:
        # 1 hinh chu nhat khep kin theo tuong chinh, lon nhat trong phong (bo hoc), lui 600 (khong du: 500)
        # khoang lui theo loai phong (PN / phong khac) - nguoi dung xac nhan truoc moi can moi (--truc-khach / --truc-ngu)
        offs = b.get("truc_cach_tuong_theo_phong", {}).get("ngu" if "ngu" in loai else "khach", b["truc_cach_tuong"])
        goc = goc_tuong_chinh(P0)
        R0 = hcn_lon_nhat(U, goc)
        if R0 is not None:
            for o in offs:
                R = R0.buffer(-o, join_style=2)
                if R.is_empty:
                    continue
                xy = list(R.exterior.coords)
                if min(math.dist(xy[0], xy[1]), math.dist(xy[1], xy[2])) >= 300:
                    hcn = [xy[0], xy[1], xy[2], xy[3]]
                    doans = [Doan(p, q) for p, q in zip(xy, xy[1:])]
                    break
            if not doans:
                doans = doan_giua(R0, offs[-1])
            # phan phong ngoai hinh chu nhat (cat theo canh keo dai): sat khoi tu bep -> truc bep; con lai du lon -> hoc
            con = U.difference(R0)
            vung_bep = []
            for g0 in getattr(con, "geoms", [con]):
                for g in chia_theo_hcn(g0, R0):
                    if g.area < b["hoc_dt_toi_thieu"] * 1e6:
                        continue
                    xy = list(g.minimum_rotated_rectangle.exterior.coords)
                    if min(math.dist(xy[0], xy[1]), math.dist(xy[1], xy[2])) < b["hoc_rong_toi_thieu"]:
                        continue
                    if tu_bep is not None and g.distance(tu_bep) < 150:
                        vung_bep.append(g)
                    else:
                        hoc.append(g)
            if tu_bep is not None and (vung_bep or "bep" in loai and not loai & {"khach", "an"}):
                doan_bep = truc_bep(U, kh_bep, offs[0])
                doans += doan_bep
        if not doans:
            doans = doan_giua(U, offs[-1])
    if not doans:
        bt.note(r, "Phòng quá hẹp: không dựng được trục đặt đèn.")
        return moi
    for d in doans:
        bt.truc.append((r["can"], r["ten"], d.a, d.b))
    truc = unary_union([LineString([d.a, d.b]) for d in doans])

    def len_truc(p, ds_doan=None):
        g = truc if ds_doan is None else unary_union([LineString([d.a, d.b]) for d in ds_doan])
        q = nearest_points(g, Point(p))[0]
        return q.x, q.y

    def doan_cua(p):
        return min(doans, key=lambda d: d.kc(p))

    def tranh_den(p, dens, kc=300):
        """Dat thiet bi tai p tren truc; vuong den (< kc) thi doi doc truc toi dung kc tu den do (uu tien phia giua doan)."""
        gan = [q for q in dens if math.dist(p, q) < kc - 1]
        if not gan:
            return p
        q = min(gan, key=lambda q: math.dist(p, q))
        d = doan_cua(q)
        tq = d.t(q)
        for s in ([1, -1] if tq < d.L / 2 else [-1, 1]):
            t = tq + s * kc
            if 0 <= t <= d.L:
                p2 = d.diem(t)
                if all(math.dist(p2, x) >= kc - 1 for x in dens) and trong(p2, khe + 60):
                    return p2
        return None

    def den_tren_doan(d, dens, ly_do, bo_goi=False):
        """Den hai dau doan, doan > 2400 them den chia deu; giu cach >= 1200 voi den da co."""
        n = max(1, math.ceil(d.L / b["den_kc_toi_da"])) if d.L > b["den_kc_toi_da"] else 1
        for k in range(n + 1):
            p = d.diem(d.L * k / n)
            if bo_goi and goi is not None and goi.contains(Point(p)):
                continue
            if all(math.dist(p, q) >= ng["den_kc_toi_thieu"] - 1 for q in dens):
                dens.append(p)
                them("LT-DL-D90", p, 0, ly_do)

    # ---- 1. thiet bi chuc nang ngoai truc (den tha dat sau den / gio / lo tham: duoc lech tim ban)
    if wc and (chau or guong):
        f = (chau or guong)[0]
        them("LT-MIR-D65", (f["x"], f["y"]), 0, "đèn D65 tại tâm chậu rửa")
    if bep:
        them("HV-EXG-200", (bep[0]["x"], bep[0]["y"]), 0, "miệng gió hút bếp trên bếp nấu (theo chụp hút)")

    # ---- 2. den
    dens = []
    goi = giuong.get("vung_goi") if giuong else None
    deu = bool(loai & set(b.get("phong_den_deu", [])))
    co_gio = hcn is not None and bool(loai & set(b["phong_co_gio_tran"]))
    if hcn is not None and loai & set(b["phong_co_luoi_den"]):
        # 4 goc truoc (dung goc, ke ca phia dau giuong), canh > 2400 them den giua (tranh vung goi), cach nhau >= 1200;
        # P. khach / an: moi canh chia deu, khoang <= den_kc_deu_toi_da va > gio_khe_den_toi_thieu (du cho cua gio)
        for p in hcn:
            if all(math.dist(p, q) >= ng["den_kc_toi_thieu"] - 1 for q in dens):
                dens.append(p)
        for p, q in zip(hcn, hcn[1:] + hcn[:1]):
            L = math.dist(p, q)
            if deu:
                n = max(1, math.ceil(L / b["den_kc_deu_toi_da"] - 1e-6))
                while n > 1 and co_gio and L / n <= b["gio_khe_den_toi_thieu"]:
                    n -= 1
            else:
                n = math.ceil(L / b["den_kc_toi_da"]) if L > b["den_kc_toi_da"] else 1
            for k in range(1, n):
                m = (p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n)
                if (goi is None or not goi.contains(Point(m))) and all(math.dist(m, x) >= ng["den_kc_toi_thieu"] - 1 for x in dens):
                    dens.append(m)
        for p in dens:
            them("LT-DL-D90", p, 0, "đèn chung: góc / chia đều cạnh hình chữ nhật trục" if deu else
                 "đèn chung: góc / giữa cạnh hình chữ nhật trục")
    elif doans and loai & set(b["phong_co_luoi_den"]) and not (wc or logia):
        den_tren_doan(doans[0], dens, "đèn chung trên trục giữa (phòng hẹp)", bo_goi=True)
    for d in doan_bep:
        den_tren_doan(d, dens, "đèn trên trục bếp (giữa, song song chiều dài bếp)")
    for g in hoc:
        c = g.centroid if g.contains(g.centroid) else g.representative_point()
        dens.append((c.x, c.y))
        them("LT-DL-D90", (c.x, c.y), 0, "đèn tại tâm hốc sảnh")
        kc = min((math.dist((c.x, c.y), q) for q in dens[:-1]), default=1e9)
        if kc < ng["den_kc_toi_thieu"] - 1:
            bt.note(r, f"Đèn tâm hốc sảnh cách đèn gần nhất {kc:.0f} mm < {ng['den_kc_toi_thieu']} mm.")
        kt = g.exterior.distance(Point(c))
        if kt < ng["den_cach_tuong_toi_thieu"] - 1:
            bt.note(r, f"Đèn tâm hốc sảnh cách tường {kt:.0f} mm (hốc rộng {2 * kt:.0f} mm) < {ng['den_cach_tuong_toi_thieu']} mm: "
                       "giữ tại tâm hốc theo yêu cầu, ngoại lệ luật cách tường.")
    if not (wc or logia) and loai & set(b["phong_co_luoi_den"]) and not dens:
        bt.note(r, "Không đặt được đèn chung trên trục.")
    # gioi han so den (PN < 15 m2: <= 5 downlight): bo den giua canh truoc, roi den hoc; giu 4 goc
    gh = st.gioi_han_den(loai, P.area / 1e6, ng)
    if gh and not wc:
        ds_den = [d for d in moi if d["ma"] in DEN]
        if len(ds_den) > gh[0]:
            goc4 = {(round(p[0]), round(p[1])) for p in (hcn or [])}
            bo = sorted(ds_den, key=lambda d: 2 if (round(d["x"]), round(d["y"])) in goc4 else 1 if "hốc" in d["ly_do"] else 0)
            bo = bo[:len(ds_den) - gh[0]]
            for d in bo:
                xoa(d)
            dens = [p for p in dens if not any(math.dist(p, (d["x"], d["y"])) < 1 for d in bo)]
            bt.note(r, f"Giới hạn {gh[2]}: tối đa {gh[0]} {gh[1]} → bỏ {len(bo)} đèn (giữa cạnh / hốc), giữ đèn góc.")
    if logia:
        d = doans[0]
        n = max(1, round(d.L / b["den_ngoai_kc"]))
        for k in range(n):
            them("LT-OUT", d.diem(d.L * (k + 0.5) / n), 0, "đèn ngoài nhà trên trục giữa lô gia")

    # ---- 3. cua gio dieu hoa: tung cap hoi / cap DOI DIEN THANG HANG tren 2 canh dai, o giua hai den, cac cap phan bo deu
    gio_cap, gio_hoi = [], []
    if co_gio:
        n = max(1, round(P.area / 1e6 / b["gio_dt_moi_cap"]))
        canh = [Doan(p, q) for p, q in zip(hcn, hcn[1:] + hcn[:1])]
        i0 = 0 if canh[0].L >= canh[1].L else 1
        A, B = canh[i0], canh[i0 + 2]
        ref = can_poly.centroid if can_poly is not None else P.centroid
        if math.dist(A.diem(A.L / 2), (ref.x, ref.y)) > math.dist(B.diem(B.L / 2), (ref.x, ref.y)):
            A, B = B, A                                              # A = canh dai phia trong can -> gio hoi
        kmin = b["gio_khe_den_toi_thieu"]
        bien = 600 + R_DEN + 50                                      # nua cua gio + den + khe
        kB = [(B.t(p), L) for p, L, _ in khe_tren_truc([B], dens, kmin) if L > kmin]
        # vung den tha (tam ban an): cap gio tranh neu con lua chon khac
        tha = unary_union([Point(f["x"], f["y"]).buffer(400) for f in ban]) if ban and loai & {"khach", "an", "bep"} else None

        def fp_gio(p, d):
            return affinity.rotate(box(p[0] - 600, p[1] - 75, p[0] + 600, p[1] + 75), d.goc, origin=p)

        def khong_chong(p, d):
            fp = fp_gio(p, d)          # hai den dau khoang: ho 50 (nhu `bien`); thiet bi khac: khe
            return all(x["fp"].distance(fp) >= (50 - 1 if x["ma"] in DEN else khe) for x in moi)
        ung = []                                                     # (tA, diem A, diem B, cham vung den tha)
        for p, L, _ in khe_tren_truc([A], dens, kmin):
            m = L / 2 - bien
            if L <= kmin or m < 0:
                continue
            for dt in sorted(range(-int(m // 50) * 50, int(m // 50) * 50 + 1, 50), key=abs):
                pa = A.diem(A.t(p) + dt)
                tb = B.t(pa)
                pb = B.diem(tb)
                if (any(abs(tb - t) <= Lb / 2 - bien + 1 for t, Lb in kB) and 0 <= tb <= B.L
                        and khong_chong(pa, A) and khong_chong(pb, B)):
                    vt_tha = tha is not None and (fp_gio(pa, A).intersects(tha) or fp_gio(pb, B).intersects(tha))
                    ung.append((A.t(pa), pa, pb, int(vt_tha)))
                    break
        chon = None
        for k in range(min(n, len(ung)), 0, -1):
            for comb in itertools.combinations(sorted(ung, key=lambda u: u[0]), k):
                ts = [0.0] + [u[0] for u in comb] + [A.L]
                key = (sum(u[3] for u in comb),
                       round(sum(abs(u[0] - A.L * (j + 0.5) / k) for j, u in enumerate(comb)), -1),
                       max(y - x for x, y in zip(ts, ts[1:])))
                if chon is None or key < chon[0]:
                    chon = (key, comb)
            if chon:
                break
        for _, pa, pb, _ in (chon[1] if chon else []):
            gio_hoi.append(them("HV-RAG-1200x150", pa, A.goc, "gió hồi: giữa hai đèn trên cạnh dài phía trong căn, đối diện gió cấp"))
            gio_cap.append(them("HV-SAG-1200x150", pb, B.goc, "gió cấp: giữa hai đèn trên cạnh dài đối diện, thẳng hàng gió hồi"))
        if len(gio_cap) < n:
            bt.note(r, f"Chỉ đặt được {len(gio_cap)}/{n} cặp cửa gió đối diện thẳng hàng (thiếu khoảng giữa hai đèn > {kmin} mm "
                       "trùng nhau trên hai cạnh dài).")

    # ---- 3b. lo tham P. khach: TAM hinh chu nhat truc
    if co_gio:
        c = Polygon(hcn).centroid
        if ho("AC-AP-600", (c.x, c.y), A.goc):
            them("AC-AP-600", (c.x, c.y), A.goc, "lỗ thăm tại tâm hình chữ nhật trục thiết bị")
        else:
            them("AC-AP-600", (c.x, c.y), A.goc, "lỗ thăm tại tâm hình chữ nhật trục thiết bị (vướng thiết bị khác: kiểm tra)")
            bt.note(r, "Lỗ thăm tại tâm hình chữ nhật trục vướng thiết bị khác.")

    # ---- 3c. den tha: gan tam ban an nhat, cach den downlight >= den_tha_cach_den (mep), duoc lech tim ban
    if loai & {"khach", "an", "bep"}:
        for f in ban:
            c0 = (f["x"], f["y"])
            x0, y0, x1, y1 = f["fp"].bounds
            pf = prep(f["fp"])
            ung = sorted(((x, y) for x in range(int(x0), int(x1) + 1, 25) for y in range(int(y0), int(y1) + 1, 25)
                          if pf.contains(Point(x, y))), key=lambda p: math.dist(p, c0))
            cach = b.get("den_tha_cach_den", 200)
            p = next((p for p in [c0] + ung
                      if all(x["fp"].distance(fp_ky_hieu(bt.cat["LT-PEND"], p[0], p[1], 0)) >= (cach if x["ma"] in DEN else khe)
                             for x in moi)), None)
            if p is None:
                them("LT-PEND", c0, 0, "tâm mặt bàn ăn (vướng thiết bị: kiểm tra)")
                bt.note(r, "Đèn thả: không tìm được vị trí trên mặt bàn ăn cách downlight ≥ 200 mm.")
            else:
                lech = math.dist(p, c0)
                them("LT-PEND", p, 0, "tâm mặt bàn ăn" if lech < 1 else f"đèn thả lệch tâm bàn {lech:.0f} mm, cách downlight ≥ {cach}")

    # ---- 4. WC: den + hut mui
    lo_wc = None
    if wc:
        dws = []
        if wc_dai and (bon_cau or vt is not None):
            # WC dai: den tai tam bon cau va tam vung tam (chieu len truc qua tim bon cau)
            if bon_cau:
                dws.append((len_truc((bon_cau[0]["x"], bon_cau[0]["y"])), "đèn WC tại tâm bồn cầu (trục qua tim bồn cầu)"))
            if vt is not None:
                dws.append((len_truc((vt.centroid.x, vt.centroid.y)), "đèn WC tại tâm vùng tắm, trên trục"))
        elif wc_dai:
            d = doans[0]
            n = max(1, math.ceil(d.L / b["den_kc_toi_da"])) if d.L > b["den_kc_toi_da"] else 1
            for k in range(n + 1):
                dws.append((d.diem(d.L * k / n), "đèn WC trên trục giữa" + (", cách tường 450" if k in (0, n) else "")))
        elif hcn_wc:
            dws += [(p, "đèn WC tại góc hình chữ nhật trục (cách tường 450)") for p in hcn_wc]
        else:
            c = truc.interpolate(0.5, normalized=True)
            dws.append(((c.x, c.y), "đèn WC trên trục"))
        den_wc = []
        for p, ly in dws:
            if all(math.dist(p, (q["x"], q["y"])) >= 2 * (R_DEN + khe) for q in den_wc):
                den_wc.append(them("LT-DL-WC-D90", p, 0, ly))
        # lo tham WC: ngay tren vung canh cua di mo; den vuong -> doi doc truc
        lt = lo_tham_cua(P, cua, b.get("lo_tham_wc_cach_tuong", 50)) if cua else None
        if lt is not None:
            lo_wc = them("AC-AP-600", lt[0], lt[1], "lỗ thăm trên vị trí cánh cửa đi WC mở")
        # gioi han so den WC (<= 6 m2: toi da 3, khong tinh D65): bo den vuong lo tham truoc, roi den gan D65 nhat
        gh = st.gioi_han_den(loai, P.area / 1e6, ng)
        if gh and len(den_wc) > gh[0]:
            d65 = next(((d["x"], d["y"]) for d in moi if d["ma"] == "LT-MIR-D65"), None)
            bo = sorted(den_wc, key=lambda d: (0 if lo_wc is not None and d["fp"].distance(lo_wc["fp"]) < khe else 1,
                                               math.dist((d["x"], d["y"]), d65) if d65 else 0))[:len(den_wc) - gh[0]]
            for d in bo:
                xoa(d)
                den_wc.remove(d)
            bt.note(r, f"Giới hạn {gh[2]}: tối đa {gh[0]} đèn {gh[1]} → bỏ {len(bo)} đèn (ưu tiên đèn vướng lỗ thăm / gần D65).")
        if lo_wc is not None:
            for d in den_wc:
                if d["fp"].distance(lo_wc["fp"]) >= khe:
                    continue
                p0 = (d["x"], d["y"])
                ung = []
                for dd in doans:
                    if dd.kc(p0) > 2:
                        continue
                    for s in range(25, 2000, 25):
                        for t in (dd.t(p0) + s, dd.t(p0) - s):
                            q = dd.diem(t)
                            if 0 <= t <= dd.L and ho("LT-DL-WC-D90", q, 0, khe, bo=(d,)):
                                ung.append((s, q))
                                break
                        else:
                            continue
                        break
                if ung:
                    s, q = min(ung)
                    d.update(x=q[0], y=q[1], insert=q, fp=fp_ky_hieu(d["cat"], q[0], q[1], 0),
                             ly_do=d["ly_do"] + f"; dời {s} mm dọc trục tránh lỗ thăm cửa")
                    bt.note(r, f"Đèn WC dời {s} mm dọc trục để tránh lỗ thăm trên cánh cửa.")
                else:
                    bt.note(r, "Đèn WC vướng lỗ thăm trên cánh cửa, không dời được dọc trục.")
        c = P0.centroid
        if wc_dai:
            p = doc_truc("HV-EAG-200", (c.x, c.y), doans, 100)
            ly = "hút mùi trên trục qua tim bồn cầu, gần tâm phòng"
        else:
            p = (c.x, c.y) if ho("HV-EAG-200", (c.x, c.y), 0, 100) else None
            ly = "hút mùi tại tâm phòng vệ sinh"
        if p is not None:
            them("HV-EAG-200", p, 0, ly)
        else:
            bt.note(r, "Tâm phòng vệ sinh / trục vướng đèn, lỗ thăm: chưa đặt hút mùi.")

    # ---- 5. dau bao khoi / nhiet: tren truc, tai DIEM GIUA hai den lien ke (khoang gan vi tri uu tien nhat)
    tat_den = dens + [(d["x"], d["y"]) for d in moi if d["ma"] in ("LT-DL-WC-D90", "LT-OUT")]

    def giua_den(ds_doan, uu_tien, loc=None):
        ks = [k for k in khe_tren_truc(ds_doan, tat_den, 2 * (R_DEN + 70 + khe)) if trong(k[0], khe + 70)]
        if loc:
            ks = [k for k in ks if loc(k[0])] or ks
        return min(ks, key=lambda k: math.dist(k[0], uu_tien))[0] if ks else None

    if loai & set(b["phong_co_dau_bao_khoi"]) and not (wc or logia):
        p, p_tranh = None, None
        if giuong is not None and goi is not None and hcn is not None:
            canh = [Doan(a, c) for a, c in zip(hcn, hcn[1:] + hcn[:1])]
            gc = goi.centroid
            ung = [d for d in canh if abs(d.u[0] * (giuong["y"] - gc.y) - d.u[1] * (giuong["x"] - gc.x)) > 0.5 * math.dist((giuong["x"], giuong["y"]), (gc.x, gc.y))]
            d = max(ung or canh, key=lambda d: d.kc((gc.x, gc.y)))
            p_tranh = d.diem(min(max(d.t((giuong["x"], giuong["y"])), 0), d.L))
            p = giua_den([d], p_tranh)
            ly = "đầu báo khói trên trục phía chân giường, giữa hai đèn"
        else:
            c = P.centroid
            cc = unary_union([d["fp"] for d in gio_cap]) if gio_cap else None
            p = giua_den([d for d in doans if d not in doan_bep], (c.x, c.y),
                         (lambda q: cc.distance(Point(q)) >= ng["dau_bao_cach_gio_cap"]) if cc is not None else None)
            ly = "đầu báo khói trên trục, giữa hai đèn"
        if p is None and p_tranh is not None:
            p = tranh_den(p_tranh, tat_den, 300)
            ly = "đầu báo khói trên trục phía chân giường, cách đèn 300"
        if p is not None and trong(p, khe + 60):
            them("FA-SMOKE", p, 0, ly)
        else:
            bt.note(r, "Không đặt được đầu báo khói trên trục giữa hai đèn (vướng đèn / thiết bị).")
    # dau bao nhiet: CHI trong bep, tren truc dat den cua bep, giua hai den, khoang gan bep nau
    if bep:
        truc_h = doan_bep or (doans if "bep" in loai and not (loai & {"khach", "an"}) else [])
        if truc_h:
            p = giua_den(truc_h, len_truc((bep[0]["x"], bep[0]["y"]), truc_h))
            if p is not None and trong(p, khe + 60):
                them("FA-HEAT", p, 0, "đầu báo nhiệt trên trục đèn bếp, giữa hai đèn")
            else:
                bt.note(r, "Không đặt được đầu báo nhiệt trên trục bếp giữa hai đèn.")
        else:
            bt.note(r, "Không có trục bếp: chưa đặt đầu báo nhiệt.")

    # ---- 6. lo tham WC khi khong nhan duoc cua di: tren truc, xa vung tam (P. khach: muc 3b; WC co cua: muc 4)
    if wc and lo_wc is None:
        bt.note(r, "Không nhận được cung cửa đi WC: lỗ thăm đặt trên trục.")
        cho = tat_den + [(d["x"], d["y"]) for d in moi if d["ma"] not in ("LT-MIR-D65",)]
        khe_ = [k for k in khe_tren_truc(doans, cho, 2 * (305 + khe + R_DEN)) if trong(k[0], 305 + khe)
                and U.buffer(-300).contains(Point(k[0])) and (vt is None or vt.distance(Point(k[0])) >= 305)]
        if khe_:
            k = max(khe_, key=lambda k: vt.distance(Point(k[0])) if vt is not None else 0)
            them("AC-AP-600", k[0], doan_cua(k[0]).goc, "lỗ thăm trên trục WC, xa vùng tắm")
        else:
            bt.note(r, "WC không còn khoảng trống trên trục cho lỗ thăm 600.")

    # ---- 7. sprinkler (tat theo cau hinh "bo_tri_sprinkler")
    if b.get("bo_tri_sprinkler") and loai & set(b["phong_co_sprinkler"]) and not (wc or logia):
        R, tl = b["sprinkler_ban_kinh_phu"], b["sprinkler_ty_le_phu"]
        xs = sorted({round(d["x"]) for d in moi}) or [round(P.centroid.x)]
        ys = sorted({round(d["y"]) for d in moi}) or [round(P.centroid.y)]
        minx, miny, maxx, maxy = P.bounds
        cam = unary_union(cam_nt) if cam_nt else Polygon()
        trong_sp = P.buffer(-300, join_style=2)
        ung = [(x, y) for x in xs for y in range(int(miny), int(maxy), 100)] + [(x, y) for y in ys for x in range(int(minx), int(maxx), 100)]
        ung = [p for p in ung if trong_sp.contains(Point(p)) and not cam.contains(Point(p)) and trong(p, khe + 60)
               and P.exterior.distance(Point(p)) <= b["sprinkler_cach_tuong_toi_da"]]
        chua = P
        sp = []
        while chua.area > (1 - tl) * P.area and ung:
            p = max(ung, key=lambda p: chua.intersection(Point(p).buffer(R, quad_segs=16)).area)
            if chua.intersection(Point(p).buffer(R, quad_segs=16)).area < 0.05e6:
                break
            sp.append(p)
            chua = chua.difference(Point(p).buffer(R, quad_segs=16))
            ung = [q for q in ung if math.dist(q, p) >= b["sprinkler_kc_toi_thieu"]]
        for p in sp:
            them("SP-D15-68", p, 0, "sprinkler thẳng hàng thiết bị, phủ R2000")
        if chua.area > (1 - tl) * P.area:
            bt.note(r, f"Sprinkler chưa phủ hết phòng ({chua.area / 1e6:.1f} m² ngoài vòng R2000): bộ môn PCCC bố trí bổ sung.")
        if bep:
            sps = [d for d in moi if d["ma"] == "SP-D15-68"]
            if sps:
                s = min(sps, key=lambda d: bep[0]["fp"].distance(Point(d["x"], d["y"])))
                if bep[0]["fp"].distance(Point(s["x"], s["y"])) < 2500:
                    s.update(cat=bt.cat["SP-D15-93"], ma="SP-D15-93", block="SP-D15-93", ly_do="sprinkler 93°C gần bếp nấu")
    return moi

def xuat_scr(path, ds, truc, thu_vien, cfg):
    """Script chen thiet bi moi len DUNG layer thiet bi va ve truc tren layer Defpoints - cho ban sao chay ngam."""
    def ls(s):
        return '"' + st.tpp.acad_str(s).replace("\\", "\\\\").replace('"', "'") + '"'
    mau = {"A-Den": 150, "A-Thiet bi PCCC": 1, "A-HVAC": 2, "A-HVAC1": 2, "A-HVAC2": 2, "A-Hoan thien tran": 8}
    L = ["CMDECHO", "0", "OSMODE", "0", "ATTREQ", "0", "FILEDIA", "0", "(vl-load-com)",
         "(defun mk-lay (n c) (if (not (tblsearch \"LAYER\" n)) (entmake (list (cons 0 \"LAYER\") (cons 100 \"AcDbSymbolTableRecord\") "
         "(cons 100 \"AcDbLayerTableRecord\") (cons 2 n) (cons 70 0) (cons 62 c) (cons 6 \"Continuous\")))) n)"]
    for lay in sorted({d["layer"] for d in ds}):
        L.append(f"(mk-lay {ls(lay)} {mau.get(lay, 7)})")
    lt = cfg["bo_tri_moi"]["layer_truc"]
    ltn = cfg["bo_tri_moi"].get("linetype_truc", "HIDDEN")
    # linetype truc: nap neu chua co (acadiso.lin khi MEASUREMENT=1); ti le net de net gach dai `net_truc_gach` mm
    L += [f'(if (not (tblsearch "LTYPE" "{ltn}")) (command "_.-LINETYPE" "_L" "{ltn}" (if (= (getvar "MEASUREMENT") 1) "acadiso.lin" "acad.lin") ""))',
          f'(setq lts (vl-some (function (lambda (x) (if (and (= (car x) 49) (> (cdr x) 0)) (cdr x)))) (tblsearch "LTYPE" "{ltn}")))',
          f'(setq lts (if lts (/ {cfg["bo_tri_moi"].get("net_truc_gach", 150)}.0 lts) 1.0))']
    for _, _, a, b in truc:
        L.append(f'(entmake (list (cons 0 "LINE") (cons 8 {ls(lt)}) (cons 6 "{ltn}") (cons 48 lts) (list 10 {a[0]:.1f} {a[1]:.1f} 0.0) (list 11 {b[0]:.1f} {b[1]:.1f} 0.0)))')
    da = set()
    for d in ds:
        f = os.path.join(thu_vien, d["ma"] + ".dwg").replace("\\", "/")
        if " " in f:
            raise SystemExit(f"Đường dẫn thư viện có dấu cách: {f}")
        L.append(f"(setvar \"CLAYER\" {ls(d['layer'])})")
        L += ["_.-INSERT", d["ma"] if d["ma"] in da else f"{d['ma']}={f}", "_S", "1", "_R", f"{d['rot']:.2f}", f"{d['x']:.1f},{d['y']:.1f}"]
        da.add(d["ma"])
    L += ['(setvar "CLAYER" "0")', "_.QSAVE", "_.QUIT", "_Y"]
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--du-an", default="")
    ap.add_argument("--layer-ten", default=None, help="layer Text ten phong (mac dinh theo cau_hinh_tran.json)")
    ap.add_argument("--cau-hinh", default=os.path.join(HERE, "cau_hinh_tran.json"))
    ap.add_argument("--catalog", default=os.path.join(SKILL, "assets", "thu-vien", "catalog.json"))
    ap.add_argument("--thu-vien", default=os.path.join(SKILL, "assets", "thu-vien"))
    ap.add_argument("--truc-khach", type=float, default=None, help="truc cach tuong P. khach / an / bep / phong khac (mm)")
    ap.add_argument("--truc-ngu", type=float, default=None, help="truc cach tuong / mat tu ao phong ngu (mm)")
    ap.add_argument("--truc-wc", type=float, default=None, help="truc WC vuong cach mep trong tuong; WC dai: dau truc cach tuong (mm)")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    cfg = json.load(open(a.cau_hinh, encoding="utf-8"))
    if a.layer_ten:
        cfg["layer_ten_phong"] = a.layer_ten
    # khoang lui truc nguoi dung xac nhan cho can nay: gia tri xac nhan truoc, khong du cho thi lui 500 (neu lon hon)
    bm = cfg["bo_tri_moi"]
    tp = bm.setdefault("truc_cach_tuong_theo_phong", {})
    for k, v in (("khach", a.truc_khach), ("ngu", a.truc_ngu)):
        if v is not None:
            tp[k] = [v, 500.0] if v > 500 else [v]
    if a.truc_wc is not None:
        bm["truc_wc_vuong_cach_tuong"] = bm["den_wc_dai_cach_tuong"] = a.truc_wc
    print("[truc cach tuong] khach %s, ngu %s, WC vuong %s, WC dai dau truc %s" % (
        tp.get("khach", bm["truc_cach_tuong"]), tp.get("ngu", bm["truc_cach_tuong"]),
        bm["truc_wc_vuong_cach_tuong"], bm["den_wc_dai_cach_tuong"]), file=sys.stderr)
    catalog = json.load(open(a.catalog, encoding="utf-8"))
    st.tpp._BO_QUA[0] = st.tpp.BLOCK_BO_QUA
    t0 = time.time()
    doc = ezdxf.readfile(a.dxf)
    msp = doc.modelspace()
    ca = box(-1e9, -1e9, 1e9, 1e9)
    co_san, _ = st.doc_thiet_bi(msp, doc, st.NhanDien(catalog, cfg), ca)
    noi_that = st.doc_noi_that(msp, doc, cfg, ca)
    ds_phong, cans = st.dung_phong(msp, doc, cfg, co_san, noi_that)
    print(f"[phong] {time.time() - t0:.0f}s", file=sys.stderr)
    vung = unary_union([c for c, _ in cans] + [x["poly"] for x in ds_phong if x["poly"] is not None]).buffer(300)
    co_san = [d for d in co_san if vung.contains(Point(d["x"], d["y"]))]
    bt = BoTri(catalog, cfg)
    can_poly = {t: c for c, t in cans}
    cua = doc_cua_di(msp, cfg)
    for r in ds_phong:
        if r["poly"] is None:
            continue
        if any(r["poly"].contains(Point(d["x"], d["y"])) for d in co_san):
            bt.note(r, "Phòng đã có thiết bị trần: không bố trí thêm (dùng soat_tran.py để soát).")
            continue
        nt_phong = [f for f in noi_that if r["poly"].buffer(200).contains(Point(f["x"], f["y"]))
                    or r["poly"].intersection(f["fp"]).area > 0.5 * f["fp"].area]
        bo_tri_phong(bt, r, nt_phong, can_poly.get(r["can"]),
                     [c for c in cua if r["poly"].distance(Point(c[0])) < 1500])
    print(f"[bo tri] {time.time() - t0:.0f}s, {len(bt.ds)} thiet bi, {len(bt.truc)} doan truc", file=sys.stderr)
    # soat lai chinh phuong an vua bo tri
    so = st.SoTay()
    for can, phong, s in bt.ghi_chu:
        so.them(can, phong, "", st.DESIGN, "Ghi chú bố trí", s)
    phong_kq, de_xuat = st.soat(ds_phong, bt.ds, noi_that, cfg["nguong"], so)
    for d in bt.ds:                      # danh dau "thay bang luoi moi" chi dung cho che do soat, khong ve len anh bo tri
        d.pop("thay_the", None)
    os.makedirs(a.out_dir, exist_ok=True)
    xlsx = os.path.join(a.out_dir, "BaoCaoBoTriTran.xlsx")
    st.xuat_excel(xlsx, a.du_an, os.path.basename(a.dxf), phong_kq, so, bt.ds, [], [])
    anh = []
    for poly, ten in cans:
        p = os.path.join(a.out_dir, f"xem_bo_tri_{st.bo_dau(ten).replace(' ', '_')}.png")
        st.ve_anh(p, poly, phong_kq, bt.ds, noi_that, [], so, truc=[(x[2], x[3]) for x in bt.truc])
        anh.append(p)
    scr = os.path.join(a.out_dir, "ve_bo_tri_tran.scr")
    xuat_scr(scr, bt.ds, bt.truc, a.thu_vien, cfg)
    ra = [dict(ma=d["ma"], x=round(d["x"], 1), y=round(d["y"], 1), rot=round(d["rot"], 2), layer=d["layer"], can=d["can_moi"],
               phong=d["phong_moi"], ly_do=d["ly_do"]) for d in bt.ds]
    truc = [dict(can=c, phong=p, x1=round(a_[0], 1), y1=round(a_[1], 1), x2=round(b_[0], 1), y2=round(b_[1], 1)) for c, p, a_, b_ in bt.truc]
    js = os.path.join(a.out_dir, "bo_tri_tran.json")
    json.dump(dict(thu_vien=a.thu_vien, layer_truc=cfg["bo_tri_moi"]["layer_truc"],
                   linetype_truc=cfg["bo_tri_moi"].get("linetype_truc", "HIDDEN"),
                   net_truc_gach=cfg["bo_tri_moi"].get("net_truc_gach", 150), truc=truc, thiet_bi=ra),
              open(js, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    dem = {}
    for x in so.ds:
        dem[x["loai"]] = dem.get(x["loai"], 0) + 1
    print(json.dumps(dict(
        file=os.path.basename(a.dxf),
        can_ho=[t for _, t in cans],
        phong=[dict(can=p["can"], ten=p["ten"], loai=p["loai"], trang_thai=p["trang_thai"],
                    dien_tich=round(p["poly"].area / 1e6, 2) if p["poly"] is not None else None,
                    so_doan_truc=sum(1 for x in bt.truc if x[0] == p["can"] and x[1] == p["ten"]),
                    thiet_bi={m: sum(1 for d in bt.ds if d["phong_moi"] == p["ten"] and d["can_moi"] == p["can"] and d["ma"] == m)
                              for m in sorted({d["ma"] for d in bt.ds if d["phong_moi"] == p["ten"] and d["can_moi"] == p["can"]})})
               for p in phong_kq],
        thiet_bi_theo_ma={m: sum(1 for d in bt.ds if d["ma"] == m) for m in sorted({d["ma"] for d in bt.ds})},
        so_doan_truc=len(bt.truc),
        ghi_chu=[f"{c} – {p}: {s}" for c, p, s in bt.ghi_chu],
        canh_bao=dem, xlsx=xlsx, anh=anh, scr=scr, json=js), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

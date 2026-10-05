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
    goi, cach nhau >= 1200).
  - CUA GIO DIEU HOA (P. khach / an): CUNG CHIEU, doc 2 canh dai, PHAN BO DEU theo chieu dai phong, o giua hai den
    cach nhau > 1400; gio hoi canh phia trong can, gio cap canh doi dien; co the nam tren sofa / ban an.
  - DAU BAO KHOI: tren truc; PN o canh phia CHAN GIUONG (chieu tam giuong); vuong den thi cach den 300 mm.
    DAU BAO NHIET: CHI trong bep, tren truc den bep, ngang bep nau.
  - Den tha tai tam mat ban an; mieng gio hut bep tren bep nau; LO THAM P. khach NGOAI TRUC, gan cum gio hoi.
WC: dai -> 1 truc giua theo chieu dai, 2 den dau tien cach tuong 450 (them den giua neu > 2400); vuong -> vong truc
    cach mep trong tuong 450, den ngang bon cau / vung tam; HUT MUI tai TAM phong; den D65 tai TAM CHAU RUA.
Lo gia: truc giua. Truc ve tren layer Defpoints. Sprinkler: tat theo cau hinh ("bo_tri_sprinkler": false).
Thong so: cau_hinh_tran.json -> "bo_tri_moi". PCCC / dieu hoa la PHUONG AN SO BO.

    python bo_tri_tran.py <file.dxf> --out-dir <thu muc> [--du-an ten] [--layer-ten A-Dimension]
Xuat: bo_tri_tran.json (thiet bi + truc cho ve_com.py), BaoCaoBoTriTran.xlsx, xem_bo_tri_<can>.png, ve_bo_tri_tran.scr.
"""
import argparse
import io
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
        fp = affinity.rotate(box(x - c["rong"] / 2, y - c["cao"] / 2, x + c["rong"] / 2, y + c["cao"] / 2), rot, origin=(x, y))
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


# ------------------------------------------------------------------------------------------------ bo tri mot phong
def bo_tri_phong(bt, r, nt_phong, can_poly):
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
    hcn, doans, doan_bep, hoc, wc_dai = None, [], [], [], False
    if wc:
        xy = list(U.minimum_rotated_rectangle.exterior.coords)
        dai, ngan = sorted((math.dist(xy[0], xy[1]), math.dist(xy[1], xy[2])), reverse=True)
        if dai / max(ngan, 1) >= b["wc_ty_le_dai"]:
            # WC dai: truc giua theo chieu dai, 2 dau cach tuong 450 (2 den dau tien)
            doans, wc_dai = doan_giua(U, b["den_wc_dai_cach_tuong"]), True
        else:
            # WC vuong: vong truc cach mep trong tuong 450
            o = b["truc_wc_vuong_cach_tuong"]
            doans = doan_vong(U, [o], 100)[0] or doan_giua(U, o)
    elif logia:
        doans = doan_giua(U, 300)
    else:
        # 1 hinh chu nhat khep kin theo tuong chinh, lon nhat trong phong (bo hoc), lui 600 (khong du: 500)
        goc = goc_tuong_chinh(P0)
        R0 = hcn_lon_nhat(U, goc)
        if R0 is not None:
            for o in b["truc_cach_tuong"]:
                R = R0.buffer(-o, join_style=2)
                if R.is_empty:
                    continue
                xy = list(R.exterior.coords)
                if min(math.dist(xy[0], xy[1]), math.dist(xy[1], xy[2])) >= 300:
                    hcn = [xy[0], xy[1], xy[2], xy[3]]
                    doans = [Doan(p, q) for p, q in zip(xy, xy[1:])]
                    break
            if not doans:
                doans = doan_giua(R0, b["truc_cach_tuong"][1])
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
                doan_bep = truc_bep(U, kh_bep, b["truc_cach_tuong"][0])
                doans += doan_bep
        if not doans:
            doans = doan_giua(U, b["truc_cach_tuong"][1])
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

    # ---- 1. thiet bi chuc nang ngoai truc
    if loai & {"khach", "an", "bep"}:
        for f in ban:
            them("LT-PEND", (f["x"], f["y"]), 0, "tâm mặt bàn ăn")
    if wc and (chau or guong):
        f = (chau or guong)[0]
        them("LT-MIR-D65", (f["x"], f["y"]), 0, "đèn D65 tại tâm chậu rửa")
    if bep:
        them("HV-EXG-200", (bep[0]["x"], bep[0]["y"]), 0, "miệng gió hút bếp trên bếp nấu (theo chụp hút)")

    # ---- 2. den
    dens = []
    goi = giuong.get("vung_goi") if giuong else None
    if hcn is not None and loai & set(b["phong_co_luoi_den"]):
        # 4 goc truoc (dung goc, ke ca phia dau giuong), canh > 2400 them den giua (tranh vung goi), cach nhau >= 1200
        for p in hcn:
            if all(math.dist(p, q) >= ng["den_kc_toi_thieu"] - 1 for q in dens):
                dens.append(p)
        for p, q in zip(hcn, hcn[1:] + hcn[:1]):
            L = math.dist(p, q)
            if L > b["den_kc_toi_da"]:
                n = math.ceil(L / b["den_kc_toi_da"])
                for k in range(1, n):
                    m = (p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n)
                    if (goi is None or not goi.contains(Point(m))) and all(math.dist(m, x) >= ng["den_kc_toi_thieu"] - 1 for x in dens):
                        dens.append(m)
        dens = [p for p in dens if not any(d["ma"] == "LT-PEND" and math.dist(p, (d["x"], d["y"])) < 600 for d in moi)]
        for p in dens:
            them("LT-DL-D90", p, 0, "đèn chung: góc / giữa cạnh hình chữ nhật trục")
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
    if logia:
        d = doans[0]
        n = max(1, round(d.L / b["den_ngoai_kc"]))
        for k in range(n):
            them("LT-OUT", d.diem(d.L * (k + 0.5) / n), 0, "đèn ngoài nhà trên trục giữa lô gia")

    # ---- 3. cua gio dieu hoa: cung chieu (doc 2 canh dai), phan bo deu, o giua hai den cach nhau > 1400
    gio_cap, gio_hoi = [], []
    if hcn is not None and loai & set(b["phong_co_gio_tran"]):
        n = max(1, round(P.area / 1e6 / b["gio_dt_moi_cap"]))
        canh = [Doan(p, q) for p, q in zip(hcn, hcn[1:] + hcn[:1])]
        i0 = 0 if canh[0].L >= canh[1].L else 1
        A, B = canh[i0], canh[i0 + 2]
        ref = can_poly.centroid if can_poly is not None else P.centroid
        if math.dist(A.diem(A.L / 2), (ref.x, ref.y)) > math.dist(B.diem(B.L / 2), (ref.x, ref.y)):
            A, B = B, A                                              # A = canh dai phia trong can -> gio hoi
        kmin = b["gio_khe_den_toi_thieu"]
        kA = [k for k in khe_tren_truc([A], dens, kmin) if k[1] > kmin]
        kB = [k for k in khe_tren_truc([B], dens, kmin) if k[1] > kmin]
        da = []
        for j in range(n):
            muc = A.L * (j + 0.5) / n                                # phan bo deu theo chieu dai phong
            def khong_chong(p, d):
                fp = affinity.rotate(box(p[0] - 600, p[1] - 75, p[0] + 600, p[1] + 75), d.goc, origin=p)
                return all(not x["fp"].intersects(fp.buffer(khe)) for x in moi)

            def vi_tri_khe(ks, d):
                """Moi khoang giua hai den: vi tri cua gio gan giua khoang nhat ma khong chong thiet bi (dich buoc 100,
                van nam gon giua hai den)."""
                out = []
                for p, L, _ in ks:
                    tm = d.t(p)
                    m = L / 2 - (600 + R_DEN + 50)
                    for dt in sorted(range(-int(m // 100) * 100, int(m // 100) * 100 + 1, 100), key=abs) if m >= 0 else []:
                        q = d.diem(tm + dt)
                        if khong_chong(q, d):
                            out.append((q, L, d))
                            break
                return out
            ung = [k for k in vi_tri_khe(kA, A) if all(math.dist(k[0], x[0]) > 1 for x in da)]
            ung_b = vi_tri_khe(kB, B)
            # chon cap khoang (A, B) gan vi tri phan bo deu nhat; khong chong len thiet bi khac (vd den tha)
            cap = sorted(((abs(A.t(ka[0]) - muc) + abs(B.t(kb[0]) - B.t(A.diem(muc))), ka, kb) for ka in ung for kb in ung_b),
                         key=lambda x: x[0])
            if not cap:
                break
            _, pa, pb = cap[0]
            da.append(pa)
            kA = [k for k in kA if abs(A.t(k[0]) - A.t(pa[0])) > k[1] / 2]
            kB = [k for k in kB if abs(B.t(k[0]) - B.t(pb[0])) > k[1] / 2]
            gio_hoi.append(them("HV-RAG-1200x150", pa[0], A.goc, "gió hồi: giữa hai đèn trên cạnh dài phía trong căn"))
            gio_cap.append(them("HV-SAG-1200x150", pb[0], B.goc, "gió cấp: giữa hai đèn trên cạnh dài đối diện, cùng chiều"))
        if len(gio_cap) < n:
            bt.note(r, f"Chỉ đặt được {len(gio_cap)}/{n} cặp cửa gió cùng chiều (thiếu khoảng giữa hai đèn > {kmin} mm trên cạnh dài).")

    # ---- 4. WC: den + hut mui
    if wc:
        dws = []
        if wc_dai:
            d = doans[0]
            n = max(1, math.ceil(d.L / b["den_kc_toi_da"])) if d.L > b["den_kc_toi_da"] else 1
            for k in range(n + 1):
                dws.append((d.diem(d.L * k / n), "đèn WC trên trục giữa" + (", cách tường 450" if k in (0, n) else "")))
        else:
            if bon_cau:
                dws.append((len_truc((bon_cau[0]["x"], bon_cau[0]["y"])), "đèn WC trên trục, ngang bồn cầu"))
            if vt is not None:
                dws.append((len_truc((vt.centroid.x, vt.centroid.y)), "đèn WC trên trục, ngang vùng tắm"))
            if not dws:
                c = truc.interpolate(0.5, normalized=True)
                dws.append(((c.x, c.y), "đèn WC trên trục"))
        nhan = []
        for p, ly in dws:
            if all(math.dist(p, q) >= 2 * (R_DEN + khe) for q, _ in nhan):
                nhan.append((p, ly))
                them("LT-DL-WC-D90", p, 0, ly)
        c = P0.centroid
        p = len_truc((c.x, c.y)) if wc_dai else (c.x, c.y)
        p = tranh_den(p, [q for q, _ in nhan], 100 + R_DEN + khe) if wc_dai else p
        if p is not None and trong(p, 100):
            them("HV-EAG-200", p, 0, "hút mùi tại tâm phòng vệ sinh")
        else:
            bt.note(r, "Tâm phòng vệ sinh vướng đèn / thiết bị: chưa đặt hút mùi.")

    # ---- 5. dau bao khoi: tren truc; PN phia chan giuong; vuong den -> cach den 300
    tat_den = dens + [(d["x"], d["y"]) for d in moi if d["ma"] in ("LT-DL-WC-D90", "LT-OUT")]
    if loai & set(b["phong_co_dau_bao_khoi"]) and not (wc or logia):
        p = None
        if giuong is not None and goi is not None and hcn is not None:
            canh = [Doan(a, c) for a, c in zip(hcn, hcn[1:] + hcn[:1])]
            gc = goi.centroid
            ung = [d for d in canh if abs(d.u[0] * (giuong["y"] - gc.y) - d.u[1] * (giuong["x"] - gc.x)) > 0.5 * math.dist((giuong["x"], giuong["y"]), (gc.x, gc.y))]
            d = max(ung or canh, key=lambda d: d.kc((gc.x, gc.y)))
            p = d.diem(min(max(d.t((giuong["x"], giuong["y"])), 0), d.L))
            ly = "đầu báo khói trên trục phía chân giường"
        else:
            khe_ = khe_tren_truc([d for d in doans if d not in doan_bep], tat_den, 2 * (R_DEN + 70 + khe))
            khe_ = [k for k in khe_ if trong(k[0], khe + 60)]
            if gio_cap:
                cc = unary_union([d["fp"] for d in gio_cap])
                khe_ = [k for k in khe_ if cc.distance(Point(k[0])) >= ng["dau_bao_cach_gio_cap"]] or khe_
            c = P.centroid
            if khe_:
                p = min(khe_, key=lambda k: math.dist(k[0], (c.x, c.y)))[0]
            ly = "đầu báo khói trên trục, giữa hai đèn"
        if p is not None:
            p2 = tranh_den(p, tat_den, 300)
            if p2 is not None and trong(p2, khe + 60):
                them("FA-SMOKE", p2, 0, ly + ("" if p2 == p else ", cách đèn 300"))
            else:
                bt.note(r, "Không đặt được đầu báo khói trên trục (vướng đèn / thiết bị).")
    # dau bao nhiet: CHI trong bep, tren truc dat den cua bep
    if bep:
        truc_h = doan_bep or (doans if "bep" in loai and not (loai & {"khach", "an"}) else [])
        if truc_h:
            p = tranh_den(len_truc((bep[0]["x"], bep[0]["y"]), truc_h), tat_den, 300)
            if p is not None and trong(p, khe + 60):
                them("FA-HEAT", p, 0, "đầu báo nhiệt trên trục đèn bếp, ngang bếp nấu")
            else:
                bt.note(r, "Không đặt được đầu báo nhiệt trên trục bếp.")
        else:
            bt.note(r, "Không có trục bếp: chưa đặt đầu báo nhiệt.")

    # ---- 6. lo tham 600
    if gio_cap:
        # P. khach: NGOAI truc, gan cum gio hoi (bao tri may dieu hoa am tran), canh theo tuong chinh
        goc = goc_tuong_chinh(P0)
        vung = U.buffer(-(305 + khe), join_style=2).difference(truc.buffer(305 + khe))
        if hoc:
            vung = vung.difference(unary_union(hoc))
        vung = vung.difference(unary_union([d["fp"].buffer(305 + khe) for d in moi] + [f["fp"] for f in sofa + ban]))
        if not vung.is_empty:
            mx = gio_hoi[0] if gio_hoi else gio_cap[0]
            q = nearest_points(vung, Point(mx["x"], mx["y"]))[0]
            them("AC-AP-600", (q.x, q.y), goc, "lỗ thăm ngoài trục, gần máy điều hòa âm trần")
        else:
            bt.note(r, "Không còn chỗ ngoài trục cho lỗ thăm 600.")
    elif wc:
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
    L = ["CMDECHO", "0", "OSMODE", "0", "ATTREQ", "0", "FILEDIA", "0",
         "(defun mk-lay (n c) (if (not (tblsearch \"LAYER\" n)) (entmake (list (cons 0 \"LAYER\") (cons 100 \"AcDbSymbolTableRecord\") "
         "(cons 100 \"AcDbLayerTableRecord\") (cons 2 n) (cons 70 0) (cons 62 c) (cons 6 \"Continuous\")))) n)"]
    for lay in sorted({d["layer"] for d in ds}):
        L.append(f"(mk-lay {ls(lay)} {mau.get(lay, 7)})")
    lt = cfg["bo_tri_moi"]["layer_truc"]
    for _, _, a, b in truc:
        L.append(f'(entmake (list (cons 0 "LINE") (cons 8 {ls(lt)}) (list 10 {a[0]:.1f} {a[1]:.1f} 0.0) (list 11 {b[0]:.1f} {b[1]:.1f} 0.0)))')
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
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    cfg = json.load(open(a.cau_hinh, encoding="utf-8"))
    if a.layer_ten:
        cfg["layer_ten_phong"] = a.layer_ten
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
    for r in ds_phong:
        if r["poly"] is None:
            continue
        if any(r["poly"].contains(Point(d["x"], d["y"])) for d in co_san):
            bt.note(r, "Phòng đã có thiết bị trần: không bố trí thêm (dùng soat_tran.py để soát).")
            continue
        nt_phong = [f for f in noi_that if r["poly"].buffer(200).contains(Point(f["x"], f["y"]))
                    or r["poly"].intersection(f["fp"]).area > 0.5 * f["fp"].area]
        bo_tri_phong(bt, r, nt_phong, can_poly.get(r["can"]))
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
    json.dump(dict(thu_vien=a.thu_vien, layer_truc=cfg["bo_tri_moi"]["layer_truc"], truc=truc, thiet_bi=ra),
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

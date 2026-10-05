#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Bo tri MOI thiet bi tran can ho (Archivina) THEO TRUC - skill thiet-ke-tran-ch (nguyen tac nguoi dung chot 05/10/2026).

1. Truc dat den / thiet bi (ve tren layer Defpoints):
   - P. khach (ke ca bep chung phong khach -> dung chung he truc): vong truc cach mep trong tuong va mat khoi tu
     (tu bep, tu ao / tu noi that) 600 (khong du cho thi 500) mm.
   - Bep rieng: 1 truc song song chieu dai khoi tu bep chinh, nam giua khong gian bep.
   - Phong ngu (va da nang, hanh lang, phong chua ro): vong truc cach mep trong tuong / mat tu ao 500-600 mm moi huong.
   - WC: dai (canh dai / canh ngan >= 1,3): 1 truc giua theo canh dai; vuong: vong truc cach deu 4 canh 300-600 mm.
   - Lo gia: truc giua theo chieu dai. Phong qua hep cho vong truc: truc giua.
2. Tren truc: mieng gio / quat hut dat truoc; den cach nhau >= 1200 (>= 1500 khi phong co mieng gio), xen ke hai ben
   mieng gio, can doi theo giuong / sofa / ban an / thiet bi ve sinh; dau bao dat o khoang giua hai den.
   Den tha tai tam mat ban an, den roi guong tren truc guong (thiet bi chuc nang, ngoai truc).
3. Sprinkler: khong theo truc nhung thang hang (cung X hoac Y) voi mot thiet bi da co; vong phu R2000 phu kin phong,
   cach tuong <= 2000; 93 do gan bep. Lo tham 600 tren truc, o khoang trong.
Thong so: cau_hinh_tran.json -> "bo_tri_moi". PCCC / dieu hoa la PHUONG AN SO BO.
Sau khi bo tri, chay lai bo soat (soat_tran.soat) tren chinh ket qua de bao cao.

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


def diem_tren_truc(f, P, d):
    (qx, qy), (nx, ny) = truc_thiet_bi(f, P)
    return qx + nx * d, qy + ny * d


def khoi_tu_bep(P, ds_bep, sau):
    """Khoi tu bep chinh: dai sau `sau` (hoac sau hon thiet bi) doc tuong cua bep nau, phu het bep nau / chau / may rua
    tren cung tuong (+300 hai dau). Tra ve (polygon, diem tren tuong, phap tuyen, huong doc tuong)."""
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
    return Polygon(pts).buffer(0), (qx, qy), (nx, ny), (wx, wy)


# ------------------------------------------------------------------------------------------------ den tren truc
def vi_tri_den(d, s_min, s_tg, s_max, khe, neo=None, co_dinh=()):
    """Cac tham so t dat den tren doan d. co_dinh: [(t tam, nua chieu dai)] thiet bi da dat tren doan -> den xen ke hai
    ben (cach tam >= max(s_min/2, nua dai + khe + R_DEN)) roi keo ra hai phia buoc s_tg. Khong co: doi xung qua neo
    (chieu cua tam noi that len truc, mac dinh giua doan), buoc gan s_tg nhat trong [s_min, s_max], phan con lai keo dai."""
    L = d.L
    ts = []
    if co_dinh:
        for tc, h in co_dinh:
            k = max(s_min / 2, h + khe + R_DEN)
            ts += [tc - k, tc + k]
        lo, hi, buoc = min(ts), max(ts), s_tg
    else:
        an = L / 2 if neo is None else min(max(neo, 0.0), L)
        h = min(an, L - an)
        pa = [([an], None)]
        for m in range(1, 40):
            s = h / m
            if s < s_min - 1:
                break
            if s <= s_max:
                pa.append(([an + k * s for k in range(-m, m + 1)], s))
        for m in range(1, 40):
            s = 2 * h / (2 * m - 1)
            if s < s_min - 1:
                break
            if s <= s_max:
                pa.append(([an + (k + 0.5) * s for k in range(-m, m)], s))
        ts, buoc = min(pa, key=lambda x: (abs((x[1] or 2 * h + s_max) - s_tg), -len(x[0])))
        buoc = buoc or s_tg
        buoc = max(buoc, s_min)
        lo, hi = min(ts), max(ts)
    t = lo - buoc
    while t >= -1:
        ts.append(t)
        t -= buoc
    t = hi + buoc
    while t <= L + 1:
        ts.append(t)
        t += buoc
    return sorted(t for t in ts if -1 <= t <= L + 1)


def khe_tren_truc(doans, dens, rong_min):
    """Cac khoang trong giua 2 den lien ke tren cung doan (hoac doan khong co den): (diem giua, do dai khoang, doan)."""
    out = []
    for d in doans:
        ts = sorted(d.t((x, y)) for x, y in dens if d.kc((x, y)) < 2 and -2 <= d.t((x, y)) <= d.L + 2)
        moc = [0.0] + ts + [d.L] if not ts else ts
        if not ts:
            if d.L >= rong_min:
                out.append((d.diem(d.L / 2), d.L, d))
            continue
        for t0, t1 in zip(moc, moc[1:]):
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
    guong = [f for f in nt_phong if f["loai"] == "guong"] or [f for f in nt_phong if f["loai"] == "chau_rua"]
    tam = [f for f in nt_phong if f["loai"] in ("sen_tam", "vach_tam")]
    vt = unary_union([f["fp"] for f in tam]) if tam else None
    wc, logia = "wc" in loai, "logia" in loai
    khach = bool(loai & {"khach", "an"})
    moi = []

    def them(ma, p, rot=0.0, ly_do=""):
        d = bt.them(ma, p[0], p[1], rot, ly_do, r)
        moi.append(d)
        return d

    def trong(p, cach_tb=khe + R_DEN):
        return all(d["fp"].distance(Point(p)) >= cach_tb for d in moi)

    # ---- vung tran dung duoc + truc
    cam_noi_that = []
    tu_bep = None
    if bep:
        ds_bep = bep + [f for f in nt_phong if f["loai"] == "chau_rua" and f["fp"].distance(bep[0]["fp"]) < 3000]
        tu_bep = khoi_tu_bep(P0, ds_bep, b["tu_bep_sau"])
        cam_noi_that.append(tu_bep[0])
    cam_noi_that += [f["fp"] for f in tu]
    U = P0.difference(unary_union(cam_noi_that)) if cam_noi_that else P0
    U = max(getattr(U, "geoms", [U]), key=lambda g: g.area)
    U2 = U.buffer(-300, join_style=2).buffer(300, join_style=2)          # lam tron hoc < 600 (cua, ho cot) cho truc thang
    U = max(getattr(U2, "geoms", [U2]), key=lambda g: g.area) if not U2.is_empty and U2.area > 0.8 * U.area else U
    if wc:
        xy = list(U.minimum_rotated_rectangle.exterior.coords)
        dai, ngan = sorted((math.dist(xy[0], xy[1]), math.dist(xy[1], xy[2])), reverse=True)
        if dai / max(ngan, 1) >= b["wc_ty_le_dai"]:
            doans = doan_giua(U, b["truc_wc_cach_tuong"][0])
        else:
            o = min(max((ngan - ng["den_kc_toi_thieu"]) / 2, b["truc_wc_cach_tuong"][0]), b["truc_wc_cach_tuong"][1])
            doans = doan_vong(U, [o, b["truc_wc_cach_tuong"][0]], 100)[0] or doan_giua(U, b["truc_wc_cach_tuong"][0])
    elif logia:
        doans = doan_giua(U, 300)
    elif "bep" in loai and not khach and tu_bep is not None:
        # bep rieng: 1 truc song song tu bep chinh, giua khong gian tu mat tu toi bien doi dien
        poly, (qx, qy), (nx, ny), (wx, wy) = tu_bep
        mx, my = poly.centroid.x, poly.centroid.y
        tia = LineString([(mx, my), (mx + nx * 20000, my + ny * 20000)]).intersection(U)
        doans = []
        if not tia.is_empty:
            seg = max(getattr(tia, "geoms", [tia]), key=lambda g: g.length)
            c = list(seg.coords)
            cx, cy = (c[0][0] + c[-1][0]) / 2, (c[0][1] + c[-1][1]) / 2
            g = LineString([(cx - wx * 20000, cy - wy * 20000), (cx + wx * 20000, cy + wy * 20000)]).intersection(
                U.buffer(-b["truc_cach_tuong"][1], join_style=2))
            if not g.is_empty:
                g = max(getattr(g, "geoms", [g]), key=lambda q: q.length)
                c = list(g.coords)
                doans = [Doan(c[0], c[-1])]
    else:
        doans, o = doan_vong(U, b["truc_cach_tuong"])
        if doans:
            # phan phong hep nam ngoai tam vong truc (vd khu bep sau 1,1 m giua mat tu bep va tuong): truc giua rieng,
            # song song canh dai (= song song tu bep)
            R = Polygon([d.a for d in doans])
            con = U.difference(R.buffer(o + 50, join_style=2))
            for g in getattr(con, "geoms", [con]):
                if g.geom_type == "Polygon" and g.area >= 1.5e6:
                    xy = list(g.minimum_rotated_rectangle.exterior.coords)
                    if max(math.dist(xy[0], xy[1]), math.dist(xy[1], xy[2])) >= ng["den_kc_toi_thieu"]:
                        doans += doan_giua(g, 300)
        else:
            doans = doan_giua(U, b["truc_cach_tuong"][1])
    if not doans:
        bt.note(r, "Phòng quá hẹp: không dựng được trục đặt đèn.")
        return moi
    for d in doans:
        bt.truc.append((r["can"], r["ten"], d.a, d.b))
    truc = unary_union([LineString([d.a, d.b]) for d in doans])

    def len_truc(p):
        q = nearest_points(truc, Point(p))[0]
        return q.x, q.y

    def doan_cua(p):
        return min(doans, key=lambda d: d.kc(p))

    # ---- 1. thiet bi theo noi that (ngoai truc: den tha, den guong)
    if loai & {"khach", "an", "bep"}:
        for f in ban:
            them("LT-PEND", (f["x"], f["y"]), 0, "tâm mặt bàn ăn")
    if wc and guong:
        them("LT-MIR-D65", diem_tren_truc(guong[0], P, b["den_guong_cach_tuong"]), 0, "trục gương / chậu rửa (đèn chức năng)")

    # ---- 2. thiet bi co dinh tren truc: mieng gio, gio hut bep
    co_dinh = {id(d): [] for d in doans}
    gio_cap = []
    if loai & set(b["phong_co_gio_tran"]):
        n = max(1, round(P.area / 1e6 / b["gio_dt_moi_cap"]))
        cap = None
        for i, di in enumerate(doans):
            for dj in doans[i + 1:]:
                if abs(di.u[0] * dj.u[1] - di.u[1] * dj.u[0]) > 0.03:
                    continue
                kc_ = abs(di.u[0] * (dj.a[1] - di.a[1]) - di.u[1] * (dj.a[0] - di.a[0]))
                if kc_ < 1500:
                    continue
                t1, t2 = sorted((di.t(dj.a), di.t(dj.b)))
                lo, hi = max(0.0, t1), min(di.L, t2)
                if hi - lo >= 1600 and (cap is None or hi - lo > cap[3] - cap[2]):
                    cap = (di, dj, lo, hi)
        if cap is None:
            bt.note(r, "Không có cặp trục song song đủ dài để đặt miệng gió cấp/hồi.")
        else:
            di, dj, lo, hi = cap
            # gio hoi tren truc phia trong can (gan tam can hon), gio cap tren truc doi dien
            ref = can_poly.centroid if can_poly is not None else P.centroid
            m_i = di.diem((lo + hi) / 2)
            hoi_o_i = math.dist(m_i, (ref.x, ref.y)) <= math.dist(dj.diem(dj.t(m_i)), (ref.x, ref.y))
            sofa_cam = unary_union([f["fp"].buffer(200) for f in sofa]) if sofa else None
            dat = 0
            for k in range(n):
                tc0 = lo + (hi - lo) * (k + 0.5) / n
                for dt in [0] + [s * j * 200 for j in range(1, 8) for s in (1, -1)]:
                    tc = tc0 + dt
                    if tc - 600 < lo - 1 or tc + 600 > hi + 1:
                        continue
                    pi_ = di.diem(tc)
                    pj_ = dj.diem(dj.t(pi_))
                    (pr, dr), (ps, ds_) = ((pi_, di), (pj_, dj)) if hoi_o_i else ((pj_, dj), (pi_, di))
                    fa = affinity.rotate(box(pr[0] - 600, pr[1] - 75, pr[0] + 600, pr[1] + 75), dr.goc, origin=pr)
                    fc = affinity.rotate(box(ps[0] - 600, ps[1] - 75, ps[0] + 600, ps[1] + 75), ds_.goc, origin=ps)
                    if not (U.buffer(-50).contains(fa) and U.buffer(-50).contains(fc)):
                        continue
                    if sofa_cam is not None and fc.intersects(sofa_cam):
                        continue
                    if any(d["fp"].intersects(fa.buffer(khe)) or d["fp"].intersects(fc.buffer(khe)) for d in moi):
                        continue
                    them("HV-RAG-1200x150", pr, dr.goc, "gió hồi trên trục phía trong phòng")
                    gio_cap.append(them("HV-SAG-1200x150", ps, ds_.goc, "gió cấp trên trục đối diện, song song gió hồi"))
                    co_dinh[id(dr)].append((dr.t(pr), 600))
                    co_dinh[id(ds_)].append((ds_.t(ps), 600))
                    dat += 1
                    break
            if dat < n:
                bt.note(r, f"Chỉ đặt được {dat}/{n} cặp miệng gió cấp/hồi trên trục (vướng sofa, hình phòng).")
    if bep:
        p = len_truc((bep[0]["x"], bep[0]["y"]))
        them("HV-EXG-200", p, 0, "miệng gió hút bếp: trục, ngang bếp nấu")
        co_dinh[id(doan_cua(p))].append((doan_cua(p).t(p), 100))
    if wc:
        # den theo truc thiet bi ve sinh (chieu tam bon cau / vung tam / chau len truc), quat hut xen giua
        diem_den = []
        if bon_cau:
            diem_den.append((len_truc((bon_cau[0]["x"], bon_cau[0]["y"])), "trục bồn cầu"))
        if vt is not None:
            diem_den.append((len_truc((vt.centroid.x, vt.centroid.y)), "trục vùng tắm"))
        if len(diem_den) < 2 and guong:
            diem_den.append((len_truc((guong[0]["x"], guong[0]["y"])), "trục chậu rửa"))
        if not diem_den:
            c = truc.interpolate(0.5, normalized=True)
            diem_den.append(((c.x, c.y), "giữa trục (không nhận diện được thiết bị vệ sinh)"))
            bt.note(r, "Không nhận diện được bồn cầu / chậu / sen: đèn đặt giữa trục, quạt hút cạnh đèn.")
        nhan = []
        for p, ly in diem_den:
            if all(math.dist(p, q) >= 2 * (R_DEN + khe) for q, _ in nhan):
                nhan.append((p, ly))
        for p, ly in nhan:
            them("LT-DL-WC-D90", p, 0, ly)
        if len(nhan) >= 2 and math.dist(nhan[0][0], nhan[1][0]) >= 2 * (R_DEN + khe) + 200:
            p = ((nhan[0][0][0] + nhan[1][0][0]) / 2, (nhan[0][0][1] + nhan[1][0][1]) / 2)
            them("HV-EAG-200", len_truc(p), 0, "quạt hút trên trục, xen giữa hai đèn")
        else:
            dd = doan_cua(nhan[0][0])
            t0 = dd.t(nhan[0][0])
            for t in (t0 + 450, t0 - 450, t0 + 350, t0 - 350):
                if 0 <= t <= dd.L and trong(dd.diem(t), khe + 100):
                    them("HV-EAG-200", dd.diem(t), 0, "quạt hút trên trục, cạnh đèn")
                    break
            else:
                bt.note(r, "Không đủ chỗ trên trục cho quạt hút.")

    # ---- 3. den chung tren truc
    dens = []
    if loai & set(b["phong_co_luoi_den"]) and not (wc or logia):
        s_min = b["den_kc_co_gio"] if gio_cap else ng["den_kc_toi_thieu"]
        neo_nt = [f for f in (sofa + ban + ([giuong] if giuong else []))]
        goi = giuong.get("vung_goi") if giuong else None
        cand = []
        for d in sorted(doans, key=lambda d: (not co_dinh[id(d)], -d.L)):
            neo = None
            gan = [f for f in neo_nt if -1 <= d.t((f["x"], f["y"])) <= d.L + 1]
            if gan:
                f = min(gan, key=lambda f: d.kc((f["x"], f["y"])))
                neo = d.t((f["x"], f["y"]))
            for t in vi_tri_den(d, s_min, b["den_kc_muc_tieu"], b["den_kc_toi_da"], khe, neo, co_dinh[id(d)]):
                cand.append(d.diem(t))
        vung = U.buffer(-b["truc_cach_tuong"][1] + 2, join_style=2)
        for p in cand:
            if not vung.contains(Point(p)) or not trong(p):
                continue
            if goi is not None and goi.contains(Point(p)):
                continue
            if any(d["ma"] == "LT-PEND" and math.dist(p, (d["x"], d["y"])) < 600 for d in moi):
                continue
            if all(math.dist(p, q) >= s_min - 1 for q in dens):
                dens.append(p)
        for p in dens:
            them("LT-DL-D90", p, 0, "đèn chung trên trục")
        if not dens:
            bt.note(r, "Không đặt được đèn chung trên trục (khoảng cách ≥ 1200, vướng thiết bị).")
    if logia:
        d = doans[0]
        n = max(1, round(d.L / b["den_ngoai_kc"]))
        for k in range(n):
            them("LT-OUT", d.diem(d.L * (k + 0.5) / n), 0, "đèn ngoài nhà trên trục giữa lô gia")

    # ---- 4. dau bao xen giua cac den
    tat_den = dens + [(d["x"], d["y"]) for d in moi if d["ma"] in ("LT-DL-WC-D90", "LT-OUT")]
    cach_cap = unary_union([d["fp"] for d in gio_cap]) if gio_cap else None

    def dat_khe(ma, dich, ly_do, them_dk=None):
        khe_ = [k for k in khe_tren_truc(doans, tat_den, 2 * (R_DEN + 70 + khe)) if trong(k[0], khe + 70)]
        if cach_cap is not None:
            khe_ = [k for k in khe_ if cach_cap.distance(Point(k[0])) >= ng["dau_bao_cach_gio_cap"]]
        if them_dk:
            khe_ = [k for k in khe_ if them_dk(k[0])]
        if not khe_:
            bt.note(r, f"Không còn khoảng trống trên trục cho {ma} ({ly_do}).")
            return None
        k = min(khe_, key=lambda k: math.dist(k[0], dich))
        return them(ma, k[0], 0, ly_do)

    if loai & set(b["phong_co_dau_bao_khoi"]) and not (wc or logia):
        c = P.centroid
        goi_ = giuong.get("vung_goi") if giuong else None
        dat_khe("FA-SMOKE", (c.x, c.y), "đầu báo khói trên trục, xen giữa hai đèn, cách gió cấp ≥ 1000",
                (lambda p: not goi_.buffer(100).contains(Point(p))) if goi_ is not None else None)
    if bep:
        dat_khe("FA-HEAT", (bep[0]["x"], bep[0]["y"]), "đầu báo nhiệt trên trục, gần bếp nhưng không ngay trên bếp",
                lambda p: bep[0]["fp"].distance(Point(p)) >= 500)

    # ---- 5. lo tham 600 tren truc (khoang trong du rong)
    can_lo = gio_cap or wc
    if can_lo:
        tranh = unary_union([f["fp"].buffer(300) for f in sofa + ban]) if (sofa or ban) else None
        khe_ = [k for k in khe_tren_truc(doans, tat_den + [(d["x"], d["y"]) for d in moi if d["cat"]["nhom"] in ("dau_bao_khoi", "dau_bao_nhiet")],
                                         2 * (305 + khe + R_DEN)) if trong(k[0], 305 + khe)]
        khe_ = [k for k in khe_ if (tranh is None or tranh.distance(Point(k[0])) > 0) and (vt is None or vt.distance(Point(k[0])) >= 305)
                and U.buffer(-300).contains(Point(k[0]))]
        if khe_:
            muc = gio_cap[0] if gio_cap else None
            k = min(khe_, key=lambda k: math.dist(k[0], (muc["x"], muc["y"])) if muc else (-vt.distance(Point(k[0])) if vt is not None else 0))
            them("AC-AP-600", k[0], doan_cua(k[0]).goc, "lỗ thăm trên trục, khoảng trống" + (" gần máy điều hòa" if muc else " xa vùng tắm"))
        else:
            bt.note(r, "Không còn khoảng trống trên trục cho lỗ thăm 600.")

    # ---- 6. sprinkler: thang hang voi thiet bi da co, phu R2000, cach tuong <= 2000
    if loai & set(b["phong_co_sprinkler"]) and not (wc or logia):
        R, tl = b["sprinkler_ban_kinh_phu"], b["sprinkler_ty_le_phu"]
        xs = sorted({round(d["x"]) for d in moi}) or [round(P.centroid.x)]
        ys = sorted({round(d["y"]) for d in moi}) or [round(P.centroid.y)]
        minx, miny, maxx, maxy = P.bounds
        cam = unary_union([f["fp"] for f in tu] + ([tu_bep[0]] if tu_bep else []))
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

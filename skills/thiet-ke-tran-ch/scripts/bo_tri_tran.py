#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Bo tri MOI thiet bi tran can ho (Archivina) tu mat bang co noi that - skill thiet-ke-tran-ch.

Thu tu dung bo cuc (thiet bi co dinh theo noi that truoc, roi cac thiet bi linh hoat chen vao khoang trong):
  1. theo noi that: den tha (tam mat ban an); WC: den roi guong (truc guong / chau), quat hut (tren bon cau),
     den WC (truc bon cau, tam vung tam)
  2. dieu hoa: cap mieng gio hoi/cap 1200x150 (P. khach / an), gio hoi phia trong phong
  3. den: lo gia (truc giua), luoi den chung (cach tuong / mat tu 600, khoang cach muc tieu 1500, toi thieu 1200,
     doi xung truc giuong, tranh vung goi, tu ao, den tha, mieng gio)
  4. PCCC (P1): sprinkler theo o phu (dien tich / khoang cach / cach tuong toi da), dat vao khoang trong cua o,
     93 do gan bep; dau bao khoi gan tam phong, cach gio cap >= 1000; dau bao nhiet + mieng gio hut gan bep
  5. lo tham 600: may dieu hoa am tran (gan cum gio hoi), WC (goc xa vung tam)
Thiet bi P1 khong bi bo vi den: den dat truoc nhung moi o phu sprinkler deu co dau (dat vao cho trong trong o).
Thong so trong cau_hinh_tran.json -> "bo_tri_moi" (rut tu ban ve mau Archivina). PCCC / dieu hoa la PHUONG AN SO BO.
Sau khi bo tri, chay lai bo soat (soat_tran.soat) tren chinh ket qua de bao cao.

    python bo_tri_tran.py <file.dxf> --out-dir <thu muc> [--du-an ten] [--layer-ten A-Dimension]
Xuat: bo_tri_tran.json (danh sach thiet bi moi cho ve_com.py), BaoCaoBoTriTran.xlsx, xem_bo_tri_<can>.png, ve_bo_tri_tran.scr.
"""
import argparse
import io
import json
import math
import os
import sys
import time

import ezdxf
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import nearest_points, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import soat_tran as st  # noqa: E402

SKILL = os.path.dirname(HERE)


class BoTri:
    def __init__(self, catalog, cfg):
        self.cat = {c["ma"]: c for c in catalog["thiet_bi"]}
        self.ng = cfg["nguong"]
        self.b = cfg["bo_tri_moi"]
        self.ds = []
        self.ghi_chu = []          # (can, phong, noi dung)

    def them(self, ma, x, y, rot=0.0, ly_do="", r=None):
        c = self.cat[ma]
        w, h = c["rong"], c["cao"]
        if round(rot) % 180 == 90:
            w, h = h, w
        d = dict(cat=c, ma=ma, x=x, y=y, fp=box(x - w / 2, y - h / 2, x + w / 2, y + h / 2), rot=rot, block=ma,
                 layer=c["layer"], handle=f"MOI{len(self.ds) + 1:03d}", insert=(x, y), ly_do=ly_do,
                 phong_moi=r["ten"] if r else "", can_moi=r["can"] if r else "")
        self.ds.append(d)
        return d

    def note(self, r, s):
        self.ghi_chu.append((r["can"], r["ten"], s))


def gan_nhat(vung, x, y):
    """Diem trong vung gan (x, y) nhat; None neu vung rong."""
    if vung is None or vung.is_empty:
        return None
    p = Point(x, y)
    if vung.contains(p):
        return p
    return nearest_points(vung, p)[0]


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


def chia_chu_nhat(P, dt_min=2.0e6, rong_min=1300):
    """Chia phong (gan truc giao, vd chu L) thanh cac o chu nhat: cat doc theo moi hoanh do dinh, gop dai cung cao do."""
    # lam tron hoc nho (khung cua, ho cot < 0,8 m) truoc khi chia
    Q = P.buffer(-400, join_style=2).buffer(400, join_style=2).simplify(20)
    Q = max(getattr(Q, "geoms", [Q]), key=lambda g: g.area) if not Q.is_empty else P
    P = Q
    minx, miny, maxx, maxy = P.bounds
    xs = sorted({round(x) for x, _ in P.exterior.coords})
    dai = []
    for x0, x1 in zip(xs, xs[1:]):
        s = box(x0, miny - 1, x1, maxy + 1).intersection(P)
        for g in getattr(s, "geoms", [s]):
            if g.geom_type == "Polygon" and g.area > 1:
                dai.append(box(*g.bounds))
    # gop tham lam: moi luot chon cap dai ke nhau cho o gop (hop theo x, giao theo y) lon nhat va lon hon ca hai dai
    # cu; phan du cua hai dai giu thanh o rieng (co the gop tiep)
    out = list(dai)
    for _ in range(60):
        best = None
        for i, a in enumerate(out):
            for j, b in enumerate(out):
                if i == j or abs(a.bounds[2] - b.bounds[0]) > 20:
                    continue
                y0, y1 = max(a.bounds[1], b.bounds[1]), min(a.bounds[3], b.bounds[3])
                if y1 - y0 < 1:
                    continue
                m = box(a.bounds[0], y0, b.bounds[2], y1)
                if m.area > max(a.area, b.area) + 1 and (best is None or m.area > best[0].area):
                    best = (m, i, j, y0, y1)
        if best is None:
            break
        m, i, j, y0, y1 = best
        a, b = out[i], out[j]
        out = [q for k, q in enumerate(out) if k not in (i, j)] + [m]
        for q in (a, b):
            if q.bounds[1] < y0 - 1:
                out.append(box(q.bounds[0], q.bounds[1], q.bounds[2], y0))
            if q.bounds[3] > y1 + 1:
                out.append(box(q.bounds[0], y1, q.bounds[2], q.bounds[3]))
    return [b for b in out if b.area >= dt_min and min(b.bounds[2] - b.bounds[0], b.bounds[3] - b.bounds[1]) >= rong_min]


def luoi_den_phong(P, cam, ng, giuong, N_tong, kc_muc_tieu):
    """Luoi den chung tren tran dung duoc (da tru dai tu ao). Phong gan chu nhat: mot khoi; phong chu L: tung o chu nhat,
    o lon truoc, so den chia theo dien tich. Khoang cach muc tieu theo mau, khong xep duoc moi ha ve toi thieu (1200)."""
    o = [P] if P.area / box(*P.bounds).area >= 0.8 else sorted(chia_chu_nhat(P), key=lambda b: -b.area)
    tong = sum(b.area for b in o) or 1.0
    trong = P.buffer(-ng["den_cach_tuong_toi_thieu"] + 1, join_style=2)
    pts = []
    for b in o:
        N = max(2, math.ceil(N_tong * b.area / tong))
        g = giuong if giuong is not None and b.contains(Point(giuong["x"], giuong["y"])) else None
        if g is not None and g.get("vung_goi") is not None and g.get("truc"):
            # dau giuong coi nhu tuong: cat het chieu phong toi mep vung goi - 500 (sau khi lui 600, cot den dau tien
            # nam ngay sau vung goi 100 mm)
            gx0, gy0, gx1, gy1 = g["vung_goi"].bounds
            bx0, by0, bx1, by1 = b.bounds
            if g["truc"][0] == "y":
                cat = box(bx0 - 1, by0 - 1, gx1 - 500, by1 + 1) if (gx0 + gx1) / 2 < g["x"] else box(gx0 + 500, by0 - 1, bx1 + 1, by1 + 1)
            else:
                cat = box(bx0 - 1, by0 - 1, bx1 + 1, gy1 - 500) if (gy0 + gy1) / 2 < g["y"] else box(bx0 - 1, gy0 + 500, bx1 + 1, by1 + 1)
            b2 = b.difference(cat)
            if not b2.is_empty:
                b = max(getattr(b2, "geoms", [b2]), key=lambda q: q.area)
        # khoang cach muc tieu (mau) va toi thieu: lay phuong an nhieu den hon, bang nhau thi uu tien muc tieu
        moi = max((st.bo_tri_lai_den(dict(poly=b), [None] * N, cam, dict(ng, den_kc_toi_thieu=kc), g)
                   for kc in (kc_muc_tieu, ng["den_kc_toi_thieu"])), key=len)
        for x, y in moi:
            if trong.contains(Point(x, y)) and all(math.dist((x, y), q) >= ng["den_kc_toi_thieu"] for q in pts):
                pts.append((x, y))
        # bo sung: doc cac duong lui 600 va duong truc giua cua o (xen ke voi mieng gio nhu ban ve mau), cach >= muc tieu
        A = b.buffer(-ng["den_cach_tuong_uu_tien"], join_style=2)
        if A.is_empty or len([p for p in pts if b.contains(Point(p))]) >= N:
            continue
        x0, y0, x1, y1 = A.bounds
        duong = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1)),
                 (((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)), ((x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2))]
        for (ax, ay), (bx, by) in duong:
            L = math.dist((ax, ay), (bx, by))
            for i in range(int(L // 100) + 1):
                if len([p for p in pts if b.contains(Point(p))]) >= N:
                    break
                t = i * 100 / L if L else 0
                q = (ax + (bx - ax) * t, ay + (by - ay) * t)
                P_ = Point(q)
                if not trong.contains(P_) or (cam is not None and not cam.is_empty and cam.contains(P_)):
                    continue
                if g is not None and g.get("vung_goi") is not None and g["vung_goi"].contains(P_):
                    continue
                if all(math.dist(q, p) >= kc_muc_tieu - 1 for p in pts):
                    pts.append(q)
    return pts


def bo_tri_phong(bt, r, nt_phong, can_poly):
    P = r["poly"]
    loai = set(r["loai"])
    b, ng = bt.b, bt.ng
    tu = [f for f in nt_phong if f["loai"] == "tu_ao"]
    cam_tu = unary_union([f["fp"] for f in tu]).buffer(150, join_style=2) if tu else None
    giuong = next((f for f in nt_phong if f["loai"] == "giuong"), None)
    ban = [f for f in nt_phong if f["loai"] == "ban_an"]
    sofa = [f for f in nt_phong if f["loai"] == "sofa"]
    bep = [f for f in nt_phong if f["loai"] == "bep_nau"]
    bon_cau = [f for f in nt_phong if f["loai"] == "bon_cau"]
    guong = [f for f in nt_phong if f["loai"] == "guong"] or [f for f in nt_phong if f["loai"] == "chau_rua"]
    tam = [f for f in nt_phong if f["loai"] in ("sen_tam", "vach_tam")]
    vt = unary_union([f["fp"] for f in tam]) if tam else None
    wc, logia = "wc" in loai, "logia" in loai
    moi = []

    def da_dat(buf=300, tru=None):
        g = [d["fp"].buffer(buf, join_style=2) for d in moi if d is not tru]
        return unary_union(g) if g else None

    def vung_cho(lui, buf_tb=300, them=None):
        A = P.buffer(-lui, join_style=2)
        for g in (cam_tu, da_dat(buf_tb), them):
            if g is not None and not A.is_empty:
                A = A.difference(g)
        return A

    def dat(ma, x, y, rot=0.0, ly_do="", lui=None, buf_tb=300, them=None):
        c = bt.cat[ma]
        half = max(c["rong"], c["cao"]) / 2
        q = gan_nhat(vung_cho(lui if lui is not None else half + 50, buf_tb, them), x, y)
        if q is None:
            bt.note(r, f"Không còn chỗ đặt {ma} ({ly_do}).")
            return None
        d = bt.them(ma, q.x, q.y, rot, ly_do, r)
        moi.append(d)
        return d

    def goc_trong(lui, buf_tb, them):
        A = vung_cho(lui, buf_tb, them)
        return [Point(p) for g in getattr(A, "geoms", [A]) if not A.is_empty for p in g.exterior.coords[:-1]]

    # ---- 1. theo noi that
    if loai & {"khach", "an", "bep"}:
        for f in ban:
            dat("LT-PEND", f["x"], f["y"], 0, "tâm mặt bàn ăn", lui=200)
    if wc:
        if guong:
            x, y = diem_tren_truc(guong[0], P, b["den_guong_cach_tuong"])
            dat("LT-MIR-D65", x, y, 0, "trục gương / chậu rửa", lui=150, buf_tb=50)
        if bon_cau:
            x, y = diem_tren_truc(bon_cau[0], P, b["quat_hut_cach_tuong"])
            dat("HV-EAG-200", x, y, 0, "trên bồn cầu (nguồn mùi)", lui=150, buf_tb=100)
            x, y = diem_tren_truc(bon_cau[0], P, b["den_wc_cach_tuong_sau_bon_cau"])
            dat("LT-DL-WC-D90", x, y, 0, "trục bồn cầu", lui=300, buf_tb=200)
        if vt is not None and vt.area > 0.4e6:
            dat("LT-DL-WC-D90", vt.centroid.x, vt.centroid.y, 0, "tâm vùng tắm", lui=300, buf_tb=200)
        elif tam:
            x, y = diem_tren_truc(tam[0], P, 600)
            dat("LT-DL-WC-D90", x, y, 0, "trục sen tắm", lui=300, buf_tb=200)
        if not (bon_cau or guong or tam):
            c = P.representative_point()
            dat("LT-DL-WC-D90", c.x, c.y, 0, "không nhận diện được thiết bị vệ sinh: đặt giữa phòng")
            bt.note(r, "Không nhận diện được bồn cầu / chậu / sen: đèn WC đặt giữa phòng, chưa đặt quạt hút.")

    # ---- 2. dieu hoa: cap mieng gio hoi / cap 1200x150 (P. khach / an)
    hop = []
    if loai & set(b["phong_co_gio_tran"]):
        n = max(1, round(P.area / 1e6 / b["gio_dt_moi_cap"]))
        # phong chu L: dat cap gio trong o chu nhat lon nhat (khong theo hop bao ca phong)
        o = chia_chu_nhat(P) if P.area / box(*P.bounds).area < 0.8 else []
        minx, miny, maxx, maxy = max(o, key=lambda q: q.area).bounds if o else P.bounds
        ngang = (maxx - minx) >= (maxy - miny)
        rong = (maxy - miny) if ngang else (maxx - minx)
        kc_cap = min(b["gio_cap_cach_gio_hoi"], rong - 2 * b["gio_hoi_cach_tuong"])
        tranh_cap = unary_union([f["fp"].buffer(200) for f in sofa]) if sofa else None
        vung = P.buffer(-100, join_style=2)
        ket = []
        for phia in (0, 1):
            ds_cap = []
            for i in range(n):
                t = (minx if ngang else miny) + ((maxx - minx) if ngang else (maxy - miny)) * (i + 0.5) / n
                if ngang:
                    yR = miny + b["gio_hoi_cach_tuong"] if phia == 0 else maxy - b["gio_hoi_cach_tuong"]
                    ds_cap.append(((t, yR), (t, yR + kc_cap * (1 if phia == 0 else -1)), 0.0))
                else:
                    xR = minx + b["gio_hoi_cach_tuong"] if phia == 0 else maxx - b["gio_hoi_cach_tuong"]
                    ds_cap.append(((xR, t), (xR + kc_cap * (1 if phia == 0 else -1), t), 90.0))
            cam = unary_union([g for g in (cam_tu, da_dat(300)) if g is not None]) if (cam_tu is not None or moi) else None
            h_ = []
            for pr, ps, rot in ds_cap:
                for dt in [0] + [s * k * 200 for k in range(1, 8) for s in (1, -1)]:
                    a = (pr[0] + (dt if rot == 0 else 0), pr[1] + (dt if rot == 90 else 0))
                    c = (ps[0] + (dt if rot == 0 else 0), ps[1] + (dt if rot == 90 else 0))
                    fa = box(a[0] - 600, a[1] - 75, a[0] + 600, a[1] + 75) if rot == 0 else box(a[0] - 75, a[1] - 600, a[0] + 75, a[1] + 600)
                    fc = box(c[0] - 600, c[1] - 75, c[0] + 600, c[1] + 75) if rot == 0 else box(c[0] - 75, c[1] - 600, c[0] + 75, c[1] + 600)
                    if not (vung.contains(fa) and vung.contains(fc)):
                        continue
                    if cam is not None and (fa.intersects(cam) or fc.intersects(cam)):
                        continue
                    if tranh_cap is not None and fc.intersects(tranh_cap):
                        continue
                    h_.append((a, c, rot))
                    break
            # gio hoi uu tien phia trong can (gan tam can) khi cung so cap
            ref = can_poly.centroid if can_poly is not None else P.centroid
            ket.append((len(h_), -min((math.dist(a, (ref.x, ref.y)) for a, _, _ in h_), default=1e18), h_))
        ket.sort(key=lambda k: (k[0], k[1]), reverse=True)
        hop = ket[0][2]
        for a, c, rot in hop:
            moi.append(bt.them("HV-RAG-1200x150", a[0], a[1], rot, "gió hồi phía trong phòng, cách tường 600", r))
            moi.append(bt.them("HV-SAG-1200x150", c[0], c[1], rot, "gió cấp song song gió hồi", r))
        if len(hop) < n:
            bt.note(r, f"Chỉ đặt được {len(hop)}/{n} cặp miệng gió cấp/hồi (vướng sofa, tủ, hình phòng).")
    gio_cap = [d for d in moi if d["ma"] == "HV-SAG-1200x150"]
    tranh_dau_bao = unary_union([d["fp"].buffer(ng["dau_bao_cach_gio_cap"]) for d in gio_cap]) if gio_cap else None

    # ---- 3. den
    if logia:
        minx, miny, maxx, maxy = P.bounds
        ngang = (maxx - minx) >= (maxy - miny)
        L = (maxx - minx) if ngang else (maxy - miny)
        n = max(1, round(L / b["den_ngoai_kc"]))
        for i in range(n):
            t = (minx if ngang else miny) + L * (i + 0.5) / n
            x, y = (t, (miny + maxy) / 2) if ngang else ((minx + maxx) / 2, t)
            dat("LT-OUT", x, y, 0, "trục giữa lô gia", lui=300)
    if loai & set(b["phong_co_luoi_den"]) and not (wc or logia):
        cam = unary_union([g for g in (da_dat(300),) if g is not None] +
                          [d["fp"].buffer(600) for d in moi if d["ma"] == "LT-PEND"]) if moi else Polygon()
        # tran dung duoc = phong tru dai tu ao keo het chieu phong (mat tu coi nhu tuong: hang den cach mat tu >= 500)
        minx, miny, maxx, maxy = P.bounds
        dai_tu = []
        for f in tu:
            fx0, fy0, fx1, fy1 = f["fp"].bounds
            dai_tu.append(box(minx - 1, fy0, maxx + 1, fy1) if (fx1 - fx0) >= (fy1 - fy0) else box(fx0, miny - 1, fx1, maxy + 1))
        Pd = P.difference(unary_union(dai_tu)) if dai_tu else P
        Pd = max(getattr(Pd, "geoms", [Pd]), key=lambda g: g.area)
        N_tong = max(1, math.ceil(P.area / 1e6 / b["den_dt_moi_den"]))
        pts = luoi_den_phong(Pd, cam, ng, giuong if "ngu" in loai else None, N_tong, b["den_kc_muc_tieu"])
        for x, y in pts:
            moi.append(bt.them("LT-DL-D90", x, y, 0, "lưới đèn chung", r))
        if not pts:
            bt.note(r, "Không bố trí được lưới đèn chung thỏa 1200/500 (phòng hẹp hoặc vướng thiết bị).")

    # ---- 4. PCCC (P1): sprinkler theo o phu, dat vao cho trong cua o
    if loai & set(b["phong_co_sprinkler"]) and not (wc or logia):
        minx, miny, maxx, maxy = P.bounds
        W, H = maxx - minx, maxy - miny
        best = None
        for nx in range(1, 9):
            for ny in range(1, 9):
                dx, dy = W / nx, H / ny
                if dx > b["sprinkler_kc_toi_da"] or dy > b["sprinkler_kc_toi_da"] or dx * dy > b["sprinkler_dt_toi_da"] * 1e6 \
                        or dx / 2 > b["sprinkler_cach_tuong_toi_da"] or dy / 2 > b["sprinkler_cach_tuong_toi_da"]:
                    continue
                cells = [box(minx + i * dx, miny + j * dy, minx + (i + 1) * dx, miny + (j + 1) * dy) for i in range(nx) for j in range(ny)]
                keep = [c for c in cells if c.intersection(P).area > 0.2 * c.area]
                sc = (len(keep), abs(dx - dy))
                if keep and (best is None or sc < best[0]):
                    best = (sc, keep)
        for c in best[1] if best else []:
            q = c.intersection(P)
            t = c.centroid if P.contains(c.centroid) else q.representative_point()
            A = vung_cho(300, 300, None)
            Aq = A.intersection(q) if not A.is_empty else A
            p = gan_nhat(Aq if not Aq.is_empty else A, t.x, t.y)
            if p is not None:
                moi.append(bt.them("SP-D15-68", p.x, p.y, 0, "lưới sprinkler sơ bộ theo mẫu", r))
            else:
                bt.note(r, "Một ô phủ sprinkler không còn chỗ trống: cần bộ môn PCCC bố trí.")
        if bep:
            sps = [d for d in moi if d["ma"] == "SP-D15-68"]
            if sps:
                s = min(sps, key=lambda d: bep[0]["fp"].distance(Point(d["x"], d["y"])))
                if bep[0]["fp"].distance(Point(s["x"], s["y"])) < 2500:
                    s.update(cat=bt.cat["SP-D15-93"], ma="SP-D15-93", block="SP-D15-93", ly_do="gần bếp nấu (93°C)")
    if loai & set(b["phong_co_dau_bao_khoi"]) and not (wc or logia):
        c = P.centroid if P.contains(P.centroid) else P.representative_point()
        dat("FA-SMOKE", c.x, c.y, 0, "gần tâm phòng, cách gió cấp ≥ 1000", lui=500, buf_tb=300, them=tranh_dau_bao)
    if bep:
        f = bep[0]
        (qx, qy), (nx, ny) = truc_thiet_bi(f, P)
        sau = abs((f["x"] - qx) * nx + (f["y"] - qy) * ny) * 2
        x, y = qx + nx * (sau + b["dau_bao_nhiet_cach_bep"]), qy + ny * (sau + b["dau_bao_nhiet_cach_bep"])
        dat("FA-HEAT", x, y, 0, "vùng bếp, không ngay trên bếp", lui=500, buf_tb=300, them=tranh_dau_bao)
        x, y = qx + nx * sau / 2, qy + ny * sau / 2
        dat("HV-EXG-200", x, y, 0, "trên bếp nấu (hút mùi)", lui=150, buf_tb=200)
    elif "bep" in loai:
        bt.note(r, "Không nhận diện được bếp nấu: chưa đặt đầu báo nhiệt / miệng gió hút bếp.")

    # ---- 5. lo tham 600
    if hop:
        cands = goc_trong(b["lo_tham_cach_tuong"], 450, unary_union([f["fp"].buffer(300) for f in sofa + ban]) if (sofa or ban) else None)
        gr = unary_union([Point(a) for a, _, _ in hop])
        cands = [p for p in cands if p.distance(gr) >= 900]
        if cands:
            q = min(cands, key=lambda p: p.distance(gr))
            moi.append(bt.them("AC-AP-600", q.x, q.y, 0, "bảo trì máy điều hòa âm trần (gần cụm gió hồi)", r))
        else:
            bt.note(r, "Không tìm được vị trí lỗ thăm cho máy điều hòa âm trần.")
    if wc:
        cands = goc_trong(b["lo_tham_cach_tuong"], 450, vt.buffer(200) if vt is not None else None)
        if cands:
            q = max(cands, key=lambda p: vt.distance(p) if vt is not None else 0)
            moi.append(bt.them("AC-AP-600", q.x, q.y, 0, "bảo trì trần WC (vùng phụ, xa vùng tắm)", r))
        else:
            bt.note(r, "WC không còn góc trống cho lỗ thăm 600.")
    return moi


def xuat_scr(path, ds, thu_vien, cfg):
    """Script chen thiet bi moi len DUNG layer thiet bi (khong -DX) - dung cho ban sao chay ngam."""
    def ls(s):
        return '"' + st.tpp.acad_str(s).replace("\\", "\\\\").replace('"', "'") + '"'
    mau = {"A-Den": 150, "A-Thiet bi PCCC": 1, "A-HVAC": 2, "A-HVAC1": 2, "A-HVAC2": 2, "A-Hoan thien tran": 8}
    L = ["CMDECHO", "0", "OSMODE", "0", "ATTREQ", "0", "FILEDIA", "0",
         "(defun mk-lay (n c) (if (not (tblsearch \"LAYER\" n)) (entmake (list (cons 0 \"LAYER\") (cons 100 \"AcDbSymbolTableRecord\") "
         "(cons 100 \"AcDbLayerTableRecord\") (cons 2 n) (cons 70 0) (cons 62 c) (cons 6 \"Continuous\")))) n)"]
    for lay in sorted({d["layer"] for d in ds}):
        L.append(f"(mk-lay {ls(lay)} {mau.get(lay, 7)})")
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
    print(f"[bo tri] {time.time() - t0:.0f}s, {len(bt.ds)} thiet bi", file=sys.stderr)
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
        st.ve_anh(p, poly, phong_kq, bt.ds, noi_that, [], so)
        anh.append(p)
    scr = os.path.join(a.out_dir, "ve_bo_tri_tran.scr")
    xuat_scr(scr, bt.ds, a.thu_vien, cfg)
    ra = [dict(ma=d["ma"], x=round(d["x"], 1), y=round(d["y"], 1), rot=d["rot"], layer=d["layer"], can=d["can_moi"],
               phong=d["phong_moi"], ly_do=d["ly_do"]) for d in bt.ds]
    js = os.path.join(a.out_dir, "bo_tri_tran.json")
    json.dump(dict(thu_vien=a.thu_vien, thiet_bi=ra), open(js, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    dem = {}
    for x in so.ds:
        dem[x["loai"]] = dem.get(x["loai"], 0) + 1
    print(json.dumps(dict(
        file=os.path.basename(a.dxf),
        can_ho=[t for _, t in cans],
        phong=[dict(can=p["can"], ten=p["ten"], loai=p["loai"], trang_thai=p["trang_thai"],
                    dien_tich=round(p["poly"].area / 1e6, 2) if p["poly"] is not None else None,
                    thiet_bi={m: sum(1 for d in bt.ds if d["phong_moi"] == p["ten"] and d["can_moi"] == p["can"] and d["ma"] == m)
                              for m in sorted({d["ma"] for d in bt.ds if d["phong_moi"] == p["ten"] and d["can_moi"] == p["can"]})})
               for p in phong_kq],
        thiet_bi_theo_ma={m: sum(1 for d in bt.ds if d["ma"] == m) for m in sorted({d["ma"] for d in bt.ds})},
        ghi_chu=[f"{c} – {p}: {s}" for c, p, s in bt.ghi_chu],
        canh_bao=dem, xlsx=xlsx, anh=anh, scr=scr, json=js), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

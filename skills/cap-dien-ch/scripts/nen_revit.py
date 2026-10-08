# -*- coding: utf-8 -*-
"""Nen mat bang XUAT TU REVIT (skill cap-dien-ch): tuong / cua / noi that da no thanh LINE / ARC / CIRCLE, khong co Text
ten phong, ma can dat ngoai can co duong dan (leader) chi vao can.

  - Phong   = mat kin cua net tuong (A-NETTUONG, A-NETCAT) + net cua (A-CUA, chi LINE), dong o cua <= 1200 bang tia.
  - Can     = loang tu diem cuoi duong dan ma can qua o cua / cua kinh; hanh lang chung (mat lon, khong noi that) chan lai.
  - Noi that = gom cum net theo dau mut chung tren layer noi that, nhan dien theo hinh dang:
      giuong (goi + 2 net canh giuong), tu ao, tivi (hinh chu nhat manh), sofa, ban an, bep nau (khung + >= 2 vong tron),
      chau rua / lavabo, bon cau, may giat (o vuong + vong tron), tu lanh, may rua bat (o vuong gach cheo), dan nong
      dieu hoa (A-NETMANH, nhieu ELLIPSE).
Moi doi tuong ghi 'suy': True (nhan dien theo hinh dang) - bao cao ghi Goi y de nguoi dung xac nhan.
Nguong o cau_hinh_o_cam.json -> "nen_revit".
"""
import math
import re
from collections import Counter, defaultdict

import shapely
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box
from shapely.ops import unary_union


# ================================================================================================= doc net
def doc_net(flat, tpp, layers, layers_text):
    """flat: doi tuong da trai phang (tpp.walk). Tra ve (net, texts):
    net[layer_goc] = list dict(t, pts, c=(cx,cy), r) ; texts = list (layer_goc, chuoi, x, y)."""
    want = {tpp.layer_goc(x) for x in layers}
    want_t = {tpp.layer_goc(x) for x in layers_text}
    net, texts = defaultdict(list), []
    for e in flat:
        t = e.dxftype()
        L = tpp.layer_goc(e.dxf.layer)
        if t in ("TEXT", "MTEXT"):
            if L in want_t:
                p = e.dxf.insert
                s = e.dxf.text if t == "TEXT" else e.plain_text()
                texts.append((L, (s or "").strip(), p.x, p.y))
            continue
        if L not in want:
            continue
        try:
            if t == "LINE":
                pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
                net[L].append(dict(t=t, pts=pts))
            elif t == "LWPOLYLINE":
                from ezdxf import path as ezpath
                pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(1.0)]
                if e.closed and pts and math.dist(pts[0], pts[-1]) > 0.5:
                    pts.append(pts[0])
                if len(pts) >= 2:
                    net[L].append(dict(t=t, pts=pts))
            elif t in ("ARC", "CIRCLE"):
                pts = [(v.x, v.y) for v in e.flattening(2.0)]
                c = e.ocs().to_wcs(e.dxf.center)
                if len(pts) >= 2:
                    net[L].append(dict(t=t, pts=pts, c=(c.x, c.y), r=e.dxf.radius))
            elif t in ("ELLIPSE", "SPLINE"):
                pts = [(v.x, v.y) for v in e.flattening(2.0)]
                if len(pts) >= 2:
                    net[L].append(dict(t=t, pts=pts))
        except Exception:
            continue
    return net, texts


# ================================================================================================= cum net
class Cum:
    """Cum net noi voi nhau qua dau mut chung (<= 1 mm), cung layer."""

    def __init__(self, L, items):
        self.L = L
        self.items = items
        self.n = Counter(i["t"] for i in items)
        g = MultiLineString([i["pts"] for i in items])
        self.g = g
        self.bb = box(*g.bounds)
        r = g.minimum_rotated_rectangle
        if r.geom_type != "Polygon":
            r = g.envelope if g.envelope.geom_type == "Polygon" else g.buffer(1).envelope
        self.mrr = r
        cs = list(r.exterior.coords)
        a, b = math.dist(cs[0], cs[1]), math.dist(cs[1], cs[2])
        if a >= b:
            self.dai, self.rong, u = a, b, (cs[1][0] - cs[0][0], cs[1][1] - cs[0][1])
        else:
            self.dai, self.rong, u = b, a, (cs[2][0] - cs[1][0], cs[2][1] - cs[1][1])
        L_ = math.hypot(*u) or 1.0
        self.u = (u[0] / L_, u[1] / L_)
        c = r.centroid
        self.x, self.y = c.x, c.y
        # cum chi gom 1 duong tron
        self.tron = None
        if len(items) == 1 and items[0]["t"] == "CIRCLE":
            self.tron = (items[0]["c"], items[0]["r"])

    def __repr__(self):
        return f"Cum({self.L} {self.dai:.0f}x{self.rong:.0f} @{self.x:.0f},{self.y:.0f} {dict(self.n)})"


def gom_cum(items, L):
    if not items:
        return []
    ends, idx = [], []
    for i, it in enumerate(items):
        p = it["pts"]
        ends += [p[0], p[-1]]
        idx += [i, i]
    pts = shapely.points(ends)
    tree = shapely.STRtree(pts)
    a, b = tree.query(pts, predicate="dwithin", distance=1.0)
    par = list(range(len(items)))

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i, j in zip(a, b):
        ri, rj = f(idx[i]), f(idx[j])
        if ri != rj:
            par[ri] = rj
    g = defaultdict(list)
    for i in range(len(items)):
        g[f(i)].append(items[i])
    return [Cum(L, v) for v in g.values()]


def _trong(c, others, pad=20):
    """Cac cum nam trong hop bao (mrr) cua c."""
    P = c.mrr.buffer(pad)
    return [o for o in others if o is not c and P.contains(Point(o.x, o.y)) and o.dai <= c.dai + pad]


def _hcn(u, v, t0, t1, s0, s1):
    """Hinh chu nhat theo truc (u, v): t trong [t0,t1] theo u, s trong [s0,s1] theo v."""
    return Polygon([(u[0] * t + v[0] * s, u[1] * t + v[1] * s) for t, s in ((t0, s0), (t1, s0), (t1, s1), (t0, s1))])


def _rec(loai, fp, ten, **kw):
    c = fp.centroid
    d = dict(loai=loai, ten=ten, fp=fp, x=c.x, y=c.y, suy=True, layer="(nen Revit)", handle="")
    d.update(kw)
    return d


# ================================================================================================= nhan dien noi that
def nhan_dien_noi_that(net, cfg):
    """Tra ve list noi that (dinh dang nhu soat_tran.doc_noi_that) + thong ke cum."""
    k = cfg
    L_nt, L_tb, L_mn = k["layer_noi_that"], k["layer_thiet_bi_ve_sinh"], k["layer_dan_nong"]
    cum_nt = [c for L in L_nt for c in gom_cum(net.get(L, []), L)]
    cum_tb = [c for L in L_tb for c in gom_cum(net.get(L, []), L)]
    cum_mn = [c for L in L_mn for c in gom_cum(net.get(L, []), L)]
    tron = [c for c in cum_nt if c.tron]
    out = []
    da_dung = set()

    # ---------------------------------------------------------------- giuong: goi -> 2 net canh giuong
    G = k["giuong"]
    goi = [c for c in cum_nt if c.n.get("ARC", 0) >= G["goi_so_cung_min"] and c.n.get("LINE", 0) <= 2 and not c.tron
           and G["goi_dai"][0] <= c.dai <= G["goi_dai"][1] and G["goi_rong"][0] <= c.rong <= G["goi_rong"][1]]
    par = list(range(len(goi)))

    def fg(i):
        while par[i] != i:
            i = par[i]
        return i
    # khong gom goi qua tuong (hai giuong doi xung qua tuong chung giua hai can / hai phong)
    tuong = [LineString(it["pts"]) for L in k["layer_tuong"] for it in net.get(L, []) if it["t"] in ("LINE", "LWPOLYLINE")]
    cay_t = shapely.STRtree(tuong) if tuong else None
    for i in range(len(goi)):
        for j in range(i + 1, len(goi)):
            a_, b_ = (goi[i].x, goi[i].y), (goi[j].x, goi[j].y)
            if math.dist(a_, b_) <= G["goi_cach_nhau_max"] and not (
                    cay_t is not None and len(cay_t.query(LineString([a_, b_]), predicate="intersects"))):
                par[fg(i)] = fg(j)
    nhom = defaultdict(list)
    for i in range(len(goi)):
        nhom[fg(i)].append(goi[i])
    # net thang dai (canh giuong) tren layer noi that
    doan = []
    for L in L_nt:
        for it in net.get(L, []):
            if it["t"] == "LINE":
                a, b = it["pts"]
                d = math.dist(a, b)
                if G["canh_dai"][0] <= d <= G["canh_dai"][1]:
                    doan.append((a, b, d))
    for gs in nhom.values():
        # goi trung lap (2 lop ve) -> bo trung tam
        uniq = []
        for g in gs:
            if not any(math.dist((g.x, g.y), (h.x, h.y)) < 60 for h in uniq):
                uniq.append(g)
        gs = uniq
        # truc ngang giuong = canh dai cua goi lon nhat (goi nam doc theo dau giuong); lam tron ve 0/90 do neu lech < 3 do
        u = max(gs, key=lambda g: g.mrr.area).u
        ang = math.degrees(math.atan2(u[1], u[0]))
        if abs(ang - round(ang / 90) * 90) < 3:
            ang = round(ang / 90) * 90
            u = (round(math.cos(math.radians(ang)), 9), round(math.sin(math.radians(ang)), 9))
        v = (-u[1], u[0])
        pts = [p for g in gs for p in g.mrr.exterior.coords]
        T = [p[0] * u[0] + p[1] * u[1] for p in pts]
        S = [p[0] * v[0] + p[1] * v[1] for p in pts]
        U0, U1, V0, V1 = min(T), max(T), min(S), max(S)
        trai, phai = [], []
        for a, b, d in doan:
            w = ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
            if abs(w[0] * u[0] + w[1] * u[1]) > 0.03:
                continue
            t = (a[0] * u[0] + a[1] * u[1] + b[0] * u[0] + b[1] * u[1]) / 2
            s0, s1 = sorted((a[0] * v[0] + a[1] * v[1], b[0] * v[0] + b[1] * v[1]))
            if s1 < V0 - 50 or s0 > V1 + 50:          # phai chong theo phuong doc giuong voi goi
                continue
            if U0 - G["canh_cach_goi_max"] <= t <= U0 + 20:
                trai.append((t, s0, s1))
            elif U1 - 20 <= t <= U1 + G["canh_cach_goi_max"]:
                phai.append((t, s0, s1))
        ghi = ""
        if trai and phai:
            tl = min(trai, key=lambda x: x[0])                # ngoai cung (khung giuong)
            tr = max(phai, key=lambda x: x[0])
            t0, t1 = tl[0], tr[0]
            s0, s1 = min(tl[1], tr[1]), max(tl[2], tr[2])
        else:
            t0, t1 = U0 - 150, U1 + 150
            s0, s1 = V0 - 100, V1 + 100
            ghi = "không thấy nét cạnh giường: mép giường lấy theo gối ± 150"
        than = _hcn(u, v, t0, t1, s0, s1)
        # dau giuong = dau gan goi
        sg = (V0 + V1) / 2
        dau_thap = abs(sg - s0) < abs(sg - s1)
        sau = G["vung_goi_sau"]
        vg = _hcn(u, v, t0, t1, s0, s0 + sau) if dau_thap else _hcn(u, v, t0, t1, s1 - sau, s1)
        out.append(_rec("giuong", than, "giường (nét Revit)", than=than, vung_goi=vg, truc=("u", u), ghi_chu=ghi))
        for g in gs:
            da_dung.add(id(g))

    giuong = [f["than"] for f in out]

    def tren_giuong(c):
        return any(gp.buffer(-50).contains(Point(c.x, c.y)) for gp in giuong)

    # ---------------------------------------------------------------- bep nau: khung + >= 2 vong tron lech tam
    B_ = k["bep_nau"]
    hob = []
    for c in cum_nt:
        if not (B_["dai"][0] <= c.dai <= B_["dai"][1] and B_["rong"][0] <= c.rong <= B_["rong"][1]) or c.tron:
            continue
        tr = [o.tron for o in tron if c.mrr.buffer(10).contains(Point(o.tron[0])) and B_["r_vong"][0] <= o.tron[1] <= B_["r_vong"][1]]
        tam = []
        for (p, r) in tr:
            if not any(math.dist(p, q) < 60 for q in tam):
                tam.append(p)
        if len(tam) >= 2:
            hob.append(c)
    for c in hob:
        if any(h.bb.contains(c.bb) and h is not c for h in hob):
            continue
        out.append(_rec("bep_nau", c.mrr, "bếp nấu (nét Revit)"))
        da_dung.add(id(c))
    hobs = [f["fp"] for f in out if f["loai"] == "bep_nau"]

    # ---------------------------------------------------------------- may giat: o vuong + vong tron lon
    M_ = k["may_giat"]
    for c in cum_nt:
        if not (M_["canh"][0] <= c.rong <= c.dai <= M_["canh"][1]) or c.tron:
            continue
        tr = [o.tron for o in tron if c.mrr.contains(Point(o.tron[0])) and M_["r_vong"][0] <= o.tron[1] <= M_["r_vong"][1]]
        if tr and not any(h.intersects(c.mrr) for h in hobs):
            out.append(_rec("may_giat", c.mrr, "máy giặt (nét Revit)"))
            da_dung.add(id(c))

    # ---------------------------------------------------------------- may rua bat: o vuong gach cheo canh bep / chau
    R_ = k["may_rua_bat"]
    for c in cum_nt:
        if not (R_["canh"][0] <= c.rong <= c.dai <= R_["canh"][1]):
            continue
        cheo = 0
        for it in c.items:
            if it["t"] != "LINE":
                continue
            a, b = it["pts"]
            d = math.dist(a, b)
            w = ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
            if d > c.dai * 1.2 and 0.5 < abs(w[0] * c.u[0] + w[1] * c.u[1]) < 0.87:
                cheo += 1
        if cheo >= 2 and any(h.distance(c.mrr) < R_["cach_bep_max"] for h in hobs):
            out.append(_rec("may_rua_bat", c.mrr, "máy rửa bát (ô gạch chéo cạnh bếp, nét Revit)"))
            da_dung.add(id(c))

    # ---------------------------------------------------------------- chau rua bep: khung chua hoc chau co cung
    C_ = k["chau_rua_bep"]
    for c in cum_nt:
        if not (C_["dai"][0] <= c.dai <= C_["dai"][1] and C_["rong"][0] <= c.rong <= C_["rong"][1]) or c.tron or id(c) in da_dung:
            continue
        hoc = [o for o in cum_nt if o is not c and o.n.get("ARC", 0) >= 2 and 200 <= o.dai <= 520 and c.mrr.buffer(10).contains(o.mrr)]
        if hoc and not any(h.intersects(c.mrr) for h in hobs):
            out.append(_rec("chau_rua", c.mrr, "chậu rửa bếp (nét Revit)"))
            da_dung.add(id(c))

    # ---------------------------------------------------------------- tu lanh: hinh chu nhat co khung trong / nep cua
    L_ = k["tu_lanh"]
    for c in cum_nt:
        if id(c) in da_dung or c.tron or c.n.get("ARC") or c.n.get("CIRCLE"):
            continue
        if not (L_["dai"][0] <= c.dai <= L_["dai"][1] and L_["rong"][0] <= c.rong <= L_["rong"][1]) or c.n.get("LINE", 0) < 4:
            continue
        # nep cua: hinh manh dai ~ bang canh dai, song song, ngay truoc mat tu
        nep = [o for o in cum_nt if o is not c and abs(o.dai - c.dai) < 120 and o.rong <= 90 and o.mrr.distance(c.mrr) < 150
               and abs(o.u[0] * c.u[0] + o.u[1] * c.u[1]) > 0.98]
        if nep and not any(h.intersects(c.mrr.buffer(50)) for h in hobs):
            out.append(_rec("tu_lanh", c.mrr, "tủ lạnh (nét Revit)"))
            da_dung.add(id(c))
            for o in nep:
                da_dung.add(id(o))

    # ---------------------------------------------------------------- tivi (hinh chu nhat manh)
    T_ = k["tivi"]
    tls = [f["fp"] for f in out if f["loai"] == "tu_lanh"]
    ung_tv = []
    for c in cum_nt:
        if id(c) in da_dung or any(t.distance(c.mrr) < 200 for t in tls):
            continue
        if T_["dai"][0] <= c.dai <= T_["dai"][1] and T_["day"][0] <= c.rong <= T_["day"][1] and c.n.get("LINE", 0) >= 4 \
                and not c.n.get("ARC") and not tren_giuong(c):
            ung_tv.append(c)
    # canh tu truot: nhieu hinh manh noi tiep / so le tren cung mot duong -> khong phai tivi
    for c in ung_tv:
        if any(o is not c and abs(o.u[0] * c.u[0] + o.u[1] * c.u[1]) > 0.98 and o.mrr.distance(c.mrr) < 300
               and LineString([(o.x, o.y), (c.x, c.y)]).length > 200 and
               abs((o.x - c.x) * -c.u[1] + (o.y - c.y) * c.u[0]) < 120 for o in ung_tv):
            continue
        out.append(_rec("ke_tv", c.mrr, "tivi (nét Revit)"))
        da_dung.add(id(c))
    tvs = [f["fp"] for f in out if f["loai"] == "ke_tv"]

    # ---------------------------------------------------------------- sofa
    S_ = k["sofa"]
    sofa = []
    for c in cum_nt:
        if not (S_["dai"][0] <= c.dai <= S_["dai"][1] and S_["rong"][0] <= c.rong <= S_["rong"][1]) or tren_giuong(c) or id(c) in da_dung:
            continue
        # co cung (tay / dem bo tron) hoac: nhieu net chia dem + goi tua ELLIPSE, sau >= sau_khong_cung_min
        if c.n.get("ARC", 0) >= S_["so_cung_min"] or (
                c.rong >= S_["sau_khong_cung_min"] and c.n.get("LINE", 0) >= 8 and c.dai <= 3600):
            sofa.append(c)
    sofa.sort(key=lambda c: -c.mrr.area)
    giu = []
    for c in sofa:
        if any(g.mrr.intersection(c.mrr).area > 0.3 * c.mrr.area for g in giu):
            continue
        giu.append(c)
        out.append(_rec("sofa", c.mrr, "sofa (nét Revit)"))

    # ---------------------------------------------------------------- ban an: mat ban + >= 2 ghe
    A_ = k["ban_an"]
    ghe = [c for c in cum_nt if A_["ghe_dai"][0] <= c.dai <= A_["ghe_dai"][1] and c.rong <= A_["ghe_rong_max"] and c.n.get("ARC", 0) >= 1]
    for c in cum_nt:
        if A_["dai"][0] <= c.dai <= A_["dai"][1] and A_["rong"][0] <= c.rong <= A_["rong"][1] and c.n.get("LINE", 0) >= 4 \
                and not c.n.get("ARC") and not tren_giuong(c):
            n_ghe = sum(1 for g in ghe if c.mrr.distance(Point(g.x, g.y)) < 450)
            if n_ghe >= 3:
                out.append(_rec("ban_an", c.mrr, "bàn ăn (nét Revit)"))
                da_dung.add(id(c))

    # ---------------------------------------------------------------- tu ao (loc theo phong ngu o buoc dung phong)
    U_ = k["tu_ao"]
    for c in cum_nt:
        if id(c) in da_dung or c.tron or c.n.get("ARC", 0) > 2:
            continue
        if U_["dai"][0] <= c.dai <= U_["dai"][1] and U_["sau"][0] <= c.rong <= U_["sau"][1] and c.n.get("LINE", 0) >= 3 \
                and not tren_giuong(c) and not any(t.intersects(c.mrr.buffer(-20)) for t in tvs):
            out.append(_rec("tu_ao", c.mrr, "tủ áo (nét Revit)", chi_phong_ngu=True))

    # ---------------------------------------------------------------- thiet bi ve sinh
    W_ = k["bon_cau"]
    V_ = k["lavabo"]
    for c in cum_tb:
        cong = c.n.get("ARC", 0) + c.n.get("ELLIPSE", 0) + c.n.get("SPLINE", 0)
        if cong >= W_["so_cung_min"] and W_["dai"][0] <= c.dai <= W_["dai"][1] and W_["rong"][0] <= c.rong <= W_["rong"][1]:
            out.append(_rec("bon_cau", c.mrr, "bồn cầu (nét Revit)"))
            continue
        cong2 = cong + c.n.get("LWPOLYLINE", 0) + c.n.get("CIRCLE", 0)
        if cong2 >= 1 and V_["dai"][0] <= c.dai <= V_["dai"][1] and V_["rong"][0] <= c.rong <= V_["rong"][1] and c.dai / max(c.rong, 1) <= 1.8:
            out.append(_rec("chau_rua", c.mrr, "lavabo (nét Revit)"))
    # bon cau ve 2 lop (than + nap): bo trung
    bc = [f for f in out if f["loai"] == "bon_cau"]
    for f in bc:
        if any(g is not f and g["fp"].contains(Point(f["x"], f["y"])) and g["fp"].area > f["fp"].area for g in bc):
            f["loai"] = "_bo"
    out = [f for f in out if f["loai"] != "_bo"]
    lav = [f for f in out if f["loai"] == "chau_rua" and "lavabo" in f["ten"]]
    for f in lav:
        if any(g is not f and g["fp"].contains(Point(f["x"], f["y"])) and g["fp"].area > f["fp"].area for g in lav) or \
                any(g["loai"] == "bon_cau" and g["fp"].buffer(80).contains(Point(f["x"], f["y"])) for g in out):
            f["loai"] = "_bo"
    out = [f for f in out if f["loai"] != "_bo"]

    # ---------------------------------------------------------------- dan nong dieu hoa (A-NETMANH, nhieu ELLIPSE)
    D_ = k["dan_nong"]
    ung = [c for c in cum_mn if c.n.get("ELLIPSE", 0) >= 1 and c.dai <= D_["dai"][1]]
    # gop cac cum gan nhau thanh mot cuc
    par = list(range(len(ung)))

    def fd(i):
        while par[i] != i:
            i = par[i]
        return i
    for i in range(len(ung)):
        for j in range(i + 1, len(ung)):
            if ung[i].bb.distance(ung[j].bb) < 60:
                par[fd(i)] = fd(j)
    nh = defaultdict(list)
    for i in range(len(ung)):
        nh[fd(i)].append(ung[i])
    for cs in nh.values():
        n_el = sum(c.n.get("ELLIPSE", 0) for c in cs)
        g = unary_union([c.mrr for c in cs])
        r = g.minimum_rotated_rectangle
        if r.geom_type != "Polygon":
            continue
        q = list(r.exterior.coords)
        a, b = sorted((math.dist(q[0], q[1]), math.dist(q[1], q[2])))
        if n_el >= D_["so_ellipse_min"] and D_["dai"][0] <= b <= D_["dai"][1] and D_["rong"][0] <= a <= D_["rong"][1]:
            out.append(_rec("dan_nong", r, "dàn nóng điều hòa (nét Revit)"))
    tk = dict(cum_noi_that=len(cum_nt), cum_ve_sinh=len(cum_tb), cum_dan_nong=len(cum_mn), loai=dict(Counter(f["loai"] for f in out)))
    return out, tk


def dem_canh_cua(lines, tree, H, X, R):
    """So do lech (offset) khac nhau cua cac net thang chay doc H -> X (ban le -> mot dau cung cua), dai 0,6R..1,15R.
    Canh cua dang mo ve bang 2 net song song cach nhau do day canh (~40 mm) -> 2; khung / nguong cua doc tuong thuong
    la cac net trung nhau tren cung mot duong -> 1."""
    if tree is None:
        return 0
    w = ((X[0] - H[0]) / R, (X[1] - H[1]) / R)
    vung = LineString([(H[0] - w[0] * 200, H[1] - w[1] * 200), (X[0] + w[0] * 100, X[1] + w[1] * 100)]).buffer(60)
    lech = []
    for i in tree.query(vung):
        g = lines[i]
        (x0, y0), (x1, y1) = g.coords[0], g.coords[-1]
        if not (0.6 * R <= g.length <= 1.15 * R) or not vung.buffer(1).contains(g) or                 abs((x1 - x0) * w[0] + (y1 - y0) * w[1]) < 0.97 * g.length:
            continue
        o = ((x0 + x1) / 2 - H[0]) * -w[1] + ((y0 + y1) / 2 - H[1]) * w[0]
        if not any(abs(o - q) < 15 for q in lech):
            lech.append(o)
    return len(lech)


# ================================================================================================= ma can
def doc_ma_can(net, texts, cfg):
    """Ma can (vd 'P5-(05-18).03') trong khung chu nhat, duong dan tu khung chi vao can. Tra ve list (ten, diem_cuoi)."""
    re_ma = re.compile(cfg["ma_can"], re.I)
    out = []
    for L, s, x, y in texts:
        if not re_ma.match(s):
            continue
        segs = [it["pts"] for it in net.get(L, []) if it["t"] in ("LINE", "LWPOLYLINE")]
        # khung: hinh chu nhat nho nhat bao text (polygonize cac net gan)
        gan = [LineString(p) for p in segs if LineString(p).distance(Point(x, y)) < 8000]
        khung = None
        if gan:
            from shapely.ops import polygonize
            ds_f = [f for f in polygonize(unary_union(gan)) if f.area < 30e6]
            f0 = [f for f in ds_f if f.buffer(50).contains(Point(x, y))]
            if f0:
                f0 = min(f0, key=lambda f: f.area)
                # khung chia doi (ma can / loai can): gop cac o chung canh
                khung = unary_union([f for f in ds_f if f.intersects(f0.buffer(5))]).envelope
        if khung is None:
            out.append((s, None))
            continue
        # duong dan: net co mot dau tren bien khung, dau kia xa khung; noi tiep cac net (polyline gay khuc)
        best = None
        for p in segs:
            for a, b in ((p[0], p[-1]), (p[-1], p[0])):
                if khung.exterior.distance(Point(a)) < 10 and khung.distance(Point(b)) > 300:
                    q = b
                    for _ in range(5):        # di tiep cac doan noi duoi
                        nxt = None
                        for p2 in segs:
                            for c, d in ((p2[0], p2[-1]), (p2[-1], p2[0])):
                                if math.dist(c, q) < 2 and math.dist(d, q) > 5 and khung.distance(Point(d)) > 300 and d != a:
                                    nxt = d
                        if nxt is None:
                            break
                        q = nxt
                    L_ = math.dist(a, q)
                    if best is None or L_ > best[0]:
                        best = (L_, q)
        out.append((s, best[1] if best else None))
    return out


# ================================================================================================= phong / can
TEN = {"ngu": "Phòng ngủ", "wc": "WC", "khach": "Phòng khách", "an": "Phòng ăn", "bep": "Bếp", "logia": "Lô gia",
       "hanh_lang": "Sảnh / hành lang", "khac": "Phòng chưa đặt tên"}


def dung_phong_can(net, nt, ma_can, cfg, tpp, log=print):
    """Tra ve (ds_phong, cans, ghi_chu) cung dinh dang soat_tran.dung_phong."""
    k = cfg
    ch_tuong = [(False, it["pts"]) for L in k["layer_tuong"] for it in net.get(L, []) if it["t"] in ("LINE", "LWPOLYLINE")]
    ch_cua = [(False, it["pts"]) for L in k["layer_cua"] for it in net.get(L, []) if it["t"] == "LINE"]
    faces, _pairs, bridges = tpp.build_faces(ch_tuong + ch_cua, k["dong_o_cua_max"])
    # mat phong + mat tu bep hep (chua bep nau / chau / may rua bat / tu lanh) de gop vao phong ke ben
    tb_bep = shapely.points([(f["x"], f["y"]) for f in nt if f["loai"] in ("bep_nau", "chau_rua", "may_rua_bat", "tu_lanh")])
    cay_tb = shapely.STRtree(tb_bep) if len(tb_bep) else None
    rf = [f for f in faces if (f.area >= k["dt_phong_min"] * 1e6 and not f.buffer(-k["be_rong_phong_min"] / 2).is_empty
                               and f.area < 500e6) or
          (0.15e6 <= f.area <= k["mat_tu_bep_dt_max"] * 1e6 and cay_tb is not None and len(cay_tb.query(f, predicate="contains")))]
    log(f"[revit] {len(faces)} mat, {len(rf)} mat phong")
    tree = shapely.STRtree(rf)

    def mat_chua(p):
        hit = [i for i in tree.query(p, predicate="within")]
        return min(hit, key=lambda i: rf[i].area) if hit else None

    # noi that -> mat
    nt_mat = defaultdict(list)
    for f in nt:
        i = mat_chua(Point(f["x"], f["y"]))
        if i is not None:
            nt_mat[i].append(f)
    # gop mat tu bep (net cat tu bep tren tao mat rieng) vao phong ke ben
    gop = {}
    for i, f in enumerate(rf):
        if f.area > k["mat_tu_bep_dt_max"] * 1e6 or not f.buffer(-k["mat_tu_bep_rong_max"] / 2).is_empty:
            continue
        if not any(x["loai"] in ("bep_nau", "chau_rua", "may_rua_bat", "tu_lanh") for x in nt_mat.get(i, [])):
            continue
        ke = [(rf[j].boundary.intersection(f.buffer(3)).length, j) for j in tree.query(f.buffer(5)) if j != i]
        ke = [x for x in ke if x[0] > 300]
        if ke:
            gop[i] = max(ke)[1]
    poly = {i: f for i, f in enumerate(rf)}
    for i, j in gop.items():
        while j in gop:
            j = gop[j]
        poly[j] = unary_union([poly[j], poly[i]]).buffer(1, join_style=2).buffer(-1, join_style=2)
        nt_mat[j] += nt_mat.pop(i, [])
        poly.pop(i)
    ids = list(poly)
    P = [poly[i] for i in ids]
    for n, p in enumerate(P):
        if p.geom_type != "Polygon":
            P[n] = max(p.geoms, key=lambda g: g.area)
    tree2 = shapely.STRtree(P)
    co_nt = {n: nt_mat.get(ids[n], []) for n in range(len(P))}
    # ke noi: hai mat chung canh KHONG phai net tuong (doan dong o cua, net cua / vach kinh) >= 300; qua cac mat mong o cua
    # (o cua di nam trong be day tuong, khung cua truot...) noi tiep nhau theo cung dieu kien.
    tuong_lines = [LineString(c[1]) for c in ch_tuong]
    cay_tuong = shapely.STRtree(tuong_lines) if tuong_lines else None

    def chung_khong_tuong(A, B):
        seg = A.boundary.intersection(B.buffer(2))
        if seg.is_empty or seg.length < 300:
            return 0.0
        ids_t = cay_tuong.query(seg.buffer(3)) if cay_tuong is not None else []
        if len(ids_t):
            seg = seg.difference(unary_union([tuong_lines[i] for i in ids_t]).buffer(3))
        return seg.length

    # mat noi: mong (be rong < mat_noi_rong_max, vd o cua trong be day tuong) - khong phai phong, khong phai sanh nho
    noi = [f for f in faces if 50 <= f.area <= k["mat_noi_dt_max"] * 1e6 and f.buffer(-k["mat_noi_rong_max"] / 2).is_empty]
    N = len(P)
    nodes = P + noi                      # 0..N-1: phong; N..: mat noi
    cay_all = shapely.STRtree(nodes)
    par = list(range(len(nodes)))

    def fp_(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    ke = defaultdict(set)
    for a in range(N, len(nodes)):
        for b in cay_all.query(nodes[a].buffer(3)):
            b = int(b)
            if b == a or chung_khong_tuong(nodes[a], nodes[b]) < 300:
                continue
            par[fp_(a)] = fp_(b)
    for a in range(N):
        for b in tree2.query(P[a].buffer(3)):
            b = int(b)
            if b > a and chung_khong_tuong(P[a], P[b]) >= 300:
                ke[a].add(b)
                ke[b].add(a)
    nhom_noi = defaultdict(set)
    for i in range(N):
        nhom_noi[fp_(i)].add(i)
    for mem in nhom_noi.values():
        for a in mem:
            ke[a] |= mem - {a}

    # cua di co cung mo (o cua thuong co net nguong / bac WC tren layer tuong nen khong noi duoc qua mat mong):
    # phong chua cung <-> phong ben kia o cua
    def phong_tai(p):
        hit = [int(i) for i in tree2.query(p, predicate="within")]
        return min(hit, key=lambda i: P[i].area) if hit else None
    # dau DONG cua cung (canh cua dong, doc tuong) = dau X co doan khep o cua (tia dong <= 1200) song song H->X, dai ~ R,
    # gan ban le; di tu giua o cua nguoc chieu canh cua dang mo -> phong ben kia.
    cay_br = shapely.STRtree(bridges) if bridges else None
    cua_lines = [LineString(c[1]) for c in ch_cua]
    cay_cua = shapely.STRtree(cua_lines)
    so_cua = 0
    for L in k["layer_cua"] + k.get("layer_cung_cua_them", []):
        for it in net.get(L, []):
            if it["t"] != "ARC" or not 500 <= it["r"] <= 1200:
                continue
            H, R = it["c"], it["r"]
            pts = it["pts"]
            A = phong_tai(Point(pts[len(pts) // 2]))
            if A is None or cay_br is None:
                continue
            # canh cua (dang mo) = 2 net A-CUA song song chay doc H -> dau mo; dau con lai la dau dong
            canh = [dem_canh_cua(cua_lines, cay_cua, H, X, R) for X in (pts[0], pts[-1])]
            thu_tu = [(pts[0], pts[-1]), (pts[-1], pts[0])]
            if canh[0] >= 2 > canh[1]:
                thu_tu = [(pts[-1], pts[0])]
            elif canh[1] >= 2 > canh[0]:
                thu_tu = [(pts[0], pts[-1])]
            for X, Y in thu_tu:
                w = ((X[0] - H[0]) / R, (X[1] - H[1]) / R)
                if len(thu_tu) > 1 and not any(0.5 * R <= bridges[i].length <= 1.5 * R and abs(
                        (bridges[i].coords[1][0] - bridges[i].coords[0][0]) * w[0] +
                        (bridges[i].coords[1][1] - bridges[i].coords[0][1]) * w[1]) > 0.95 * bridges[i].length
                        for i in cay_br.query(Point(H).buffer(R * 0.6))):
                    continue
                O = ((H[0] + X[0]) / 2, (H[1] + X[1]) / 2)
                v = ((H[0] - Y[0]) / R, (H[1] - Y[1]) / R)     # nguoc chieu canh dang mo
                for t in range(0, 900, 50):
                    B = phong_tai(Point(O[0] + v[0] * t, O[1] + v[1] * t))
                    if B is not None and B != A:
                        ke[A].add(B)
                        ke[B].add(A)
                        so_cua += 1
                        break
                break
    log(f"[revit] noi qua cung cua: {so_cua}")

    def chung(n):
        return not co_nt[n] and P[n].area > k["hanh_lang_chung_dt_min"] * 1e6

    # loang nhieu nguon (moi ma can mot nguon) theo tung buoc
    chu = {}
    hang = []
    ghi_chu = []
    for ten, q in ma_can:
        if q is None:
            ghi_chu.append(f"{ten}: không tìm được đường dẫn mã căn – bỏ qua căn này.")
            continue
        n = None
        hit = [int(i) for i in tree2.query(Point(q), predicate="within")]
        if hit:
            n = min(hit, key=lambda i: P[i].area)
        else:
            gan = [(P[int(i)].distance(Point(q)), int(i)) for i in tree2.query(Point(q).buffer(1500))]
            if gan:
                n = min(gan)[1]
        if n is None or chung(n):
            ghi_chu.append(f"{ten}: điểm cuối đường dẫn không nằm trong phòng nào – bỏ qua.")
            continue
        if n in chu:
            ghi_chu.append(f"{ten}: điểm cuối đường dẫn trùng căn {chu[n]} – kiểm tra.")
            continue
        chu[n] = ten
        hang.append(n)
    while hang:
        moi = []
        for n in hang:
            for m in ke[n]:
                if m in chu or chung(m):
                    continue
                chu[m] = chu[n]
                moi.append(m)
        hang = moi
    # mat khong noi that giap mat cua can khac (manh hanh lang chung, sanh tang) -> bo
    for n in list(chu):
        if co_nt[n]:
            continue
        if any(m in chu and chu[m] != chu[n] for m in ke[n]):
            chu.pop(n)
    # dung phong
    ds = []
    for n, can in chu.items():
        co = {f["loai"] for f in co_nt[n]}
        loai = []
        if "giuong" in co:
            loai.append("ngu")
        if co & {"bon_cau"}:
            loai.append("wc")
        if "sofa" in co and "giuong" not in co:
            loai.append("khach")
        if "ban_an" in co and "giuong" not in co:
            loai.append("an")
        if "bep_nau" in co:
            loai.append("bep")
        if not loai and co & {"may_giat", "dan_nong"}:
            loai.append("logia")
        if not loai:
            loai.append("hanh_lang" if P[n].area < k["hanh_lang_dt_max"] * 1e6 and not co else "khac")
        ds.append(dict(ten=" + ".join(TEN[x] for x in loai), loai=loai, poly=P[n], can=can, gan_dung=False,
                       seed=P[n].representative_point(), suy_ra=True, nen_revit=True))
    # danh so phong trung ten
    dem = defaultdict(list)
    for x in ds:
        dem[(x["can"], x["ten"])].append(x)
    for v in dem.values():
        if len(v) > 1:
            for i, x in enumerate(sorted(v, key=lambda x: (-round(x["seed"].y, -2), x["seed"].x)), 1):
                x["ten"] = f"{x['ten']} {i}"
    cans = []
    for ten in dict.fromkeys(chu.values()):
        mem = [x["poly"] for x in ds if x["can"] == ten]
        g = unary_union([p.buffer(160, join_style=2) for p in mem]).buffer(-160, join_style=2)
        if g.geom_type != "Polygon":
            g = max(g.geoms, key=lambda x: x.area)
        cans.append((g, ten))
    return ds, cans, ghi_chu

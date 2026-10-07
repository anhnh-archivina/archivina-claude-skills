#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Mat bang TANG nhieu can ho (xref can ho da bind, ma can dat ngoai cua vao): dung polyline phong, lo gia, duong bo
thong thuy tung can + nhan m2 / DTCH, xuat .scr (ve vao BAN SAO), Excel, anh.

Hai buoc, giua hai buoc phai trinh anh cho nguoi dung duyet:

  python mat_bang_tang.py phan-tich <file.dxf> --out-dir <thu muc>
      -> de_xuat_ranh_phong.png, phan_loai_vung.png (vung chua ten danh so #), mbt_phan_tich.json, mbt_trang_thai.pkl
  python mat_bang_tang.py xuat <file.dxf> --out-dir <thu muc> [--doi "#76=ngoai;#25=Phong ngu;#41=loai-tru"]
      -> ve_dien_tich_tang.scr, <ngay>_<du an>_<tang>_BaoCaoDienTich.xlsx, tong_dien_tich.png, ket_qua_dien_tich.json

Quy tac (nguoi dung chot 06/10/2026, ban ve CT1 tang 5A-10):
  1. Phong co vach kinh / cua so goc khong co tuong: ranh theo MAT TRONG KINH/KHUNG (quy tac C).
  2. O mo chua ve cua 1,2-2,6 m (cua truot ra lo gia, cua so ra gieng troi): dong theo mat trat hai ben; doan dong dai
     chi giu khi tach phong ngu/WC/da nang khoi khong gian chung hoac tach lo gia (vung giap lan can/kinh/nhom);
     doan dong chia doi khong gian mo (Sinh hoat chung | Bep) hoac cat hoc trong phong thi bo, gop tra lai.
  3. Sinh hoat chung + Bep khong vach: gop 1 polyline.
  4. Lo gia khong co text ten: tu nhan (giap lan can/lam nhom, hoac co may giat/cuc nong), ten "Lo gia", tinh 100%.
  5. Vung co noi that nhung thieu text ten: dat ten theo noi that (thiet bi ve sinh -> Wc, may giat/cuc nong -> Lo gia,
     giuong/tu ao -> Phong ngu), bao Loi thieu ten phong.
  Chua chot: ranh tai cua chinh khi ban ve khong ve cua -> duong bo theo mat tuong trong, bao Canh bao.
Gom can: phong thuoc can theo tien to xref cua net bao quanh ('CH15$0$A-Wall' -> CH15); can ghep voi text ma can
(regex --ma-can) gan nhat. Ban ve khong co xref can ho -> dung tao_duong_bo_can_ho.py.
"""
import argparse
import collections
import datetime
import importlib.util
import io
import json
import math
import os
import pickle
import re
import sys
import unicodedata
from decimal import Decimal, ROUND_HALF_UP

import ezdxf
import shapely
from ezdxf import path as ezpath
from shapely.geometry import LineString, MultiPoint, Point, Polygon, box
from shapely.ops import nearest_points, polylabel, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("tpp", os.path.join(HERE, "tao_polyline_phong.py"))
tpp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tpp)
r1, acad, layer_goc = tpp.r1, tpp.acad_str, tpp.layer_goc
LOI, CB, GY, DAT = "Lỗi", "Cảnh báo", "Gợi ý", "Đạt"

LAYER_PHONG, LAYER_CAN = "A- Dien tich phong", "Dien tich thong thuy"
RANH_PHU = ["A-Lancan", "A_Wall BT", "S-Wall", "Nhom", "玻璃层", "Kính", "Kinh", "A-Glass", "A-Wall-G", "A-Window-G"]
KINH = {"玻璃层", "kính", "kinh", "a-glass"}
LAN_CAN = {"a-lancan"}
LAM_NHOM = {"nhom"}
CUA = {layer_goc(x) for x in tpp.LAYER_CUA}
NT_WC = {"a-interior wc", "a_interior wc", "a-ga thu wc"}
NT_DO = {"a-nội thất", "a-noi that", "boho-i-furniture"}
NT_MAY = {"av-m-hvac-thiet bi"}
TUONG_NHAN = None   # tap layer vat can (tuong, cua, kinh) - gan trong main
VACH_BTCT = ["S-Wall"]   # vach/cot BTCT: khoi kin tren layer nay KHONG tinh vao DTCH (nguoi dung chot 07/10/2026, CT1 CH03)
PHU_VACH = 0.6           # vung co >= 60% dien tich nam trong khoi vach -> la vach BTCT, khong phai hanh lang/lo gia


def doc_vach(msp, layers):
    """Da giac khoi vach BTCT: polyline kin / hatch tren layer vach (ke ca trong xref da bind)."""
    ten = {layer_goc(x).lower() for x in layers}
    out = []
    for e, names in duyet(msp):
        if layer_goc(e.dxf.layer).lower() not in ten:
            continue
        rings = []
        if e.dxftype() == "HATCH":
            try:
                rings = [[(v.x, v.y) for v in pa.flattening(5)] for pa in ezpath.from_hatch(e)]
            except Exception:
                rings = []
        elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            try:
                pts, closed = diem(e, 5.0)
            except Exception:
                continue
            if pts and closed:
                rings = [pts]
        for r_ in rings:
            if len(r_) >= 3:
                g = Polygon(r_)
                g = g if g.is_valid else g.buffer(0)
                if g.area > 0.01e6:
                    out.append(g)
    return out


def ty_le_vach(g, vach, vtree):
    if vtree is None:
        return 0.0
    hit = [vach[k] for k in vtree.query(g)]
    return unary_union(hit).intersection(g).area / g.area if hit else 0.0


def bo_dau(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D").lower()


def dai(p):
    return sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))


# ---------------------------------------------------------------------------------------------------------------------
# 1. Doc ban ve: mot lan duyet lay het (ke thua layer 0 nhu tpp.walk, kem ten block de nhan noi that)
# ---------------------------------------------------------------------------------------------------------------------
def duyet(entities, depth=0, max_depth=3, par=None, names=()):
    for e in entities:
        if e.dxf.get("invisible", 0):
            continue
        if e.dxftype() == "INSERT":
            if depth >= max_depth or (tpp._BO_QUA[0] is not None and tpp._BO_QUA[0].search(e.dxf.name or "")):
                continue
            lay = par if (par and layer_goc(e.dxf.layer) == "0") else e.dxf.layer
            try:
                subs = list(e.virtual_entities())
            except Exception:
                continue
            for v in subs:
                if layer_goc(v.dxf.layer) == "0":
                    v.dxf.layer = lay
            yield from duyet(subs, depth + 1, max_depth, lay, names + (e.dxf.name or "",))
        else:
            yield e, names


def diem(e, tol):
    t = e.dxftype()
    if t == "LINE":
        return [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)], False
    if t in ("LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE"):
        pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(tol)]
        closed = bool(getattr(e, "closed", False)) if t != "CIRCLE" else True
        if len(pts) >= 2 and math.dist(pts[0], pts[-1]) < 1.0:
            closed, pts = True, pts[:-1]
        return pts, closed
    return None, False


def doc_ban_ve(msp, layers_ranh, layers_phu, min_phu):
    base = {layer_goc(x) for x in layers_ranh}
    phu = {layer_goc(x) for x in layers_phu}
    R = dict(chains=[], chain_lay=[], tien_to=[], kinh=[], cua=[], cua_diem=[], cung_cua=[], lan_can=[], nhom=[], noi_that=[], vat_can=[])
    for e, names in duyet(msp):
        t = e.dxftype()
        if t not in ("LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE"):
            continue
        lay = layer_goc(e.dxf.layer)
        raw = e.dxf.layer
        la_ranh = t in ("LINE", "LWPOLYLINE") and (lay in base or lay in phu)
        tol = 0.5 if la_ranh else 20.0
        try:
            pts, closed = diem(e, tol)
        except Exception:
            continue
        if not pts or len(pts) < 2:
            continue
        if la_ranh and (lay in base or dai(pts + ([pts[0]] if closed else [])) >= min_phu):
            R["chains"].append((closed, pts))
            R["chain_lay"].append(lay)
        if lay in base or lay in CUA or lay in NT_WC or lay in NT_DO:
            R["tien_to"].append((LineString(pts), raw))
        if lay in KINH and t in ("LINE", "LWPOLYLINE"):
            R["kinh"].append(pts)
        if lay in CUA:
            R["cua_diem"] += pts
            if t == "ARC" and 400 <= float(e.dxf.radius) <= 1300:     # cung quay canh cua di
                R["cung_cua"].append(LineString(pts))
            if t in ("LINE", "LWPOLYLINE"):
                R["cua"].append(pts)
        if lay in LAN_CAN:
            R["lan_can"].append(LineString(pts))
        if lay in LAM_NHOM:
            R["nhom"].append(LineString(pts))
        if lay in NT_WC or lay in NT_DO or lay in NT_MAY:
            nm = re.sub(r"^.*\$0\$", "", names[-1]) if names else ""
            R["noi_that"].append((LineString(pts), "wc" if lay in NT_WC else "may" if lay in NT_MAY else "do", nm))
        if lay in TUONG_NHAN or lay in NT_WC or lay in NT_DO or lay in NT_MAY:
            R["vat_can"].append((LineString(pts), lay in TUONG_NHAN))
    return R


# ---------------------------------------------------------------------------------------------------------------------
# 2. Mang net -> mat, quy tac giu/bo doan dong dai, vach kinh, noi khe nho
# ---------------------------------------------------------------------------------------------------------------------
def noi_khe_nho(chains, lo=6.0, hi=25.0):
    """Noi dau mut tu do vao net ranh gan nhat khi khe 6-25 mm (sai so ve, khong phai o mo)."""
    lines = [LineString(p + ([p[0]] if c else [])) for c, p in chains]
    tree = shapely.STRtree(lines)
    out = []
    for i, (c, p) in enumerate(chains):
        if c:
            continue
        for e in (p[0], p[-1]):
            E = Point(e)
            near = [k for k in tree.query(E.buffer(hi)) if k != i]
            if not near or any(lines[k].distance(E) <= lo for k in near):
                continue
            k = min(near, key=lambda k: lines[k].distance(E))
            if lo < lines[k].distance(E) <= hi:
                q = nearest_points(lines[k], E)[0]
                out.append((False, [e, (q.x, q.y)]))
    return out


def tim_mat(pt, faces, ftree):
    hit = [i for i in ftree.query(pt) if faces[i].contains(pt)]
    return min(hit, key=lambda k: faces[k].area) if hit else None


def dung_mat_gop(chains, khung, seeds, gap_max, gap_dai, mat_ngoai, re_mo):
    """Dung mat voi khe dong toi gap_dai; doan dong dai (> gap_max) bi bo (gop hai mat) khi: hai ben deu la khong gian mo
    (Sinh hoat chung/Bep...), hoac mot ben la phong co ten va ben kia la hoc nho khong giap mat ngoai (lan can/kinh/nhom).
    Tra ve faces, par (nhom mat sau gop), thong ke quyet dinh, bridges."""
    faces, pairs, bridges = tpp.build_faces(chains, gap_dai, khung)
    ftree = shapely.STRtree(faces)
    fseeds = collections.defaultdict(list)
    for t, (x, y), _i in seeds:
        i = tim_mat(Point(x, y), faces, ftree)
        if i is not None:
            fseeds[i].append(t)
    mtree = shapely.STRtree(mat_ngoai) if mat_ngoai else None

    def giap_ngoai(f):
        return mtree is not None and any(mat_ngoai[k].distance(f) < 60 for k in mtree.query(f.buffer(60)))

    par = list(range(len(faces)))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    tk = collections.Counter()
    for a_, b_, d in pairs:
        if d <= gap_max:
            continue
        l = LineString([a_, b_])
        m = l.interpolate(0.5, normalized=True)
        adj = [i for i in ftree.query(m.buffer(1)) if faces[i].area > 2e5 and
               (faces[i].exterior.distance(m) < 1 or any(r.distance(m) < 1 for r in faces[i].interiors))]
        if len(adj) != 2:
            tk["giu (khong xac dinh 2 ben)"] += 1
            continue
        a, c = adj
        sa, sc = fseeds.get(a, []), fseeds.get(c, [])
        if sa and sc:
            ten = {bo_dau(x) for x in sa + sc}
            bo = all(re_mo.search(x) for x in ten)
            why = "bo: chia khong gian mo" if bo else "giu: tach phong"
        elif sa or sc:
            other = c if sa else a
            if faces[other].area > 25e6:
                bo, why = False, "giu: giap vung lon"
            elif giap_ngoai(faces[other]):
                bo, why = False, "giu: tach lo gia/mat ngoai"
            else:
                bo, why = True, "bo: hoc trong phong"
        else:
            bo, why = False, "giu: hai ben chua ten"
        tk[why] += 1
        if bo:
            par[find(a)] = find(c)
    par = [find(i) for i in range(len(faces))]
    return faces, par, tk, bridges


def nhom_mat(faces, par):
    grp = collections.defaultdict(list)
    for i, r in enumerate(par):
        grp[r].append(i)
    return {r: (unary_union([faces[i] for i in ids]) if len(ids) > 1 else faces[ids[0]]) for r, ids in grp.items()}


def duong_kinh(opens, R, walls_tree, walls):
    """Duong mat trong vach kinh cho cac phong chua dong kin: gom tam kinh (layer kinh + net cua doi 2-8 mm thang hang)
    theo phuong/do lech, lay do lech gan phong nhat, keo suot cum (noi khe <= 300), noi dau vao tuong gan nhat <= 300 mm,
    keo hai duong vuong goc gap nhau o goc cua so chu L (<= 300 mm)."""
    def tach(p):
        for i in range(len(p) - 1):
            a, b_ = p[i], p[i + 1]
            if math.dist(a, b_) < 100:
                continue
            if abs(a[1] - b_[1]) < 2:
                yield ("H", (a[1] + b_[1]) / 2, min(a[0], b_[0]), max(a[0], b_[0]))
            elif abs(a[0] - b_[0]) < 2:
                yield ("V", (a[0] + b_[0]) / 2, min(a[1], b_[1]), max(a[1], b_[1]))
    G = [x for p in R["kinh"] for x in tach(p)]
    offs = {(o, round(v / 10)) for o, v, a, b_ in G}
    A0 = [x for p in R["cua"] for x in tach(p) if x[3] - x[2] >= 400]
    bk = collections.defaultdict(list)
    for x in A0:
        bk[(x[0], round(x[1] / 10))].append(x)

    def kinh_doi(x):
        for k in (-1, 0, 1):
            for y in bk.get((x[0], round(x[1] / 10) + k), []):
                if y is not x and 2 <= abs(y[1] - x[1]) <= 8 and min(x[3], y[3]) - max(x[2], y[2]) >= 0.8 * (x[3] - x[2]):
                    return True
        return False
    allg = G + [x for x in A0 if kinh_doi(x) or any((x[0], round(x[1] / 10) + k) in offs for k in range(-3, 4))]
    them = []
    for (X, Y) in opens:
        Rr = 4500
        loc = [x for x in allg if (x[0] == "H" and abs(x[1] - Y) < Rr and x[3] > X - Rr and x[2] < X + Rr) or
               (x[0] == "V" and abs(x[1] - X) < Rr and x[3] > Y - Rr and x[2] < Y + Rr)]
        for o in ("H", "V"):
            Ls = sorted([x for x in loc if x[0] == o], key=lambda x: x[1])
            cl = []
            for x in Ls:
                if cl and x[1] - cl[-1][-1][1] <= 40:
                    cl[-1].append(x)
                else:
                    cl.append([x])
            for c_ in cl:
                seed = Y if o == "H" else X
                inner = min((x[1] for x in c_), key=lambda v: abs(v - seed))
                iv = sorted((x[2], x[3]) for x in c_)
                spans = [list(iv[0])]
                for a, b_ in iv[1:]:
                    if a <= spans[-1][1] + 300:
                        spans[-1][1] = max(spans[-1][1], b_)
                    else:
                        spans.append([a, b_])
                for a, b_ in spans:
                    if b_ - a < 400:
                        continue
                    seg = ((a, inner), (b_, inner)) if o == "H" else ((inner, a), (inner, b_))
                    them.append(seg[0] + seg[1])
                    for e in seg:
                        E = Point(e)
                        ws = list(walls_tree.query(E.buffer(300)))
                        if not ws:
                            continue
                        k = min(ws, key=lambda k: walls[k].distance(E))
                        q = nearest_points(walls[k], E)[0]
                        if 1 < q.distance(E) <= 300:
                            them.append((e[0], e[1], q.x, q.y))
    syn = [t for t in them if (abs(t[1] - t[3]) < 1e-6 or abs(t[0] - t[2]) < 1e-6) and math.dist(t[:2], t[2:]) >= 400]
    for h in [t for t in syn if abs(t[1] - t[3]) < 1e-6]:
        for v in [t for t in syn if abs(t[0] - t[2]) < 1e-6]:
            ix, iy = v[0], h[1]
            eh = min(((h[0], h[1]), (h[2], h[3])), key=lambda e: math.dist(e, (ix, iy)))
            ev = min(((v[0], v[1]), (v[2], v[3])), key=lambda e: math.dist(e, (ix, iy)))
            if math.dist(eh, (ix, iy)) <= 300 and math.dist(ev, (ix, iy)) <= 300:
                them += [(eh[0], eh[1], ix, iy), (ev[0], ev[1], ix, iy)]
    them = list(dict.fromkeys(tuple(round(v, 1) for v in t) for t in them if math.dist(t[:2], t[2:]) > 0.5))
    return [(False, [t[:2], t[2:]]) for t in them]


# ---------------------------------------------------------------------------------------------------------------------
# 3. Gom can theo tien to xref, ghep ma can, phan loai vung chua ten
# ---------------------------------------------------------------------------------------------------------------------
def chuan_tien_to(raw, re_xref):
    if "$0$" not in raw and "|" not in raw:
        return None
    pre = raw.split("|")[0] if "|" in raw else raw.split("$0$")[0]
    m = re_xref.findall(pre)
    return m[-1].upper() if m else None


def phan_tich(a, doc, msp):
    global TUONG_NHAN
    TUONG_NHAN = {layer_goc(x) for x in tpp.LAYER_RANH + RANH_PHU} | CUA
    problems = []
    if doc.header.get("$INSUNITS", 0) != 4:
        problems.append((LOI, "Đơn vị bản vẽ", f"INSUNITS={doc.header.get('$INSUNITS', 0)}, chuẩn là 4 (mm)."))
    layers = [x.strip() for x in a.layer_ranh.split(",") if x.strip()]
    phu = [x.strip() for x in a.layer_ranh_phu.split(",") if x.strip()]
    print("doc ban ve...", file=sys.stderr, flush=True)
    R = doc_ban_ve(msp, layers, phu, a.do_dai_phu_min)
    dong = tpp.doc_chains(msp, [a.layer_dong_ranh]) + tpp.parse_them_ranh(a.them_ranh)
    chains = R["chains"] + dong
    seeds_all = tpp.doc_seeds(msp, a.layer_ten, doc)
    re_ma = re.compile(a.ma_can, re.I)
    ma_can = [(t, (x, y), i) for t, (x, y), i in seeds_all if re_ma.fullmatch(t.strip())]
    so_le = [(t, (x, y)) for t, (x, y), i in seeds_all if re.fullmatch(r"\d+", t.strip())]
    seeds = [s for s in seeds_all if not re_ma.fullmatch(s[0].strip()) and not re.fullmatch(r"\d+", s[0].strip())]
    khung, tk_cua = tpp.doc_khung_cua(msp, chains, [x.strip() for x in a.layer_cua.split(",") if x.strip()])
    re_mo = re.compile(a.khong_gian_mo, re.I)
    mat_ngoai = R["lan_can"] + R["nhom"] + [LineString(p) for p in R["kinh"]]
    vach = doc_vach(msp, [x.strip() for x in a.layer_vach.split(",") if x.strip()])
    vtree = shapely.STRtree(vach) if vach else None

    # lan 1: tim phong chua dong -> dung duong mat trong kinh
    print("dung mat lan 1...", file=sys.stderr, flush=True)
    faces, par, tk1, _br = dung_mat_gop(chains, khung, seeds, a.gap_max, a.gap_dai, mat_ngoai, re_mo)
    ftree = shapely.STRtree(faces)
    opens = [(x, y) for t, (x, y), i in seeds if tim_mat(Point(x, y), faces, ftree) is None]
    walls = [LineString(p + ([p[0]] if c else [])) for (c, p), ly in zip(R["chains"], R["chain_lay"]) if ly not in KINH]
    kinh = duong_kinh(opens, R, shapely.STRtree(walls), walls) if opens else []
    chains2 = chains + kinh
    chains2 = chains2 + noi_khe_nho(chains2)
    print(f"dung mat lan 2 (phong ho {len(opens)}, net kinh {len(kinh)})...", file=sys.stderr, flush=True)
    faces, par, tk, bridges = dung_mat_gop(chains2, khung, seeds, a.gap_max, a.gap_dai, mat_ngoai, re_mo)
    node = nhom_mat(faces, par)
    ftree = shapely.STRtree(faces)

    def node_of(pt):
        i = tim_mat(pt, faces, ftree)
        return par[i] if i is not None else None

    rooms = collections.OrderedDict()
    con_ho = []
    for t, (x, y), info in seeds:
        n = node_of(Point(x, y))
        if n is None:
            con_ho.append(dict(ten=t, xy=(round(x), round(y)), khe_ho_gan_nhat=tpp.khe_ho_gan(chains2, (x, y), 6000)[:3]))
            problems.append((LOI, "Phòng không đóng kín", f"'{t}' tại ({x:.0f}, {y:.0f}) chưa đóng kín sau khi đóng ô mở và dựng mặt trong kính; cần chỉ ranh (layer A-Dong ranh phong hoặc --them-ranh=)."))
            continue
        r = rooms.setdefault(n, dict(ten=[], seed=(x, y), info=info))
        r["ten"].append(t)

    # tien to xref
    re_xref = re.compile(a.xref_can, re.I)
    W, P = [], []
    for l, raw in R["tien_to"]:
        p = chuan_tien_to(raw, re_xref)
        if p:
            W.append(l); P.append(p)
    wt = shapely.STRtree(W) if W else None

    def tien_to(g):
        ring = g.exterior.buffer(60)
        cnt = collections.Counter()
        if wt is not None:
            for k in wt.query(ring):
                L = W[k].intersection(ring).length
                if L > 0:
                    cnt[P[k]] += L
        tot = sum(cnt.values())
        if not tot:
            return None, 0.0
        p, v = cnt.most_common(1)[0]
        return p, v / tot

    can = collections.defaultdict(list)
    yeu = []
    for n, r in rooms.items():
        p, fr = tien_to(node[n])
        r.update(xref=p, frac=fr)
        if p is None:
            yeu.append(r)
            continue
        can[p].append(n)
        if fr < 0.6:
            problems.append((CB, "Gán căn", f"'{' + '.join(r['ten'])}' tại ({r['seed'][0]:.0f}, {r['seed'][1]:.0f}): tiền tố xref {p} chỉ chiếm {fr:.0%} nét bao quanh."))
    if not can:
        raise SystemExit("Không thấy xref căn hộ đã bind (tên layer dạng 'CHxx$0$A-Wall'): dùng tao_duong_bo_can_ho.py cho bản vẽ này.")
    for r in yeu:
        problems.append((LOI, "Gán căn", f"Phòng '{' + '.join(r['ten'])}' tại ({r['seed'][0]:.0f}, {r['seed'][1]:.0f}) không xác định được căn (không có tiền tố xref)."))
    hop = {k: unary_union([node[n] for n in v]) for k, v in can.items()}
    cap = sorted((hop[k].distance(Point(xy)), k, t) for k in hop for t, xy, i in ma_can)
    gan, dk, dt_ = {}, set(), set()
    for d, k, t in cap:
        if k in dk or t in dt_ or d > a.ma_can_xa:
            continue
        gan[k] = (t, d); dk.add(k); dt_.add(t)
    for k in can:
        if k not in gan:
            gan[k] = (f"(xref {k})", None)
            problems.append((LOI, "Mã căn", f"Không ghép được text mã căn cho xref {k} (không có text mã căn trong {a.ma_can_xa:g} mm)."))
    for t, xy, i in ma_can:
        if t not in dt_:
            problems.append((CB, "Mã căn", f"Text mã căn '{t}' tại ({xy[0]:.0f}, {xy[1]:.0f}) không ghép với căn nào."))

    # vung chua ten
    ma_pts = [Point(xy) for t, xy, i in ma_can]
    lt = shapely.STRtree(R["lan_can"]) if R["lan_can"] else None
    nt_ = shapely.STRtree(R["nhom"]) if R["nhom"] else None
    fu = R["noi_that"]
    fut = shapely.STRtree([f[0] for f in fu]) if fu else None
    br_long = [b_ for b_ in bridges if b_.length >= 300]
    bt = shapely.STRtree(br_long) if br_long else None

    def cham(lines, tree, g, tol=80):
        return tree is not None and any(lines[k].distance(g.exterior) < tol for k in tree.query(g.buffer(tol)))

    def noi_that(g):
        gi = g.buffer(-50)
        out = collections.Counter(); blk = collections.Counter()
        if fut is None or gi.is_empty:
            return out, blk
        for k in fut.query(gi):
            L = fu[k][0].intersection(gi).length
            if L > 0:
                out[fu[k][1]] += L / 1000.0
                blk[bo_dau(fu[k][2])] += L / 1000.0
        return out, blk
    vung = []
    room_nodes = {n for v in can.values() for n in v}
    node_xref = {n: k for k, v in can.items() for n in v}

    def phia_ben_kia(arc, g):
        """Node o phia ben kia o cua cua cung quay canh 'arc' (mo vao vung g): tra ve xref cua can neu la phong cua can,
        hoac xref theo tien to neu la vung cua can; None neu la hanh lang chung / ngoai."""
        pts = list(arc.coords)
        if len(pts) < 3:
            return None
        (x1, y1), (x2, y2), (x3, y3) = pts[0], pts[len(pts) // 2], pts[-1]
        dd = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        if abs(dd) < 1e-9:
            return None
        ux = ((x1 * x1 + y1 * y1) * (y2 - y3) + (x2 * x2 + y2 * y2) * (y3 - y1) + (x3 * x3 + y3 * y3) * (y1 - y2)) / dd
        uy = ((x1 * x1 + y1 * y1) * (x3 - x2) + (x2 * x2 + y2 * y2) * (x1 - x3) + (x3 * x3 + y3 * y3) * (x2 - x1)) / dd
        H = (ux, uy)
        e_mo, e_dong = sorted([pts[0], pts[-1]], key=lambda q: -g.exterior.distance(Point(q)))   # dau canh mo nam sau trong vung
        L_ = math.dist(H, e_mo)
        if L_ < 1:
            return None
        nx, ny = (H[0] - e_mo[0]) / L_, (H[1] - e_mo[1]) / L_           # huong ra ngoai vung (nguoc canh mo)
        M = ((H[0] + e_dong[0]) / 2, (H[1] + e_dong[1]) / 2)          # giua o cua
        for d in (350, 500, 700):
            q = Point(M[0] + nx * d, M[1] + ny * d)
            i = tim_mat(q, faces, ftree)
            if i is None:
                continue
            n_ = par[i]
            if node[n_].area < 0.3e6 or node[n_].buffer(-100).is_empty:
                continue                      # tuong / o cua: thu xa hon
            if n_ in node_xref:
                return "can"
            if any(node[n_].contains(pm) for pm in ma_pts) or node[n_].area > 40e6:
                return None
            pre, fr_ = tien_to(node[n_])
            return pre if fr_ >= 0.6 else None
        return None
    ct_ = shapely.STRtree(R["cung_cua"]) if R["cung_cua"] else None
    for n, g in node.items():
        if n in rooms or g.area < 0.4e6 or g.area > 40e6 or g.buffer(-150).is_empty:
            continue
        if any(g.contains(p) for p in ma_pts):
            continue
        p, fr = tien_to(g)
        if p is None or fr < 0.5 or p not in gan:
            continue
        mo = 0
        if bt is not None:
            for k in bt.query(g.buffer(5)):
                m = br_long[k].interpolate(0.5, normalized=True)
                if g.exterior.distance(m) < 2 and any(node[rn].distance(m) < 250 for rn in can[p]):
                    mo += 1
        lc, nh = cham(R["lan_can"], lt, g), cham(R["nhom"], nt_, g)
        nt, blk = noi_that(g)
        tong_nt = sum(nt.values())
        may_giat = any("may giat" in b_ for b_ in blk)
        # cua di mo vao vung (cung quay canh nam trong vung): khong gian co cua la PHONG, khong phai hop ky thuat.
        # Phia ben kia cua la phong/khong gian cua chinh can -> phong cua can; la hanh lang chung -> ngoai can.
        cua_vao = [R["cung_cua"][k] for k in (ct_.query(g) if ct_ is not None else [])
                   if R["cung_cua"][k].intersection(g.buffer(20)).length > 0.3 * R["cung_cua"][k].length]
        co_cua = bool(cua_vao)
        cua_tu_can = any(phia_ben_kia(arc, g) in ("can", p) for arc in cua_vao)
        # phong cung can thong voi vung qua doan dong o mo (de gop hoc sanh/hanh lang vao phong)
        thong = collections.Counter()
        cau = collections.defaultdict(list)
        if bt is not None:
            for k in bt.query(g.buffer(5)):
                m = br_long[k].interpolate(0.5, normalized=True)
                if g.exterior.distance(m) < 2:
                    for rn in can[p]:
                        if node[rn].distance(m) < 250:
                            thong[rn] += br_long[k].length
                            cau[rn].append(list(br_long[k].coords))
        if ty_le_vach(g, vach, vtree) >= PHU_VACH:
            loai, ten = "vach btct", None          # khoi vach S-Wall day > 300 mm: khong phai hanh lang/lo gia, khong tinh
        elif fr < 0.6:
            loai, ten = "ngoai", None
        elif co_cua and not cua_tu_can:
            loai, ten = "ngoai", None              # phong co cua mo ra hanh lang chung (phong ky thuat/sinh hoat chung)
        elif (lc or nh or may_giat or nt["may"] >= 5) and not co_cua and nt["wc"] < 8 and g.area < 25e6                 and not g.buffer(-200).is_empty:
            # lo gia, ke ca goc dat cuc nong / may giat canh lo gia (nguoi dung chot 07/10/2026: khong phai HKT)
            loai, ten = "lo gia", "Lô gia"
        elif tong_nt >= 3 and g.area >= 2.5e6:
            loai = "phong thieu ten"
            ten = "Wc" if nt["wc"] >= 8 else "Lô gia" if (may_giat or nt["may"] >= 5) else "Phòng ngủ" if g.area >= 6e6 else "Phòng chưa tên"
        elif co_cua:
            # khong gian co cua di = phong (nguoi dung chot 07/10/2026); HKT phai xay kin, khong cua
            loai, ten = "phong thieu ten", ("Wc" if nt["wc"] >= 8 else "Phòng chưa tên")
        elif mo >= 1 and g.area < 6e6:
            loai, ten = "hanh lang", None
        else:
            loai, ten = "loai tru", None
        gop_vao = None
        if loai == "hanh lang" and thong and not g.buffer(-300).is_empty:     # hoc rong >= 600 mm; dai hep = tuong/bau, khong gop
            # hoc sanh/hanh lang truoc cua phong: gop vao phong no thong ra, uu tien phong khach/sinh hoat chung
            mo_ = [rn for rn in thong if any(re_mo.search(bo_dau(t)) for t in rooms[rn]["ten"])]
            gop_vao = max(mo_ or list(thong), key=lambda rn: (thong[rn], node[rn].area))
        c = g.representative_point()
        vung.append(dict(n=n, xref=p, ma=gan[p][0], dt=g.area / 1e6, lan_can=lc, nhom=nh, noi_that=round(tong_nt, 1),
                         wc=round(nt["wc"], 1), may=round(nt["may"], 1), may_giat=may_giat, mo=mo, frac=fr, co_cua=co_cua,
                         loai=loai, ten=ten, gop_vao=gop_vao, cau=cau.get(gop_vao, []) if gop_vao is not None else [],
                         gop_vao_ten=" + ".join(rooms[gop_vao]["ten"]) if gop_vao is not None else None, c=(c.x, c.y)))
    vung.sort(key=lambda v: (v["ma"], -v["c"][1], v["c"][0]))
    for i, v in enumerate(vung, 1):
        v["id"] = i
    return dict(problems=problems, faces=[f.wkb for f in faces], par=par, rooms=rooms, can=dict(can), gan=gan,
                vung=vung, vach=[x.wkb for x in vach], ma_can=[(t, xy) for t, xy, i in ma_can], so_le=so_le, con_ho=con_ho, tk=dict(tk), tk1=dict(tk1),
                so_kinh=len(kinh), so_phong_ho_lan1=len(opens), khung=tk_cua, file=os.path.basename(a.dxf),
                vat_can=[(l.wkb, w) for l, w in R["vat_can"]], cua_diem=R["cua_diem"], cung_cua=[l.wkb for l in R["cung_cua"]],
                ve_nen=[list(l.coords) for l in R["lan_can"]] + [p + ([p[0]] if c else []) for c, p in R["chains"]])


# ---------------------------------------------------------------------------------------------------------------------
# 4. Anh
# ---------------------------------------------------------------------------------------------------------------------
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    return plt, LineCollection


def anh_phan_tich(st, out_dir):
    plt, LC = _plt()
    from shapely import wkb
    faces = [wkb.loads(f) for f in st["faces"]]
    node = nhom_mat(faces, st["par"])
    allg = unary_union([node[n] for v in st["can"].values() for n in v])
    b = allg.bounds
    asp = (b[2] - b[0]) / max(1.0, b[3] - b[1])
    W_ = 24
    H_ = max(8, W_ / asp)
    # 1) de xuat ranh phong
    fig = plt.figure(figsize=(W_, H_), dpi=80)
    ax = fig.add_axes([0.01, 0.01, 0.98, 0.96])
    ax.add_collection(LC(st["ve_nen"], colors="#999", lw=.3))
    cm = plt.cm.tab20.colors
    for i, (k, ns) in enumerate(sorted(st["can"].items())):
        for n in ns:
            g = node[n]; r = st["rooms"][n]
            ax.fill(*g.exterior.xy, color=cm[i % 20], alpha=.5)
            ax.text(*g.representative_point().coords[0], f"{' + '.join(r['ten'])}\n{g.area / 1e6:.1f}", fontsize=6, ha="center")
        u = unary_union([node[n] for n in ns]).representative_point()
        ax.text(u.x, u.y, f"{st['gan'][k][0]}\n(xref {k})", fontsize=11, weight="bold", ha="center", color="#1864ab")
    for t, xy in st["ma_can"]:
        ax.text(*xy, t, color="b", fontsize=9, bbox=dict(fc="w", ec="b"))
    for h in st["con_ho"]:
        ax.plot(*h["xy"], "rx", ms=14, mew=3); ax.text(*h["xy"], h["ten"] + " (HỞ)", color="r", fontsize=8)
    ax.set_xlim(b[0] - 2000, b[2] + 2000); ax.set_ylim(b[1] - 2000, b[3] + 2000); ax.set_aspect("equal")
    ax.set_title("Đề xuất ranh phòng và gán căn (màu theo căn). Đỏ X = phòng chưa đóng kín", fontsize=14)
    p1 = os.path.join(out_dir, "de_xuat_ranh_phong.png"); fig.savefig(p1); plt.close(fig)
    # 2) phan loai vung chua ten
    col = {"lo gia": "#40c057", "phong thieu ten": "#7950f2", "hanh lang": "#fab005", "ngoai": "#adb5bd", "loai tru": "#fa5252",
           "vach btct": "#343a40"}
    nhan = {"lo gia": "lô gia (tính, tên 'Lô gia')", "phong thieu ten": "phòng thiếu tên (đặt tên theo nội thất)",
            "hanh lang": "hành lang/ô cửa trong căn (tính vào DTCH)", "ngoai": "ngoài căn (không tính)",
            "loai tru": "loại trừ (HKT/khoảng trống, không tính)", "vach btct": "vách BTCT S-Wall (không tính)"}
    fig = plt.figure(figsize=(W_, H_), dpi=80)
    ax = fig.add_axes([0.01, 0.01, 0.98, 0.96])
    ax.add_collection(LC(st["ve_nen"], colors="#999", lw=.3))
    for k, ns in st["can"].items():
        for n in ns:
            ax.fill(*node[n].exterior.xy, color="#d0ebff", alpha=.5)
    for v in st["vung"]:
        ax.fill(*node[v["n"]].exterior.xy, color=col[v["loai"]], alpha=.65)
        ax.text(*v["c"], f"#{v['id']}\n{v['dt']:.1f}" + (f"\n{v['ten']}" if v["ten"] else ""), fontsize=7, ha="center", va="center", weight="bold")
    for t, xy in st["ma_can"]:
        ax.text(*xy, t, color="b", fontsize=9, bbox=dict(fc="w", ec="b"))
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=col[k], label=nhan[k]) for k in col], loc="upper right", fontsize=12)
    ax.set_xlim(b[0] - 2000, b[2] + 2000); ax.set_ylim(b[1] - 2000, b[3] + 2000); ax.set_aspect("equal")
    ax.set_title("Vùng chưa có text tên phòng: phân loại tự động (số # để chỉnh bằng --doi)", fontsize=14)
    p2 = os.path.join(out_dir, "phan_loai_vung.png"); fig.savefig(p2); plt.close(fig)
    return p1, p2


# ---------------------------------------------------------------------------------------------------------------------
# 5. Xuat: polyline, nhan, duong bo can, .scr, Excel
# ---------------------------------------------------------------------------------------------------------------------
def doc_doi(text):
    """'#76=ngoai;#25=Phong ngu;#41=loai-tru;#6=hanh-lang' -> {76: ('ngoai', None), 25: ('ten', 'Phong ngu'), ...}"""
    out = {}
    for part in (text or "").split(";"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = int(k.strip().lstrip("#"))
        v = v.strip()
        vb = bo_dau(v).replace(" ", "-")
        if vb in ("ngoai", "loai-tru", "hanh-lang"):
            out[k] = (vb, None)
        else:
            out[k] = ("ten", v)
    return out


def xuat(a, doc, msp, st):
    from shapely import wkb
    LE, BUOC = a.le, a.buoc_luoi
    faces = [wkb.loads(f) for f in st["faces"]]
    node = nhom_mat(faces, st["par"])
    doi = doc_doi(a.doi)
    problems = list(st["problems"])
    vach = [wkb.loads(x) for x in st["vach"]] if "vach" in st else doc_vach(msp, [x.strip() for x in a.layer_vach.split(",") if x.strip()])
    vtree = shapely.STRtree(vach) if vach else None

    def don_gian(poly):
        p = poly.simplify(a.don_gian, preserve_topology=True)
        p = p if isinstance(p, Polygon) else max(p.geoms, key=lambda q: q.area)
        return Polygon(p.exterior, [h for h in p.interiors if Polygon(h).area > 0.01e6])

    def ring(r):
        return list(r.coords)[:-1]

    vc = [(wkb.loads(l), w) for l, w in st["vat_can"]]
    all_l = [l for l, w in vc]
    wall_l = [l for l, w in vc if w]
    t_all, t_wall = shapely.STRtree(all_l), shapely.STRtree(wall_l)
    txt = []
    for n, r in st["rooms"].items():
        i = r["info"]
        if i:
            txt.append(box(i["cx"] - i["w"] / 2, i["cy"] - i["hb"] / 2, i["cx"] + i["w"] / 2, i["cy"] + i["hb"] / 2))

    def tim_cho(vung, anchor, w, h, them=(), chi_tuong=False):
        lines = [wall_l[k] for k in t_wall.query(vung.buffer(LE))] if chi_tuong else [all_l[k] for k in t_all.query(vung.buffer(LE))]
        O = unary_union([l.buffer(LE) for l in lines] + [b_.buffer(LE) for b_ in txt if b_.intersects(vung)] + [b_.buffer(LE) for b_ in them])
        shapely.prepare(O); shapely.prepare(vung)
        minx, miny, maxx, maxy = vung.bounds
        best, bd = None, 1e18
        hw, hh = w / 2 + LE, h / 2 + LE
        y = miny + hh
        while y <= maxy - hh:
            x = minx + hw
            while x <= maxx - hw:
                d = math.hypot(x - anchor[0], y - anchor[1])
                if d < bd:
                    bb = box(x - hw, y - hh, x + hw, y + hh)
                    if vung.contains(bb) and not O.intersects(bb):
                        best, bd = (x, y), d
                x += BUOC
            y += BUOC
        return best

    ftree_x = shapely.STRtree(faces)
    cans = []
    for xref, ns in st["can"].items():
        ma = st["gan"][xref][0]
        raw = {n: node[n] for n in ns}
        gop = collections.defaultdict(list)          # phong -> cac hoc sanh/hanh lang gop vao
        for v in st["vung"]:
            if v["xref"] == xref and v.get("gop_vao") in raw and v["loai"] == "hanh lang" and v["id"] not in doi                     and not node[v["n"]].buffer(-300).is_empty:
                A_, B_ = raw[v["gop_vao"]], node[v["n"]]
                # dai o mo mong giua hai mat (be day tuong tai cho mo, giua hai doan dong) cung gop vao
                noi = [faces[k] for k in ftree_x.query(B_.buffer(5)) if faces[k].area < 1e6
                       and faces[k].distance(A_) < 1 and faces[k].distance(B_) < 1 and not faces[k].within(A_.buffer(1))]
                u_ = unary_union([A_, B_] + noi)
                if not isinstance(u_, Polygon) and v.get("cau") and A_.distance(B_) <= 250:
                    # khe mong (lop trat, be day tuong tai cho mo): lap dai chu nhat doc theo doan dong o mo, rong bang khe
                    G_ = unary_union([LineString(c_).buffer(min(300.0, LineString(c_).distance(A_) + 10), cap_style=2)
                                      for c_ in v["cau"]])
                    u_ = unary_union([A_, B_, G_.intersection(unary_union([A_, B_]).buffer(300, join_style=2))])
                if isinstance(u_, Polygon):          # chi gop khi lien mot khoi (thong qua o mo)
                    raw[v["gop_vao"]] = u_
                    gop[v["gop_vao"]].append(v["id"])
        phong = [dict(ten=" + ".join(st["rooms"][n]["ten"]), geom=don_gian(raw[n]), info=st["rooms"][n]["info"], them=False,
                      gop=gop.get(n, [])) for n in ns]
        da_gop = {i for v in gop.values() for i in v}
        them, hl = [], []
        for v in st["vung"]:
            if v["xref"] != xref:
                continue
            loai, ten = v["loai"], (v["ten"] or "").replace("Phòng (chưa tên)", "Phòng chưa tên") or None
            if v["id"] not in doi and loai != "vach btct" and ty_le_vach(node[v["n"]], vach, vtree) >= PHU_VACH:
                loai, ten = "vach btct", None      # trang thai phan tich cu chua co loai nay
            if v["id"] in doi:
                kd, tn = doi[v["id"]]
                loai, ten = ("ten", tn) if kd == "ten" else ({"ngoai": "ngoai", "loai-tru": "loai tru", "hanh-lang": "hanh lang"}[kd], None)
            g = don_gian(node[v["n"]])
            if loai in ("lo gia", "phong thieu ten", "ten") and ten and ten != "(chưa rõ)":
                them.append(dict(ten=ten, geom=g, info=None, them=True, id=v["id"], loai=v["loai"] if loai != "ten" else "nguoi dung dat ten"))
            elif loai == "phong thieu ten":
                hl.append(dict(id=v["id"], geom=g))
                problems.append((CB, "Vùng chưa rõ", f"{ma}: vùng #{v['id']} ({v['dt']:.1f} m²) có nội thất nhưng không đoán được tên; tạm tính vào DTCH, không vẽ polyline phòng. Đặt tên bằng --doi \"#{v['id']}=<tên>\"."))
            elif loai == "hanh lang" and v["id"] not in da_gop:
                hl.append(dict(id=v["id"], geom=g))
            elif loai == "vach btct":
                problems.append((GY, "Vách BTCT", f"{ma}: vùng #{v['id']} ({v['dt']:.2f} m², tâm {v['c'][0]:.0f}, {v['c'][1]:.0f}) "
                                 "là khối vách S-Wall, không tính vào DTCH."))
        u = unary_union([p["geom"] for p in phong + them] + [h["geom"] for h in hl])
        g_ = a.day_tuong_max / 2
        u = u.buffer(g_, join_style=2, mitre_limit=5).buffer(-g_, join_style=2, mitre_limit=5)
        # khoi vach BTCT (S-Wall) khong tinh vao DTCH: nam giua can -> lo loai tru; nam o bien -> duong bo di vong
        vb = [vach[k] for k in vtree.query(u)] if vtree is not None else []
        vb = [x for x in vb if x.intersection(u).area > 0.05e6]
        dt_vach = 0.0
        if vb:
            V_ = unary_union(vb)
            dt_vach = V_.intersection(u).area / 1e6
            u = u.difference(V_)
            problems.append((GY, "Vách BTCT", f"{ma}: trừ {len(vb)} khối vách S-Wall, {dt_vach:.2f} m² khỏi DTCH "
                             + "; ".join(f"({x.centroid.x:.0f}, {x.centroid.y:.0f})" for x in vb) + "."))
        pieces = sorted(getattr(u, "geoms", [u]), key=lambda q: q.area, reverse=True)
        main = don_gian(pieces[0])
        for q in pieces[1:]:
            if q.area > 0.05e6:
                problems.append((CB, "Khối rời", f"{ma}: khối {q.area / 1e6:.2f} m² tại ({q.centroid.x:.0f}, {q.centroid.y:.0f}) tách khỏi căn, không tính."))
        ext = Polygon(main.exterior)
        ho = [Polygon(h) for h in main.interiors]
        cans.append(dict(ma=ma, xref=xref, phong=phong, them=them, hl=hl, ext=ext, ho=ho,
                         dt_bo=ext.area / 1e6, dt_lt=sum(h.area for h in ho) / 1e6, dt_vach=dt_vach))
    cans.sort(key=lambda c: c["ma"])

    L = ["CMDECHO", "0", "OSMODE", "0",
         "_.-LAYER", "_M", f'"{LAYER_PHONG}"', "_C", "222", "", "",
         "_.-LAYER", "_M", f'"{LAYER_CAN}"', "_C", "6", "", ""]
    ghi_chu_nhan = []
    VE = []          # cung noi dung voi .scr, dang du lieu cho ve_com_tab_mo.py (ve thang vao tab AutoCAD dang mo qua COM)

    def ve_pl(layer, r_):
        VE.append(dict(loai="pline", layer=layer, pts=[[round(x, 4), round(y, 4)] for x, y in ring(r_)]))

    def ve_chu(n_, text):
        VE.append(dict(loai=n_["kind"].lower(), layer=n_["layer"], style=n_["style"], h=n_["h"], color=n_["color"],
                       rot=n_.get("rot", 0.0) or 0.0, x=round(n_["x"], 2), y=round(n_["y"], 2), text=text))
    for c in cans:
        c["dt"] = c["dt_bo"] - c["dt_lt"]
        ref = next((p["info"] for p in c["phong"] if p["info"]), None)
        c["ref"] = ref
        dat = []
        for p in c["phong"] + c["them"]:
            g = p["geom"]
            p["dt"] = g.area / 1e6
            p["ho"] = sum(Polygon(h).area for h in g.interiors) / 1e6
            L += ["_.-LAYER", "_S", f'"{LAYER_PHONG}"', "", "_.PLINE " + " ".join(f"{x:.4f},{y:.4f}" for x, y in ring(g.exterior)) + " _C"]
            ve_pl(LAYER_PHONG, g.exterior)
            for h in g.interiors:
                L.append("_.PLINE " + " ".join(f"{x:.4f},{y:.4f}" for x, y in ring(h)) + " _C")
                ve_pl(LAYER_PHONG, h)
            nhan = f"{r1(p['dt']):.1f} m2"
            if p["info"]:
                i = p["info"]
                wl, hl_ = tpp.do_text(doc, i["kind"], i["style"], i["h"], nhan)
                nx, ny = i["x"], i["y"]

                def vua(x_, y_):
                    return g.contains(box(x_ - wl / 2, y_ - hl_ / 2, x_ + wl / 2, y_ + hl_ / 2))
                if not vua(nx, ny):
                    ux, uy = 2 * i["cx"] - i["x"], 2 * i["cy"] - i["y"]
                    if vua(ux, uy):
                        nx, ny = ux, uy
                    else:
                        ch_ = tim_cho(g, (i["cx"], i["cy"]), wl, hl_, dat, chi_tuong=True)
                        if ch_ is None:
                            pl = polylabel(g, tolerance=20); ch_ = (pl.x, pl.y)
                        nx, ny = ch_
                    ghi_chu_nhan.append(f"{c['ma']} – {p['ten']}")
                n_ = dict(kind=i["kind"], layer=i["layer"], style=i["style"], h=i["h"], style_h=i["style_h"],
                          color=i["color"], rot=i["rot"], x=nx, y=ny)
                L += tpp.lenh_nhan(n_, nhan)
                ve_chu(n_, nhan)
                dat.append(box(nx - wl / 2, ny - hl_ / 2, nx + wl / 2, ny + hl_ / 2))
            else:
                i = ref or dict(kind="TEXT", layer=a.label_layer, style="Standard", h=a.label_h, style_h=0.0, color=256, rot=0.0)
                wt, ht = tpp.do_text(doc, i["kind"], i["style"], i["h"], p["ten"])
                wl, hl_ = tpp.do_text(doc, i["kind"], i["style"], i["h"], nhan)
                w2, h2 = max(wt, wl), ht + hl_ + 0.5 * i["h"]
                pl = polylabel(g, tolerance=20)
                cho = tim_cho(g, (pl.x, pl.y), w2, h2, dat) or tim_cho(g, (pl.x, pl.y), w2, h2, dat, chi_tuong=True) or (pl.x, pl.y)
                b0 = dict(kind=i["kind"], layer=i["layer"], style=i["style"], h=i["h"], style_h=i["style_h"], color=i["color"], rot=0.0)
                # chu trong .scr: dau "(" o dau nhac nhap chu bi AutoCAD hieu la bieu thuc LISP -> lenh TEXT treo; bo ngoac
                ten_ = re.sub(r"[()]", "", p["ten"]).strip()
                L += tpp.lenh_nhan(dict(b0, x=cho[0], y=cho[1] + h2 / 2 - ht / 2), acad(ten_))
                L += tpp.lenh_nhan(dict(b0, x=cho[0], y=cho[1] - h2 / 2 + hl_ / 2), nhan)
                ve_chu(dict(b0, x=cho[0], y=cho[1] + h2 / 2 - ht / 2), ten_)
                ve_chu(dict(b0, x=cho[0], y=cho[1] - h2 / 2 + hl_ / 2), nhan)
                dat.append(box(cho[0] - w2 / 2, cho[1] - h2 / 2, cho[0] + w2 / 2, cho[1] + h2 / 2))
        c["dat"] = dat
    re_pk = re.compile(a.phong_khach, re.I)
    for c in cans:
        L += ["_.-LAYER", "_S", f'"{LAYER_CAN}"', "", "_.PLINE " + " ".join(f"{x:.4f},{y:.4f}" for x, y in ring(c["ext"].exterior)) + " _C"]
        ve_pl(LAYER_CAN, c["ext"].exterior)
        for h in c["ho"]:
            L.append("_.PLINE " + " ".join(f"{x:.4f},{y:.4f}" for x, y in ring(h.exterior)) + " _C")
            ve_pl(LAYER_CAN, h.exterior)
        nhan = f"{a.tieu_de}: {r1(c['dt']):.1f} m2"
        pk = [p for p in c["phong"] if p["info"] and re_pk.search(bo_dau(p["ten"]))]
        i = pk[0]["info"] if pk else c["ref"]
        if i is None:
            i = dict(kind="TEXT", layer=a.label_layer, style="Standard", h=a.label_h, style_h=0.0, color=256, rot=0.0)
        vung = pk[0]["geom"] if pk else c["ext"]
        anchor = (i["cx"], i["cy"]) if pk else (lambda q: (q.x, q.y))(polylabel(c["ext"], tolerance=50))
        h = i["h"] * a.ti_le_cao
        w, hb = tpp.do_text(doc, i["kind"], i["style"], h, nhan)
        c["nhan_muc"] = "trong"
        cho = tim_cho(vung, anchor, w, hb, c["dat"])
        if cho is None:
            cho = tim_cho(vung, anchor, w, hb, c["dat"], chi_tuong=True); c["nhan_muc"] = "de noi that"
        if cho is None:
            cho = tim_cho(c["ext"], anchor, w, hb, c["dat"], chi_tuong=True); c["nhan_muc"] = "ngoai phong khach"
        if cho is None:
            cho = (i["x"], i["y"] - i["h"] - 0.5 * h) if pk else anchor; c["nhan_muc"] = "khong cho trong"
        c["nhan"] = dict(text=nhan, x=cho[0], y=cho[1], h=h, layer=i["layer"], style=i["style"])
        n_ = dict(kind=i["kind"], layer=i["layer"], style=i["style"], h=h, style_h=i["style_h"], color=i["color"],
                  rot=i.get("rot", 0.0), x=cho[0], y=cho[1])
        L += tpp.lenh_nhan(n_, nhan)
        ve_chu(n_, nhan)
    L += ["_.-LAYER", "_S", f'"{acad(doc.header.get("$CLAYER", "0"))}"', "", "_.QSAVE", "_.QUIT _Y"]
    os.makedirs(a.out_dir, exist_ok=True)
    scr = os.path.join(a.out_dir, "ve_dien_tich_tang.scr")
    open(scr, "w", encoding="ascii", newline="\n").write("\n".join(L) + "\n")
    json.dump(dict(layer={LAYER_PHONG: 222, LAYER_CAN: 6}, doi_tuong=VE),
              open(os.path.join(a.out_dir, "ve_dien_tich_tang.json"), "w", encoding="utf-8"), ensure_ascii=False)

    # cua chinh: chi ghi nhan co/khong co phan tu cua gan ma can
    cd = st["cua_diem"]
    ct = shapely.STRtree([Point(p) for p in cd]) if cd else None
    co_cua, khong_cua = [], []
    mc = dict(st["ma_can"])
    for c in cans:
        xy = mc.get(c["ma"])
        if xy is None:
            continue
        P_ = Point(xy)
        n_ = [k for k in ct.query(P_.buffer(2500))] if ct is not None else []
        (co_cua if any(c["ext"].distance(Point(cd[k])) < 400 for k in n_) else khong_cua).append(c["ma"])

    # ---- van de -----------------------------------------------------------------------------------------------------
    vd = [(None, h, m, muc) for muc, h, m in problems]
    cung = [wkb.loads(x) for x in st.get("cung_cua", [])]
    ctr = shapely.STRtree(cung) if cung else None
    for c in cans:
        for i_, h in enumerate(c["ho"], 1):
            if ctr is not None and any(cung[k].intersection(h.buffer(20)).length > 0.3 * cung[k].length for k in ctr.query(h)):
                vd.append((c["ma"], "Loại trừ có cửa", f"Phần loại trừ #{i_} ({h.area / 1e6:.2f} m²) có cửa đi mở vào: không gian có cửa là phòng, không phải HKT – kiểm tra lại.", LOI))
        for p in c["phong"]:
            if p.get("gop"):
                vd.append((c["ma"], "Gộp hốc sảnh", f"'{p['ten']}' đã gộp hốc sảnh/hành lang #{', #'.join(map(str, p['gop']))} (không gian thông với phòng, không có cửa).", GY))
        for i_, h in enumerate(c["ho"], 1):
            b_ = h.bounds
            vd.append((c["ma"], "Phần loại trừ", f"#{i_}: {h.area / 1e6:.2f} m² ({b_[2]-b_[0]:.0f}×{b_[3]-b_[1]:.0f} mm) tại ({(b_[0]+b_[2])/2:.0f}, {(b_[1]+b_[3])/2:.0f}) – vùng kín không cửa trong căn, coi là hộp kỹ thuật/cột; cần xác nhận.", CB))
        for p in c["them"]:
            if p["loai"] == "nguoi dung dat ten":
                continue
            vd.append((c["ma"], "Thiếu tên phòng", f"Vùng #{p['id']} ({p['dt']:.1f} m²) không có text tên phòng; đặt tên '{p['ten']}' theo "
                       + ("lan can/lam nhôm" if p["loai"] == "lo gia" else "nội thất") + ". Nhân viên cần bổ sung text.", LOI))
        if c["nhan_muc"] != "trong":
            vd.append((c["ma"], "Nhãn DTCH", {"de noi that": "Phòng khách/sinh hoạt chung không còn chỗ trống: nhãn đè nét nội thất (không đè tường/cửa/chữ).",
                                              "ngoai phong khach": "Phòng khách/sinh hoạt chung không đủ chỗ: nhãn đặt ở chỗ trống gần nhất trong căn.",
                                              "khong cho trong": "Không có chỗ trống đủ rộng: nhãn đặt dưới nhãn m² phòng khách, kiểm tra bằng mắt."}[c["nhan_muc"]], CB))
    if cans:
        vd.append(("Toàn tầng", "Ranh tại cửa chính", f"Quy tắc C (ranh theo mặt ngoài tường hành lang tại cửa chính) chưa áp dụng: đường bo theo mặt tường trong ở mọi căn, cần người dùng quyết định. Không thấy phần tử cửa nào trong 2,5 m quanh mã căn ở: {', '.join(khong_cua)}.", CB))
    for t, xy in st["so_le"]:
        vd.append(("Toàn tầng", "Text lạ", f"Text '{t}' tại ({xy[0]:.0f}, {xy[1]:.0f}) trên layer tên phòng không phải tên phòng – kiểm tra.", GY))
    if ghi_chu_nhan:
        vd.append(("Toàn tầng", "Nhãn phòng", f"{len(ghi_chu_nhan)} phòng hẹp: nhãn m² không đặt được ngay dưới tên, đã dời vào trong phòng.", GY))
    if st["so_kinh"]:
        vd.append(("Toàn tầng", "Vách kính", f"{st['so_phong_ho_lan1']} phòng có vách kính/cửa sổ góc không tường: ranh theo mặt trong kính (quy tắc 06/10/2026).", GY))

    # ---- Excel ------------------------------------------------------------------------------------------------------
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    DA, FT = a.du_an or "", f"{st['file']}" + (f" / {a.tang}" if a.tang else "")
    cols = ["STT", "Dự án", "File/Tầng", "Căn hộ", "Phòng", "Hạng mục", "Mô tả", "Giá trị CAD", "Giá trị thống kê",
            "Chênh lệch (m²)", "Chênh lệch (%)", "Mức độ", "Người phụ trách", "Trạng thái"]
    wb = Workbook()
    w0 = wb.active; w0.title = "Tom tat"
    ws = wb.create_sheet("Dien tich"); ws.append(cols)
    n = 0
    for c in cans:
        ph = [p for p in c["phong"] + c["them"] if p["ten"] != "Lô gia"]
        lg = [p for p in c["phong"] + c["them"] if p["ten"] == "Lô gia"]
        for p in sorted(ph, key=lambda p: p["ten"]):
            n += 1
            mt = "Thông thủy theo mặt hoàn thiện" + (f"; vùng #{p['id']} không có text tên, tên đặt theo nội thất" if p["them"] else "") \
                 + (f"; đã trừ cột/vật đứng riêng {p['ho']:.2f} m²" if p["ho"] > 0 else "") + ("; không gian mở, gộp 1 polyline" if " + " in p["ten"] else "") + (f"; gồm hốc sảnh #{', #'.join(map(str, p['gop']))}" if p.get("gop") else "")
            ws.append([n, DA, FT, c["ma"], p["ten"], "DT phòng", mt, round(p["dt"], 4), None, None, None, CB if (p["them"] or p["ho"] > 0) else DAT, None, "Đã dựng"])
        for p in lg:
            n += 1
            ws.append([n, DA, FT, c["ma"], "Lô gia", "DT lô gia (tính 100%)", ("Có text tên" if not p["them"] else f"Vùng #{p['id']}, không có text tên") + "; đo đến mặt trong lan can/vách" + ("; góc đặt cục nóng/máy giặt" if p["them"] and p["dt"] < 2.0 else ""),
                       round(p["dt"], 4), None, None, None, CB if p["them"] else DAT, None, "Đã dựng"])
        c["sp"], c["sl"] = sum(p["dt"] for p in ph), sum(p["dt"] for p in lg)
        n += 1; ws.append([n, DA, FT, c["ma"], None, "Đường bo thông thủy căn", f"Layer '{LAYER_CAN}', xref {c['xref']}", round(c["dt_bo"], 4), None, None, None, DAT, None, "Đã dựng"])
        for i_, h in enumerate(c["ho"], 1):
            n += 1; ws.append([n, DA, FT, c["ma"], None, f"Loại trừ #{i_}", "Hộp kỹ thuật/cột (cần xác nhận)", -round(h.area / 1e6, 4), None, None, None, CB, None, "Đã dựng"])
        n += 1; ws.append([n, DA, FT, c["ma"], None, "DIỆN TÍCH THÔNG THỦY CĂN HỘ (DTCH)", "= đường bo − loại trừ; nhãn " + c["nhan"]["text"], round(c["dt"], 4), None, None, None, DAT, None, "Đã dựng"])
        ch_ = c["dt"] - c["sp"] - c["sl"]
        n += 1; ws.append([n, DA, FT, c["ma"], None, "Kiểm tra: DTCH − Σ phòng − Σ lô gia", f"tường ngăn + ô cửa + hành lang trong căn chưa tên ({sum(h['geom'].area for h in c['hl']) / 1e6:.2f} m²); phải dương",
                           round(ch_, 4), None, None, None, DAT if ch_ > 0 else LOI, None, None])
    wv = wb.create_sheet("Van de"); wv.append(cols)
    for i_, (cn, hm, mt, muc) in enumerate(vd, 1):
        wv.append([i_, DA, FT, cn, None, hm, mt, None, None, None, None, muc, None, "Chờ xử lý"])
    wz = wb.create_sheet("Vung chua ten")
    wz.append(["#", "Căn", "Xref", "DT (m²)", "Phân loại", "Tên đề xuất", "Giáp lan can", "Giáp lam nhôm", "Nét nội thất (m)", "Nét TB vệ sinh (m)", "Ô mở sang phòng", "Tâm X", "Tâm Y", "Chỉnh (--doi)", "Có cửa đi", "Gộp vào phòng"])
    for v in st["vung"]:
        wz.append([v["id"], v["ma"], v["xref"], round(v["dt"], 4), v["loai"], v["ten"], "x" if v["lan_can"] else "", "x" if v["nhom"] else "",
                   v["noi_that"], v["wc"], v["mo"], round(v["c"][0]), round(v["c"][1]), "%s=%s" % (v["id"], doi[v["id"]][1] or doi[v["id"]][0]) if v["id"] in doi else "",
                   "x" if v.get("co_cua") else "", v.get("gop_vao_ten") or ""])
    w0.append([f"BÁO CÁO DIỆN TÍCH THÔNG THỦY – {DA} {a.tang or ''}".strip()])
    w0.append([f"File: {st['file']} (bản sao). Ngày {datetime.date.today():%d/%m/%Y}. Đơn vị mm. Làm tròn 1 số thập phân khi hiển thị, tính trên giá trị chưa làm tròn."])
    w0.append([])
    w0.append(["Căn hộ", "Xref", "Số phòng", "Σ phòng (m²)", "Σ lô gia (m²)", "Đường bo (m²)", "Loại trừ (m²)", "DTCH (m²)", "DTCH làm tròn", "DTCH − Σ (m²)", "Lỗi", "Cảnh báo", "Gợi ý"])
    hdr = w0.max_row
    cnt = collections.defaultdict(collections.Counter)
    for cn, hm, mt, muc in vd:
        cnt[cn][muc] += 1
    for c in cans:
        w0.append([c["ma"], c["xref"], len([p for p in c["phong"] + c["them"] if p["ten"] != "Lô gia"]), round(c["sp"], 2), round(c["sl"], 2),
                   round(c["dt_bo"], 2), round(c["dt_lt"], 2), round(c["dt"], 4), r1(c["dt"]), round(c["dt"] - c["sp"] - c["sl"], 2),
                   cnt[c["ma"]][LOI], cnt[c["ma"]][CB], cnt[c["ma"]][GY]])
    w0.append(["Toàn tầng", "", "", "", "", "", "", round(sum(c["dt"] for c in cans), 2), "", "",
               sum(v[LOI] for v in cnt.values()), sum(v[CB] for v in cnt.values()), sum(v[GY] for v in cnt.values())])
    bold, fill = Font(bold=True), PatternFill("solid", fgColor="DDEBF7")
    red, yel = PatternFill("solid", fgColor="F8CBAD"), PatternFill("solid", fgColor="FFF2CC")
    for sh, wd in ((ws, [5, 6, 30, 9, 26, 34, 80, 12, 10, 10, 10, 10, 12, 12]), (wv, [5, 6, 30, 12, 8, 22, 110, 10, 10, 10, 10, 10, 12, 12]),
                   (wz, [5, 9, 9, 9, 16, 12, 8, 8, 10, 10, 9, 9, 9, 14])):
        for cc in sh[1]:
            cc.font, cc.fill, cc.alignment = bold, fill, Alignment(wrap_text=True, vertical="center")
        for i_, w_ in enumerate(wd, 1):
            sh.column_dimensions[get_column_letter(i_)].width = w_
        sh.freeze_panes = "A2"; sh.auto_filter.ref = sh.dimensions
    for sh in (ws, wv):
        for row in sh.iter_rows(min_row=2):
            if row[11].value in (LOI, CB):
                row[11].fill = red if row[11].value == LOI else yel
    w0["A1"].font = Font(bold=True, size=14)
    for cc in w0[hdr]:
        cc.font, cc.fill, cc.alignment = bold, fill, Alignment(wrap_text=True)
    for i_, w_ in enumerate([10, 10, 9, 13, 13, 13, 12, 12, 10, 13, 7, 9, 7], 1):
        w0.column_dimensions[get_column_letter(i_)].width = w_
    ten_xlsx = f"{datetime.date.today():%Y%m%d}_{re.sub(r'[^A-Za-z0-9-]+', '', a.du_an or 'DuAn')}_{re.sub(r'[^A-Za-z0-9-]+', '', a.tang or 'Tang')}_BaoCaoDienTich.xlsx"
    xlsx = os.path.join(a.out_dir, ten_xlsx)
    wb.save(xlsx)

    # ---- anh tong ---------------------------------------------------------------------------------------------------
    plt, LC = _plt()
    b = unary_union([c["ext"] for c in cans]).bounds
    asp = (b[2] - b[0]) / max(1.0, b[3] - b[1])
    fig = plt.figure(figsize=(24, max(8, 24 / asp)), dpi=80)
    ax = fig.add_axes([0.01, 0.01, 0.98, 0.96])
    ax.add_collection(LC(st["ve_nen"], colors="#999", lw=.3))
    for c in cans:
        for p in c["phong"] + c["them"]:
            g = p["geom"]
            ax.fill(*g.exterior.xy, color="#b2f2bb" if p["ten"] == "Lô gia" else "#ffd8a8" if p["them"] else "#d0ebff", alpha=.7)
            ax.plot(*g.exterior.xy, color="#e64980", lw=.6)
            q = g.representative_point()
            ax.text(q.x, q.y, f"{p['ten']}\n{r1(p['dt']):.1f}", fontsize=5.5, ha="center", va="center")
        ax.plot(*c["ext"].exterior.xy, color="#ae3ec9", lw=2.2)
        for h in c["ho"]:
            ax.fill(*h.exterior.xy, color="#495057", alpha=.8)
        ax.text(c["nhan"]["x"], c["nhan"]["y"], f"{c['ma']}\n{c['nhan']['text']}", fontsize=10, weight="bold", ha="center", va="center",
                bbox=dict(fc="#fff3bf", ec="#ae3ec9", alpha=.9))
    ax.set_xlim(b[0] - 2000, b[2] + 2000); ax.set_ylim(b[1] - 2000, b[3] + 2000); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Phòng (xanh), lô gia (lục), phòng thiếu tên đặt theo nội thất (cam), đường bo căn (tím), loại trừ (xám)", fontsize=13)
    png = os.path.join(a.out_dir, "tong_dien_tich.png"); fig.savefig(png); plt.close(fig)
    kq = [dict(ma=c["ma"], xref=c["xref"], dtch=round(c["dt"], 4), dtch_lam_tron=r1(c["dt"]), duong_bo=round(c["dt_bo"], 4),
               loai_tru=[round(h.area / 1e6, 4) for h in c["ho"]], tong_phong=round(c["sp"], 4), tong_lo_gia=round(c["sl"], 4),
               chenh=round(c["dt"] - c["sp"] - c["sl"], 4), nhan_dtch=c["nhan_muc"],
               phong=[dict(ten=p["ten"], dt=round(p["dt"], 4), dt_lam_tron=r1(p["dt"]), vung=p.get("id")) for p in c["phong"] + c["them"]]) for c in cans]
    json.dump(kq, open(os.path.join(a.out_dir, "ket_qua_dien_tich.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return dict(scr=scr, xlsx=xlsx, anh=png, so_can=len(cans), so_phong=sum(len(c["phong"]) + len(c["them"]) for c in cans),
                van_de=dict(collections.Counter(v[3] for v in vd)), can=[dict(ma=k["ma"], dtch=k["dtch_lam_tron"], chenh=k["chenh"]) for k in kq],
                co_cua_chinh=co_cua, khong_cua_chinh=khong_cua)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("buoc", choices=["phan-tich", "xuat"])
    ap.add_argument("dxf")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--layer-ranh", default=",".join(tpp.LAYER_RANH))
    ap.add_argument("--layer-ranh-phu", default=",".join(RANH_PHU), help="layer ranh phu (lan can, tuong BTCT, nhom, kinh): bo net ngan < --do-dai-phu-min")
    ap.add_argument("--do-dai-phu-min", type=float, default=200.0)
    ap.add_argument("--layer-ten", default=tpp.LAYER_TEN)
    ap.add_argument("--layer-cua", default=",".join(tpp.LAYER_CUA))
    ap.add_argument("--layer-dong-ranh", default="A-Dong ranh phong")
    ap.add_argument("--them-ranh", default="")
    ap.add_argument("--gap-max", type=float, default=1200.0, help="o cua tu dong (mm)")
    ap.add_argument("--gap-dai", type=float, default=2600.0, help="o mo chua ve cua dong theo mat trat (mm), loc theo quy tac")
    ap.add_argument("--khong-gian-mo", default=r"sinh hoat|khach|bep|an\b|phong an", help="regex (khong dau) ten khong gian mo")
    ap.add_argument("--ma-can", default=r"CH\s*\.?\s*\d+[A-Z]?", help="regex text ma can dat ngoai cua vao")
    ap.add_argument("--ma-can-xa", type=float, default=4000.0, help="khoang cach toi da tu can den text ma can (mm)")
    ap.add_argument("--xref-can", default=r"CH\d+[A-Z]?", help="regex lay ma xref can ho tu tien to layer")
    ap.add_argument("--layer-vach", default=",".join(VACH_BTCT), help="layer vach/cot BTCT: khoi kin tren layer nay khong tinh vao DTCH")
    ap.add_argument("--doi", default="", help="chinh phan loai vung: '#76=ngoai;#25=Phong ngu;#41=loai-tru;#6=hanh-lang'")
    ap.add_argument("--day-tuong-max", type=float, default=300.0)
    ap.add_argument("--don-gian", type=float, default=10.0, help="lam gon polyline (mm), bo dinh lech < gia tri (rang cua do kinh)")
    ap.add_argument("--le", type=float, default=80.0)
    ap.add_argument("--buoc-luoi", type=float, default=50.0, help="buoc luoi tim vi tri nhan (mm)")
    ap.add_argument("--ti-le-cao", type=float, default=1.5)
    ap.add_argument("--tieu-de", default="DTCH")
    ap.add_argument("--phong-khach", default=r"sinh hoat|khach")
    ap.add_argument("--label-h", type=float, default=250.0)
    ap.add_argument("--label-layer", default="A-Text")
    ap.add_argument("--du-an", default="")
    ap.add_argument("--tang", default="")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    global TUONG_NHAN
    TUONG_NHAN = {layer_goc(x) for x in tpp.LAYER_RANH + RANH_PHU} | CUA
    os.makedirs(a.out_dir, exist_ok=True)
    doc = ezdxf.readfile(a.dxf)
    msp = doc.modelspace()
    pk = os.path.join(a.out_dir, "mbt_trang_thai.pkl")
    if a.buoc == "phan-tich":
        st = phan_tich(a, doc, msp)
        pickle.dump(st, open(pk, "wb"))
        p1, p2 = anh_phan_tich(st, a.out_dir)
        from shapely import wkb
        faces = [wkb.loads(f) for f in st["faces"]]
        node = nhom_mat(faces, st["par"])
        res = dict(file=st["file"], so_can=len(st["can"]), so_phong=len(st["rooms"]), phong_ho=st["con_ho"],
                   so_phong_ho_lan1=st["so_phong_ho_lan1"], net_kinh=st["so_kinh"], doan_dong_dai=st["tk"], khung_cua=st["khung"],
                   can=[dict(ma=st["gan"][k][0], xref=k, cach_ma_can_mm=None if st["gan"][k][1] is None else round(st["gan"][k][1]),
                             phong=[dict(ten=" + ".join(st["rooms"][n]["ten"]), dt=round(node[n].area / 1e6, 4)) for n in v])
                        for k, v in sorted(st["can"].items(), key=lambda kv: st["gan"][kv[0]][0])],
                   vung_chua_ten=[dict(id=v["id"], ma=v["ma"], dt=round(v["dt"], 2), loai=v["loai"], ten_de_xuat=v["ten"],
                                       lan_can=v["lan_can"], nhom=v["nhom"], noi_that_m=v["noi_that"], tb_ve_sinh_m=v["wc"],
                                       o_mo=v["mo"], tam=[round(t) for t in v["c"]]) for v in st["vung"]],
                   thong_ke_vung=dict(collections.Counter(v["loai"] for v in st["vung"])),
                   van_de=[dict(muc=m, hang_muc=h, mo_ta=d) for m, h, d in st["problems"]], anh=[p1, p2], trang_thai=pk)
        json.dump(res, open(os.path.join(a.out_dir, "mbt_phan_tich.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        res.pop("vung_chua_ten")
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        if not os.path.exists(pk):
            raise SystemExit("Chưa chạy bước phan-tich (thiếu mbt_trang_thai.pkl trong --out-dir).")
        st = pickle.load(open(pk, "rb"))
        print(json.dumps(xuat(a, doc, msp, st), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

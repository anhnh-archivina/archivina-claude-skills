# -*- coding: utf-8 -*-
"""doc_mb_ket_cau.py – Đọc MẶT BẰNG KẾT CẤU AutoCAD (DXF, mm) -> spec JSON dựng mô hình kết cấu BTCT trong Revit 2026.

Mục đích : skill dung-ket-cau-revit. Nhận diện theo từng mặt bằng (tên "MẶT BẰNG ĐỊNH VỊ CỘT TẦNG 1",
           "MẶT BẰNG KẾT CẤU SÀN TẦNG 2 ( CỐT +3.850 )"…): lưới trục (tên trục từ bóng trục), cột (polyline kín layer
           cột, nhãn C1…), dầm (cặp nét song song layer nét thấy / khuất + nhãn "D1-22X40", số ≤ 200 hiểu là cm), sàn
           (biên ngoài, lỗ mở có dấu X, vùng hạ / nâng cốt theo hatch + chú giải "SÀN BTCT DÀY 150, HẠ CỐT 50").
           Toạ độ quy về gốc = giao trục chữ đầu tiên × trục số đầu tiên (A × 1) để các tầng chồng đúng nhau.
Cách dùng: python doc_mb_ket_cau.py <ban_ve.dxf> --ra <thu_muc> [--vat-lieu "cot=B25;dam=B22.5;san=B22.5"]
              [--tang-tren "Mai=17350"] [--layer-cot REGEX] [--layer-dam REGEX] [--layer-truc REGEX]
Đầu ra   : <ra>/spec_ket_cau.json (cho tool rv_dung_ket_cau), <ra>/ket_qua.json (tóm tắt + can_hoi),
           <ra>/xem_lai_<tầng>.png (ảnh chồng nhận diện lên nét gốc để người dùng duyệt TRƯỚC khi ghi Revit).
Nguyên tắc: không tự suy đoán – nhãn lệch hình học, dầm thiếu nhãn, thiếu cốt / chiều dày sàn / vật liệu, cột dựng không
           có tầng trên… đều vào "can_hoi"; Claude phải hỏi người dùng trước khi dựng.
"""
import argparse
import json
import math
import os
import re
import sys
import unicodedata
from collections import defaultdict

import ezdxf
from ezdxf import path as ezpath
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, unary_union

# ------------------------------------------------------------------------------------------------ cấu hình mặc định
LAYER_TRUC = r"truc|grid|axis"
LAYER_COT = r"(^|[-_ ])cot|column|col\b"
LAYER_COT_DUNG = r"cot\s*dung"
LAYER_DAM = r"thay|khuat|dam|beam"
DO_LECH_B = 15.0        # mm – sai số cho phép giữa nhãn bề rộng dầm và khoảng cách 2 nét
TOL = 2.0               # mm – trùng / thẳng hàng


def khong_dau(s):
    s = re.sub(r"\\U\+([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), s)
    s = s.replace("%%U", "").replace("%%u", "").replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn").upper().strip()


def co_dau(s):
    s = re.sub(r"\\U\+([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), s)
    return s.replace("%%U", "").replace("%%u", "").strip()


# ------------------------------------------------------------------------------------------------ làm phẳng DXF
class Ban:
    def __init__(self):
        self.seg = []      # (layer, x0, y0, x1, y1)
        self.kin = []      # (layer, [(x,y)...]) polyline kín
        self.chu = []      # dict(layer, text, raw, x, y, rot, h)
        self.hatch = []    # (layer, pattern, [poly pts...])
        self.tron = []     # (layer, x, y, r)


def lam_phang(doc):
    b = Ban()

    def lay_ten(e, cha):
        L = e.dxf.layer if e.dxf.hasattr("layer") else "0"
        return cha if (L == "0" and cha) else L

    def goc_m(m):
        if m is None:
            return 0.0
        v = m.transform_direction((1, 0, 0))
        return math.degrees(math.atan2(v.y, v.x))

    def tf(m, p):
        if m is None:
            return (p[0], p[1])
        q = m.transform((p[0], p[1], p[2] if len(p) > 2 else 0))
        return (q.x, q.y)

    def them_chu(L, raw, ins, rot, h, m, halign=0, align=None):
        txt = co_dau(raw)
        if not txt:
            return
        rr = math.radians(rot)
        w = len(txt) * h * 0.75
        if halign in (1, 4) and align is not None:
            cx, cy = align[0], align[1]
        elif halign == 2 and align is not None:
            cx, cy = align[0] - math.cos(rr) * w / 2, align[1] - math.sin(rr) * w / 2
        else:
            cx, cy = ins[0] + math.cos(rr) * w / 2, ins[1] + math.sin(rr) * w / 2
        cx, cy = cx - math.sin(rr) * h / 2, cy + math.cos(rr) * h / 2
        x, y = tf(m, (cx, cy, 0))
        b.chu.append(dict(layer=L, text=khong_dau(txt), raw=txt, x=x, y=y, rot=(rot + goc_m(m)) % 180, h=h))

    def walk(ents, m, cha, sau=0):
        if sau > 12:
            return
        for e in ents:
            t = e.dxftype()
            L = lay_ten(e, cha)
            try:
                if t == "INSERT":
                    mm = e.matrix44() if m is None else e.matrix44() * m
                    if e.dxf.name in doc.blocks:
                        walk(doc.blocks[e.dxf.name], mm, L, sau + 1)
                    for a in e.attribs:
                        them_chu(L, a.dxf.text, a.dxf.insert, a.dxf.get("rotation", 0), a.dxf.get("height", 250), m,
                                 a.dxf.get("halign", 0), a.dxf.get("align_point"))
                elif t == "LINE":
                    p0, p1 = tf(m, e.dxf.start), tf(m, e.dxf.end)
                    b.seg.append((L, *p0, *p1))
                elif t in ("LWPOLYLINE", "POLYLINE"):
                    pth = ezpath.make_path(e)
                    if m is not None:
                        pth = pth.transform(m)
                    pts = [(v.x, v.y) for v in pth.flattening(5)]
                    if len(pts) < 2:
                        continue
                    for i in range(len(pts) - 1):
                        b.seg.append((L, *pts[i], *pts[i + 1]))
                    kin = e.closed if t == "LWPOLYLINE" else e.is_closed
                    if kin or math.dist(pts[0], pts[-1]) < TOL:
                        if math.dist(pts[0], pts[-1]) < TOL:
                            pts = pts[:-1]
                        if len(pts) >= 3:
                            b.kin.append((L, pts))
                        if kin and math.dist(pts[0], pts[-1]) >= TOL:
                            b.seg.append((L, *pts[-1], *pts[0]))
                elif t == "CIRCLE":
                    c = tf(m, e.dxf.center)
                    r = e.dxf.radius * (abs(m.transform_direction((1, 0, 0)).magnitude) if m is not None else 1)
                    b.tron.append((L, c[0], c[1], r))
                elif t == "TEXT":
                    them_chu(L, e.dxf.text, e.dxf.insert, e.dxf.get("rotation", 0), e.dxf.get("height", 250), m,
                             e.dxf.get("halign", 0), e.dxf.get("align_point"))
                elif t == "MTEXT":
                    ins = e.dxf.insert
                    h = e.dxf.get("char_height", 250)
                    them_chu(L, e.plain_text(), ins, e.dxf.get("rotation", 0), h, m, 0, None)
                elif t == "HATCH":
                    for pth in ezpath.from_hatch(e):
                        if m is not None:
                            pth = pth.transform(m)
                        pts = [(v.x, v.y) for v in pth.flattening(5)]
                        if len(pts) >= 3:
                            b.hatch.append((L, e.dxf.pattern_name.upper(), pts))
            except Exception:
                continue

    walk(doc.modelspace(), None, None)
    return b


# ------------------------------------------------------------------------------------------------ hình học phụ
def huong(s):
    dx, dy = s[3] - s[1], s[4] - s[2]
    L = math.hypot(dx, dy)
    return (dx / L, dy / L, L) if L > 1e-9 else (0, 0, 0)


def gop_thang_hang(segs, khe=5.0):
    """Gộp các đoạn thẳng hàng chồng / nối nhau (theo layer bất kỳ). Trả về [(ux,uy, c (khoảng cách pháp tuyến), t0, t1)]."""
    nhom = defaultdict(list)
    for s in segs:
        ux, uy, L = huong(s)
        if L < 20:
            continue
        if ux < -1e-9 or (abs(ux) < 1e-9 and uy < 0):
            ux, uy = -ux, -uy
        ang = round(math.degrees(math.atan2(uy, ux)) % 180, 1)
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        c = -uy * s[1] + ux * s[2]
        t0, t1 = sorted((ux * s[1] + uy * s[2], ux * s[3] + uy * s[4]))
        nhom[(ang, round(c / TOL))].append((t0, t1, c))
    ra = []
    for (ang, _), ds in nhom.items():
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        ds.sort()
        cur = list(ds[0])
        for t0, t1, c in ds[1:]:
            if t0 <= cur[1] + khe:
                cur[1] = max(cur[1], t1)
            else:
                ra.append((ux, uy, cur[2], cur[0], cur[1]))
                cur = [t0, t1, c]
        ra.append((ux, uy, cur[2], cur[0], cur[1]))
    return ra


def diem(ux, uy, c, t):
    return (ux * t - uy * c, uy * t + ux * c)


def hcn_xoay(pts):
    poly = Polygon(pts)
    if not poly.is_valid or poly.area <= 0:
        return None
    mrr = poly.minimum_rotated_rectangle
    q = list(mrr.exterior.coords)[:4]
    e0 = (q[1][0] - q[0][0], q[1][1] - q[0][1])
    e1 = (q[2][0] - q[1][0], q[2][1] - q[1][1])
    a = math.degrees(math.atan2(e0[1], e0[0]))
    l0, l1 = math.hypot(*e0), math.hypot(*e1)
    # chuẩn hoá góc về (-45, 45]
    while a > 45:
        a -= 90
        l0, l1 = l1, l0
    while a <= -45:
        a += 90
        l0, l1 = l1, l0
    return dict(cx=mrr.centroid.x, cy=mrr.centroid.y, b=l0, h=l1, rot=a, ty_le=poly.area / mrr.area if mrr.area else 0)


# ------------------------------------------------------------------------------------------------ mặt bằng (theo tên)
RE_TEN = re.compile(r"MAT\s*BANG.*?TANG\s*([0-9A-Z]+)")
RE_COT_CAO = re.compile(r"COT\s*([+\-±]?)\s*(\d+[.,]\d+)")
RE_NHAN_DAM = re.compile(r"^(?:([A-Z]{1,3}\d*[A-Z]?)\s*-\s*)?(\d+(?:[.,]\d+)?)\s*[X×]\s*(\d+(?:[.,]\d+)?)$")
RE_NHAN_COT = re.compile(r"^[A-Z]{0,3}C\d+[A-Z]?$")


def cum_truc(ban, re_truc):
    """Cụm nét trục (bbox chồng nhau) -> mỗi cụm là 1 mặt bằng."""
    segs = [s for s in ban.seg if re.search(re_truc, s[0], re.I)]
    hop = []
    for s in segs:
        hop.append([min(s[1], s[3]), min(s[2], s[4]), max(s[1], s[3]), max(s[2], s[4]), [s]])
    doi = True
    while doi:
        doi = False
        ra = []
        for h in hop:
            for r in ra:
                if h[0] <= r[2] + 500 and h[2] >= r[0] - 500 and h[1] <= r[3] + 500 and h[3] >= r[1] - 500:
                    r[0], r[1], r[2], r[3] = min(r[0], h[0]), min(r[1], h[1]), max(r[2], h[2]), max(r[3], h[3])
                    r[4] += h[4]
                    doi = True
                    break
            else:
                ra.append(h)
        hop = ra
    return [h for h in hop if (h[2] - h[0]) > 1000 and (h[3] - h[1]) > 1000]


def tim_mat_bang(ban, re_truc):
    cums = cum_truc(ban, re_truc)
    tens = [t for t in ban.chu if RE_TEN.search(t["text"])]
    mbs = []
    for cu in cums:
        x0, y0, x1, y1 = cu[:4]
        best = None
        for t in tens:
            if not (x0 - 3000 <= t["x"] <= x1 + 3000):
                continue
            dy = y0 - t["y"]
            if -500 <= dy <= 12000 and (best is None or dy < best[0]):
                best = (dy, t)
        if best is None:
            continue
        t = best[1]
        tang = RE_TEN.search(t["text"]).group(1)
        loai = "dinh_vi_cot" if "DINH VI COT" in t["text"] else "san"
        cao = None
        for u in ban.chu:
            mm = RE_COT_CAO.search(u["text"])
            if mm and abs(u["x"] - t["x"]) < 6000 and -2500 < t["y"] - u["y"] < 2500:
                cao = float(mm.group(2).replace(",", ".")) * 1000 * (-1 if mm.group(1) == "-" else 1)
                break
        if cao is None:
            mm = RE_COT_CAO.search(t["text"])
            if mm:
                cao = float(mm.group(2).replace(",", ".")) * 1000 * (-1 if mm.group(1) == "-" else 1)
        mbs.append(dict(ten=t["raw"], tang=tang, loai=loai, cao=cao, bbox=(x0, y0, x1, y1), truc_seg=cu[4]))
    mbs.sort(key=lambda m: (m["bbox"][1] // 50000 * -1, m["bbox"][0]))
    return mbs


def doc_truc(ban, mb):
    x0, y0, x1, y1 = mb["bbox"]
    lines = gop_thang_hang([s for s in mb["truc_seg"]])
    truc = []
    for ux, uy, c, t0, t1 in lines:
        if t1 - t0 < 1000:
            continue
        ten = None
        for p in (diem(ux, uy, c, t0), diem(ux, uy, c, t1)):
            for L, cx, cy, r in ban.tron:
                if r < 150 or r > 1500:
                    continue
                # bóng trục nằm trên phương kéo dài của trục, sát đầu mút
                if math.dist(p, (cx, cy)) > r * 4 + 1500:
                    continue
                dlech = abs(-uy * cx + ux * cy - c)
                if dlech > r * 0.6:
                    continue
                for t in ban.chu:
                    if math.dist((t["x"], t["y"]), (cx, cy)) < r * 1.2 and re.fullmatch(r"[0-9A-Z']{1,4}", t["text"]):
                        ten = t["text"]
                        break
                if ten:
                    break
            if ten:
                break
        truc.append(dict(ten=ten, ux=ux, uy=uy, c=c, t0=t0, t1=t1))
    # trục trùng tên (2 đoạn) -> giữ đoạn dài nhất
    gon = {}
    for tr in truc:
        k = tr["ten"] or f"?{round(tr['c'])}"
        if k not in gon or (tr["t1"] - tr["t0"]) > (gon[k]["t1"] - gon[k]["t0"]):
            gon[k] = tr
    return list(gon.values())


def goc_toa_do(truc):
    """Gốc = giao trục chữ đầu tiên × trục số đầu tiên."""
    chu = sorted([t for t in truc if t["ten"] and t["ten"][0].isalpha()], key=lambda t: t["ten"])
    so = sorted([t for t in truc if t["ten"] and t["ten"][0].isdigit()], key=lambda t: (len(t["ten"]), t["ten"]))
    if not chu or not so:
        return None
    a, n = chu[0], so[0]
    det = a["ux"] * n["uy"] - a["uy"] * n["ux"]
    if abs(det) < 1e-6:
        return None
    # điểm trên a: P = c_a * (-uy, ux) + s*(ux, uy); giải giao 2 đường
    pa = (-a["uy"] * a["c"], a["ux"] * a["c"])
    pn = (-n["uy"] * n["c"], n["ux"] * n["c"])
    s = ((pn[0] - pa[0]) * n["uy"] - (pn[1] - pa[1]) * n["ux"]) / det
    return (pa[0] + s * a["ux"], pa[1] + s * a["uy"]), f"{a['ten']}x{n['ten']}"


# ------------------------------------------------------------------------------------------------ cột
def doc_cot(ban, mb, re_cot, re_cot_dung, vung, xung_dot=None):
    cots = []
    xung_dot = [] if xung_dot is None else xung_dot
    for L, pts in ban.kin:
        if not re.search(re_cot, L, re.I):
            continue
        if not vung.contains(Point(pts[0])):
            continue
        r = hcn_xoay(pts)
        if r is None or r["b"] < 100 or r["h"] < 100 or max(r["b"], r["h"]) > 3000:
            continue
        r["dung"] = bool(re.search(re_cot_dung, L, re.I))
        r["poly"] = pts
        # cột cắt và cột dựng cùng vị trí là 2 đoạn cột khác nhau (dưới / trên sàn) – chỉ bỏ trùng cùng loại
        if any(math.dist((r["cx"], r["cy"]), (c["cx"], c["cy"])) < 20 and c["dung"] == r["dung"]
               and abs(c["b"] - r["b"]) < 5 and abs(c["h"] - r["h"]) < 5 for c in cots):
            continue
        chong = next((c for c in cots if c["dung"] == r["dung"] and Polygon(c["poly"]).intersects(Polygon(pts))), None)
        if chong is not None:
            # 2 polyline cột chồng nhau khác tiết diện: giữ cột lớn, ghi lại để hỏi
            lon, nho = (chong, r) if chong["b"] * chong["h"] >= r["b"] * r["h"] else (r, chong)
            xung_dot.append((lon["cx"], lon["cy"], f"{lon['b']:.0f}x{lon['h']:.0f}", f"{nho['b']:.0f}x{nho['h']:.0f}"))
            if lon is r:
                cots.remove(chong)
            else:
                continue
        r["layer"] = L
        r["poly"] = pts
        r["nhan"] = None
        cots.append(r)
    nhans = [t for t in ban.chu if RE_NHAN_COT.match(t["text"]) and vung.contains(Point(t["x"], t["y"]))]
    for t in nhans:
        best = min(cots, key=lambda c: math.dist((c["cx"], c["cy"]), (t["x"], t["y"])), default=None)
        if best and math.dist((best["cx"], best["cy"]), (t["x"], t["y"])) < 1500 and best["nhan"] is None:
            best["nhan"] = t["text"]
    return cots


# ------------------------------------------------------------------------------------------------ dầm
def doc_nhan_dam(t):
    m = RE_NHAN_DAM.match(t["text"].replace(" ", ""))
    if not m:
        return None
    a, b = float(m.group(2).replace(",", ".")), float(m.group(3).replace(",", "."))
    he = 10.0 if max(a, b) <= 200 else 1.0
    return dict(ma=m.group(1), b=a * he, h=b * he, don_vi="cm" if he == 10 else "mm")


def doc_dam(ban, mb, re_dam, vung, cots, can_hoi, ten_mb):
    segs = [s for s in ban.seg if re.search(re_dam, s[0], re.I) and not re.search(LAYER_COT, s[0], re.I)
            and vung.intersects(LineString([(s[1], s[2]), (s[3], s[4])]))]
    lines = gop_thang_hang(segs, khe=600)
    nhans = []
    for t in ban.chu:
        if not vung.contains(Point(t["x"], t["y"])):
            continue
        nd = doc_nhan_dam(t)
        if nd:
            nd.update(x=t["x"], y=t["y"], rot=t["rot"], raw=t["raw"])
            nhans.append(nd)
    tho = []
    for nd in nhans:
        a = math.radians(round(nd["rot"]) % 180)
        ux, uy = math.cos(a), math.sin(a)
        tl = ux * nd["x"] + uy * nd["y"]
        cl = -uy * nd["x"] + ux * nd["y"]
        song = [ln for ln in lines if abs(ln[0] * ux + ln[1] * uy) > 0.999 and ln[3] - 50 <= tl <= ln[4] + 50]
        best, gan = None, None
        for i, l1 in enumerate(song):
            for l2 in song[i + 1:]:
                d = abs(l1[2] - l2[2])
                if d < 80 or d > 1200:
                    continue
                t0, t1 = max(l1[3], l2[3]), min(l1[4], l2[4])
                if t1 - t0 < 200:
                    continue
                cm = (l1[2] + l2[2]) / 2
                kc = abs(cm - cl)
                if kc > d / 2 + 900:
                    continue
                if abs(d - nd["b"]) <= DO_LECH_B:
                    if best is None or kc < best[0]:
                        best = (kc, cm, t0, t1, d)
                elif gan is None or kc < gan[0]:
                    gan = (kc, cm, t0, t1, d)
        if best is None:
            if gan is not None and gan[0] < 600:
                can_hoi.append(dict(loai="dam_lech_tiet_dien", mat_bang=ten_mb, nhan=nd["raw"],
                                    mo_ta=f"Nhãn {nd['raw']} (b={nd['b']:.0f}) nhưng 2 nét gần nhất cách nhau {gan[4]:.0f} mm – dầm nào đúng?"))
            else:
                can_hoi.append(dict(loai="nhan_dam_khong_thay_dam", mat_bang=ten_mb, nhan=nd["raw"],
                                    mo_ta=f"Nhãn {nd['raw']} tại ({nd['x']:.0f}, {nd['y']:.0f}) không ghép được cặp nét dầm nào."))
            continue
        _, cm, t0, t1, d = best
        tho.append(dict(ux=ux, uy=uy, c=cm, t0=t0, t1=t1, tl=tl, b=nd["b"], h=nd["h"], ma=nd["ma"], nhan=nd["raw"], don_vi=nd["don_vi"]))

    # chia nhịp theo gối (cột cắt dải dầm, dầm vuông góc) -> lấy nhịp chứa nhãn, đầu dầm về tim gối
    dams = []
    for d in tho:
        strip = LineString([diem(d["ux"], d["uy"], d["c"], d["t0"] - 600), diem(d["ux"], d["uy"], d["c"], d["t1"] + 600)]).buffer(d["b"] / 2, cap_style=2)
        # nhịp chỉ chia theo CỘT (dầm cắt ngang không chia dầm chính: nhãn ghi 1 lần cho cả dầm liên tục)
        goi = []
        for c in cots:
            if strip.intersects(Polygon(c["poly"])):
                goi.append(d["ux"] * c["cx"] + d["uy"] * c["cy"])
        goi = sorted(set(round(g, 1) for g in goi))
        trai = max([g for g in goi if g <= d["tl"]], default=None)
        phai = min([g for g in goi if g >= d["tl"]], default=None)
        a = trai if trai is not None and trai >= d["t0"] - 600 else d["t0"]
        b2 = phai if phai is not None and phai <= d["t1"] + 600 else d["t1"]
        # đầu dầm không tựa cột: kéo về tim dầm vuông góc mà nó chạm tới
        for dau in ("a", "b"):
            t_dau = a if dau == "a" else b2
            if t_dau in goi:
                continue
            p = Point(diem(d["ux"], d["uy"], d["c"], t_dau))
            best = None
            for e in tho:
                if e is d or abs(e["ux"] * d["ux"] + e["uy"] * d["uy"]) > 0.1:
                    continue
                le = LineString([diem(e["ux"], e["uy"], e["c"], e["t0"] - 300), diem(e["ux"], e["uy"], e["c"], e["t1"] + 300)])
                kc = le.distance(p)
                if kc <= e["b"] / 2 + d["b"] / 2 + 150 and (best is None or kc < best[0]):
                    x = LineString([diem(d["ux"], d["uy"], d["c"], d["t0"] - 2000), diem(d["ux"], d["uy"], d["c"], d["t1"] + 2000)]).intersection(
                        LineString([diem(e["ux"], e["uy"], e["c"], e["t0"] - 2000), diem(e["ux"], e["uy"], e["c"], e["t1"] + 2000)]))
                    if not x.is_empty:
                        best = (kc, d["ux"] * x.x + d["uy"] * x.y)
            if best is not None:
                if dau == "a":
                    a = best[1]
                else:
                    b2 = best[1]
        if b2 - a < 200:
            continue
        k = (round(d["ux"], 3), round(d["uy"], 3), round(d["c"]), round(a), round(b2))
        if any(x["_k"] == k for x in dams):
            continue
        dams.append(dict(_k=k, p0=diem(d["ux"], d["uy"], d["c"], a), p1=diem(d["ux"], d["uy"], d["c"], b2),
                         b=d["b"], h=d["h"], ma=d["ma"], nhan=d["nhan"]))

    # cặp nét khuất (dầm) không có nhãn -> hỏi
    khuat = gop_thang_hang([s for s in segs if re.search(r"khuat|hidden|dash", s[0], re.I)])
    phu = unary_union([LineString([x["p0"], x["p1"]]).buffer(x["b"] / 2 + 30) for x in dams]) if dams else None
    da_bao = []
    for i, l1 in enumerate(khuat):
        for l2 in khuat[i + 1:]:
            if abs(l1[0] * l2[0] + l1[1] * l2[1]) < 0.999:
                continue
            dd = abs(l1[2] - l2[2])
            t0, t1 = max(l1[3], l2[3]), min(l1[4], l2[4])
            if not (100 <= dd <= 600) or t1 - t0 < 500:
                continue
            cm = (l1[2] + l2[2]) / 2
            mid = Point(diem(l1[0], l1[1], cm, (t0 + t1) / 2))
            if phu is not None and phu.contains(mid):
                continue
            if any(mid.distance(p) < 300 for p in da_bao):
                continue
            da_bao.append(mid)
    return dams, da_bao


# ------------------------------------------------------------------------------------------------ sàn
RE_DAY = re.compile(r"DAY\s*(\d+)")
RE_HA = re.compile(r"(HA|NANG)\s*COT\s*(\d+)")


def doc_chu_giai(ban):
    """Mục chú giải sàn: text 'SÀN … DÀY 150, HẠ CỐT 50' + ô mẫu (polyline kín bên trái) + hatch trong ô."""
    muc = []
    for t in ban.chu:
        if "SAN" not in t["text"] or not (RE_DAY.search(t["text"]) or RE_HA.search(t["text"])):
            continue
        o = None
        for L, pts in ban.kin:
            p = Polygon(pts)
            if p.area > 4e6 or p.area < 1e4:
                continue
            c = p.centroid
            if 0 < t["x"] - c.x < 3500 and abs(t["y"] - c.y) < 400:
                if o is None or t["x"] - c.x < t["x"] - o.centroid.x:
                    o = p
        if o is None:
            continue
        mau = None
        for L, pat, pts in ban.hatch:
            if o.buffer(5).contains(Point(Polygon(pts).centroid)):
                mau = pat
                break
        md = RE_DAY.search(t["text"])
        mh = RE_HA.search(t["text"])
        muc.append(dict(x=o.bounds[0], y=t["y"], text=t["raw"], mau=mau, day=float(md.group(1)) if md else None,
                        lech=(-1 if mh.group(1) == "HA" else 1) * float(mh.group(2)) if mh else 0.0))
    return muc


def la_lo_mo(face, segs):
    """Ô có dấu X (2 đường chéo nối góc đối) = lỗ mở / ô thông tầng."""
    f = face.simplify(5)
    if len(f.exterior.coords) - 1 != 4 or f.area < 0.97 * f.minimum_rotated_rectangle.area:
        return False
    q = list(f.exterior.coords)[:-1]
    cheo = 0
    for s in segs:
        a, b = (s[1], s[2]), (s[3], s[4])
        if math.dist(a, b) < 300:
            continue
        for i, j in ((0, 2), (1, 3)):
            if True:
                if (math.dist(a, q[i]) < 60 and math.dist(b, q[j]) < 60) or (math.dist(b, q[i]) < 60 and math.dist(a, q[j]) < 60):
                    cheo += 1
    return cheo >= 2


def doc_san(ban, mb, re_dam, vung, cots, chu_giai, can_hoi, ten_mb):
    segs = [s for s in ban.seg if s[0].upper() != "DEFPOINTS" and vung.intersects(LineString([(s[1], s[2]), (s[3], s[4])]))]
    ket = [s for s in segs if re.search(re_dam, s[0], re.I) and not re.search(LAYER_COT, s[0], re.I)]
    net = unary_union([LineString([(s[1], s[2]), (s[3], s[4])]) for s in ket])
    faces = [f for f in polygonize(net) if f.area > 2e5]
    if not faces:
        can_hoi.append(dict(loai="khong_dung_duoc_bien_san", mat_bang=ten_mb, mo_ta="Không khép được biên sàn từ nét dầm / mép sàn."))
        return [], [], None
    bien = unary_union(faces)
    if bien.geom_type == "MultiPolygon":
        bien = max(bien.geoms, key=lambda g: g.area)
    bien = Polygon(bien.exterior)
    # ô ứng viên: polyline kín + ô khép bởi nét song song trục (bỏ đường chéo của dấu X để ô không bị chia tam giác)
    vuong = [s for s in segs if abs(s[1] - s[3]) < TOL or abs(s[2] - s[4]) < TOL]
    ung = [Polygon(pts) for L, pts in ban.kin if not re.search(LAYER_COT, L, re.I) and vung.contains(Point(pts[0]))]
    ung += list(polygonize(unary_union([LineString([(s[1], s[2]), (s[3], s[4])]) for s in vuong])))
    lo = []
    for f in ung:
        if not f.is_valid or f.area < 4e4 or f.area > 0.5 * bien.area or not bien.buffer(50).contains(f) or not la_lo_mo(f, segs):
            continue
        if any(f.symmetric_difference(g).area < 0.02 * f.area for g in lo):
            continue
        lo.append(f)
    # chú giải của mặt bằng: mục gần nhất bên phải / dưới cùng tờ
    x0, y0, x1, y1 = mb["bbox"]
    cg = [m for m in chu_giai if x0 - 2000 <= m["x"] <= x1 + 20000 and y0 - 25000 <= m["y"] <= y1 + 5000]
    if cg:
        xg = min(m["x"] for m in cg)
        cg = [m for m in cg if abs(m["x"] - xg) < 3000]
    goc = [m for m in cg if m["mau"] is None and m["day"]]
    day0 = goc[0]["day"] if goc else None
    if day0 is None:
        can_hoi.append(dict(loai="thieu_chieu_day_san", mat_bang=ten_mb, mo_ta="Không đọc được chiều dày sàn (chú giải 'SÀN BTCT DÀY …')."))
    theo_mau = {m["mau"]: m for m in cg if m["mau"]}
    vung_cot = []
    for L, pat, pts in ban.hatch:
        p = Polygon(pts)
        if not p.is_valid:
            p = p.buffer(0)
        if p.area < 1e4 or not bien.buffer(50).contains(p.representative_point()):
            continue
        if any(p.intersection(Polygon(c["poly"])).area > 0.8 * p.area for c in cots):
            continue
        if pat not in theo_mau:
            if pat != "SOLID":
                can_hoi.append(dict(loai="hatch_khong_co_chu_giai", mat_bang=ten_mb,
                                    mo_ta=f"Hatch {pat} ({p.area / 1e6:.2f} m²) trong sàn không có trong chú giải – vùng hạ / nâng cốt bao nhiêu?"))
            continue
        m = theo_mau[pat]
        vung_cot.append(dict(poly=p.intersection(bien), lech=m["lech"], day=m["day"] or day0, ghi_chu=m["text"]))
    return bien, lo, dict(day=day0, vung=vung_cot, chu_giai=[m["text"] for m in cg])


def vong(poly, goc):
    pts = [(round(x - goc[0], 1), round(y - goc[1], 1)) for x, y in list(poly.exterior.coords)[:-1]]
    ra = [pts]
    for r in poly.interiors:
        ra.append([(round(x - goc[0], 1), round(y - goc[1], 1)) for x, y in list(r.coords)[:-1]])
    return ra


def tach_da_giac(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [x for x in getattr(g, "geoms", []) if x.geom_type == "Polygon" and x.area > 1e4]


# ------------------------------------------------------------------------------------------------ ảnh xem lại
def ve_anh(ban, mb, vung, cots, dams, nghi, san, lo, duong_dan):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x0, y0, x1, y1 = vung.bounds
    fig, ax = plt.subplots(figsize=(16, 16 * (y1 - y0) / max(x1 - x0, 1) + 1.5), dpi=90)
    for s in ban.seg:
        if x0 <= s[1] <= x1 and y0 <= s[2] <= y1:
            ax.plot([s[1], s[3]], [s[2], s[4]], color="#bbbbbb", lw=0.4)
    if san is not None:
        ax.fill(*san["bien"].exterior.xy, color="#cfe3ff", alpha=0.5, lw=0)
        for v in san["vung"]:
            for g in tach_da_giac(v["poly"]):
                ax.fill(*g.exterior.xy, color="#ffd27f", alpha=0.6, lw=0)
                ax.text(g.centroid.x, g.centroid.y, f"{v['lech']:+.0f}", color="#a05a00", fontsize=8, ha="center")
    for f in lo:
        ax.fill(*f.exterior.xy, color="white", hatch="xx", ec="#888888", lw=0.6)
    for d in dams:
        r = LineString([d["p0"], d["p1"]]).buffer(d["b"] / 2, cap_style=2)
        ax.fill(*r.exterior.xy, color="#2e7d32", alpha=0.55, lw=0)
        mx, my = (d["p0"][0] + d["p1"][0]) / 2, (d["p0"][1] + d["p1"][1]) / 2
        ax.text(mx, my, f"{d['ma'] or ''} {d['b']:.0f}x{d['h']:.0f}", fontsize=7, color="#0b3d0b", ha="center", va="center")
    for p in nghi:
        ax.plot(p.x, p.y, "o", ms=10, mfc="none", mec="red", mew=2)
    for c in cots:
        ax.fill(*Polygon(c["poly"]).exterior.xy, color="#c62828" if not c["dung"] else "#6a1b9a", alpha=0.85, lw=0)
        ax.text(c["cx"], c["cy"] - c["h"] / 2 - 250, f"{c['nhan'] or '?'} {c['b']:.0f}x{c['h']:.0f}", fontsize=7, color="#b71c1c", ha="center")
    ax.set_aspect("equal")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_title(f"{mb['ten']}  –  xanh lá: dầm | đỏ: cột (tím: cột dựng) | cam: vùng hạ/nâng cốt | X: lỗ mở | vòng đỏ: nghi dầm thiếu nhãn", fontsize=9)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(duong_dan)
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ chính
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf")
    ap.add_argument("--ra", required=True)
    ap.add_argument("--vat-lieu", default="", help='"cot=B25;dam=B22.5;san=B22.5"')
    ap.add_argument("--tang-tren", default="", help='level trên cùng cho cột dựng, ví dụ "Mai=17350"')
    ap.add_argument("--layer-cot", default=LAYER_COT)
    ap.add_argument("--layer-cot-dung", default=LAYER_COT_DUNG)
    ap.add_argument("--layer-dam", default=LAYER_DAM)
    ap.add_argument("--layer-truc", default=LAYER_TRUC)
    a = ap.parse_args()
    os.makedirs(a.ra, exist_ok=True)

    doc = ezdxf.readfile(a.dxf)
    can_hoi, canh_bao = [], []
    don_vi = doc.header.get("$INSUNITS", 0)
    if don_vi != 4:
        can_hoi.append(dict(loai="don_vi", mo_ta=f"INSUNITS={don_vi} (không phải mm) – xác nhận đơn vị bản vẽ."))
    ban = lam_phang(doc)
    mbs = tim_mat_bang(ban, a.layer_truc)
    if not mbs:
        print(json.dumps(dict(loi="Không tìm thấy mặt bằng (tên 'MẶT BẰNG … TẦNG …' dưới cụm lưới trục)."), ensure_ascii=False))
        sys.exit(2)
    chu_giai = doc_chu_giai(ban)

    vl = {}
    for kv in a.vat_lieu.split(";"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            vl[k.strip().lower()] = v.strip()
    for k in ("cot", "dam", "san"):
        if k not in vl:
            can_hoi.append(dict(loai="vat_lieu", mo_ta=f"Chưa có cấp bền bê tông cho {k} (--vat-lieu \"cot=B25;dam=B22.5;san=B22.5\")."))
    ten_vl = {k: f"Archivina_BT {vl[k]}" if k in vl else "Archivina_BTCT (chua xac dinh)" for k in ("cot", "dam", "san")}

    # ---- từng mặt bằng
    ds = []
    truc_chuan, ten_goc = None, None
    for mb in mbs:
        tr = doc_truc(ban, mb)
        g = goc_toa_do(tr)
        if g is None:
            can_hoi.append(dict(loai="khong_xac_dinh_goc", mat_bang=mb["ten"], mo_ta="Không đọc được tên trục (A…/1…) để quy gốc toạ độ."))
            continue
        goc, ten_g = g
        x0, y0, x1, y1 = mb["bbox"]
        vung = box(x0 - 1500, y0 - 1500, x1 + 1500, y1 + 1500)
        xd = []
        cots = doc_cot(ban, mb, a.layer_cot, a.layer_cot_dung, vung, xd)
        for cx, cy, lon, nho in xd:
            can_hoi.append(dict(loai="cot_chong_khac_tiet_dien", mat_bang=mb["ten"],
                                mo_ta=f"Tại ({cx - goc[0]:.0f}, {cy - goc[1]:.0f}) có 2 polyline cột chồng nhau {lon} và {nho} – "
                                      f"đang lấy {lon}; tiết diện đúng là gì (đổi tiết diện ở tầng này?)"))
        dams, nghi = doc_dam(ban, mb, a.layer_dam, vung, cots, can_hoi, mb["ten"]) if mb["loai"] == "san" else ([], [])
        for p in nghi:
            can_hoi.append(dict(loai="dam_thieu_nhan", mat_bang=mb["ten"],
                                mo_ta=f"Cặp nét khuất tại ({p.x - goc[0]:.0f}, {p.y - goc[1]:.0f}) so với {ten_g} giống dầm nhưng không có nhãn tiết diện."))
        san, lo, bien = None, [], None
        if mb["loai"] == "san":
            bien, lo, sinfo = doc_san(ban, mb, a.layer_dam, vung, cots, chu_giai, can_hoi, mb["ten"])
            if bien is not None:
                san = dict(bien=bien, **sinfo)
        ten_anh = re.sub(r"[^0-9A-Za-z]+", "_", khong_dau(mb["ten"])).strip("_")[:60]
        ve_anh(ban, mb, vung, cots, dams, nghi, san, lo, os.path.join(a.ra, f"xem_lai_{ten_anh}.png"))
        # đối chiếu lưới trục giữa các mặt bằng
        tr_loc = {t["ten"]: round(t["c"] - (-t["uy"] * goc[0] + t["ux"] * goc[1])) for t in tr if t["ten"]}
        if truc_chuan is None:
            truc_chuan, ten_goc = (tr, goc, tr_loc), ten_g
        elif tr_loc != truc_chuan[2]:
            canh_bao.append(f"Lưới trục '{mb['ten']}' khác mặt bằng đầu: {tr_loc} / {truc_chuan[2]}")
        ds.append(dict(mb=mb, goc=goc, cots=cots, dams=dams, san=san, lo=lo, anh=f"xem_lai_{ten_anh}.png"))

    # ---- level
    levels = {}
    for d in ds:
        mb = d["mb"]
        cao = mb["cao"]
        if cao is None and mb["loai"] == "dinh_vi_cot":
            cao = 0.0  # quy ước đã chốt: chân cột tầng 1 tại ±0.000
            canh_bao.append(f"{mb['ten']}: không ghi cốt – lấy ±0.000 (quy ước chân cột tầng 1).")
        if cao is None:
            can_hoi.append(dict(loai="thieu_cot", mat_bang=mb["ten"], mo_ta="Mặt bằng không ghi cốt (CỐT +x.xxx)."))
            continue
        ten = f"Tầng {mb['tang']}"
        if ten in levels and abs(levels[ten] - cao) > 1:
            can_hoi.append(dict(loai="cot_mau_thuan", mo_ta=f"{ten}: cốt {levels[ten]:.0f} và {cao:.0f} mâu thuẫn."))
        levels[ten] = cao
    if a.tang_tren:
        for kv in a.tang_tren.split(";"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                levels[k.strip()] = float(v)
    lv_ds = sorted(levels.items(), key=lambda kv: kv[1])
    idx = {ten: i for i, (ten, _) in enumerate(lv_ds)}

    def lv_cua(d):
        return idx.get(f"Tầng {d['mb']['tang']}")

    spec = dict(levels=[dict(name=t, elev=round(e, 1)) for t, e in lv_ds], grids=[], materials=[], columns=[], beams=[], floors=[],
                view_3d="Archivina_3D KC")
    mau_vl = {"cot": [150, 150, 150], "dam": [175, 175, 170], "san": [200, 200, 195]}
    for k in ("cot", "dam", "san"):
        if not any(m["name"] == ten_vl[k] for m in spec["materials"]):
            spec["materials"].append(dict(name=ten_vl[k], color=mau_vl[k]))

    # ---- trục (theo mặt bằng đầu tiên)
    if truc_chuan:
        tr, goc, _ = truc_chuan
        for t in tr:
            p0, p1 = diem(t["ux"], t["uy"], t["c"], t["t0"]), diem(t["ux"], t["uy"], t["c"], t["t1"])
            spec["grids"].append(dict(name=t["ten"], p0=[round(p0[0] - goc[0], 1), round(p0[1] - goc[1], 1)],
                                      p1=[round(p1[0] - goc[0], 1), round(p1[1] - goc[1], 1)]))
        if any(t["ten"] is None for t in tr):
            can_hoi.append(dict(loai="truc_thieu_ten", mo_ta=f"{sum(t['ten'] is None for t in tr)} trục không đọc được tên bóng trục."))

    # ---- cột theo tầng: (tầng k -> k+1) = định vị cột tầng k ∪ cột cắt trên MB sàn tầng k+1 ∪ cột dựng tầng k
    doan = defaultdict(dict)   # (i_duoi) -> {(x,y): cot}
    for d in ds:
        i = lv_cua(d)
        if i is None:
            continue
        for c in d["cots"]:
            q = (round(c["cx"] - d["goc"][0]), round(c["cy"] - d["goc"][1]))
            if d["mb"]["loai"] == "dinh_vi_cot" or c["dung"]:
                k = i
            else:
                k = i - 1
            if k < 0:
                continue
            ton = next((v for p, v in doan[k].items() if math.dist(p, q) < 30), None)
            if ton is None:
                doan[k][q] = dict(c, nguon=d["mb"]["ten"])
            elif abs(ton["b"] - c["b"]) > 5 or abs(ton["h"] - c["h"]) > 5:
                canh_bao.append(f"Cột {c['nhan'] or ''} tại {q}: {ton['nguon']} {ton['b']:.0f}x{ton['h']:.0f} ≠ {d['mb']['ten']} "
                                f"{c['b']:.0f}x{c['h']:.0f} – dùng tiết diện mặt bằng dưới.")
            if ton is not None and not ton.get("nhan") and c.get("nhan"):
                ton["nhan"] = c["nhan"]
    ma_vt = {}
    for cs in doan.values():
        for q, c in cs.items():
            if c.get("nhan"):
                ma_vt.setdefault(q, c["nhan"])
    for cs in doan.values():
        for q, c in cs.items():
            if not c.get("nhan"):
                c["nhan"] = next((m for p, m in ma_vt.items() if math.dist(p, q) < 30), None)
    for k, cs in sorted(doan.items()):
        if k + 1 >= len(lv_ds):
            for q, c in cs.items():
                can_hoi.append(dict(loai="cot_khong_co_tang_tren", mo_ta=f"Cột {c['nhan'] or '?'} {c['b']:.0f}x{c['h']:.0f} tại {q} "
                                    f"bắt đầu ở {lv_ds[k][0]} nhưng không có tầng trên – đỉnh cột ở cốt nào? (--tang-tren \"Mai=…\")"))
            continue
        for q, c in cs.items():
            spec["columns"].append(dict(mark=c["nhan"] or "", b=round(c["b"]), h=round(c["h"]), pt=list(q), rot=round(c["rot"], 2),
                                        level=k, top_level=k + 1, material=ten_vl["cot"]))
            if not c["nhan"]:
                canh_bao.append(f"Cột tại {q} ({lv_ds[k][0]}) không có mã (C1…).")
    # cột cùng mã khác tiết diện trong cùng tầng
    ma = defaultdict(set)
    for c in spec["columns"]:
        if c["mark"]:
            ma[(c["level"], c["mark"])].add((c["b"], c["h"]))
    for (lv, m), s in ma.items():
        if len(s) > 1:
            can_hoi.append(dict(loai="cot_cung_ma_khac_tiet_dien", mo_ta=f"{lv_ds[lv][0]}: cột {m} có các tiết diện {sorted(s)}."))

    # ---- dầm, sàn
    tk = defaultdict(int)
    for d in ds:
        i = lv_cua(d)
        if i is None or d["mb"]["loai"] != "san":
            continue
        g = d["goc"]
        for b in d["dams"]:
            spec["beams"].append(dict(mark=b["ma"] or "", b=round(b["b"]), h=round(b["h"]),
                                      p0=[round(b["p0"][0] - g[0], 1), round(b["p0"][1] - g[1], 1)],
                                      p1=[round(b["p1"][0] - g[0], 1), round(b["p1"][1] - g[1], 1)],
                                      level=i, offset=0, material=ten_vl["dam"]))
            tk[f"dam {lv_ds[i][0]}"] += 1
        s = d["san"]
        if s is None or s["day"] is None:
            continue
        bien = s["bien"]
        for f in d["lo"]:
            bien = bien.difference(f)
        con = bien
        for v in s["vung"]:
            con = con.difference(v["poly"])
            for gp in tach_da_giac(v["poly"].difference(unary_union(d["lo"])) if d["lo"] else v["poly"]):
                spec["floors"].append(dict(type_name=f"Archivina_San BTCT {v['day']:.0f}", thickness=v["day"], material=ten_vl["san"],
                                           level=i, offset=v["lech"], loops=vong(gp.simplify(1), g), mark=v["ghi_chu"]))
        for gp in tach_da_giac(con):
            spec["floors"].append(dict(type_name=f"Archivina_San BTCT {s['day']:.0f}", thickness=s["day"], material=ten_vl["san"],
                                       level=i, offset=0, loops=vong(gp.simplify(1), g)))

    with open(os.path.join(a.ra, "spec_ket_cau.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    tom = dict(
        file=a.dxf,
        goc_toa_do=f"giao trục {ten_goc}" if ten_goc else None,
        mat_bang=[dict(ten=d["mb"]["ten"], loai=d["mb"]["loai"], cot=d["mb"]["cao"], so_cot=len(d["cots"]), so_dam=len(d["dams"]),
                       so_lo_mo=len(d["lo"]), chieu_day_san=d["san"]["day"] if d["san"] else None,
                       vung_lech_cot=[dict(lech=v["lech"], dien_tich_m2=round(v["poly"].area / 1e6, 2)) for v in d["san"]["vung"]] if d["san"] else [],
                       chu_giai=d["san"]["chu_giai"] if d["san"] else [], anh=d["anh"]) for d in ds],
        levels=spec["levels"],
        so_luong=dict(truc=len(spec["grids"]), cot=len(spec["columns"]), dam=len(spec["beams"]), san=len(spec["floors"])),
        loai_cot=sorted({f"{c['mark']} {c['b']}x{c['h']}" for c in spec["columns"]}),
        loai_dam=sorted({f"{b['mark']} {b['b']}x{b['h']}" for b in spec["beams"]}),
        vat_lieu=ten_vl,
        can_hoi=can_hoi,
        canh_bao=canh_bao,
        spec=os.path.join(a.ra, "spec_ket_cau.json"),
    )
    with open(os.path.join(a.ra, "ket_qua.json"), "w", encoding="utf-8") as f:
        json.dump(tom, f, ensure_ascii=False, indent=1)
    print(json.dumps(tom, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dung DUONG BO thong thuy CAN HO (layer 'Dien tich thong thuy') + nhan "DTCH: xx.x m2" cho tung can trong ban ve.

Nguyen tac (quy tac Archivina, xem references/quy-tac-do.md):
- Duong bo la MOT polyline dong, di theo mat trat hoan thien cua tuong bao / tuong chung / vach, om ca ban cong, lo gia;
  tuong ngan trong can nam BEN TRONG (duoc tinh); cot, hop ky thuat (va tuong bao hop ky thuat) nam trong can: LOAI TRU
  (polyline rieng, cung layer).  DT can ho = DT duong bo - tong DT phan loai tru.
- Cach dung: (1) neu co text ten phong: hop cac vung phong, dong khe tuong ngan/o cua bang phep "dong hinh" (buffer +, -);
  (2) neu KHONG co ten phong (can hop de tho, chua chia phong): moi vung kin lon (>= --dt-toi-thieu-can) la mot can.
  Bam dung net da ve (tuong, vua trat, cot, khung cua); lop trat khong ve thi khong lui.  Vung kin nho nam trong can (hop ky thuat,
  cot) la lo cua da giac -> thanh polyline loai tru.
- Nhieu can trong cung ban ve: moi khoi roi nhau la mot can (danh so tu trai sang phai).
- Nhan "DTCH: xx.x m2" o giua phong khach (hoac giua can neu khong co ten phong), KHONG de len tuong, cua, noi that, chu;
  cung style/layer/mau voi text ten phong, cao = 1,5 lan cao chu ten phong.

    python tao_duong_bo_can_ho.py <file.dxf> --out-dir <thu muc> [--layer-ten A-Dimension]
Khong sua DXF dau vao; xuat ve_duong_bo_can_ho.scr, DienTichCanHo.xlsx, xem_duong_bo_can_ho.png, JSON (stdout).
"""
import argparse
import importlib.util
import io
import json
import math
import os
import re
import sys
import unicodedata

import ezdxf
import shapely
from ezdxf import path as ezpath
from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.ops import polylabel, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("tpp", os.path.join(HERE, "tao_polyline_phong.py"))
tpp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tpp)

LAYER_CAN = "Dien tich thong thuy"
MAU_LAYER_CAN = 6          # theo template ISO - ARCHIVINA
LOI, CANH_BAO, DAT = tpp.LOI, tpp.CANH_BAO, tpp.DAT
# layer cua di / cua so: net bao khung lam ranh (tpp.doc_khung_cua); ca cum net con dung de nhan ra lo gia/ban cong gan lien voi can
OPEN_LAYERS = {tpp.layer_goc(x) for x in tpp.LAYER_CUA}


def bo_dau(s):
    s = unicodedata.normalize("NFD", (s or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def simplify_ring(coords):
    """Bo dinh thang hang va dinh trung de polyline gon."""
    pts = list(coords)[:-1] if coords[0] == coords[-1] else list(coords)
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if math.dist(a, b) < 0.01 or abs(cross) < 1e-3 * max(1.0, math.dist(a, c)):
                del pts[i]
                changed = True
                break
    return pts


def lay_primitives(entities):
    """Sinh (dang, [diem]) cho moi hinh co ban; dang = 'dong' (khep kin, coi nhu dac) hoac 'mo'."""
    for e in entities:
        t = e.dxftype()
        try:
            if t in ("LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE"):
                p = ezpath.make_path(e)
                pts = [(v.x, v.y) for v in p.flattening(20)]
                if len(pts) >= 2:
                    yield ("dong" if (p.is_closed or t == "CIRCLE") else "mo"), pts
            elif t == "HATCH":
                for path in e.paths:
                    vs = [(v[0], v[1]) for v in getattr(path, "vertices", [])]
                    if len(vs) >= 3:
                        yield "dong", vs
        except Exception:
            continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--layer-can", default=LAYER_CAN)
    ap.add_argument("--layer-phong", default=tpp.LAYER_PHONG)
    ap.add_argument("--layer-ranh", default=",".join(tpp.LAYER_RANH))
    ap.add_argument("--layer-ten", default=tpp.LAYER_TEN)
    ap.add_argument("--layer-dong-ranh", default="A-Dong ranh phong")
    ap.add_argument("--them-ranh", default="")
    ap.add_argument("--them-phong", default="")
    ap.add_argument("--block-bo-qua", default=None)
    ap.add_argument("--gap-max", type=float, default=1200.0)
    ap.add_argument("--lop-trat", default="0",
                    help="mm lui vao trong net ranh; mac dinh 0 = bam dung net da ve (lop trat khong ve thi khong lui)")
    ap.add_argument("--layer-cua", default=",".join(tpp.LAYER_CUA),
                    help="layer cua di/cua so lay net bao khung lam ranh (bo canh mo, cung quay); \x27\x27 = khong dung")
    ap.add_argument("--day-tuong-max", type=float, default=300.0,
                    help="be day tuong ngan/o cua lon nhat (mm) can lap day khi om cac phong thanh duong bo can ho")
    ap.add_argument("--dt-toi-thieu-can", type=float, default=15.0, help="m2: khoi/vung nho hon khong coi la can ho")
    ap.add_argument("--tol-cua", type=float, default=60.0,
                    help="mm: cho mo (cua/cua so) phai cham den ca hai ben (vung phu va can) trong sai so nay de coi la gan lien")
    ap.add_argument("--dt-gan-toi-thieu", type=float, default=1.0,
                    help="m2: vung kin khong ten nho hon muc nay (va hep < 600 mm) khong xet gan vao can")
    ap.add_argument("--tieu-de", default="DTCH")
    ap.add_argument("--ti-le-cao", type=float, default=1.5, help="cao nhan can ho = ti-le x cao chu ten phong")
    ap.add_argument("--phong-khach", default=r"kh[a]ch", help="regex (khong dau) nhan ra text ten phong khach")
    ap.add_argument("--le", type=float, default=80.0, help="khoang trong toi thieu quanh nhan (mm)")
    ap.add_argument("--buoc", type=float, default=50.0, help="buoc luoi tim vi tri nhan (mm)")
    ap.add_argument("--cao-chu-mac-dinh", type=float, default=200.0,
                    help="cao chu ten phong gia dinh (mm) khi ban ve khong co text ten phong")
    ap.add_argument("--style-mac-dinh", default="Standard")
    ap.add_argument("--layer-nhan-mac-dinh", default="A-Text")
    ap.add_argument("--chap-nhan-thieu-phong", action="store_true",
                    help="van dung duong bo khi con phong co ten chua dong kin (mac dinh: dung lai va bao)")
    ap.add_argument("--khong-loai-tru-lo", action="store_true",
                    help="khong coi vung kin nho nam trong can la loai tru (mac dinh: loai tru, kem canh bao)")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    doc = ezdxf.readfile(a.dxf)
    msp = doc.modelspace()
    problems = []
    if doc.header.get("$INSUNITS", 0) != 4:
        problems.append((LOI, "Đơn vị bản vẽ", f"INSUNITS={doc.header.get('$INSUNITS', 0)}, chuẩn là 4 (mm)."))

    # ---- mang net ranh, vung kin, ten phong (giong tao_polyline_phong.py) ------------------------------------------
    layers = [x.strip() for x in a.layer_ranh.split(",") if x.strip()]
    if a.block_bo_qua is not None:
        tpp._BO_QUA[0] = re.compile(a.block_bo_qua, re.I) if a.block_bo_qua else None
    dong_ranh = tpp.doc_chains(msp, [a.layer_dong_ranh]) + tpp.parse_them_ranh(a.them_ranh)
    chains = tpp.doc_chains(msp, layers) + dong_ranh
    seeds = tpp.doc_seeds(msp, a.layer_ten, doc)
    for part in (a.them_phong or "").split(";"):
        if ":" in part:
            ten, xy = part.rsplit(":", 1)
            sx, sy = [float(t) for t in xy.split(",")]
            seeds.append((ten.strip(), (sx, sy), None))
    khung, tk_cua = tpp.doc_khung_cua(msp, chains, [x.strip() for x in a.layer_cua.split(",") if x.strip()])
    faces, pairs, _ = tpp.build_faces(chains, a.gap_max, khung)
    t_in, ghi_chu_trat = tpp.chon_lop_trat(msp, a.lop_trat)
    if ghi_chu_trat:
        problems.append((tpp.GOI_Y, "Lớp trát", ghi_chu_trat))

    # ---- cac phong (vung kin chua ten) hoac, neu khong co ten, cac vung kin lon = can ho ---------------------------
    rooms = {}       # id(face) -> dict(face, ten[], info)
    chua_dong = []
    che_do = "co_ten_phong" if seeds else "khong_ten_phong"
    for ten, (x, y), info in seeds:
        hit = [f for f in faces if f.contains(Point(x, y))]
        if not hit:
            chua_dong.append(f"{ten} ({x:.0f}, {y:.0f})")
            problems.append((LOI, "Phòng không đóng kín", f"'{ten}' tại ({x:.0f}, {y:.0f}) không nằm trong vùng kín; "
                             "đường bo căn hộ sẽ thiếu phòng này. Chạy tao_polyline_phong.py để xem khe hở rồi đóng ranh."))
            continue
        f = min(hit, key=lambda p: p.area)
        r = rooms.setdefault(id(f), dict(face=f, ten=[], info=info, seed=(x, y)))
        r["ten"].append(ten)
    if not seeds:
        for f in faces:
            if f.area / 1e6 >= a.dt_toi_thieu_can:
                c = f.representative_point()
                rooms[id(f)] = dict(face=f, ten=["(không tên)"], info=None, seed=(c.x, c.y))
        problems.append((CANH_BAO, "Không có tên phòng",
                         "Bản vẽ không có text tên phòng: mỗi vùng kín lớn (≥ %g m²) được coi là một căn hộ; nhãn DTCH dùng chữ "
                         "mặc định (style %s, cao tên phòng giả định %g mm, layer %s), cần anh xác nhận."
                         % (a.dt_toi_thieu_can, a.style_mac_dinh, a.cao_chu_mac_dinh, a.layer_nhan_mac_dinh)))
    if not rooms:
        raise SystemExit("Không có vùng kín nào để dựng đường bo căn hộ (chưa đóng kín được). Chạy tao_polyline_phong.py để xem khe hở.")
    room_list = list(rooms.values())

    # ---- gop vung thanh khoi can ho: nhom phong, gan them lo gia/ban cong/phong phu qua cua - cua so, dong khe tuong --
    g = a.day_tuong_max / 2.0

    def dong_hinh(geom):
        return geom.buffer(g, join_style=2, mitre_limit=5).buffer(-g, join_style=2, mitre_limit=5)

    if che_do == "co_ten_phong":
        env0 = dong_hinh(unary_union([r["face"] for r in room_list]))
        nhom = [[r for r in room_list if p.contains(r["face"].representative_point())] for p in
                sorted(getattr(env0, "geoms", [env0]), key=lambda p: p.bounds[0])]
    else:
        nhom = [[r] for r in sorted(room_list, key=lambda r: r["face"].bounds[0])]
    # cua + cua so: cac cum net tren layer cua/cua so, moi cum la mot "cho mo" (rong >= 600 mm) noi hai ben tuong
    prims = []
    for e in tpp.walk(msp):
        if tpp.layer_goc(e.dxf.layer) in OPEN_LAYERS:
            for _k, p in lay_primitives([e]):
                if len(p) >= 2:
                    prims.append(shapely.LineString(p).buffer(20))
    mo_hull = []
    if prims:
        cu = unary_union(prims)
        for c in getattr(cu, "geoms", [cu]):
            b = c.bounds
            if max(b[2] - b[0], b[3] - b[1]) >= 600:
                mo_hull.append(c.convex_hull)
    used_faces = {id(r["face"]) for r in room_list}
    gap = a.day_tuong_max
    nhom_geom = [unary_union([r["face"] for r in grp]) for grp in nhom]
    gan = [[] for _ in nhom]
    khong_gan = []
    for f in faces:
        if id(f) in used_faces or f.area / 1e6 < a.dt_gan_toi_thieu or f.buffer(-300).is_empty:
            continue
        fb = f.buffer(a.tol_cua)
        lien = [i for i, gg in enumerate(nhom_geom)
                if any(h.intersects(fb) and h.intersects(gg.buffer(a.tol_cua)) for h in mo_hull)]
        if len(lien) == 1:
            gan[lien[0]].append(f)
        elif len(lien) > 1:
            problems.append((CANH_BAO, "Vùng nối nhiều căn",
                             f"Vùng {f.area / 1e6:.2f} m² tại ({f.centroid.x:.0f}, {f.centroid.y:.0f}) có cửa/cửa sổ thông sang {len(lien)} căn: "
                             "coi là khu vực chung, không tính vào căn nào."))
        else:
            khong_gan.append(f)
    can_parts, can_faces = [], []
    for grp, extra in zip(nhom, gan):
        gm = dong_hinh(unary_union([r["face"] for r in grp] + extra))
        pieces = sorted(getattr(gm, "geoms", [gm]), key=lambda p: p.area, reverse=True)
        main_p = pieces[0]
        if main_p.area / 1e6 >= a.dt_toi_thieu_can:
            can_parts.append(main_p)
            can_faces.append((grp, extra))
        else:
            problems.append((CANH_BAO, "Khối nhỏ rời", f"Khối {main_p.area / 1e6:.2f} m² tại ({main_p.centroid.x:.0f}, "
                             f"{main_p.centroid.y:.0f}) nhỏ hơn {a.dt_toi_thieu_can:g} m², không coi là căn hộ."))
        for p in pieces[1:]:
            problems.append((CANH_BAO, "Khối rời trong căn", f"Khối {p.area / 1e6:.2f} m² tại ({p.centroid.x:.0f}, {p.centroid.y:.0f}) "
                             "tách khỏi khối chính của căn, không tính; kiểm tra ô cửa/khe hở."))
    order = sorted(range(len(can_parts)), key=lambda i: can_parts[i].bounds[0])
    can_parts = [can_parts[i] for i in order]
    can_faces = [can_faces[i] for i in order]
    nho = []
    if chua_dong and not a.chap_nhan_thieu_phong:
        print(json.dumps(dict(
            file=os.path.basename(a.dxf), trang_thai="khong_dung_duoc",
            ly_do="Còn phòng chưa đóng kín: " + "; ".join(chua_dong),
            huong_xu_ly="Chạy tao_polyline_phong.py, xem khe hở của các phòng chưa đóng kín, nhờ người dùng chỉ ranh "
                        "(layer A-Dong ranh phong hoặc --them-ranh=), rồi chạy lại. Chỉ dùng --chap-nhan-thieu-phong khi "
                        "người dùng đồng ý đường bo bỏ qua các phòng đó.",
            van_de=[dict(muc=m, hang_muc=h, mo_ta=d) for m, h, d in problems]), ensure_ascii=False, indent=2))
        return
    if not can_parts:
        raise SystemExit("Không có khối nào đạt diện tích tối thiểu của một căn hộ.")

    # ---- doc san polyline cua nguoi dung (de doi chieu) -----------------------------------------------------------
    ref_layers = {tpp.layer_goc(a.layer_can), "a-do dientich", tpp.layer_goc(a.layer_phong)}
    user_pl = []
    for e in msp:
        if e.dxftype() == "LWPOLYLINE" and tpp.layer_goc(e.dxf.layer) in ref_layers:
            pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(0.5)]
            if len(pts) >= 3:
                user_pl.append((e.dxf.handle, e.dxf.layer, Polygon(pts)))

    # ---- vat can cho nhan (noi that, cua, chu) -- tinh mot lan cho ca ban ve ----------------------------------------
    le = a.le
    skip_layers = {tpp.layer_goc(x) for x in layers} | {"defpoints", tpp.layer_goc(a.layer_can), tpp.layer_goc(a.layer_phong),
                                                       "a-do dientich", tpp.layer_goc(a.layer_dong_ranh)}
    allb = unary_union(can_parts).bounds
    vb_all = box(allb[0] - 2000, allb[1] - 2000, allb[2] + 2000, allb[3] + 2000)
    obst = []
    saved_bo_qua = tpp._BO_QUA[0]
    tpp._BO_QUA[0] = None                       # noi that nam trong block co the trung ten bo loc: lay het
    for e in msp:
        t = e.dxftype()
        if t in ("TEXT", "MTEXT"):
            continue
        if t == "INSERT":
            sub = list(tpp.walk([e]))
            if tpp.layer_goc(e.dxf.layer) not in skip_layers:
                pts = []
                for e2 in sub:
                    for _k, p in lay_primitives([e2]):
                        pts.extend(p)
                if len(pts) >= 2:
                    hull = MultiPoint(pts).convex_hull       # do dac cua noi that/cua: bao loi
                    if hull.intersects(vb_all):
                        obst.append(hull.buffer(le))
            else:
                for e2 in sub:
                    if tpp.layer_goc(e2.dxf.layer) in skip_layers:
                        continue
                    for kind, p in lay_primitives([e2]):
                        geom = Polygon(p) if (kind == "dong" and len(p) >= 3) else shapely.LineString(p)
                        if geom.is_valid and geom.intersects(vb_all):
                            obst.append(geom.buffer(le))
        elif tpp.layer_goc(e.dxf.layer) not in skip_layers:
            for kind, p in lay_primitives([e]):
                geom = Polygon(p) if (kind == "dong" and len(p) >= 3) else shapely.LineString(p)
                if geom.is_valid and geom.intersects(vb_all):
                    obst.append(geom.buffer(le))
    tpp._BO_QUA[0] = saved_bo_qua
    for e in msp:                                # chu da co (ten phong, nhan khac)
        if e.dxftype() in ("TEXT", "MTEXT"):
            try:
                ti = tpp.thong_so_text(e, doc)
            except Exception:
                continue
            obst.append(box(ti["cx"] - ti["w"] / 2 - le, ti["cy"] - ti["hb"] / 2 - le,
                            ti["cx"] + ti["w"] / 2 + le, ti["cy"] + ti["hb"] / 2 + le))
    for r in room_list:                          # nhan dien tich phong se ghi o duoi ten phong
        ti = r["info"]
        r["dt"] = (tpp.inset_face(r["face"], t_in) or Polygon()).area / 1e6 if t_in else r["face"].area / 1e6
        if ti:
            wl, hl = tpp.do_text(doc, ti["kind"], ti["style"], ti["h"], f"{tpp.r1(r['dt']):.1f} m2")
            obst.append(box(ti["x"] - wl / 2 - le, ti["y"] - hl / 2 - le, ti["x"] + wl / 2 + le, ti["y"] + hl / 2 + le))
    O = unary_union(obst) if obst else Polygon()
    shapely.prepare(O)

    # ---- xu ly tung can ho -------------------------------------------------------------------------------------------
    re_pk = re.compile(a.phong_khach, re.I)
    ket_qua = []
    for stt, part in enumerate(can_parts, 1):
        rin = [r for r in room_list if part.contains(r["face"].representative_point())]
        holes_raw = [Polygon(h) for h in part.interiors]
        if a.khong_loai_tru_lo:
            part = Polygon(part.exterior)
            holes_raw = []
        can = tpp.inset_face(part, t_in) if t_in else part
        if can is None:
            problems.append((LOI, f"Căn {stt}", "Đường bo rỗng sau khi lùi lớp trát."))
            continue
        ext_pts = simplify_ring(can.exterior.coords)
        ho_pts = [simplify_ring(r_.coords) for r_ in can.interiors]
        ho_poly = [Polygon(p) for p in ho_pts]
        dt_goc = Polygon(ext_pts).area / 1e6
        dt_loai_tru = sum(h.area for h in ho_poly) / 1e6
        dt_can = dt_goc - dt_loai_tru                            # = duong bo - loai tru, tinh tu dung polyline se ve
        dt_tong_phong = sum(r["dt"] for r in rin) if (rin and che_do == "co_ten_phong") else None
        chenh_phong = (dt_can - dt_tong_phong) if dt_tong_phong is not None else None
        if chenh_phong is not None and chenh_phong < 0:
            problems.append((LOI, f"Căn {stt}: chênh căn − Σ phòng âm",
                             f"DT căn {dt_can:.4f} < Σ phòng {dt_tong_phong:.4f}: ranh phòng chồng lấn."))
        for i, h in enumerate(ho_poly, 1):
            problems.append((CANH_BAO, f"Căn {stt}: phần loại trừ #{i}",
                             f"{h.area / 1e6:.4f} m² tại ({h.centroid.x:.0f}, {h.centroid.y:.0f}), "
                             f"{h.bounds[2] - h.bounds[0]:.0f} × {h.bounds[3] - h.bounds[1]:.0f} mm; coi là hộp kỹ thuật/cột "
                             "(kèm tường bao) và loại khỏi DT căn hộ; xác nhận đúng là hộp kỹ thuật/cột, không phải hành lang/kho."))
        # doi chieu voi polyline nguoi dung: polyline lon nhat chua tam can, tru cac polyline nho nam trong no
        ref = None
        rp = part.representative_point()
        outers = [c for c in user_pl if c[2].contains(rp) and c[2].area / 1e6 >= a.dt_toi_thieu_can]
        if outers:
            o = max(outers, key=lambda c: c[2].area)
            inner = [c for c in user_pl if c is not o and o[2].contains(c[2]) and tpp.layer_goc(c[1]) == tpp.layer_goc(o[1])]
            ref = dict(handle=o[0], layer=o[1], dt=(o[2].area - sum(c[2].area for c in inner)) / 1e6,
                       dt_duong_bo=o[2].area / 1e6, loai_tru=[c[0] for c in inner])
            ref["chenh"] = dt_can - ref["dt"]
            ref["chenh_pct"] = ref["chenh"] / ref["dt"] * 100 if ref["dt"] else 0
            if tpp.layer_goc(o[1]) != tpp.layer_goc(a.layer_can):
                problems.append((LOI, f"Căn {stt}: layer đường bo có sẵn",
                                 f"Polyline {o[0]} nằm ở layer '{o[1]}', chuẩn là '{a.layer_can}'."))

        # nhan "DTCH: xx.x m2" -------------------------------------------------------------------------------------------
        nhan_txt = f"{a.tieu_de}: {tpp.r1(dt_can):.1f} m2"
        pk = [r for r in rin if any(re_pk.search(bo_dau(t)) for t in r["ten"])] if che_do == "co_ten_phong" else []
        info = None
        if pk:
            vung = tpp.inset_face(pk[0]["face"], t_in) if t_in else pk[0]["face"]
            info = next((i for t, _, i in seeds if t in pk[0]["ten"] and i), None) or pk[0]["info"]
        else:
            vung = can
            if che_do == "co_ten_phong":
                problems.append((CANH_BAO, f"Căn {stt}: không thấy phòng khách",
                                 "Không có text tên phòng khớp 'khách' trong căn; đặt nhãn ở giữa căn. Dùng --phong-khach để chỉ regex tên."))
            lay_ten = next((i for t, _, i in seeds if i and any(part.contains(Point(x, y)) for tt, (x, y), ii in seeds if tt == t)), None)
            info = lay_ten
        if info is None:
            info = dict(kind="MTEXT", layer=a.layer_nhan_mac_dinh, style=a.style_mac_dinh, h=a.cao_chu_mac_dinh, style_h=0.0,
                        color=256, rot=0.0, cx=vung.centroid.x, cy=vung.centroid.y, w=800.0, hb=a.cao_chu_mac_dinh)
        h_lab = info["h"] * a.ti_le_cao
        w_lab, hb_lab = tpp.do_text(doc, info["kind"], info["style"], h_lab, nhan_txt)
        shapely.prepare(vung)
        anchor = (info["cx"], info["cy"]) if pk else (lambda pp: (pp.x, pp.y))(polylabel(vung, tolerance=50))
        minx, miny, maxx, maxy = vung.bounds
        best, best_d = None, 1e18
        hw, hh = w_lab / 2 + le, hb_lab / 2 + le
        y = miny + hh
        while y <= maxy - hh:
            x = minx + hw
            while x <= maxx - hw:
                d = math.hypot(x - anchor[0], y - anchor[1])
                if d < best_d:
                    b = box(x - hw, y - hh, x + hw, y + hh)
                    if vung.contains(b) and not O.intersects(b):
                        best, best_d = (x, y), d
                x += a.buoc
            y += a.buoc
        nhan_ok = best is not None
        if not nhan_ok:
            problems.append((CANH_BAO, f"Căn {stt}: không tìm được chỗ đặt nhãn",
                             f"Không có vị trí đủ chứa nhãn {w_lab:.0f}×{hb_lab:.0f} mm mà không đè tường/nội thất "
                             f"(lề {le:g} mm). Giảm --le hoặc đặt nhãn tay."))
            best = (vung.centroid.x, vung.centroid.y)
        n = dict(kind=info["kind"], layer=info["layer"], style=info["style"], h=h_lab, style_h=info["style_h"],
                 color=info["color"], rot=info["rot"], x=best[0], y=best[1])
        ket_qua.append(dict(stt=stt, ext=ext_pts, ho=ho_pts, ho_poly=ho_poly, dt_goc=dt_goc, dt_loai_tru=dt_loai_tru,
                            dt_can=dt_can, dt_tong_phong=dt_tong_phong, chenh_phong=chenh_phong, ref=ref, nhan_txt=nhan_txt,
                            n=n, nhan_ok=nhan_ok, w_lab=w_lab, hb_lab=hb_lab, h_ten=info["h"], pk=bool(pk),
                            so_phong=len(rin)))
        # nhan da dat: coi la vat can cho can ke tiep (tranh chong nhau neu hai can sat nhau)
        O = unary_union([O, box(best[0] - w_lab / 2 - le, best[1] - hb_lab / 2 - le, best[0] + w_lab / 2 + le, best[1] + hb_lab / 2 + le)])
        shapely.prepare(O)
    if not ket_qua:
        raise SystemExit("Không dựng được căn hộ nào.")

    # ---- xuat: scr, excel, anh, json ---------------------------------------------------------------------------------
    os.makedirs(a.out_dir, exist_ok=True)
    L = ["CMDECHO", "0", "OSMODE", "0",
         "_.-LAYER", "_M", f'"{tpp.acad_str(a.layer_can)}"', "_C", str(MAU_LAYER_CAN), "", ""]
    for k in ket_qua:
        L += ["_.-LAYER", "_S", f'"{tpp.acad_str(a.layer_can)}"', "",
              "_.PLINE " + " ".join(f"{x:.4f},{y:.4f}" for x, y in k["ext"]) + " _C"]
        for hp in k["ho"]:
            L.append("_.PLINE " + " ".join(f"{x:.4f},{y:.4f}" for x, y in hp) + " _C")
        L += tpp.lenh_nhan(k["n"], k["nhan_txt"])
    L += ["_.-LAYER", "_S", f'"{tpp.acad_str(doc.header.get("$CLAYER", "0"))}"', "", "_.QSAVE", "_.QUIT _Y"]
    scr = os.path.join(a.out_dir, "ve_duong_bo_can_ho.scr")
    with open(scr, "w", encoding="ascii", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")

    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "Can-ho"
    ws.append(["Căn", "Hạng mục", "Giá trị (m²)", "Làm tròn 1 số (m²)", "Mức độ", "Ghi chú"])
    for k in ket_qua:
        s = f"Căn {k['stt']}"
        ws.append([s, "Đường bo thông thủy (polyline ngoài)", round(k["dt_goc"], 4), tpp.r1(k["dt_goc"]), DAT,
                   f"{len(k['ext'])} đỉnh, layer '{a.layer_can}'" + (f"; lùi lớp trát {t_in:g} mm" if t_in else "")])
        for i, h in enumerate(k["ho_poly"], 1):
            ws.append([s, f"Loại trừ #{i} (hộp kỹ thuật/cột, kèm tường bao)", -round(h.area / 1e6, 4), -tpp.r1(h.area / 1e6),
                       CANH_BAO, f"{h.bounds[2] - h.bounds[0]:.0f} × {h.bounds[3] - h.bounds[1]:.0f} mm tại "
                                 f"({h.centroid.x:.0f}, {h.centroid.y:.0f}); cần xác nhận"])
        ws.append([s, "DIỆN TÍCH THÔNG THỦY CĂN HỘ", round(k["dt_can"], 4), tpp.r1(k["dt_can"]), DAT, "= đường bo − loại trừ"])
        if k["dt_tong_phong"] is not None:
            ws.append([s, "Σ diện tích các phòng; chênh căn − Σ phòng", round(k["dt_tong_phong"], 4), tpp.r1(k["dt_tong_phong"]),
                       DAT if k["chenh_phong"] >= 0 else LOI, f"chênh {k['chenh_phong']:.4f} m² (≈ tường ngăn + ô cửa; phải dương)"])
        if k["ref"]:
            rf = k["ref"]
            ws.append([s, f"Đối chiếu polyline có sẵn {rf['handle']} (layer {rf['layer']})", round(rf["dt"], 4), tpp.r1(rf["dt"]),
                       DAT if abs(rf["chenh_pct"]) <= 0.5 else LOI,
                       f"đường bo có sẵn {rf['dt_duong_bo']:.4f} − loại trừ {rf['loai_tru']}; chênh {rf['chenh']:+.4f} m² ({rf['chenh_pct']:+.3f}%)"])
        ws.append([s, "Nhãn căn hộ", None, None, DAT if k["nhan_ok"] else CANH_BAO,
                   f"'{k['nhan_txt']}' tại ({k['n']['x']:.0f}, {k['n']['y']:.0f}), cao {k['n']['h']:g} mm "
                   f"(= {a.ti_le_cao:g} × {k['h_ten']:g}), layer {k['n']['layer']}, style {k['n']['style']}"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for col, w in zip("ABCDEF", [8, 58, 16, 20, 11, 110]):
        ws.column_dimensions[col].width = w
    xlsx = os.path.join(a.out_dir, "DienTichCanHo.xlsx")
    wb.save(xlsx)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ex = unary_union([Polygon(k["ext"]) for k in ket_qua]).bounds
    asp = max(0.35, min(2.8, (ex[2] - ex[0]) / max(1.0, (ex[3] - ex[1]))))
    fig = plt.figure(figsize=(14, 14 / asp if asp < 1 else max(5, 14 / asp)), dpi=80)
    ax = fig.add_axes([0.03, 0.03, 0.95, 0.95])
    for cl, ch in chains:
        xs, ys = zip(*(ch + ([ch[0]] if cl else [])))
        ax.plot(xs, ys, color="#adb5bd", lw=0.8)
    for k in ket_qua:
        xs, ys = zip(*(k["ext"] + [k["ext"][0]]))
        ax.fill(xs, ys, color="#74c0fc", alpha=0.12)
        ax.plot(xs, ys, color="#c2255c", lw=2.2)
        for hp in k["ho"]:
            xs, ys = zip(*(hp + [hp[0]]))
            ax.fill(xs, ys, color="#868e96", alpha=0.6)
            ax.plot(xs, ys, color="#212529", lw=1.3)
        nn = k["n"]
        bx = box(nn["x"] - k["w_lab"] / 2, nn["y"] - k["hb_lab"] / 2, nn["x"] + k["w_lab"] / 2, nn["y"] + k["hb_lab"] / 2)
        xs, ys = zip(*bx.exterior.coords)
        ax.fill(xs, ys, color="#fcc419", alpha=0.7)
        ax.text(nn["x"], nn["y"], k["nhan_txt"], ha="center", va="center", fontsize=8)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.3)
    png = os.path.join(a.out_dir, "xem_duong_bo_can_ho.png")
    fig.savefig(png)
    plt.close(fig)

    can_json = []
    for k in ket_qua:
        can_json.append(dict(
            stt=k["stt"], dt_duong_bo=round(k["dt_goc"], 4), dt_loai_tru=round(k["dt_loai_tru"], 4), dt_can=round(k["dt_can"], 4),
            dt_can_lam_tron=tpp.r1(k["dt_can"]), so_dinh=len(k["ext"]), so_phong=k["so_phong"],
            tong_phong=None if k["dt_tong_phong"] is None else round(k["dt_tong_phong"], 4),
            chenh_can_tru_phong=None if k["chenh_phong"] is None else round(k["chenh_phong"], 4),
            loai_tru=[dict(dt=round(h.area / 1e6, 4), bounds=[round(v) for v in h.bounds]) for h in k["ho_poly"]],
            doi_chieu_co_san=k["ref"],
            nhan=dict(text=k["nhan_txt"], x=round(k["n"]["x"], 1), y=round(k["n"]["y"], 1), cao=k["n"]["h"],
                      layer=k["n"]["layer"], style=k["n"]["style"], kich_thuoc=[round(k["w_lab"]), round(k["hb_lab"])],
                      khong_de_len_vat_can=k["nhan_ok"])))
    print(json.dumps(dict(
        file=os.path.basename(a.dxf), che_do=che_do, lop_trat_mm=t_in, khung_cua=tk_cua, layer_can=a.layer_can, so_can=len(can_json),
        can_ho=can_json,
        van_de=[dict(muc=m, hang_muc=h, mo_ta=d) for m, h, d in problems], scr=scr, xlsx=xlsx, anh=png),
        ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()

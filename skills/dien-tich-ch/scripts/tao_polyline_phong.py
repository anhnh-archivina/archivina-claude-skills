#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dung polyline thong thuy tung phong tu net hoan thien/tuong trong DXF (Archivina).

Y tuong: gom cac net bien (vua trat, tuong, cot, lan can lo-gia...) thanh mang luoi, dong cac
o cua <= 1,2 m bang doan thang o CA HAI MAT tuong (o cua thanh vung rieng, khong thuoc phong nao),
roi lay vung kin chua diem dat ten phong (text) lam polyline phong.

Khong sua file DXF dau vao. Xuat: JSON tom tat (stdout), .scr ve polyline, .xlsx, .png xem lai.

    python tao_polyline_phong.py <file.dxf> --out-dir <thu muc> [--gap-max 1200] [--debug]
"""
import argparse
import io
import json
import math
import re
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

import ezdxf
import shapely
from ezdxf import path as ezpath
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

LAYER_PHONG = "A- Dien tich phong"
# Layer lam ranh phong (net hoan thien, tuong, cot, lan can lo-gia). KHONG gom noi that, thiet bi, canh cua.
LAYER_RANH = ["A-Vua trat", "A-Wall", "A-Column", "A-Line"]
LAYER_TEN = "A-Text"
# Layer cua di / cua so (ke ca doi tuong AutoCAD Architecture da no): chi lay NET BAO KHUNG nam trong chieu day tuong
# lam ranh; canh cua mo ra ngoai tuong va cung quay canh bi bo.
LAYER_CUA = ["A-Door", "A-Window", "A-Glaz", "A-Cửa", "A-Cua", "A-Opening", "A-Window-G"]
DAY_TUONG_TOI_DA = 400.0   # mm: nua be day tuong lon nhat khi tim hai mat tuong hai ben cua
RET_MAX = 400.0      # do dai toi da cua doan "ma cua" (jamb return), mm
TOL_THANG = 20.0     # sai so thang hang giua 2 dau o cua, mm
SNAP = 6.0           # khe ho nho coi nhu cham nhau, mm
GAP_GOC = 150.0      # khe ho nho o GOC (hai net vuong goc khong cham nhau), mm
LOI, CANH_BAO, DAT, GOI_Y = "Lỗi", "Cảnh báo", "Đạt", "Gợi ý"
RE_NHAN = re.compile(r"\d+(?:[.,]\d+)?\s*(?:m2|m²|㎡)", re.I)


def r1(x):
    return float(Decimal(str(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def layer_goc(name):
    """Ten layer sau khi bo tien to xref/bind: 'CH06|A-Vua trat', '$0$A-Vua trat' va 'CH03$0$A-Vua trat'
    (xref da bind) deu thanh 'a-vua trat'."""
    s = (name or "").split("|")[-1]
    s = re.split(r"\$\d+\$", s)[-1]
    return norm(s)


# Block/xref khong chua ranh phong (chu thich, chu giai, khung ten, luoi truc, mat bang tran...): bo qua.
BLOCK_BO_QUA = re.compile(r"\b(ghi ?ch[uú]|note|legend|chu giai|khung|luoi|tran|loi thang)\b", re.I)


_BO_QUA = [BLOCK_BO_QUA]   # co the doi bang --block-bo-qua


def walk(entities, depth=0, max_depth=3):
    """Duyet doi tuong Model, di sau vao block/xref (INSERT) da duoc ezdxf bien doi toa do ve he Model."""
    for e in entities:
        if e.dxftype() == "INSERT":
            if depth >= max_depth or (_BO_QUA[0] is not None and _BO_QUA[0].search(e.dxf.name or "")):
                continue
            try:
                yield from walk(e.virtual_entities(), depth + 1, max_depth)
            except Exception:
                continue
        else:
            yield e


def doc_chains(msp, layers):
    """Tra ve list (closed, [(x,y)...]) tu LINE/LWPOLYLINE tren cac layer cho phep (ke ca ben trong block/xref)."""
    want = {layer_goc(x) for x in layers}
    chains = []
    for e in walk(msp):
        if e.dxftype() not in ("LINE", "LWPOLYLINE") or layer_goc(e.dxf.layer) not in want:
            continue
        if e.dxftype() == "LINE":
            chains.append((False, [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]))
        elif e.dxftype() == "LWPOLYLINE":
            try:
                pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(0.5)]
            except Exception:
                continue
            if len(pts) < 2:
                continue
            closed = bool(e.closed)
            if math.dist(pts[0], pts[-1]) < 1.0:
                closed = True
                pts = pts[:-1]
            if len(pts) >= 2:
                chains.append((closed, pts))
    return chains


def unit(a, b):
    n = math.dist(a, b)
    return None if n < 1e-9 else ((b[0] - a[0]) / n, (b[1] - a[1]) / n)


def make_rays(chains):
    """Cac 'tia keo dai' tai dau mut va tai goc ma cua (goc ~90 do voi doan ngan <= RET_MAX)."""
    rays = []
    for closed, pts in chains:
        n = len(pts)
        for i, p in enumerate(pts):
            prev = pts[i - 1] if (i > 0 or closed) else None
            nxt = pts[(i + 1) % n] if (i < n - 1 or closed) else None
            if prev is not None and nxt is None:
                d = unit(prev, p)
                if d:
                    rays.append((p, d, "dau"))
            elif nxt is not None and prev is None:
                d = unit(nxt, p)
                if d:
                    rays.append((p, d, "dau"))
            elif prev is not None and nxt is not None:
                d1, d2 = unit(prev, p), unit(p, nxt)
                if d1 is None or d2 is None:
                    continue
                if abs(d1[0] * d2[0] + d1[1] * d2[1]) < 0.2:   # goc ~90 do
                    l1, l2 = math.dist(prev, p), math.dist(p, nxt)
                    if min(l1, l2) <= RET_MAX:
                        # goc ma cua: keo dai ca hai canh, buoc ghep se loc canh nao thang hang voi dau doi dien
                        rays.append((p, d1, "goc"))
                        rays.append((p, (-d2[0], -d2[1]), "goc"))
    return rays


def pair_rays(rays, gap_max, barrier=None):
    """Ghep cac tia doi dien, thang hang, cach nhau <= gap_max thanh doan dong.

    barrier: hinh hoc cac net ranh; doan dong cat qua net ranh (khong chi cham o hai dau) bi loai.
    """
    # chi xet cap tia trong ban kinh gap_max (STRtree) - mat bang ca tang co hang chuc nghin tia, duyet het cap qua cham;
    # thu tu duyet (i tang, j tang) va tieu chi ghep giu nguyen nen ket qua khong doi
    if not rays:
        return []
    goc_tia = shapely.points([r[0] for r in rays])
    cay = shapely.STRtree(goc_tia)
    if barrier is not None:
        shapely.prepare(barrier)
    cands = []
    for i, (p, d, _) in enumerate(rays):
        for j in sorted(int(k) for k in cay.query(goc_tia[i], predicate="dwithin", distance=gap_max) if k > i):
            q, e2, _ = rays[j]
            dist = math.dist(p, q)
            if dist < 0.5 or dist > gap_max:
                continue
            vx, vy = q[0] - p[0], q[1] - p[1]
            if (vx * d[0] + vy * d[1]) > 0 and -(vx * e2[0] + vy * e2[1]) > 0 \
                    and abs(-vx * d[1] + vy * d[0]) <= TOL_THANG and abs(vx * e2[1] - vy * e2[0]) <= TOL_THANG:
                if barrier is not None:
                    # chi tinh phan giua cua doan, bo 3 mm moi dau de khong bi tinh cham vao chinh net ranh
                    ln = LineString([p, q])
                    inner = LineString([ln.interpolate(3.0), ln.interpolate(dist - 3.0)]) if dist > 8 else ln
                    if inner.intersects(barrier):
                        continue
                cands.append((dist, i, j))
    cands.sort()
    used, out = set(), []
    for dist, i, j in cands:
        if i in used or j in used:
            continue
        used.add(i)
        used.add(j)
        out.append((rays[i][0], rays[j][0], dist))
    # Goc ho nho: dau mut cua mot net nam ngay tren duong keo dai cua dau mut net vuong goc voi no (khe <= GAP_GOC),
    # vi du hop ky thuat co net ngoai khong cham nhau o goc. Dong bang doan thang.
    for i, (p, d, k) in enumerate(rays):
        if k != "dau" or i in used:
            continue
        best = None
        for j in sorted(int(k) for k in cay.query(goc_tia[i], predicate="dwithin", distance=GAP_GOC)):
            q, _e2, k2 = rays[j]
            if j == i or k2 != "dau":
                continue
            dist = math.dist(p, q)
            if dist < 0.5 or dist > GAP_GOC:
                continue
            vx, vy = q[0] - p[0], q[1] - p[1]
            if (vx * d[0] + vy * d[1]) > 0 and abs(-vx * d[1] + vy * d[0]) <= TOL_THANG:
                if barrier is not None and dist > 8:
                    ln = LineString([p, q])
                    if LineString([ln.interpolate(3.0), ln.interpolate(dist - 3.0)]).intersects(barrier):
                        continue
                if best is None or dist < best[0]:
                    best = (dist, j)
        if best:
            used.add(i)
            out.append((p, rays[best[1]][0], best[0]))
    return out


def snap_bridges(chains):
    """Dong khe ho rat nho (<= SNAP): dau mut cham gan net khac nhung khong chung dinh."""
    segs = [LineString(pts + ([pts[0]] if closed else [])) for closed, pts in chains]
    out = []
    ends = [pts[0] for closed, pts in chains if not closed] + [pts[-1] for closed, pts in chains if not closed]
    cay = shapely.STRtree(segs) if segs else None
    for p in ends:
        P = Point(p)
        best = None
        gan = sorted(int(k) for k in cay.query(P, predicate="dwithin", distance=SNAP)) if cay is not None else []
        for s in (segs[k] for k in gan):
            d = s.distance(P)
            if 1e-6 < d <= SNAP and (best is None or d < best[0]):
                a = s.interpolate(s.project(P))
                best = (d, (a.x, a.y))
        if best:
            out.append(LineString([p, best[1]]))
    return out


def _doan_cua(entities):
    """Cac doan thang (a, b) cua mot cua/cua so; ARC (cung quay canh) bi bo. Tra ve (doan, so_cung)."""
    out, n_arc = [], 0
    for e in entities:
        t = e.dxftype()
        if t == "LINE":
            out.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
        elif t == "LWPOLYLINE":
            pts = [(v.x, v.y) for v in e.vertices_in_wcs()]     # WCS: cua chen lat guong co extrusion (0,0,-1)
            if e.closed and len(pts) > 2:
                pts.append(pts[0])
            out += [(pts[i], pts[i + 1]) for i in range(len(pts) - 1) if math.dist(pts[i], pts[i + 1]) > 0.5]
        elif t in ("ARC", "CIRCLE", "ELLIPSE", "SPLINE"):
            n_arc += 1
    return out, n_arc


def _nhom_cua(entities, want, depth=0, max_depth=3):
    """Moi INSERT tren layer cua/cua so la MOT cua (sinh list doi tuong con da trai phang); di sau vao block/xref khac."""
    for e in entities:
        if e.dxftype() != "INSERT":
            continue
        if depth >= max_depth or (_BO_QUA[0] is not None and _BO_QUA[0].search(e.dxf.name or "")):
            continue
        try:
            subs = list(e.virtual_entities())
        except Exception:
            continue
        if layer_goc(e.dxf.layer) in want:
            flat, stack = [], subs
            while stack:
                s = stack.pop()
                if s.dxftype() == "INSERT":
                    try:
                        stack += list(s.virtual_entities())
                    except Exception:
                        pass
                else:
                    flat.append(s)
            yield flat
        else:
            yield from _nhom_cua(subs, want, depth + 1, max_depth)


def doc_khung_cua(msp, chains, layers_cua):
    """Net bao khung cua di / cua so lam ranh phong.

    Voi moi cua (INSERT tren layer cua): huong tuong = huong troi cua cac net tuong quanh cua; dai tuong = khoang giua
    hai mat tuong ngoai cung song song, nam hai ben truc cua (<= DAY_TUONG_TOI_DA). Chi giu cac doan cua co ca hai dau nam
    trong dai tuong (khung, kinh, canh dong). Canh cua mo ra phong (vuot ra ngoai dai tuong) va cung quay canh bi bo.
    Khong tim duoc dai tuong (cua dung tu do, khong co tuong): giu doan song song huong cua va doan ngan <= RET_MAX.
    """
    want = {layer_goc(x) for x in layers_cua}
    if not want:
        return [], dict(so_cua=0)
    wall = []
    for closed, pts in chains:
        q = pts + ([pts[0]] if closed else [])
        wall += [LineString([q[i], q[i + 1]]) for i in range(len(q) - 1) if math.dist(q[i], q[i + 1]) > 0.5]
    tree = shapely.STRtree(wall) if wall else None
    out, so_cua, bo_canh, bo_cung, khong_dai = [], 0, 0, 0, 0

    def goc(a, b):
        return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0

    def cung_huong(g1, g2, tol=3.0):
        d = abs(g1 - g2) % 180.0
        return min(d, 180.0 - d) <= tol

    for ents in _nhom_cua(msp, want):
        doan, n_arc = _doan_cua(ents)
        if not doan:
            continue
        so_cua += 1
        bo_cung += n_arc
        xs = [p[0] for s in doan for p in s]
        ys = [p[1] for s in doan for p in s]
        vung = shapely.box(min(xs) - 50, min(ys) - 50, max(xs) + 50, max(ys) + 50)
        gan = [wall[i] for i in tree.query(vung)] if tree is not None else []
        # huong tuong: goc co tong chieu dai net tuong (cat trong vung cua) lon nhat
        hist = defaultdict(float)
        for w in gan:
            c = w.intersection(vung)
            if not c.is_empty and c.length > 1:
                (x0, y0), (x1, y1) = w.coords[0], w.coords[-1]
                hist[round(goc((x0, y0), (x1, y1))) % 180] += c.length
        if not hist:
            for a_, b_ in doan:
                hist[round(goc(a_, b_)) % 180] += math.dist(a_, b_)
        g0 = max(hist, key=hist.get)
        ux, uy = math.cos(math.radians(g0)), math.sin(math.radians(g0))
        nx, ny = -uy, ux
        off = lambda p: p[0] * nx + p[1] * ny       # noqa: E731
        dl = lambda p: p[0] * ux + p[1] * uy       # noqa: E731
        ss = [s for s in doan if cung_huong(goc(*s), g0)]
        if ss:
            w_ = sorted((off(((s[0][0] + s[1][0]) / 2, (s[0][1] + s[1][1]) / 2)), math.dist(*s)) for s in ss)
            half, acc, c0 = sum(L for _, L in w_) / 2, 0.0, w_[0][0]
            for o, L in w_:
                acc += L
                if acc >= half:
                    c0 = o
                    break
        else:
            c0 = off(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
        t_min = min(dl(p) for s in doan for p in s)
        t_max = max(dl(p) for s in doan for p in s)
        offs = []
        for w in (wall[i] for i in tree.query(vung.buffer(DAY_TUONG_TOI_DA))) if tree is not None else []:
            p0, p1 = w.coords[0], w.coords[-1]
            if not cung_huong(goc(p0, p1), g0):
                continue
            o = off(p0)
            if abs(o - c0) > DAY_TUONG_TOI_DA:
                continue
            a0, a1 = sorted((dl(p0), dl(p1)))
            if a1 < t_min - 50 or a0 > t_max + 50:     # net tuong phai nam ngang qua hoac cham dau cua
                continue
            offs.append(o)
        tren = [o for o in offs if o >= c0 - 1]
        duoi = [o for o in offs if o <= c0 + 1]
        dai = (min(duoi + [c0]) if duoi else None, max(tren + [c0]) if tren else None)
        co_dai = bool(duoi) and bool(tren) and dai[1] - dai[0] > 20
        if not co_dai:
            khong_dai += 1
        for s in doan:
            if co_dai:
                ok = all(dai[0] - 15 <= off(p) <= dai[1] + 15 for p in s)
            else:
                ok = cung_huong(goc(*s), g0) or math.dist(*s) <= RET_MAX
            if ok:
                out.append(LineString(s))
            else:
                bo_canh += 1
    return out, dict(so_cua=so_cua, so_doan_khung=len(out), bo_canh_ngoai_tuong=bo_canh, bo_cung_quay=bo_cung,
                     cua_khong_co_tuong=khong_dai)


def build_faces(chains, gap_max, khung=None):
    """khung: doan khung cua (doc_khung_cua) - chi them vao luoi net, KHONG sinh tia dong o cua va khong chan tia dong
    (canh khung nam tren mat tuong, neu dung lam vat chan se lam hong doan dong o cua)."""
    rays = make_rays(chains)
    segs = [LineString(pts + ([pts[0]] if closed else [])) for closed, pts in chains]
    pairs = pair_rays(rays, gap_max, unary_union(segs))
    bridges = [LineString([a, b]) for a, b, _ in pairs] + snap_bridges(chains)
    # grid_size 0,01 mm: dau mut chi lech ~1e-7 mm so voi net ke ben van duoc coi la cham (nut giao that su), neu khong
    # polygonize se coi la dau tu do va nhieu phong bi gop vao nhau (loi gap o ban ve co doi tuong ACA da no).
    noded = shapely.union_all(segs + bridges + list(khung or []), grid_size=0.01)
    faces = list(polygonize(noded))
    return faces, pairs, bridges


def thong_so_text(e, doc):
    """Doc style, cao, layer, mau, goc xoay, tam hinh hoc cua text ten phong de dat nhan dien tich ngay ben duoi.

    Tra ve dict: kind, layer, style, h, style_h, color, rot, cx, cy (tam text ten), d (khoang tu tam text ten
    den tam nhan = nua chieu cao khoi chu + 1 lan cao chu: nhan nam duoi, cach 0,5 lan cao chu).
    Ghi chu: chieu rong text uoc luong = so ky tu x 0,55 x cao x he so rong (chi dung khi text can le trai/phai).
    """
    d = e.dxf
    style = d.get("style", "Standard")
    st = doc.styles.get(style) if style else None
    style_h = float(st.dxf.height) if st is not None and st.dxf.hasattr("height") else 0.0
    color = d.get("color", 256)
    if e.dxftype() == "MTEXT":
        h = float(d.get("char_height", 2.5))
        txt = e.plain_text()
        lines = txt.count("\n") + 1
        maxlen = max(len(s) for s in txt.split("\n"))
        wf = float(st.dxf.width) if st is not None and st.dxf.hasattr("width") else 1.0
        w = float(d.get("width", 0.0)) or maxlen * 0.55 * h * wf
        hb = (1.5 * lines - 0.5) * h
        try:                               # do bang so do phong chu that (TTF), chinh xac hon uoc luong
            from ezdxf.tools.text_size import mtext_size
            ms = mtext_size(e)
            w = float(d.get("width", 0.0)) or ms.total_width
            hb = ms.total_height or hb
        except Exception:
            pass
        ap = int(d.get("attachment_point", 1))
        col, row = (ap - 1) % 3, (ap - 1) // 3
        x, y = d.insert.x, d.insert.y
        cx = x if col == 1 else x + w / 2 if col == 0 else x - w / 2
        cy = y if row == 1 else y - hb / 2 if row == 0 else y + hb / 2
        rot = float(d.get("rotation", 0.0) or 0.0)
        kind = "MTEXT"
    else:
        h = float(d.height)
        wf = float(d.get("width", 1.0))
        txt = d.text
        w = len(txt) * 0.55 * h * wf
        try:                               # do bang so do phong chu that (TTF), chinh xac hon uoc luong
            from ezdxf.tools.text_size import text_size
            w = text_size(e).width
        except Exception:
            pass
        ha, va = int(d.get("halign", 0)), int(d.get("valign", 0))
        ix, iy = d.insert.x, d.insert.y
        if ha or va:
            ax, ay = d.align_point.x, d.align_point.y
        else:
            ax, ay = ix, iy
        cx = ax if ha in (1, 4) else (ix + ax) / 2 if ha in (3, 5) else ax + w / 2 if ha == 0 else ax - w / 2
        cy = ay if (va == 2 or ha == 4) else ay - h / 2 if va == 3 else ay + h / 2
        hb, lines = h, 1
        rot = float(d.get("rotation", 0.0) or 0.0)
        kind = "TEXT"
    dd = hb / 2 + h
    th = math.radians(rot)
    return dict(kind=kind, layer=d.layer, style=style, h=h, style_h=style_h, color=color, rot=rot,
                cx=cx, cy=cy, d=dd, x=cx + dd * math.sin(th), y=cy - dd * math.cos(th), w=w, hb=hb)


def do_text(doc, kind, style, h, text):
    """Do (rong, cao) cua mot chuoi chu theo style (font thật); uoc luong neu khong do duoc."""
    msp = doc.modelspace()
    try:
        if kind == "MTEXT":
            from ezdxf.tools.text_size import mtext_size
            e = msp.add_mtext(text, dxfattribs={"style": style, "char_height": h})
            ms = mtext_size(e)
            w, hb = ms.total_width, ms.total_height or h
        else:
            from ezdxf.tools.text_size import text_size
            e = msp.add_text(text, dxfattribs={"style": style, "height": h})
            w, hb = text_size(e).width, h
        msp.delete_entity(e)
        return w, hb
    except Exception:
        return len(text) * 0.55 * h, h


def lenh_nhan(n, nhan):
    """Cac dong lenh .scr ve mot nhan co thong so n (layer, style, cao, mau, goc xoay, vi tri tam) voi noi dung nhan."""
    L = ["_.-LAYER", "_M", f'"{acad_str(n["layer"])}"', ""]       # Make: tao neu chua co, da co thi chi dat hien hanh
    st = f'"{acad_str(n["style"])}"'
    if n["kind"] == "MTEXT":
        L += ["_.-MTEXT", f'{n["x"]:.2f},{n["y"]:.2f}', "_S", st, "_H", f'{n["h"]:g}', "_J", "_MC"]
        if abs(n["rot"]) > 1e-6:
            L += ["_R", f'{n["rot"]:g}']
        L += ["_W", "0", nhan, ""]
    else:
        L += ["_.-TEXT", "_S", st, "_J", "_MC", f'{n["x"]:.2f},{n["y"]:.2f}']
        if n["style_h"] == 0:     # style co chieu cao co dinh thi AutoCAD khong hoi chieu cao
            L.append(f'{n["h"]:g}')
        L += [f'{n["rot"]:g}', nhan]
    if n["color"] not in (256, 0):
        L += ["_.CHPROP", "_L", "", "_C", str(n["color"]), ""]
    return L


def doc_seeds(msp, layer_ten, doc=None):
    out = []
    # Ten phong chi lay o Model (khong lay trong block/xref): text trong xref thuong la chu thich, khong phai ten phong.
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT") and layer_goc(e.dxf.layer) == layer_goc(layer_ten):
            if e.dxftype() == "TEXT":
                p = e.dxf.align_point if (e.dxf.halign or e.dxf.valign) else e.dxf.insert
                t = e.dxf.text
            else:
                p, t = e.dxf.insert, e.plain_text()
            t = (t or "").strip()
            if t:
                info = None
                if doc is not None:
                    try:
                        info = thong_so_text(e, doc)
                    except Exception:
                        info = None
                out.append((t, (p.x, p.y), info))
    return out


DAY_LOP_TRAT = 15.0   # mm: lop trat hoan thien (ghi chu ban ve: "TRAT HOAN THIEN DAY 15")


def phat_hien_lop_trat(msp, day=DAY_LOP_TRAT):
    """Nét 'A-Vua trat' TRUNG voi nét 'A-Wall' (mat tuong) = ban ve CHUA VE lop trat rieng: tra ve `day`, nguoc lai 0.
    Chi dung de GHI CHU. Quy tac da chot (05/10/2026): duong bo bam dung net da ve; lop trat khong ve thi KHONG lui 15 mm.
    Muon lui thi nguoi dung phai yeu cau ro (--lop-trat 15)."""
    vt, wl = [], []
    for e in walk(msp):
        if e.dxftype() != "LINE":
            continue
        ls = LineString([(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)])
        lay = layer_goc(e.dxf.layer)
        if lay == "a-vua trat":
            vt.append(ls)
        elif lay == "a-wall":
            wl.append(ls)
    if not vt or not wl:
        return 0.0
    u = unary_union(wl).buffer(1.0)
    tong = sum(l.length for l in vt)
    phu = sum(l.intersection(u).length for l in vt)
    return day if tong > 0 and phu / tong > 0.5 else 0.0


def chon_lop_trat(msp, gia_tri):
    """So mm lui vao (mac dinh 0) + ghi chu khi ban ve chua ve lop trat rieng. 'auto' (cach cu) nay cung = 0."""
    s = str(gia_tri).strip().lower()
    t = 0.0 if s in ("", "auto") else float(s)
    note = None
    if phat_hien_lop_trat(msp) > 0:
        note = ("Nét A-Vua trat trùng mặt tường A-Wall (bản vẽ chưa vẽ lớp trát riêng): đường bo theo đúng mặt tường đã vẽ"
                + (", không lùi lớp trát." if not t else f"; đã lùi {t:g} mm theo yêu cầu."))
    return t, note


def inset_face(f, t):
    """Lui mat `f` vao trong t mm (goc nhon giu nguyen); tra ve Polygon lon nhat hoac None."""
    if not t:
        return f
    g = f.buffer(-t, join_style=2, mitre_limit=5).simplify(0.01)
    if g.is_empty:
        return None
    return max(getattr(g, "geoms", [g]), key=lambda p: p.area)


def acad_str(s):
    """Chuoi an toan cho .scr ASCII: ky tu ngoai ASCII thanh \\U+XXXX (AutoCAD hieu khi nhap lenh)."""
    return "".join(c if ord(c) < 128 else "\\U+%04X" % ord(c) for c in s)


def dangling_near(chains, point, radius):
    pts = []
    for closed, ch in chains:
        if not closed:
            for p in (ch[0], ch[-1]):
                if math.dist(p, point) <= radius:
                    pts.append((round(p[0]), round(p[1])))
    return sorted(set(pts))


def parse_them_ranh(text):
    """'x1,y1,x2,y2;x1,y1,x2,y2' -> list chuoi (False, [(x1,y1),(x2,y2)])."""
    out = []
    for part in (text or "").split(";"):
        part = part.strip()
        if not part:
            continue
        v = [float(t) for t in part.replace(" ", "").split(",")]
        if len(v) != 4:
            raise ValueError(f"Doan dong ranh sai dinh dang (can 4 so x1,y1,x2,y2): {part}")
        out.append((False, [(v[0], v[1]), (v[2], v[3])]))
    return out


def khe_ho_gan(chains, point, radius, top=6):
    """Cac cap dau ho gan diem dat ten, de goi y cho nguoi dung noi o dau can dong ranh."""
    ends = []
    for closed, ch in chains:
        if not closed:
            ends.extend([ch[0], ch[-1]])
    near = [e for e in ends if math.dist(e, point) <= radius]
    pairs = []
    for i, p in enumerate(near):
        for q in near[i + 1:]:
            d = math.dist(p, q)
            if d > 5:
                pairs.append((round(d), (round(p[0]), round(p[1])), (round(q[0]), round(q[1]))))
    pairs.sort()
    return [dict(dai=d, tu=p, den=q) for d, p, q in pairs[:top]]


def anh_xem_lai(path, chains, rooms, failed, extra):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(12, 12), dpi=90)
    ax = fig.add_axes([0.03, 0.03, 0.95, 0.95])
    for closed, ch in chains:
        xs, ys = zip(*(ch + ([ch[0]] if closed else [])))
        ax.plot(xs, ys, color="#868e96", lw=1)
    cols = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#008080", "#9a6324", "#800000", "#808000"]
    for i, r in enumerate(rooms):
        xs, ys = zip(*(r["dinh"] + [r["dinh"][0]]))
        c = cols[i % len(cols)]
        ax.fill(xs, ys, color=c, alpha=0.2)
        ax.plot(xs, ys, color=c, lw=2)
        ax.text(r["nhan_xy"][0], r["nhan_xy"][1], f'{r["ten"]}\n{r["dt_lam_tron"]:.1f} m2', ha="center", fontsize=9)
    for f in failed:
        ax.plot(*f["xy"], "rx", ms=14, mew=3)
        ax.text(f["xy"][0], f["xy"][1], "  " + f["ten"] + " (hở)", color="red", fontsize=9)
        for p in f["dau_ho_gan"]:
            ax.plot(*p, "ro", ms=6, mfc="none")
    for a_, b_ in extra:
        ax.plot([a_[0], b_[0]], [a_[1], b_[1]], color="#1c7ed6", lw=2, ls="--")
    ax.set_aspect("equal")
    ax.grid(True, lw=0.3)
    fig.savefig(path)
    plt.close(fig)


def scr_for(rooms, layer, label_h, label_layer, clayer="0"):
    """Sinh lenh AutoCAD ve polyline phong + nhan m2 (chay tren BAN SAO DWG)."""
    # Trong .scr, dong trong = phim Enter; "" se bi hieu la ky tu nen khong dung. Moi tuy chon mot dong.
    L = ["CMDECHO", "0", "OSMODE", "0",
         "_.-LAYER", "_M", f'"{label_layer}"', "",                       # tao/dat layer nhan (da co thi chi dat)
         "_.-LAYER", "_M", f'"{layer}"', "_C", "222", "", ""]           # tao layer phong, mau 222 (theo ban mau)
    for r in rooms:
        if not r.get("chi_nhan"):
            L += ["_.-LAYER", "_S", f'"{layer}"', ""]
            L.append("_.PLINE " + " ".join(f"{x:.4f},{y:.4f}" for x, y in r["dinh"]) + " _C")
            # cot/hop ky thuat nam rieng trong phong: ve polyline loai tru cung layer, de DT nhan = duong bo - loai tru
            for ho in r.get("ho", []):
                L.append("_.PLINE " + " ".join(f"{x:.4f},{y:.4f}" for x, y in ho) + " _C")
        if r.get("nhan_co_san"):
            continue                      # phong da co nhan m2 tren lop in duoc: khong ghi them
        nhan = f'{r["dt_lam_tron"]:.1f} m2'
        n = r.get("nhan")
        if n:
            # Nhan dien tich: cung layer, style, cao, mau, goc xoay voi text ten phong; can giua, nam ben duoi ten phong.
            L += lenh_nhan(n, nhan)
        else:
            # phong khai bao bang --them-phong (khong co text ten): dat nhan tai tam vung bang gia tri mac dinh
            L += ["_.-LAYER", "_S", f'"{label_layer}"', ""]
            cx, cy = r["nhan_xy"]
            L += ["_.-TEXT", "_J", "_MC", f"{cx:.2f},{cy:.2f}", f"{label_h:g}", "0", nhan]
    L += ["_.-LAYER", "_S", f'"{acad_str(clayer)}"', ""]       # tra lai layer hien hanh cua ban ve
    L += ["_.QSAVE", "_.QUIT _Y"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--layer-phong", default=LAYER_PHONG)
    ap.add_argument("--layer-ranh", default=",".join(LAYER_RANH), help="cac layer lam ranh, cach nhau dau phay")
    ap.add_argument("--layer-ten", default=LAYER_TEN)
    ap.add_argument("--gap-max", type=float, default=1200.0)
    ap.add_argument("--label-h", type=float, default=250.0)
    ap.add_argument("--label-layer", default="A-Text")
    ap.add_argument("--layer-dong-ranh", default="A-Dong ranh phong",
                    help="layer chua LINE/PLINE do nguoi dung ve de dong ranh cho cho ho (tuy chon)")
    ap.add_argument("--them-ranh", default="", help="doan dong ranh nhap tay: 'x1,y1,x2,y2;x1,y1,x2,y2'")
    ap.add_argument("--block-bo-qua", default=None,
                    help="regex ten block/xref khong lay lam ranh (mac dinh: ghi chu, legend, khung, luoi, tran, loi thang); '' = lay het")
    ap.add_argument("--them-phong", default="",
                    help="khai bao phong khong co text ten: 'Ten:x,y;Ten:x,y' (dung toa do diem trong phong)")
    ap.add_argument("--lop-trat", default="0",
                    help="so mm lui vao trong net ranh. Mac dinh 0: duong bo bam dung net da ve (lop trat khong ve thi khong "
                         "lui). Chi dat 15 khi nguoi dung yeu cau ro.")
    ap.add_argument("--layer-cua", default=",".join(LAYER_CUA),
                    help="layer cua di/cua so lay net bao khung lam ranh (bo canh mo, cung quay); '' = khong dung")
    ap.add_argument("--nhan-tat-ca", action="store_true",
                    help="ghi them nhan m2 cho ca phong da co polyline (mac dinh chi ghi nhan cho phong dung moi)")
    ap.add_argument("--ve-lai", action="store_true",
                    help="dung va ve lai ca phong da co polyline tren layer phong (mac dinh: chi doi chieu, khong ve trung)")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    doc = ezdxf.readfile(a.dxf)
    msp = doc.modelspace()
    problems = []
    if doc.header.get("$INSUNITS", 0) != 4:
        problems.append((LOI, "Đơn vị bản vẽ", f"INSUNITS={doc.header.get('$INSUNITS', 0)}, chuẩn là 4 (mm)."))

    layers = [x.strip() for x in a.layer_ranh.split(",") if x.strip()]
    chains = doc_chains(msp, layers)
    dong_ranh = doc_chains(msp, [a.layer_dong_ranh]) + parse_them_ranh(a.them_ranh)
    chains = chains + dong_ranh
    if a.block_bo_qua is not None:
        _BO_QUA[0] = re.compile(a.block_bo_qua, re.I) if a.block_bo_qua else None
        chains = doc_chains(msp, layers) + dong_ranh   # tinh lai voi bo loc moi
    seeds = doc_seeds(msp, a.layer_ten, doc)
    for part in (a.them_phong or "").split(";"):
        if ":" in part:
            ten, xy = part.rsplit(":", 1)
            sx, sy = [float(t) for t in xy.split(",")]
            seeds.append((ten.strip(), (sx, sy), None))
    # nhan m2 da co tren lop in duoc (khong tinh Defpoints): khong ghi nhan trung
    nhan_co = []
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT") and layer_goc(e.dxf.layer) != "defpoints":
            t = e.dxf.text if e.dxftype() == "TEXT" else e.plain_text()
            m = RE_NHAN.search(t or "")
            if m:
                so = re.match(r"\d+(?:[.,]\d+)?", m.group(0)).group(0).replace(",", ".")
                nhan_co.append((Point(e.dxf.insert.x, e.dxf.insert.y), float(so), e.dxf.handle))
    if not seeds:
        problems.append((CANH_BAO, "Không có tên phòng",
                         "Không thấy text tên phòng (layer A-Text) ở Model và không có --them-phong; chỉ liệt kê vùng kín chưa đặt tên."))
    khung, tk_cua = doc_khung_cua(msp, chains, [x.strip() for x in a.layer_cua.split(",") if x.strip()])
    faces, pairs, bridges = build_faces(chains, a.gap_max, khung)
    t_in, ghi_chu_trat = chon_lop_trat(msp, a.lop_trat)
    if ghi_chu_trat:
        problems.append((GOI_Y, "Lớp trát", ghi_chu_trat))

    # polyline phong da co san tren layer phong (nhan vien/nguoi dung da bo): doi chieu, khong ve trung
    existing = []
    for e in msp:
        if e.dxftype() == "LWPOLYLINE" and norm(e.dxf.layer) == norm(a.layer_phong):
            pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(0.5)]
            if len(pts) >= 3:
                g = Polygon(pts)
                # dong = co bat co Closed (dau cuoi chi trung diem van tinh la chua dong)
                existing.append(dict(handle=e.dxf.handle, dong=bool(e.closed),
                                     geom=g if g.is_valid else g.buffer(0)))

    rooms, failed, da_co, da_co_chua_dc = [], [], [], []
    seen_face = {}
    for name, (x, y), tinfo in seeds:
        hit = [f for f in faces if f.contains(Point(x, y))]
        if not hit:
            info = dict(ten=name, xy=(round(x), round(y)),
                        dau_ho_gan=dangling_near(chains, (x, y), 8000),
                        khe_ho_gan_nhat=khe_ho_gan(chains, (x, y), 8000))
            ex0 = [q for q in existing if q["geom"].contains(Point(x, y))]
            if ex0:
                # Phong da co polyline cua nguoi dung nhung net ranh chua du de dung lai: KHONG phai loi cua phong,
                # chi la chua doi chieu doc lap duoc. Khong bao "Loi - khong dong kin".
                q = min(ex0, key=lambda t: t["geom"].area)
                info.update(handle=q["handle"], dt_co_san=q["geom"].area / 1e6, dong=q["dong"])
                da_co_chua_dc.append(info)
            else:
                failed.append(info)
            continue
        f = min(hit, key=lambda p: p.area)
        if id(f) in seen_face:
            # Nhieu ten phong cung nam trong mot vung kin (khong gian mo, vi du phong khach + bep): chi dung MOT polyline.
            r0 = seen_face[id(f)]
            r0["ten"] += " + " + name
            r0["canh_bao"] = [w for w in r0["canh_bao"] if not w.startswith("Không gian mở")] + [
                f"Không gian mở: {r0['ten']} nằm chung một vùng kín (không có vách ngăn). Muốn tách riêng, "
                f"vẽ đoạn chia ranh trên layer '{a.layer_dong_ranh}' hoặc dùng --them-ranh rồi chạy lại."]
            continue
        f_goc = f
        f = inset_face(f_goc, t_in)          # lui vao lop trat (neu nét A-Vua trat trung mat tuong) -> mat hoan thiện
        if f is None:
            continue
        ring = list(f.exterior.coords)[:-1]
        warn = []
        if t_in:
            warn.append(f"Đã lùi {t_in:g} mm vào trong nét ranh theo yêu cầu (--lop-trat {t_in:g}).")
        if len(f.interiors):
            holes = sum(Polygon(i).area for i in f.interiors) / 1e6
            warn.append(f"Có {len(f.interiors)} vật nằm riêng trong phòng (tổng {holes:.2f} m²) đã trừ khỏi diện tích; cần xác nhận cột/hộp kỹ thuật.")
        c = f.representative_point()
        # DT ghi nhan tinh tu chinh hinh se ve (duong bo - cac lo loai tru), khong tu gia tri khac
        ho = [list(i.coords)[:-1] for i in f.interiors]
        dt_ve = (Polygon(ring).area - sum(Polygon(h).area for h in ho)) / 1e6
        nhan_trong = [(v, hd) for pt, v, hd in nhan_co if f.contains(pt)]
        for v, hd in nhan_trong:
            if abs(v - r1(dt_ve)) > 0.05:
                warn.append(f"Nhãn m² có sẵn {hd} ghi {v:g} m², khác diện tích polyline {r1(dt_ve):.1f} m²: "
                            "không ghi đè nhãn cũ, cần sửa tay.")
                problems.append((LOI, "Nhãn diện tích sai", f"'{name}': nhãn {hd} ghi {v:g} m², polyline {r1(dt_ve):.1f} m²."))
        room = dict(ten=name, dt=dt_ve, dt_lam_tron=r1(dt_ve), dinh=ring, ho=ho,
                    nhan_xy=(c.x, c.y), canh_bao=warn, nhan=tinfo,
                    nhan_co_san=bool(nhan_trong))
        seen_face[id(f_goc)] = room
        ex = [q for q in existing if q["geom"].contains(Point(x, y))]
        if ex and not a.ve_lai:
            q = min(ex, key=lambda t: t["geom"].area)
            chenh = (q["geom"].area - f.area) / 1e6
            room["da_co"] = dict(handle=q["handle"], dt=q["geom"].area / 1e6, chenh=chenh,
                                 chenh_pct=chenh / (f.area / 1e6) * 100 if f.area else 0, dong=q["dong"])
            if not q["dong"]:
                room["canh_bao"].append(f"Polyline có sẵn handle {q['handle']} chưa bật Closed.")
            da_co.append(room)
        else:
            rooms.append(room)

    # polyline trung chong tren layer phong
    for i, p in enumerate(existing):
        for q in existing[i + 1:]:
            ua = p["geom"].union(q["geom"]).area
            if ua > 0 and p["geom"].intersection(q["geom"]).area / ua > 0.98:
                problems.append((CANH_BAO, "Polyline trùng chồng",
                                 f"Handle {p['handle']} và {q['handle']} trùng nhau trên layer '{a.layer_phong}'."))
    for p in existing:
        if not p["dong"]:
            problems.append((CANH_BAO, "Polyline chưa đóng", f"Handle {p['handle']} không bật Closed."))

    # vung kin chua co ten phong (vi du WC chi co nhan m2): de nguoi dung dat ten
    seed_pts = [Point(x, y) for _, (x, y), _i in seeds]
    chua_ten = []
    for f in faces:
        if f.area < 1.0e6 or f.area > 120.0e6 or f.buffer(-300).is_empty:   # bo loi tuong/khe hep
            continue
        if any(f.contains(s) for s in seed_pts):
            continue
        c = f.representative_point()
        chua_ten.append(dict(xy=(round(c.x), round(c.y)), dt=round(f.area / 1e6, 4), dt_lam_tron=r1(f.area / 1e6)))

    import os
    os.makedirs(a.out_dir, exist_ok=True)
    scr_path = os.path.join(a.out_dir, "ve_polyline_phong.scr")
    with open(scr_path, "w", encoding="ascii", newline="\n") as fh:
        # --nhan-tat-ca: ghi them nhan cho phong da co polyline (chi nhan, khong ve lai polyline)
        # nhan cua phong da co polyline lay theo CHINH polyline co san trong ban ve (khong theo vung dung lai)
        chi_nhan = [dict(r, chi_nhan=True, dt_lam_tron=r1(r["da_co"]["dt"])) for r in da_co] if a.nhan_tat_ca else []
        fh.write(scr_for(rooms + chi_nhan, a.layer_phong, a.label_h, a.label_layer,
                         doc.header.get("$CLAYER", "0")))

    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = "Phong"
    ws.append(["STT", "Phòng", "Diện tích thông thủy (m²)", "Làm tròn 1 số (m²)", "Trạng thái", "Mức độ", "Ghi chú"])
    n = 0
    for r in rooms + da_co:
        n += 1
        if "da_co" in r:
            d = r["da_co"]
            ok = abs(d["chenh_pct"]) <= 0.5
            ws.append([n, r["ten"], round(r["dt"], 4), r["dt_lam_tron"], "Đã có polyline, đối chiếu",
                       DAT if ok and not r["canh_bao"] else CANH_BAO if abs(d["chenh_pct"]) <= 1 else LOI,
                       f"Polyline sẵn có {d['handle']}: {d['dt']:.4f} m², chênh {d['chenh']:+.4f} m² ({d['chenh_pct']:+.2f}%). "
                       + " ".join(r["canh_bao"])])
        else:
            ws.append([n, r["ten"], round(r["dt"], 4), r["dt_lam_tron"], "Dựng mới",
                       CANH_BAO if r["canh_bao"] else DAT, " ".join(r["canh_bao"])])
    for r in da_co_chua_dc:
        n += 1
        ws.append([n, r["ten"], round(r["dt_co_san"], 4), r1(r["dt_co_san"]), "Đã có polyline, chưa đối chiếu được",
                   CANH_BAO,
                   f"Polyline sẵn có {r['handle']} ({r['dt_co_san']:.4f} m²). Nét ranh quanh phòng chưa đủ để dựng lại "
                   f"độc lập (khe hở gần nhất: {r['khe_ho_gan_nhat'][:2]}). Muốn đối chiếu cần đóng ranh chỗ hở."
                   + ("" if r["dong"] else " Polyline chưa bật Closed.")])
    for r in failed:
        ws.append([None, r["ten"], None, None, "Không đóng kín được", LOI,
                   f"Vùng quanh ({r['xy'][0]}, {r['xy'][1]}). Khe hở gần nhất: {r['khe_ho_gan_nhat'][:3]}"])
    for r in chua_ten:
        ws.append([None, f"(chưa đặt tên) tại {r['xy']}", r["dt"], r["dt_lam_tron"], "Vùng kín chưa có tên", CANH_BAO,
                   "Cần đặt tên phòng (text layer A-Text) để dựng polyline."])
    for c in ws[1]:
        c.font = Font(bold=True)
    for col, w in zip("ABCDEFG", [5, 28, 24, 18, 26, 11, 90]):
        ws.column_dimensions[col].width = w
    xlsx_path = os.path.join(a.out_dir, "DienTichPhong.xlsx")
    wb.save(xlsx_path)
    png_path = os.path.join(a.out_dir, "xem_lai.png")
    anh_xem_lai(png_path, chains + [(False, list(l.coords)) for l in khung], rooms + da_co, failed, [(p, q) for p, q, _ in pairs])

    result = dict(file=os.path.basename(a.dxf), gap_max=a.gap_max, lop_trat_mm=t_in, khung_cua=tk_cua,
                  so_chain=len(chains), so_cau_noi=len(pairs),
                  dung_moi=[dict(ten=r["ten"], dt=round(r["dt"], 4), dt_lam_tron=r["dt_lam_tron"],
                                 so_dinh=len(r["dinh"]), canh_bao=r["canh_bao"]) for r in rooms],
                  da_co_doi_chieu=[dict(ten=r["ten"], dt_moi=round(r["dt"], 4), handle=r["da_co"]["handle"],
                                        dt_co_san=round(r["da_co"]["dt"], 4),
                                        chenh_pct=round(r["da_co"]["chenh_pct"], 3), canh_bao=r["canh_bao"])
                                   for r in da_co],
                  da_co_chua_doi_chieu=[dict(ten=r["ten"], handle=r["handle"], dt_co_san=round(r["dt_co_san"], 4),
                                             dong=r["dong"], khe_ho_gan_nhat=r["khe_ho_gan_nhat"][:3])
                                        for r in da_co_chua_dc],
                  khong_dong_duoc=failed, vung_chua_ten=chua_ten,
                  van_de=[dict(muc=m, hang_muc=h, mo_ta=d) for m, h, d in problems],
                  scr=scr_path, xlsx=xlsx_path, anh_xem_lai=png_path)
    if a.debug:
        result["cau_noi"] = [dict(a=(round(p[0]), round(p[1])), b=(round(q[0]), round(q[1])), dai=round(d))
                             for p, q, d in pairs]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

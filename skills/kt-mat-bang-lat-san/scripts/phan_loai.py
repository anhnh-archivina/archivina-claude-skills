# -*- coding: utf-8 -*-
"""Dung chung cho tao_hatch_lat_san.py va thong_ke_lat_san.py:
doc polyline phong + ten phong tu DXF, phan nhom lat san PN / PK / WC / LG, tim diem goc (origin) hatch.
Bang nhom + quy tac diem goc: references/phan-loai-phong.md (ty le chot 21/10/2026 theo ban anh sua)."""
import math
import re
import unicodedata

from ezdxf import bbox as ezbbox
from shapely.geometry import LineString, Point, Polygon, box

LAYER_PHONG = "A- Dien tich phong"
LAYER_HATCH = "A-Materials"
MAU_LAYER_HATCH = 251  # mau chuan A-Materials trong ISO - ARCHIVINA

# nhom: (pattern, ty le, goc, mo ta)
NHOM = {
    "PN": ("DOLMIT", 500, 0, "Phòng ngủ, làm việc, thay đồ"),
    "PK": ("ANSI37", 5000, 45, "Phòng khách, bếp, ăn, sảnh, hành lang"),
    "WC": ("ANSI37", 2500, 45, "Vệ sinh, kho"),
    "LG": ("ANSI37", 2500, 45, "Ban công, lô gia"),
}

SAT_CUA = 150  # mm: cua cach polyline phong <= nguong nay thi coi la cua cua phong
_LAYER_CUA = re.compile(r"door|\bcua\b|cua di", re.I)
_TEN_SEN_TAM = re.compile(r"sen ?tam|shower|voi sen", re.I)

# tu khoa tren ten da bo dau, viet thuong; xet theo thu tu LG -> WC -> PN -> PK
TU_KHOA = [
    ("LG", [r"ban cong", r"lo ?gg?ia", r"\blg\d*\b", r"\bbc\d*\b"]),
    ("WC", [r"\bwc\d*\b", r"ve sinh", r"\bvs\d*\b", r"\btam\b", r"\bkho\b"]),
    ("PN", [r"\bngu\b", r"\bpn\d*\b", r"lam viec", r"thay do", r"\bmaster\b"]),
    ("PK", [r"\bkhach\b", r"\bpk\b", r"\bbep\b", r"\ban\b", r"\bsanh\b", r"hanh lang",
            r"sinh hoat", r"\bkitchen\b", r"\bliving\b", r"\bdining\b"]),
]

_LA_NHAN_DT = re.compile(r"(m2|m²|dtch|^[\d.,\s]+$)", re.I)


def _giai_ma(s):
    s = re.sub(r"\\U\+([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), s)
    return s


def bo_dau(s):
    s = _giai_ma(s).replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower()).strip()


def nhom_cua_ten(ten):
    t = bo_dau(ten)
    for nhom, mau in TU_KHOA:
        if any(re.search(p, t) for p in mau):
            return nhom
    return None


def _chu(e):
    if e.dxftype() == "MTEXT":
        return e.plain_text().strip()
    return (e.dxf.text or "").strip()


def doc_phong(msp, layer_phong=LAYER_PHONG):
    """Tra ve list dict: handle, poly (shapely, mm), dt_m2, ten (list), nhom, ly_do."""
    chu = []
    for e in msp.query("TEXT MTEXT"):
        s = _chu(e)
        if s and not _LA_NHAN_DT.search(bo_dau(s)):
            chu.append((Point(e.dxf.insert[0], e.dxf.insert[1]), _giai_ma(s)))
    ds = []
    for p in msp.query("LWPOLYLINE"):
        if p.dxf.layer != layer_phong or not p.closed:
            continue
        pts = [(x, y) for x, y, *_ in p.get_points()]
        if len(pts) < 3:
            continue
        poly = Polygon(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        ten = [s for pt, s in chu if poly.contains(pt)]
        cac_nhom = {n for n in (nhom_cua_ten(s) for s in ten) if n}
        ly_do = ""
        if not ten:
            ly_do = "khong co ten phong"
        elif not cac_nhom:
            ly_do = "ten phong khong khop nhom nao"
        elif len(cac_nhom) > 1:
            ly_do = "ten phong thuoc nhieu nhom: " + ",".join(sorted(cac_nhom))
        ds.append(dict(handle=p.dxf.handle, poly=poly, dt_m2=poly.area / 1e6, ten=ten,
                       nhom=next(iter(cac_nhom)) if len(cac_nhom) == 1 else None, ly_do=ly_do))
    # polyline loai tru (HKT/cot) nam tron trong phong khac -> lo cua phong do
    for a in ds:
        a["lo"] = []
    ngoai = []
    for a in ds:
        cha = [b for b in ds if b is not a and b["poly"].area > a["poly"].area
               and b["poly"].contains(a["poly"].representative_point())]
        if cha:
            min(cha, key=lambda b: b["poly"].area)["lo"].append(a)
        else:
            ngoai.append(a)
    for a in ngoai:
        a["dt_m2"] -= sum(h["poly"].area for h in a["lo"]) / 1e6
        a["lo"] = [h["handle"] for h in a["lo"]]
    return ngoai


# ---------------- diem goc (origin) hatch ----------------
def _hinh(e):
    for v in e.virtual_entities():
        if v.dxftype() == "INSERT":
            yield from _hinh(v)
        else:
            yield v


def _hop(e):
    try:
        b = ezbbox.extents(_hinh(e))
    except Exception:
        return None
    if not b.has_data:
        return None
    return box(b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y)


def doc_cua(msp):
    """Cua di (block / AEC_DOOR da no tren layer *Door* / *Cua*): list dict hop (shapely), ban_le (Point|None).
    Can DXF xuat CO no doi tuong AEC (xuat_dxf no_doi_tuong_aec=true)."""
    ds = []
    for e in msp.query("INSERT"):
        if not (_LAYER_CUA.search(bo_dau(e.dxf.layer)) or _LAYER_CUA.search(bo_dau(e.dxf.name))):
            continue
        hop = _hop(e)
        if hop is None:
            continue
        cung = [v for v in _hinh(e) if v.dxftype() == "ARC"]
        ban_le = Point(cung[0].dxf.center.x, cung[0].dxf.center.y) if cung else None
        ds.append(dict(hop=hop, ban_le=ban_le))
    return ds


def doc_sen_tam(msp):
    """Sen tam: list (diem sen, list hop thiet bi WC chua diem sen = vung tam/vach kinh)."""
    hop_tb, sen = [], []
    for e in msp.query("INSERT"):
        hop = _hop(e)
        if hop is None:
            continue
        if _TEN_SEN_TAM.search(bo_dau(e.dxf.name)):
            sen.append(hop)
        else:
            hop_tb.append(hop)
    return [(s.centroid, [h for h in hop_tb if h.contains(s.centroid) and h.area > s.area * 1.5]) for s in sen]


def _dinh(p):
    return [Point(c) for c in p["poly"].exterior.coords[:-1]]


def _cua_cua_phong(p, cua):
    return [c for c in cua if c["hop"].distance(p["poly"].exterior) <= SAT_CUA]


def _gan_cua(dinh, cac_cua):
    return min(dinh, key=lambda d: min(c["hop"].distance(d) for c in cac_cua))


def diem_goc(p, ds_phong, cua, sen_tam):
    """Tra ve ((x, y) | None, ghi chu). Quy tac (anh chot 21/10/2026):
    PK: goc sanh - canh tuong chua cua chinh (cua khong thong sang phong nao khac), dau canh phia xa ban le;
    WC: goc phong tam - dinh nam trong vung tam (hop thiet bi chua sen), nhieu dinh -> gan cua WC nhat;
        khong co sen (kho) -> dinh gan cua nhat;
    LG: goc trong gan cua di ra lo gia; PN: goc gan cua di vao phong."""
    dinh = _dinh(p)
    cc = _cua_cua_phong(p, cua)
    if not cc:
        return None, "khong tim thay cua cua phong"
    nhom = p["nhom"]
    if nhom == "PK":
        khac = [q for q in ds_phong if q is not p]
        chinh = [c for c in cc if all(c["hop"].distance(q["poly"].exterior) > SAT_CUA for q in khac)]
        if not chinh:
            return _xy(_gan_cua(dinh, cc)), "khong co cua chinh - lay goc gan cua"
        c = max(chinh, key=lambda c: c["hop"].area)
        canh = [LineString([a, b]) for a, b in zip(dinh, dinh[1:] + dinh[:1])]
        k = max(canh, key=lambda k: (k.intersection(c["hop"].buffer(20)).length, -k.distance(c["hop"])))
        a, b = Point(k.coords[0]), Point(k.coords[1])
        moc = c["ban_le"] or c["hop"].centroid
        return _xy(a if a.distance(moc) > b.distance(moc) else b), "goc sanh (canh cua chinh, phia xa ban le)"
    if nhom == "WC":
        vung = [h for s, hs in sen_tam if p["poly"].contains(s) for h in hs]
        sen = [s for s, _ in sen_tam if p["poly"].contains(s)]
        if vung:
            ung = [d for d in dinh if any(h.buffer(60).contains(d) for h in vung)]
            if ung:
                return _xy(_gan_cua(ung, cc)), "goc phong tam (vung tam)"
        if sen:
            return _xy(min(dinh, key=lambda d: d.distance(sen[0]))), "goc gan sen tam (khong thay vung tam)"
        return _xy(_gan_cua(dinh, cc)), "khong co sen tam - lay goc gan cua"
    if nhom == "PN":
        vao = [c for c in cc if any(q["nhom"] == "PK" and c["hop"].distance(q["poly"].exterior) <= SAT_CUA
                                    for q in ds_phong if q is not p)] or cc
        return _xy(_gan_cua(dinh, vao)), "goc gan cua vao phong"
    if nhom == "LG":
        return _xy(_gan_cua(dinh, cc)), "goc trong gan cua ra lo gia"
    return None, "chua co quy tac"


def _xy(d):
    return (round(d.x, 1), round(d.y, 1))

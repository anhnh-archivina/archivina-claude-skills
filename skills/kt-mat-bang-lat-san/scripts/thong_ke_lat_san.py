# -*- coding: utf-8 -*-
"""
KT-Mat bang lat san can ho (Archivina) - thong ke dien tich lat theo nhom phong.

Doc DXF ban sao da hatch (layer A-Materials), tinh dien tich tung hatch tu bien (tru lo), ghep voi polyline
phong lien ket (layer "A- Dien tich phong") va ten phong; xuat Excel 3 sheet:
  Tong hop  : nhom - pattern / ty le / goc - so phong - tong DT lat (m2)
  Chi tiet  : phong - nhom - DT hatch (4 so le / 1 so le) - DT polyline - lech
  Kiem tra  : phong chua hatch, hatch khong khop polyline / nhom, lech > 0,01 m2
Tinh tren gia tri chua lam tron; chi lam tron khi hien thi.

  python thong_ke_lat_san.py --dxf CanTho_LatSan.dxf --out 20261021_CT_T5_ThongKeLatSan.xlsx [--du-an CT] [--tang T5]
"""
import argparse
import json
import os
import sys

import ezdxf
from ezdxf import path as ezpath
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from shapely.geometry import Polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phan_loai import LAYER_HATCH, LAYER_PHONG, NHOM, doc_phong  # noqa: E402

NGUONG_LECH = 0.01  # m2


def dt_hatch(h):
    vung = Polygon()
    for p in ezpath.from_hatch(h):
        pts = [(v.x, v.y) for v in p.flattening(distance=1)]
        if len(pts) >= 3:
            vung = vung.symmetric_difference(Polygon(pts).buffer(0))
    return vung


def _khop(h, n):
    pat, tl, goc, _ = NHOM[n]
    return (h.dxf.pattern_name.upper() == pat and abs(h.dxf.pattern_scale - tl) < 1e-6
            and abs((h.dxf.pattern_angle - goc) % 360) < 1e-6)


def nhom_cua_hatch(h, uu_tien=None):
    """WC va LG cung ANSI37 2500/45 -> uu tien nhom theo ten phong chua hatch."""
    if uu_tien and _khop(h, uu_tien):
        return uu_tien
    return next((n for n in NHOM if _khop(h, n)), None)


def phan_tich(dxf, layer_phong):
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    phong = doc_phong(msp, layer_phong)
    theo_handle = {p["handle"]: p for p in phong}
    chi_tiet, kiem_tra, da_hatch = [], [], set()
    for h in msp.query("HATCH"):
        if h.dxf.layer != LAYER_HATCH:
            continue
        vung = dt_hatch(h)
        nguon = [s for bp in h.paths for s in getattr(bp, "source_boundary_objects", [])]
        p = next((theo_handle[s] for s in nguon if s in theo_handle), None)
        if p is None and not vung.is_empty:
            p = next((q for q in phong if q["poly"].contains(vung.representative_point())), None)
        n_h = nhom_cua_hatch(h, p["nhom"] if p else None)
        dong = dict(hatch=h.dxf.handle, pattern=h.dxf.pattern_name, ty_le=h.dxf.pattern_scale,
                    goc=h.dxf.pattern_angle, nhom=n_h, dt_hatch=vung.area / 1e6,
                    phong=p["handle"] if p else "", ten=", ".join(p["ten"]) if p else "",
                    dt_phong=p["dt_m2"] if p else None)
        dong["lech"] = dong["dt_hatch"] - dong["dt_phong"] if p else None
        chi_tiet.append(dong)
        if p:
            da_hatch.add(p["handle"])
        if n_h is None:
            kiem_tra.append(("Cảnh báo", dong["ten"], h.dxf.handle,
                             "Hatch %s %g/%g° không thuộc bảng nhóm lát sàn" % (dong["pattern"], dong["ty_le"], dong["goc"])))
        if p is None:
            kiem_tra.append(("Cảnh báo", "", h.dxf.handle, "Hatch không nằm trong polyline phòng nào"))
        else:
            if p["nhom"] and n_h and p["nhom"] != n_h:
                kiem_tra.append(("Lỗi", dong["ten"], h.dxf.handle,
                                 "Hatch nhóm %s nhưng tên phòng thuộc nhóm %s" % (n_h, p["nhom"])))
            if abs(dong["lech"]) > NGUONG_LECH:
                kiem_tra.append(("Lỗi", dong["ten"], h.dxf.handle,
                                 "DT hatch lệch polyline phòng %.4f m²" % dong["lech"]))
    for p in phong:
        if p["handle"] not in da_hatch:
            kiem_tra.append(("Cảnh báo", ", ".join(p["ten"]), p["handle"],
                             "Phòng chưa hatch" + (" (%s)" % p["ly_do"] if p["ly_do"] else "")))
    return chi_tiet, kiem_tra


def _dinh_dang(ws, rong=None):
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="D9E1F2")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    for i, col in enumerate(ws.columns, 1):
        w = max(len(str(c.value)) if c.value is not None else 0 for c in col)
        ws.column_dimensions[get_column_letter(i)].width = min(max(w + 2, 8), 60)


def xuat_excel(chi_tiet, kiem_tra, out, du_an, tang, dxf):
    wb = Workbook()
    ws = wb.active
    ws.title = "Tổng hợp"
    ws.append(["Nhóm", "Loại phòng", "Pattern", "Tỷ lệ", "Góc (°)", "Số phòng", "DT lát (m²)", "DT lát (m², 4 số lẻ)"])
    tong = 0.0
    for n, (pat, tl, goc, mo_ta) in NHOM.items():
        ds = [d for d in chi_tiet if d["nhom"] == n]
        s = sum(d["dt_hatch"] for d in ds)
        tong += s
        ws.append([n, mo_ta, pat, tl, goc, len(ds), round(s, 1), round(s, 4)])
    ws.append(["", "Tổng", "", "", "", sum(1 for d in chi_tiet if d["nhom"]), round(tong, 1), round(tong, 4)])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
    ws.append([])
    ws.append(["Dự án: %s · Tầng: %s · Nguồn: %s" % (du_an or "chưa xác định", tang or "chưa xác định",
                                                       os.path.basename(dxf))])
    _dinh_dang(ws)
    ws.column_dimensions["A"].width = 8

    ws = wb.create_sheet("Chi tiết")
    ws.append(["STT", "Phòng", "Nhóm", "Pattern", "Tỷ lệ", "Góc (°)", "DT lát (m²)", "DT lát (4 số lẻ)",
               "DT polyline phòng (4 số lẻ)", "Lệch (m²)", "Handle hatch", "Handle polyline"])
    for i, d in enumerate(sorted(chi_tiet, key=lambda d: (d["nhom"] or "Z", d["ten"])), 1):
        ws.append([i, d["ten"], d["nhom"] or "?", d["pattern"], d["ty_le"], d["goc"], round(d["dt_hatch"], 1),
                   round(d["dt_hatch"], 4), None if d["dt_phong"] is None else round(d["dt_phong"], 4),
                   None if d["lech"] is None else round(d["lech"], 4), d["hatch"], d["phong"]])
    _dinh_dang(ws)

    ws = wb.create_sheet("Kiểm tra")
    ws.append(["STT", "Mức độ", "Phòng", "Handle", "Mô tả"])
    mau = {"Lỗi": "F8CBAD", "Cảnh báo": "FFE699"}
    for i, k in enumerate(kiem_tra, 1):
        ws.append([i] + list(k))
        ws.cell(ws.max_row, 2).fill = PatternFill("solid", fgColor=mau.get(k[0], "FFFFFF"))
    if not kiem_tra:
        ws.append(["", "Đạt", "", "", "Mọi phòng đã hatch, DT hatch khớp polyline (≤ 0,01 m²)"])
    _dinh_dang(ws)
    wb.save(out)
    return tong


def main():
    ap = argparse.ArgumentParser(description="Thong ke dien tich lat san theo nhom phong tu DXF ban sao da hatch")
    ap.add_argument("--dxf", required=True)
    ap.add_argument("--out", required=True, help=".xlsx moi (khong ghi de)")
    ap.add_argument("--du-an", default="")
    ap.add_argument("--tang", default="")
    ap.add_argument("--layer-phong", default=LAYER_PHONG)
    a = ap.parse_args()
    if os.path.exists(a.out):
        sys.exit("Da ton tai, khong ghi de: " + a.out)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    chi_tiet, kiem_tra = phan_tich(a.dxf, a.layer_phong)
    tong = xuat_excel(chi_tiet, kiem_tra, a.out, a.du_an, a.tang, a.dxf)
    nhom = {n: round(sum(d["dt_hatch"] for d in chi_tiet if d["nhom"] == n), 4) for n in NHOM}
    print(json.dumps(dict(file_xlsx=a.out, so_hatch=len(chi_tiet), dt_theo_nhom_m2=nhom, tong_m2=round(tong, 4),
                          so_loi=sum(k[0] == "Lỗi" for k in kiem_tra),
                          so_canh_bao=sum(k[0] == "Cảnh báo" for k in kiem_tra),
                          kiem_tra=[" | ".join(map(str, k)) for k in kiem_tra[:20]]), ensure_ascii=False))


if __name__ == "__main__":
    main()

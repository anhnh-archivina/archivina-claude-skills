#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ve ket qua dien tich (ve_dien_tich_tang.json do mat_bang_tang.py xuat) THANG vao ban ve dang mo trong AutoCAD qua COM.

Chi dung khi nguoi dung yeu cau sua truc tiep tren ban ve dang mo VA ban ve do la ban sao ket qua (khong phai ban goc).
- Tao doi tuong bang API (AddLightWeightPolyline / AddText / AddMText), khong qua dong lenh: khong the treo o dau nhac
  (lenh SCRIPT qua SendCommand da tung treo vi dau "(" trong chu bi hieu la LISP, va keo AutoCAD dung >45 phut).
- Xoa truoc cac doi tuong ket qua cu theo danh sach handle (--xoa-handle), chi xoa neu nam tren layer ket qua.
- Gom mot nhom UNDO (U mot lan la tra lai), KHONG luu ban ve. Ghi handle moi ra --luu-handle de lan sau xoa dung.
- Ve xong tu gan FIELD cho nhan dien tich (gan_field_dien_tich.py): sua tay polyline -> nhan tu cap nhat. --khong-field de bo.
- --luu: luu ban ve sau khi ve (chi dung voi ban sao ket qua do chinh Claude tao/mo).

    python ve_com_tab_mo.py --ban-ve "<ten.dwg>" --json ve_dien_tich_tang.json [--xoa-handle cu.txt] [--luu-handle moi.txt] [--luu]
"""
import argparse
import json
import sys
import time

import os

import pythoncom  # noqa: F401
import win32com.client

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gan_field_dien_tich as gfd  # noqa: E402

LAYER_KQ = {"A- Dien tich phong", "Dien tich thong thuy", "A-Text"}


goi = gfd.goi


def mang(vals):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(v) for v in vals])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ban-ve", required=True, help="ten tab dang mo, vi du CT1-T5A-10_dien-tich-thong-thuy.dwg")
    ap.add_argument("--json", required=True)
    ap.add_argument("--xoa-handle", default="")
    ap.add_argument("--luu-handle", default="")
    ap.add_argument("--layer-xoa", default=",".join(sorted(LAYER_KQ)))
    ap.add_argument("--khong-field", action="store_true", help="giu nhan chu thuong, khong gan Field")
    ap.add_argument("--luu", action="store_true", help="luu ban ve sau khi ve (ban sao ket qua)")
    a = ap.parse_args()
    data = json.load(open(a.json, encoding="utf-8"))
    acad = win32com.client.GetActiveObject("AutoCAD.Application")
    if not goi(lambda: acad.GetAcadState().IsQuiescent):
        sys.exit("AutoCAD đang bận (đang chạy lệnh/script): nhấn Esc trong AutoCAD rồi chạy lại.")
    docs = goi(lambda: acad.Documents)
    doc = None
    for k in range(goi(lambda: docs.Count)):
        d = goi(lambda: docs.Item(k))
        if goi(lambda: d.Name).lower() == a.ban_ve.lower():
            doc = d
    if doc is None:
        sys.exit(f"Không thấy bản vẽ đang mở: {a.ban_ve}")
    ms = goi(lambda: doc.ModelSpace)
    goi(lambda: doc.StartUndoMark())
    so_xoa = 0
    try:
        lx = {x.strip() for x in a.layer_xoa.split(",") if x.strip()}
        if a.xoa_handle:
            for h in [t.strip() for t in open(a.xoa_handle, encoding="utf-8") if t.strip()]:
                try:
                    e = doc.HandleToObject(h)
                except pythoncom.com_error:
                    continue                                   # da xoa / khong ton tai
                if e.Layer in lx:
                    e.Delete()
                    so_xoa += 1
        layers = doc.Layers
        for ten, mau in data.get("layer", {}).items():
            try:
                ly = layers.Item(ten)
            except pythoncom.com_error:
                ly = layers.Add(ten)
                ly.color = int(mau)
        moi = []
        for o in data["doi_tuong"]:
            if o["loai"] == "pline":
                xy = [v for p in o["pts"] for v in p]
                e = goi(lambda: ms.AddLightWeightPolyline(mang(xy)))
                e.Closed = True
                e.Layer = o["layer"]
            else:
                try:
                    layers.Item(o["layer"])
                except pythoncom.com_error:
                    layers.Add(o["layer"])
                p = mang([o["x"], o["y"], 0.0])
                if o["loai"] == "mtext":
                    e = goi(lambda: ms.AddMText(p, 0.0, o["text"]))
                    e.AttachmentPoint = 5                      # giua - giua
                    e.InsertionPoint = p
                    e.StyleName = o["style"]
                    e.Height = float(o["h"])
                else:
                    e = goi(lambda: ms.AddText(o["text"], p, float(o["h"])))
                    e.StyleName = o["style"]
                    e.Height = float(o["h"])
                    e.Alignment = 10                           # acAlignmentMiddleCenter
                    e.TextAlignmentPoint = p
                if o.get("rot"):
                    import math
                    e.Rotation = math.radians(float(o["rot"]))
                e.Layer = o["layer"]
                if o.get("color") not in (None, 256, 0):
                    e.color = int(o["color"])
            moi.append(e.Handle)
        field = None if a.khong_field else gfd.gan_field(doc)
    finally:
        goi(lambda: doc.EndUndoMark())
    if a.luu_handle:
        open(a.luu_handle, "w", encoding="utf-8").write("\n".join(moi))
    if a.luu:
        goi(lambda: doc.Save())
    if field:
        field.pop("chi_tiet")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(dict(ban_ve=a.ban_ve, da_xoa=so_xoa, da_ve=len(moi), field=field, da_luu=bool(doc.Saved),
                          ghi_chu="Một nhóm UNDO: gõ U một lần để trả lại." + ("" if a.luu else " Bản vẽ chưa lưu.")),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

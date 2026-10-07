#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Gan FIELD cho nhan dien tich: nhan 'xx.x m2' / 'DTCH: xx.x m2' lien ket voi polyline da bo, sua tay polyline thi
nhan tu cap nhat (REGEN / mo / luu ban ve, theo FIELDEVAL).

- Ghep nhan <-> polyline giong kiem_tra_nhan.py: vung = polyline dong ngoai cung tren layer phong / layer can,
  polyline cung layer nam trong no la phan loai tru (cot, hop ky thuat). Nhan 'DTCH...' -> layer can, con lai -> layer phong.
- CHI gan khi so tren nhan = dien tich vung (AutoCAD .Area, lam tron nhu nhan); lech -> bao Loi, giu nguyen nhan.
- Vung khong co loai tru: %<\\AcObjProp Object(%<\\_ObjId id>%).Area \\f "%lu2%pr1%ps[tien to,hau to]%ds46%ct8[1E-06]">%
  Vung co loai tru: %<\\AcExpr (Area ngoai - Area lo 1 - ...) \\f "...">% (cong thuc, cung tu cap nhat).
  Tien to/hau to, so chu so thap phan, dau thap phan lay dung theo chu nhan dang co.
- Can AutoCAD GUI (COM). AutoCAD Core Console KHONG tao duoc Field (khong co ham vla/ActiveX).

Dung:
  python gan_field_dien_tich.py --ban-ve "<ten tab dang mo.dwg>"            # tab dang mo: 1 nhom UNDO, KHONG luu
  python gan_field_dien_tich.py --mo-file <ban_sao.dwg> [--luu-thanh <kq.dwg>]   # mo file, gan, luu, dong
In JSON (UTF-8). Ma thoat 1 neu co nhan khong gan duoc.
"""
import argparse
import io
import json
import re
import sys
import time
from decimal import Decimal, ROUND_HALF_UP

import pythoncom
import win32com.client
from shapely.geometry import Point, Polygon

RE_NHAN = re.compile(r"^(?P<truoc>.*?)(?P<so>\d+(?:[.,]\d+)?)(?P<sau>\s*(?:m2|m²|㎡).*)$", re.I | re.S)


def goi(f, *a, lan=60):
    """Goi COM, thu lai khi AutoCAD dang ban (RPC_E_CALL_REJECTED / SERVERCALL_RETRYLATER).
    Khi ban, ca buoc tra ten phuong thuc cung hong (AttributeError '<unknown>.X'): truyen lambda de thu lai ca buoc do."""
    for k in range(lan):
        try:
            return f(*a)
        except pythoncom.com_error as e:
            if e.hresult in (-2147418111, -2147417846) and k < lan - 1:
                time.sleep(0.5)
                continue
            raise
        except AttributeError:
            if k < lan - 1:
                time.sleep(0.5)
                continue
            raise


def rn(v, n):
    return float(Decimal(str(v)).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP))


def chon(doc, ten, ma, gt):
    """Selection set theo bo loc DXF (ma, gia tri)."""
    try:
        goi(lambda: doc.SelectionSets.Item(ten).Delete())
    except pythoncom.com_error:
        pass
    ss = goi(lambda: doc.SelectionSets.Add(ten))
    ft = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I2, list(ma))
    fd = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_VARIANT, list(gt))
    goi(lambda: ss.Select(5, pythoncom.Empty, pythoncom.Empty, ft, fd))       # 5 = acSelectionSetAll
    kq = [goi(lambda: ss.Item(i)) for i in range(goi(lambda: ss.Count))]
    goi(lambda: ss.Delete())
    return kq


def vung_tren_layer(doc, layer):
    pls = []
    for e in chon(doc, "DT_PL", (0, 8), ("LWPOLYLINE", layer)):
        c = list(goi(lambda: e.Coordinates))
        if len(c) < 6:
            continue
        g = Polygon(list(zip(c[0::2], c[1::2])))
        pls.append(dict(e=e, handle=goi(lambda: e.Handle), dong=bool(goi(lambda: e.Closed)), area=float(goi(lambda: e.Area)), g=g if g.is_valid else g.buffer(0)))
    vung = []
    for p in pls:
        if any(q is not p and q["g"].area > p["g"].area and q["g"].contains(p["g"]) for q in pls):
            continue
        con = [q for q in pls if q is not p and p["g"].contains(q["g"])]
        vung.append(dict(p=p, con=con, g=p["g"], dt=p["area"] - sum(q["area"] for q in con)))
    return vung


def ma_field(doc, vung, truoc, sau, n_tp, dau):
    u = goi(lambda: doc.Utility)
    fmt = f"%lu2%pr{n_tp}%ps[{truoc},{sau}]%ds{ord(dau)}%ct8[1E-06]"
    obj = lambda e: "%%<\\AcObjProp Object(%%<\\_ObjId %s>%%).Area>%%" % goi(lambda: u.GetObjectIdString(e, False))
    if not vung["con"]:
        return '%%<\\AcObjProp Object(%%<\\_ObjId %s>%%).Area \\f "%s">%%' % (goi(lambda: u.GetObjectIdString(vung["p"]["e"], False)), fmt)
    bt = "-".join(obj(x["e"]) for x in [vung["p"]] + vung["con"])
    return '%%<\\AcExpr (%s) \\f "%s">%%' % (bt, fmt)


def so_(m):
    return m.group("so")


def gan_field(doc, layer_phong="A- Dien tich phong", layer_can="Dien tich thong thuy", tieu_de="DTCH"):
    """Gan Field cho moi nhan dien tich trong doc. Tra ve dict ket qua (khong luu ban ve)."""
    vungs = {"phong": vung_tren_layer(doc, layer_phong), "can": vung_tren_layer(doc, layer_can)}
    nhans = chon(doc, "DT_NHAN", (0, 1), ("TEXT,MTEXT", "*m2*,*m²*,*㎡*"))
    loi, canh_bao, khac, da_gan = [], [], [], []
    ds = []
    for t in nhans:
        s = goi(lambda: t.TextString).strip()
        hd = goi(lambda: t.Handle)
        m = RE_NHAN.match(s)
        if not m:
            continue
        lo, hi = goi(lambda: t.GetBoundingBox())
        P = Point((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
        loai = "can" if s.upper().startswith(tieu_de.upper()) else "phong"
        vs = [v for v in vungs[loai] if v["g"].contains(P) and not any(c["g"].contains(P) for c in v["con"])]
        v = min(vs, key=lambda x: x["g"].area) if vs else None
        so = m.group("so")
        dau = "," if "," in so else "."
        n_tp = len(so.split(dau)[1]) if dau in so else 0
        dt = rn(v["dt"] / 1e6, n_tp) if v else None
        khop = v is not None and abs(float(so.replace(",", ".")) - dt) < 1e-9
        ds.append(dict(t=t, hd=hd, s=s, m=m, v=v, loai=loai, dau=dau, n_tp=n_tp, dt=dt, khop=khop,
                       vi_tri=f"{hd} '{s}' tại ({P.x:.0f}, {P.y:.0f})"))
    # nhan cua vung = nhan nam trong vung VA ghi dung so cua vung; chu khac co "m2" trong vung (ghi chu cu) bo qua
    khop_vung = {}
    for d in ds:
        if d["khop"]:
            khop_vung.setdefault(id(d["v"]), []).append(d)
    for d in ds:
        t, s, m, v = d["t"], d["s"], d["m"], d["v"]
        if v is None:
            if vungs[d["loai"]]:
                khac.append(f"{d['vi_tri']}: không nằm trong polyline nào trên layer "
                            f"'{layer_can if d['loai'] == 'can' else layer_phong}'")
            continue
        if not d["khop"]:
            if id(v) in khop_vung:
                khac.append(f"{d['vi_tri']}: chữ khác trong polyline {v['p']['handle']} (đã có nhãn đúng), bỏ qua")
            else:
                loi.append(f"{d['vi_tri']}: nhãn ghi {so_(m)}, polyline {v['p']['handle']} = {v['dt'] / 1e6:.4f} m² → "
                           f"{d['dt']}; không gán")
            continue
        if len(khop_vung[id(v)]) > 1:
            canh_bao.append(f"{d['vi_tri']}: polyline {v['p']['handle']} có {len(khop_vung[id(v)])} nhãn đúng số, không gán")
            continue
        if goi(lambda: t.ObjectName) == "AcDbMText" and re.search(r"[\{}]", s):
            canh_bao.append(f"{d['vi_tri']}: MText có mã định dạng, không gán Field")
            continue
        truoc, sau = m.group("truoc"), m.group("sau")
        if any(c in truoc + sau for c in ",[]%\\"):
            canh_bao.append(f"{d['vi_tri']}: tiền tố/hậu tố có ký tự đặc biệt, không gán")
            continue
        fc = ma_field(doc, v, truoc, sau, d["n_tp"], d["dau"])
        goi(lambda: setattr(t, "TextString", fc))
        da_gan.append(dict(nhan=d["hd"], cu=s, polyline=v["p"]["handle"], loai_tru=[c["handle"] for c in v["con"]],
                           loai=d["loai"], field=fc))
    goi(lambda: doc.Regen(1))
    lech = []
    for d in da_gan:
        moi = goi(lambda: doc.HandleToObject(d["nhan"]).TextString).strip()
        d["sau_regen"] = moi
        if moi != d["cu"]:
            lech.append(f"{d['nhan']}: trước '{d['cu']}' → Field '{moi}'")
    khong_nhan = [f"{k} {v['p']['handle']} ({v['dt'] / 1e6:.1f} m²)" for k in vungs for v in vungs[k] if id(v) not in khop_vung]
    return dict(so_vung_phong=len(vungs["phong"]), so_vung_can=len(vungs["can"]), da_gan=len(da_gan),
                gan_phong=sum(1 for d in da_gan if d["loai"] == "phong"), gan_can=sum(1 for d in da_gan if d["loai"] == "can"),
                co_cong_thuc=sum(1 for d in da_gan if d["loai_tru"]), loi=loi, canh_bao=canh_bao, chu_khac_bo_qua=khac, lech_sau_regen=lech,
                vung_khong_nhan=khong_nhan, chi_tiet=da_gan)


def tim_doc(acad, ten):
    docs = goi(lambda: acad.Documents)
    for k in range(goi(lambda: docs.Count)):
        d = goi(lambda: docs.Item(k))
        if goi(lambda: d.Name).lower() == ten.lower() or goi(lambda: d.FullName).lower() == ten.lower():
            return d
    return None


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ban-ve", help="ten tab dang mo (hoac duong dan day du)")
    g.add_argument("--mo-file", help="ban sao .dwg: mo trong AutoCAD, gan Field, luu, dong")
    ap.add_argument("--luu-thanh", default="", help="kem --mo-file: luu ra file khac (mac dinh luu de ban sao)")
    ap.add_argument("--layer-phong", default="A- Dien tich phong")
    ap.add_argument("--layer-can", default="Dien tich thong thuy")
    ap.add_argument("--tieu-de", default="DTCH")
    ap.add_argument("--chi-tiet", action="store_true", help="in ca danh sach Field da gan")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    try:
        acad = win32com.client.GetActiveObject("AutoCAD.Application")
    except pythoncom.com_error:
        if a.ban_ve:
            sys.exit("AutoCAD chưa chạy.")
        acad = win32com.client.Dispatch("AutoCAD.Application")
    if not goi(lambda: acad.GetAcadState().IsQuiescent):
        sys.exit("AutoCAD đang bận (đang chạy lệnh/script): nhấn Esc trong AutoCAD rồi chạy lại.")
    if a.ban_ve:
        doc = tim_doc(acad, a.ban_ve)
        if doc is None:
            sys.exit(f"Không thấy bản vẽ đang mở: {a.ban_ve}")
        goi(lambda: doc.StartUndoMark())
        try:
            kq = gan_field(doc, a.layer_phong, a.layer_can, a.tieu_de)
        finally:
            goi(lambda: doc.EndUndoMark())
        kq["ghi_chu"] = "Một nhóm UNDO (U một lần để trả lại). Bản vẽ chưa lưu."
    else:
        if tim_doc(acad, a.mo_file):
            sys.exit(f"File đang mở trong AutoCAD, dùng --ban-ve: {a.mo_file}")
        doc = goi(lambda: acad.Documents.Open(a.mo_file, False))
        try:
            kq = gan_field(doc, a.layer_phong, a.layer_can, a.tieu_de)
            if a.luu_thanh:
                goi(lambda: doc.SaveAs(a.luu_thanh))
            else:
                goi(lambda: doc.Save())
        finally:
            goi(lambda: doc.Close(False))
        kq["ghi_chu"] = f"Đã lưu: {a.luu_thanh or a.mo_file}"
    if not a.chi_tiet:
        kq.pop("chi_tiet")
    print(json.dumps(kq, ensure_ascii=False, indent=2))
    sys.exit(1 if kq["loi"] else 0)


if __name__ == "__main__":
    main()

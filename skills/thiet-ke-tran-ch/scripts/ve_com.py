#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Noi voi AutoCAD / AutoCAD Architecture DANG MO qua COM (pywin32) - skill thiet-ke-tran-ch.

  ban-sao  : ghi toan bo ban ve dang mo (ke ca thay doi chua luu) ra file MOI bang -WBLOCK * ; tab dang mo khong doi
             duong dan, khong bi luu. FILEDIA dat tam 0 roi tra lai gia tri cu.
  ve       : mo file DWG (ban sao) trong AutoCAD dang chay, chen thiet bi tu bo_tri_tran.json (block thu vien 1:1,
             dung layer), gom trong 1 nhom UNDO, luu ban sao. Tu choi neu file la file dang mo khac / khong phai ban sao.

    python ve_com.py ban-sao --ten-ban-ve "<ten tab .dwg>" --ra <duong dan .dwg moi, khong dau cach>
    python ve_com.py ve --dwg <ban sao .dwg> --json <bo_tri_tran.json> [--goc <duong dan file goc de tu choi>]
"""
import argparse
import json
import math
import os
import sys
import time

import pythoncom
import win32com.client

MAU = {"A-Den": 150, "A-Thiet bi PCCC": 1, "A-HVAC": 2, "A-HVAC1": 2, "A-HVAC2": 2, "A-Hoan thien tran": 8}


def goi(f, *a, lan=40):
    """AutoCAD ban (RPC_E_CALL_REJECTED) -> thu lai."""
    for i in range(lan):
        try:
            return f(*a)
        except pythoncom.com_error as e:
            if e.hresult in (-2147418111, -2147417846) and i < lan - 1:
                time.sleep(0.5)
                continue
            raise


def acad():
    return win32com.client.GetActiveObject("AutoCAD.Application")


def cho_ranh(app, toi_da=120):
    t = time.time()
    while time.time() - t < toi_da:
        try:
            if app.GetAcadState().IsQuiescent:
                return True
        except pythoncom.com_error:
            pass
        time.sleep(0.5)
    return False


def ban_sao(ten, ra):
    if " " in ra or os.path.exists(ra):
        raise SystemExit(f"Đường dẫn ra phải mới và không có dấu cách: {ra}")
    app = acad()
    doc = next((d for d in app.Documents if d.Name.lower() == ten.lower()), None)
    if doc is None:
        raise SystemExit(f"Không thấy bản vẽ '{ten}' đang mở.")
    if not cho_ranh(app):
        raise SystemExit("AutoCAD đang bận (có lệnh đang chạy): dừng lệnh rồi thử lại.")
    goi(doc.Activate)
    cu = goi(doc.GetVariable, "FILEDIA")
    goi(doc.SetVariable, "FILEDIA", 0)
    try:
        goi(doc.SendCommand, f"_.-WBLOCK\n{ra}\n*\n")
        t = time.time()
        while time.time() - t < 180 and not (os.path.exists(ra) and cho_ranh(app, 5)):
            time.sleep(1)
    finally:
        cho_ranh(app)
        goi(doc.SetVariable, "FILEDIA", cu)
    if not os.path.exists(ra):
        raise SystemExit("-WBLOCK không tạo được file.")
    return dict(ban_sao=ra, kich_thuoc=os.path.getsize(ra), tab_goc=doc.FullName, tab_goc_da_luu=bool(doc.Saved))


def diem(x, y):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, (float(x), float(y), 0.0))


def ve(dwg, js, goc=None):
    dwg = os.path.abspath(dwg)
    if goc and os.path.normcase(os.path.abspath(goc)) == os.path.normcase(dwg):
        raise SystemExit("Từ chối: đường dẫn vẽ trùng file gốc.")
    data = json.load(open(js, encoding="utf-8"))
    app = acad()
    if not cho_ranh(app):
        raise SystemExit("AutoCAD đang bận.")
    doc = next((d for d in app.Documents if os.path.normcase(d.FullName) == os.path.normcase(dwg)), None)
    if doc is None:
        doc = goi(app.Documents.Open, dwg)
    goi(doc.Activate)
    cho_ranh(app)
    goi(doc.StartUndoMark)
    n = 0
    try:
        lays = {L.Name for L in doc.Layers}
        for lay in sorted({d["layer"] for d in data["thiet_bi"]}):
            if lay not in lays:
                L = goi(doc.Layers.Add, lay)
                L.Color = MAU.get(lay, 7)
        blk = {b.Name.upper() for b in doc.Blocks}
        ms = doc.ModelSpace
        lt = data.get("layer_truc", "Defpoints")
        if lt not in lays:
            goi(doc.Layers.Add, lt)
        for t in data.get("truc", []):          # truc dat den / thiet bi: layer Defpoints (khong in)
            ln = goi(ms.AddLine, diem(t["x1"], t["y1"]), diem(t["x2"], t["y2"]))
            ln.Layer = lt
        for d in data["thiet_bi"]:
            src = d["ma"] if d["ma"].upper() in blk else os.path.join(data["thu_vien"], d["ma"] + ".dwg")
            ref = goi(ms.InsertBlock, diem(d["x"], d["y"]), src, 1.0, 1.0, 1.0, math.radians(d["rot"]))
            ref.Layer = d["layer"]
            blk.add(d["ma"].upper())
            n += 1
    finally:
        goi(doc.EndUndoMark)
    goi(doc.Regen, 1)
    goi(doc.Save)
    return dict(dwg=doc.FullName, da_chen=n, so_truc=len(data.get("truc", [])), da_luu=bool(doc.Saved))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="lenh", required=True)
    a1 = sub.add_parser("ban-sao")
    a1.add_argument("--ten-ban-ve", required=True)
    a1.add_argument("--ra", required=True)
    a2 = sub.add_parser("ve")
    a2.add_argument("--dwg", required=True)
    a2.add_argument("--json", required=True)
    a2.add_argument("--goc", default=None)
    a = ap.parse_args()
    kq = ban_sao(a.ten_ban_ve, a.ra) if a.lenh == "ban-sao" else ve(a.dwg, a.json, a.goc)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(kq, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

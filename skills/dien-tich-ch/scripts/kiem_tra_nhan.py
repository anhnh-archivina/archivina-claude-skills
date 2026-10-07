#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Kiem tra BAN SAO sau khi ve: moi nhan dien tich phai khop dung polyline chua no.

- Phong: polyline dong tren layer phong (mac dinh 'A- Dien tich phong'), tru polyline cung layer nam trong no;
  nhan 'xx.x m2' nam trong vung do phai = DT lam tron 1 so.
- Can ho: polyline dong tren layer can (mac dinh 'Dien tich thong thuy'), tru polyline cung layer nam trong no;
  nhan 'DTCH: xx.x m2' nam trong vung do phai = DT lam tron 1 so.
- Bao: nhan sai so, vung khong co nhan, vung co nhieu nhan, nhan khong nam trong vung nao.

Dung: python kiem_tra_nhan.py <ban_sao.dxf> [--layer-phong "A- Dien tich phong"] [--layer-can "Dien tich thong thuy"]
In JSON (UTF-8); ma thoat 0 neu khong co loi, 1 neu co loi.
"""
import argparse
import io
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

import ezdxf
from ezdxf import path as ezpath
from shapely.geometry import Point, Polygon

RE_SO = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|㎡)", re.I)


def r1(v):
    return float(Decimal(str(v)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def norm(s):
    return (s or "").strip().lower()


def vung_tren_layer(msp, layer):
    pls = []
    for e in msp:
        if e.dxftype() == "LWPOLYLINE" and norm(e.dxf.layer) == norm(layer):
            pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(0.5)]
            if len(pts) >= 3:
                g = Polygon(pts)
                pls.append(dict(handle=e.dxf.handle, dong=bool(e.closed), g=g if g.is_valid else g.buffer(0)))
    # polyline nam trong polyline khac cung layer = phan loai tru cua vung ngoai cung chua no
    vung = []
    for p in pls:
        cha = [q for q in pls if q is not p and q["g"].area > p["g"].area and q["g"].contains(p["g"])]
        if cha:
            continue
        con = [q for q in pls if q is not p and p["g"].contains(q["g"])]
        dt = (p["g"].area - sum(q["g"].area for q in con)) / 1e6
        vung.append(dict(handle=p["handle"], dong=p["dong"], g=p["g"], loai_tru=[q["handle"] for q in con], dt=dt))
    return vung


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf")
    ap.add_argument("--layer-phong", default="A- Dien tich phong")
    ap.add_argument("--layer-can", default="Dien tich thong thuy")
    ap.add_argument("--tieu-de", default="DTCH")
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    msp = ezdxf.readfile(a.dxf).modelspace()
    nhan = []
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT"):
            t = e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text
            m = RE_SO.search(t or "")
            if m:
                # TEXT can le (giua, phai...): diem neo la align_point; insert chi la goc trai-duoi tinh lai,
                # voi phong hep (lo gia 500 mm) goc nay co the roi ra ngoai polyline
                q = e.dxf.insert
                if e.dxftype() == "TEXT" and (e.dxf.get("halign", 0) or e.dxf.get("valign", 0)) and e.dxf.get("align_point"):
                    q = e.dxf.align_point
                nhan.append(dict(handle=e.dxf.handle, text=t.strip(), so=float(m.group(1).replace(",", ".")),
                                 can=t.strip().upper().startswith(a.tieu_de.upper()), p=Point(q.x, q.y)))
    loi, ket_qua, da_dung = [], [], set()
    for loai, layer in (("phong", a.layer_phong), ("can", a.layer_can)):
        for v in vung_tren_layer(msp, layer):
            ns = [n for n in nhan if n["can"] == (loai == "can") and v["g"].contains(n["p"])]
            dung = r1(v["dt"])
            muc = dict(loai=loai, handle=v["handle"], dt=round(v["dt"], 4), dt_lam_tron=dung,
                       loai_tru=v["loai_tru"], nhan=[(n["handle"], n["text"]) for n in ns], dat=True)
            if not v["dong"]:
                muc["dat"] = False
                loi.append(f"{loai} {v['handle']}: polyline chưa bật Closed")
            if not ns:
                muc["dat"] = False
                loi.append(f"{loai} {v['handle']} ({dung:.1f} m²): không có nhãn diện tích")
            elif len(ns) > 1:
                muc["dat"] = False
                loi.append(f"{loai} {v['handle']}: {len(ns)} nhãn trong cùng vùng")
            for n in ns:
                da_dung.add(n["handle"])
                if abs(n["so"] - dung) > 1e-6:
                    muc["dat"] = False
                    loi.append(f"{loai} {v['handle']}: nhãn {n['handle']} ghi '{n['text']}', polyline {v['dt']:.4f} m² → {dung:.1f}")
            ket_qua.append(muc)
    le = [dict(handle=n["handle"], text=n["text"]) for n in nhan if n["handle"] not in da_dung]
    print(json.dumps(dict(file=a.dxf, so_vung=len(ket_qua), so_dat=sum(1 for k in ket_qua if k["dat"]),
                          loi=loi, nhan_khong_thuoc_vung=le, chi_tiet=ket_qua), ensure_ascii=False, indent=2))
    sys.exit(1 if loi else 0)


if __name__ == "__main__":
    main()

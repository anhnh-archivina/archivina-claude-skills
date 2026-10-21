# -*- coding: utf-8 -*-
"""
KT-Mat bang lat san can ho (Archivina) - sinh script hatch lat san theo nhom phong.

  tao : doc DXF ban sao (da co polyline phong layer "A- Dien tich phong"), loc phong thuoc --nhom,
        ghi <out>.scr (doan LISP, chua QSAVE) + <out>.json (phong da hatch, phong chua phan loai).
  gop : noi cac doan .scr cua 4 nhom thanh mot file chay duoc bang ve_vao_ban_sao (them QSAVE/QUIT).

Hatch: layer A-Materials (tao neu thieu, mau 251), lien ket (HPASSOC 1), chon polyline phong + lo (HKT/cot)
nam trong. Khong doi layer/doi tuong khac. Nhom: PN DOLMIT 500/0, PK ANSI37 5000/45, WC ANSI37 2500/45,
LG ANSI37 2500/45. Diem goc (HPORIGIN) tung phong theo cua di / vung tam (phan_loai.diem_goc): DXF phai
xuat CO no doi tuong AEC (xuat_dxf no_doi_tuong_aec=true) moi thay cua.

  python tao_hatch_lat_san.py tao --dxf ban_sao.dxf --nhom PN --out D:\\kq\\hatch_PN
  python tao_hatch_lat_san.py gop --out D:\\kq\\ve_hatch_lat_san.scr D:\\kq\\hatch_PN.scr D:\\kq\\hatch_PK.scr ...
"""
import argparse
import json
import os
import sys

import ezdxf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phan_loai import (LAYER_HATCH, LAYER_PHONG, MAU_LAYER_HATCH, NHOM, diem_goc, doc_cua,  # noqa: E402
                       doc_phong, doc_sen_tam)

DAU_SCR = ["CMDECHO", "0", "OSMODE", "0"]


def _lisp_nhom(nhom, phong):
    pat, tl, goc, _ = NHOM[nhom]
    # moi phong: ((x y) "handle" "lo"...) ; diem goc nil = giu HPORIGIN hien hanh
    ds = " ".join("(%s %s)" % ("(%.1f %.1f)" % p["goc"] if p["goc"] else "nil",
                               " ".join('"%s"' % h for h in [p["handle"]] + p["lo"])) for p in phong)
    bien = "'(\"HPLAYER\" \"HPASSOC\" \"HPORIGIN\" \"HPORIGINMODE\")"
    return [
        "(defun latsan-%s (/ *error* tra cu n e ss hs)" % nhom,
        " (setq cu (mapcar 'getvar %s) n 0)" % bien,
        " (defun tra () (mapcar 'setvar %s cu))" % bien,
        " (defun *error* (m) (tra) (princ (strcat \"\\nLoi hatch %s: \" m)) (princ))" % nhom,
        " (if (not (tblsearch \"LAYER\" \"%s\"))" % LAYER_HATCH,
        "  (entmake '((0 . \"LAYER\") (100 . \"AcDbSymbolTableRecord\")"
        " (100 . \"AcDbLayerTableRecord\") (2 . \"%s\") (70 . 0) (62 . %d) (6 . \"Continuous\"))))"
        % (LAYER_HATCH, MAU_LAYER_HATCH),
        " (setvar \"HPLAYER\" \"%s\") (setvar \"HPASSOC\" 1) (setvar \"HPORIGINMODE\" 0)" % LAYER_HATCH,
        " (foreach r '(%s)" % ds,
        "  (setq hs (cdr r) ss (ssadd))",
        "  (if (car r) (setvar \"HPORIGIN\" (car r)))",
        "  (foreach h hs (if (setq e (handent h)) (ssadd e ss)))",
        "  (if (handent (car hs))",
        "   (progn (command \"_.-HATCH\" \"_P\" \"%s\" %s %s \"_S\" ss \"\" \"\")" % (pat, tl, goc),
        "    (setq n (1+ n)))))",
        " (tra)",
        " (princ (strcat \"\\nHatch %s: \" (itoa n))) (princ))" % nhom,
        "(latsan-%s)" % nhom,
    ]


def tao(a):
    nhom = a.nhom.upper()
    msp = ezdxf.readfile(a.dxf).modelspace()
    ds = doc_phong(msp, a.layer_phong)
    phong = [p for p in ds if p["nhom"] == nhom]
    cua, sen_tam = doc_cua(msp), doc_sen_tam(msp)
    for p in phong:
        p["goc"], p["ghi_chu_goc"] = diem_goc(p, ds, cua, sen_tam)
    chua =[p for p in ds if p["nhom"] is None]
    base = os.path.splitext(a.out)[0]
    os.makedirs(os.path.dirname(os.path.abspath(base)), exist_ok=True)
    with open(base + ".scr", "w", encoding="ascii") as f:
        f.write("\n".join(_lisp_nhom(nhom, phong) if phong else ["; nhom %s: khong co phong" % nhom]) + "\n")
    pat, tl, goc, mo_ta = NHOM[nhom]
    kq = dict(
        nhom=nhom, mo_ta=mo_ta, pattern=pat, ty_le=tl, goc=goc, layer=LAYER_HATCH, dxf=a.dxf,
        file_scr=base + ".scr", so_phong=len(phong), tong_dt_m2=round(sum(p["dt_m2"] for p in phong), 4),
        so_cua=len(cua), so_sen_tam=len(sen_tam),
        phong=[dict(handle=p["handle"], ten=p["ten"], lo=p["lo"], dt_m2=round(p["dt_m2"], 4),
                    diem_goc=p["goc"], ghi_chu_goc=p["ghi_chu_goc"]) for p in phong],
        chua_co_diem_goc=[dict(handle=p["handle"], ten=p["ten"], ly_do=p["ghi_chu_goc"])
                          for p in phong if not p["goc"]],
        chua_phan_loai=[dict(handle=p["handle"], ten=p["ten"], ly_do=p["ly_do"],
                             toa_do=[round(c) for c in p["poly"].representative_point().coords[0]],
                             dt_m2=round(p["dt_m2"], 4)) for p in chua],
    )
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(kq, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: kq[k] for k in ("nhom", "so_phong", "tong_dt_m2", "file_scr")}
                     | {"chua_phan_loai": len(chua), "chua_co_diem_goc": len(kq["chua_co_diem_goc"]),
                        "file_json": base + ".json"}, ensure_ascii=False))


def gop(a):
    if os.path.exists(a.out):
        sys.exit("Da ton tai, khong ghi de: " + a.out)
    L = list(DAU_SCR)
    for s in a.doan:
        with open(s, encoding="ascii") as f:
            L += f.read().splitlines()
    L += ["_.QSAVE", "_.QUIT _Y"]
    with open(a.out, "w", encoding="ascii") as f:
        f.write("\n".join(L) + "\n")
    print(json.dumps({"file_scr": a.out, "so_doan": len(a.doan)}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="lenh", required=True)
    t = sub.add_parser("tao", help="sinh doan .scr + .json cho mot nhom phong")
    t.add_argument("--dxf", required=True)
    t.add_argument("--nhom", required=True, choices=list(NHOM) + [n.lower() for n in NHOM])
    t.add_argument("--out", required=True, help="duong dan khong duoi (ghi .scr va .json)")
    t.add_argument("--layer-phong", default=LAYER_PHONG)
    g = sub.add_parser("gop", help="noi cac doan .scr thanh file ve_vao_ban_sao")
    g.add_argument("--out", required=True)
    g.add_argument("doan", nargs="+")
    a = ap.parse_args()
    tao(a) if a.lenh == "tao" else gop(a)


if __name__ == "__main__":
    main()

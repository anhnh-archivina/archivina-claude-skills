#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dung (lai) thu vien block thiet bi tran tu mot ban ve mau, bang AutoCAD Core Console chay ngam tren BAN SAO.

Moi thiet bi trong file khai bao (JSON): ma, ten, block nguon (ten trong DWG, co the co tien to xref da bind), ti le
chen that, layer dich... Script:
  1. doc DXF cua ban ve mau (ezdxf) -> tinh tam & kich thuoc that cua ky hieu (sau khi nhan ti le);
  2. tren ban sao DWG: chen block nguon tai 0,0 voi ti le that, no het long nhau, dua tam ky hieu ve 0,0 (neu goc
     block lech tam > 50 mm), doi doi tuong ben trong ve layer 0, vong phu R > 900 -> layer A-PCCC-Phu (khong in),
     tao block <MA> va WBLOCK ra <MA>.dwg (them vong R2000 cho sprinkler neu 'them_vong_phu');
  3. ghep Thu-vien-thiet-bi-tran.dwg (moi block chen tren layer dich, co nhan ma / ten / kich thuoc);
  4. doc lai, so kich thuoc tung block voi ban ve mau -> bao cao.

    python tao_thu_vien.py --dwg <ban_ve_mau.dwg> --dxf <ban_ve_mau.dxf> --khai-bao <thiet_bi.json> --out <thu muc>
File khai bao: {"thiet_bi": [{"ma": "LT-DL-D90", "ten": "...", "block_nguon": "XREF.TRAN P5$0$E1", "tien_to": "CT1-T(3-21)-Xref Tran$0$",
                "ti_le": 1.0, "layer": "A-Den", "them_vong_phu": false}, ...], "mau_layer": {"A-Den": 150, ...}}
Can MCP autocad-archivina (autocad_mcp.py) de goi accoreconsole; duong dan dat qua bien AUTOCAD_MCP_PY.
"""
import argparse
import importlib.util
import io
import json
import os
import shutil
import sys

import ezdxf
from ezdxf import bbox

MCP_PY = os.environ.get("AUTOCAD_MCP_PY", r"H:\@AI Claude Test\03-Cong-Cu\02-Python\autocad-mcp\autocad_mcp.py")


def nap_mcp():
    spec = importlib.util.spec_from_file_location("acmcp", MCP_PY)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def wc(s):
    """Mau wcmatch: ky tu ngoai ASCII -> ? (tranh loi ma hoa ten block co dau), escape ky tu dac biet."""
    out = []
    for ch in s:
        if ord(ch) >= 128:
            out.append("?")
        elif ch in "#@.*?~[]-,`":
            out.append("`" + ch)
        else:
            out.append(ch)
    return "".join(out)


def u(s):
    """Chuoi AutoLISP: ky tu co dau -> \\U+XXXX (AutoCAD tu chuyen khi nhap lenh)."""
    r = []
    for ch in s:
        if ch == '"':
            r.append('\\"')
        elif ord(ch) < 128:
            r.append(ch)
        else:
            r.append("\\U+%04X" % ord(ch))
    return "".join(r)


def phang(ents):
    for e in ents:
        if e.dxftype() == "INSERT":
            yield from phang(e.virtual_entities())
        else:
            yield e


def thong_so(dxf, ds):
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    for d in ds:
        name = d.get("tien_to", "") + d["block_nguon"]
        if name not in doc.blocks:
            raise SystemExit(f"Không thấy block nguồn '{name}' trong DXF.")
        ins = msp.add_blockref(name, (0, 0), dxfattribs={"xscale": d["ti_le"], "yscale": d["ti_le"], "zscale": d["ti_le"]})
        ents = list(phang(ins.virtual_entities()))
        core = [e for e in ents if not (e.dxf.layer.lower() == "defpoints" or (e.dxftype() == "CIRCLE" and e.dxf.radius > 900))]
        ext = bbox.extents(core)
        msp.delete_entity(ins)
        d["tam"] = [ext.center.x, ext.center.y]
        d["rong"], d["cao"] = round(ext.size.x, 1), round(ext.size.y, 1)
    return ds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dwg", required=True)
    ap.add_argument("--dxf", required=True, help="DXF xuat thuong (khong no AEC) cua chinh ban ve mau")
    ap.add_argument("--khai-bao", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    m = nap_mcp()
    kb = json.load(open(a.khai_bao, encoding="utf-8"))
    ds = thong_so(a.dxf, kb["thiet_bi"])
    os.makedirs(a.out, exist_ok=True)
    tmp = os.path.join(m.tempfile.gettempdir(), "tran_lib_" + m.uuid.uuid4().hex[:8])
    os.makedirs(tmp)
    fo = tmp.replace("\\", "/")
    L = ['(setvar "CMDECHO" 0)', '(setvar "FILEDIA" 0)', '(setvar "OSMODE" 0)', '(setvar "EXPLMODE" 1)',
         '(defun lib-new (e0 / l e) (setq e (if e0 (entnext e0) (entnext))) (while e (setq l (cons e l) e (entnext e))) l)',
         f'(defun lib-log (s / f) (setq f (open "{fo}/log.txt" "a")) (write-line s f) (close f))',
         '(defun lib-find (pat / b r) (setq b (tblnext "BLOCK" T)) (while (and b (not r)) (if (wcmatch (cdr (assoc 2 b)) pat) (setq r (cdr (assoc 2 b)))) (setq b (tblnext "BLOCK"))) (if (not r) (lib-log (strcat "KHONG THAY " pat))) r)',
         '(command "_.-LAYER" "_M" "A-PCCC-Phu" "_C" "250" "" "_P" "_N" "" "")', '(command "_.-LAYER" "_S" "0" "")',
         """(defun lib-mk (blk sc cx cy code addcov / e0 ss n e d)
  (setq e0 (entlast) blk (lib-find blk))
  (entmake (list (cons 0 "INSERT") (cons 2 blk) (cons 8 "0") (list 10 0.0 0.0 0.0) (cons 41 sc) (cons 42 sc) (cons 43 sc) (cons 50 0.0)))
  (repeat 4 (foreach e (lib-new e0) (if (and (entget e) (= (cdr (assoc 0 (entget e))) "INSERT")) (command "_.EXPLODE" e))))
  (setq ss (ssadd) n 0)
  (foreach e (lib-new e0) (if (entget e) (progn (ssadd e ss) (setq n (1+ n)))))
  (if (> n 0) (progn
    (if (or (/= cx 0.0) (/= cy 0.0)) (command "_.MOVE" ss "" (list cx cy 0.0) "0,0,0"))
    (command "_.CHPROP" ss "" "_LA" "0" "")
    (foreach e (lib-new e0) (setq d (entget e)) (if (and d (= (cdr (assoc 0 d)) "CIRCLE") (> (cdr (assoc 40 d)) 900.0)) (command "_.CHPROP" e "" "_LA" "A-PCCC-Phu" "_C" "250" "")))
    (if addcov (progn (entmake (list '(0 . "CIRCLE") '(8 . "A-PCCC-Phu") '(62 . 250) '(10 0.0 0.0 0.0) '(40 . 2000.0))) (ssadd (entlast) ss)))
    (command "_.-BLOCK" code "0,0" ss "")
    (command "_.-WBLOCK" (strcat "FOLDER/" code ".dwg") code)
    (lib-log (strcat "OK " code " " (itoa n))))
   (lib-log (strcat "RONG " code))))""".replace("FOLDER", fo)]
    for d in ds:
        cx, cy = d["tam"]
        if abs(cx) < 50 and abs(cy) < 50:
            cx = cy = 0.0
        L.append(f'(lib-mk "{wc(d.get("tien_to", "") + d["block_nguon"])}" {d["ti_le"]} {cx} {cy} "{d["ma"]}" {"T" if d.get("them_vong_phu") else "nil"})')
    work, log, _ = m._chay_accore(a.dwg, "\n".join(L + ["_.QUIT", "_Y"]) + "\n")
    shutil.rmtree(work, ignore_errors=True)
    nhat_ky = open(os.path.join(tmp, "log.txt"), encoding="utf-8", errors="replace").read() if os.path.exists(os.path.join(tmp, "log.txt")) else ""
    # ghep thu vien tong hop
    ma0 = next((d["ma"] for d in ds if os.path.exists(os.path.join(tmp, d["ma"] + ".dwg"))), None)
    if ma0 is None:
        raise SystemExit("Không tạo được block nào.\n" + nhat_ky + log[-2000:])
    M = ['(setvar "CMDECHO" 0)', '(setvar "FILEDIA" 0)', '(setvar "OSMODE" 0)', '(setvar "ATTREQ" 0)', '(command "_.ERASE" "_ALL" "")',
         '(command "_.-STYLE" "Arial" "arial.ttf" "0" "1" "0" "_N" "_N")']
    for lay, col in dict(kb.get("mau_layer", {}), **{"A-Text": 2}).items():
        M.append(f'(command "_.-LAYER" "_M" "{u(lay)}" "_C" "{col}" "" "")')
    M.append('(command "_.-LAYER" "_M" "A-PCCC-Phu" "_C" "250" "" "_P" "_N" "" "")')
    M.append(f'(defun lib-put (code lay x y) (command "_.-LAYER" "_S" lay "") (command "_.-INSERT" (strcat code "={fo}/" code ".dwg") "_S" "1" "_R" "0" (list x y 0.0)))')
    M.append('(defun lib-txt (s x y h) (command "_.-LAYER" "_S" "A-Text" "") (command "_.-TEXT" "_S" "Arial" (list x y 0.0) h "0" s))')
    M.append(f'(lib-txt "{u("THƯ VIỆN THIẾT BỊ TRẦN CĂN HỘ - ARCHIVINA (tỷ lệ 1:1, mm, chèn tỷ lệ 1)")}" 0 1500 250)')
    for i, d in enumerate(ds):
        if not os.path.exists(os.path.join(tmp, d["ma"] + ".dwg")):
            continue
        x, y = (i % 2) * 9000 + 600, -(i // 2) * 1600 - 600
        M.append(f'(lib-put "{d["ma"]}" "{u(d["layer"])}" {x} {y})')
        M.append(f'(lib-txt "{d["ma"]}" {x + 1000} {y + 60} 120)')
        M.append(f'(lib-txt "{u(d["ten"])} - {d["rong"]:g}x{d["cao"]:g} mm - layer {u(d["layer"])}" {x + 1000} {y - 160} 100)')
    M += ['(command "_.ZOOM" "_E")', '(command "_.-PURGE" "_A" "*" "_N")',
          f'(command "_.SAVEAS" "2018" "{fo}/Thu-vien-thiet-bi-tran.dwg")',
          "FILEDIA", "0", "_.DXFOUT", fo + "/Thu-vien-thiet-bi-tran.dxf", "V", "2018", "16", "_.QUIT", "_Y"]
    work, log2, _ = m._chay_accore(os.path.join(tmp, ma0 + ".dwg"), "\n".join(M) + "\n")
    shutil.rmtree(work, ignore_errors=True)
    # kiem tra lai
    kq = []
    lib = ezdxf.readfile(os.path.join(tmp, "Thu-vien-thiet-bi-tran.dxf"))
    for d in ds:
        if d["ma"] not in lib.blocks:
            kq.append(dict(ma=d["ma"], dat=False, ly_do="không có trong thư viện"))
            continue
        blk = lib.blocks.get(d["ma"])
        core = [e for e in blk if e.dxf.layer != "A-PCCC-Phu"]
        ext = bbox.extents(core)
        ok = abs(ext.size.x - d["rong"]) < 1 and abs(ext.size.y - d["cao"]) < 1 and abs(ext.center.x) < 60 and abs(ext.center.y) < 60
        kq.append(dict(ma=d["ma"], dat=ok, rong=round(ext.size.x, 1), cao=round(ext.size.y, 1), mau_rong=d["rong"], mau_cao=d["cao"],
                       vong_phu=[round(e.dxf.radius) for e in blk if e.dxf.layer == "A-PCCC-Phu"]))
    for fn in os.listdir(tmp):
        if fn.endswith((".dwg", ".dxf")):
            shutil.copy2(os.path.join(tmp, fn), os.path.join(a.out, fn))
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps(dict(nhat_ky=nhat_ky.splitlines(), kiem_tra=kq, so_dat=sum(k["dat"] for k in kq), tong=len(kq), thu_muc=a.out),
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

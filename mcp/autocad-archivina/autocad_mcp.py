#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MCP server "autocad-archivina": noi Claude voi AutoCAD / AutoCAD Architecture qua AutoCAD Core Console CHAY NGAM.

Muc dich : cho Claude doc thong tin DWG, xuat DXF (no doi tuong ACA), dung polyline thong thuy phong/can ho, ve vao
           BAN SAO va kiem tra nhan - bang cong cu MCP thay vi lenh tay.
Nguyen tac (quy tac Archivina):
  - KHONG BAO GIO sua/ghi de file DWG goc: moi lan chay deu chep DWG vao thu muc tam roi moi mo bang accoreconsole.
  - KHONG dung den AutoCAD dang mo cua nguoi dung (khong COM, khong plugin): chi chay accoreconsole.exe rieng.
  - File ket qua chi duoc tao moi, khong ghi de file da co, khong trung file nguon.
Cach dung: dang ky voi Claude Code (stdio):
    claude mcp add --scope user autocad-archivina -- "<python.exe>" "<duong dan>\autocad_mcp.py"
Bien moi truong (tuy chon): DIEN_TICH_CH_SCRIPTS = thu muc scripts cua skill dien-tich-ch;
                            ACCORECONSOLE = duong dan accoreconsole.exe; AUTOCAD_MCP_TIMEOUT = giay (mac dinh 240).
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from mcp.server.mcpserver import MCPServer

PY = sys.executable
SKILL_SCRIPTS = os.environ.get("DIEN_TICH_CH_SCRIPTS",
                               os.path.join(os.path.expanduser("~"), ".claude", "skills", "dien-tich-ch", "scripts"))
TIMEOUT = int(os.environ.get("AUTOCAD_MCP_TIMEOUT", "240"))
OUT_ROOT = os.path.join(tempfile.gettempdir(), "autocad-mcp")

mcp = MCPServer(
    "autocad-archivina",
    instructions=(
        "Cong cu AutoCAD/AutoCAD Architecture chay ngam tren BAN SAO (accoreconsole). Khong sua file goc, khong dung "
        "AutoCAD dang mo. Quy trinh do dien tich: xuat_dxf -> dung_polyline_phong -> (nguoi dung dong y) ve_vao_ban_sao "
        "-> dung_duong_bo_can_ho -> ve_vao_ban_sao -> xuat_dxf ban sao -> kiem_tra_nhan. Don vi ban ve Archivina: mm."
    ),
)


# ---------------------------------------------------------------------------------------------------------------- tien ich
def _accoreconsole():
    p = os.environ.get("ACCORECONSOLE")
    if p and os.path.isfile(p):
        return p
    found = sorted(glob.glob(r"C:\Program Files\Autodesk\AutoCAD *\accoreconsole.exe"), reverse=True)
    if not found:
        raise RuntimeError("Không tìm thấy accoreconsole.exe (AutoCAD 2022+). Đặt biến ACCORECONSOLE.")
    return found[0]


def _can_file(path, ext=None):
    path = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Không thấy file: {path}")
    if ext and not path.lower().endswith(ext):
        raise ValueError(f"Cần file {ext}: {path}")
    return path


def _file_moi(path, *nguon):
    """Duong dan file ket qua: phai la file MOI, khong trung file nguon."""
    path = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
    for n in nguon:
        if n and os.path.normcase(path) == os.path.normcase(os.path.abspath(n)):
            raise ValueError("File kết quả trùng file nguồn: không được ghi đè bản vẽ gốc.")
    if os.path.exists(path):
        raise FileExistsError(f"Đã tồn tại, không ghi đè: {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _thu_muc_ra(thu_muc):
    if thu_muc:
        d = os.path.abspath(os.path.expandvars(os.path.expanduser(thu_muc)))
    else:
        d = os.path.join(OUT_ROOT, time.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6])
    os.makedirs(d, exist_ok=True)
    return d


def _doc_txt(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8", "cp1258", "cp1252"):
        try:
            s = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        s = raw.decode("utf-8", "replace")
    # chu Viet trong DWG doi 2007+ co the ra dang \U+1EA1
    return re.sub(r"\\U\+([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), s)


def _chay_accore(dwg, scr_text, giu_ban_sao=False):
    """Chep DWG vao thu muc tam (ASCII), chay script, tra ve (thu_muc_tam). Nguoi goi tu don thu muc."""
    work = os.path.join(tempfile.gettempdir(), "acmcp_" + uuid.uuid4().hex)
    os.makedirs(work)
    src = os.path.join(work, "src.dwg")
    shutil.copy2(dwg, src)
    mtime0 = os.path.getmtime(src)
    with open(os.path.join(work, "run.scr"), "w", encoding="ascii", errors="strict", newline="\r\n") as fh:
        fh.write(scr_text.rstrip("\n") + "\n")
    p = subprocess.Popen([_accoreconsole(), "/i", src, "/s", os.path.join(work, "run.scr"), "/l", "en-US"],
                         cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        out, _ = p.communicate(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError(f"Quá {TIMEOUT} giây, đã dừng AutoCAD Core Console.")
    log = out.decode("utf-16-le", "ignore") if out[:200].count(b"\x00") > 20 else out.decode("utf-8", "ignore")
    return work, log, os.path.getmtime(src) > mtime0


def _ps(script, *args):
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(SKILL_SCRIPTS, script), *args]
    r = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT + 60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    out = r.stdout.decode("utf-8", "ignore").strip()
    err = r.stderr.decode("utf-8", "ignore").strip()
    if r.returncode != 0:
        raise RuntimeError(f"{script} lỗi: {err or out}")
    return out


def _py(script, args):
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run([PY, os.path.join(SKILL_SCRIPTS, script), *args], capture_output=True, timeout=TIMEOUT + 300, env=env)
    out = r.stdout.decode("utf-8", "ignore").strip()
    err = r.stderr.decode("utf-8", "ignore")
    err = "\n".join(l for l in err.splitlines() if "copy process ignored" not in l).strip()
    try:
        data = json.loads(out.lstrip("\ufeff")) if out else None
    except json.JSONDecodeError:
        data = None
    return dict(ma_thoat=r.returncode, ket_qua=data if data is not None else out, loi=err[-3000:] or None)


# ------------------------------------------------------------------------------------------------------------------- tools
LISP_THONG_TIN = r'''
(defun mcp-cnt (ss key / i d lst c)
  (setq lst nil i 0)
  (if ss (repeat (sslength ss) (setq d (cdr (assoc key (entget (ssname ss i))))) (if (setq c (assoc d lst)) (setq lst (subst (cons d (1+ (cdr c))) c lst)) (setq lst (cons (cons d 1) lst))) (setq i (1+ i))))
  lst)
(defun mcp-pt (p) (strcat (rtos (car p) 2 2) "," (rtos (cadr p) 2 2)))
(defun mcp-info ( / f l b s ss fl d)
  (setq f (open "OUTFILE" "w"))
  (foreach v '("INSUNITS" "LUNITS" "LUPREC" "AUNITS" "MEASUREMENT" "ACADVER" "DWGNAME" "LTSCALE" "PSLTSCALE" "CLAYER")
    (write-line (strcat "VAR|" v "|" (vl-princ-to-string (getvar v))) f))
  (write-line (strcat "VAR|EXTMIN|" (mcp-pt (getvar "EXTMIN"))) f)
  (write-line (strcat "VAR|EXTMAX|" (mcp-pt (getvar "EXTMAX"))) f)
  (setq l (tblnext "LAYER" T))
  (while l (write-line (strcat "LAYER|" (cdr (assoc 2 l)) "|" (itoa (cdr (assoc 62 l))) "|" (itoa (cdr (assoc 70 l))) "|" (cdr (assoc 6 l))) f) (setq l (tblnext "LAYER")))
  (setq b (tblnext "BLOCK" T))
  (while b (setq fl (cdr (assoc 70 b))) (if (= 4 (logand 4 fl)) (write-line (strcat "XREF|" (cdr (assoc 2 b)) "|" (vl-princ-to-string (cdr (assoc 1 b))) "|" (itoa fl)) f)) (setq b (tblnext "BLOCK")))
  (setq s (tblnext "STYLE" T))
  (while s (write-line (strcat "STYLE|" (cdr (assoc 2 s)) "|" (vl-princ-to-string (cdr (assoc 3 s))) "|" (rtos (cdr (assoc 40 s)) 2 2)) f) (setq s (tblnext "STYLE")))
  (setq s (tblnext "DIMSTYLE" T))
  (while s (write-line (strcat "DIMSTYLE|" (cdr (assoc 2 s))) f) (setq s (tblnext "DIMSTYLE")))
  (setq d (dictsearch (namedobjdict) "ACAD_LAYOUT"))
  (foreach x d (if (= (car x) 3) (write-line (strcat "LAYOUT|" (cdr x)) f)))
  (setq ss (ssget "X" '((410 . "Model"))))
  (foreach c (mcp-cnt ss 0) (write-line (strcat "TYPE|" (car c) "|" (itoa (cdr c))) f))
  (foreach c (mcp-cnt ss 8) (write-line (strcat "ONLAYER|" (car c) "|" (itoa (cdr c))) f))
  (close f) T)
(setq mcpr (vl-catch-all-apply 'mcp-info))
(if (vl-catch-all-error-p mcpr) (progn (setq f (open "ERRFILE" "w")) (write-line (vl-catch-all-error-message mcpr) f) (close f)))
'''

DON_VI = {0: "không đơn vị", 1: "inch", 2: "feet", 4: "mm", 5: "cm", 6: "m"}


@mcp.tool()
def thong_tin_dwg(duong_dan_dwg: str) -> dict:
    """Đọc thông tin một bản vẽ DWG (chỉ đọc, chạy trên bản sao tạm): đơn vị (INSUNITS/LUNITS), phạm vi bản vẽ,
    danh sách layer (màu, trạng thái tắt/đóng băng), xref (đường dẫn, đã nạp hay chưa), text style, dim style,
    layout, số đối tượng ở Model theo loại (kể cả đối tượng AutoCAD Architecture AEC_WALL/AEC_DOOR/AEC_WINDOW…)
    và theo layer. Dùng trước khi đo/soát để biết bản vẽ có đúng chuẩn mm, có tường ACA hay xref thiếu không."""
    dwg = _can_file(duong_dan_dwg, ".dwg")
    work = None
    try:
        tmp = os.path.join(tempfile.gettempdir(), "acmcp_info_" + uuid.uuid4().hex[:8])
        os.makedirs(tmp)
        outf, errf = (os.path.join(tmp, n).replace("\\", "/") for n in ("info.txt", "err.txt"))
        lisp = LISP_THONG_TIN.replace("OUTFILE", outf).replace("ERRFILE", errf)
        lines = [ln for ln in lisp.splitlines() if ln.strip()]
        work, log, _ = _chay_accore(dwg, "\n".join(lines) + "\n_.QUIT\n_Y\n")
        if not os.path.isfile(outf):
            err = _doc_txt(errf) if os.path.isfile(errf) else log[-1500:]
            raise RuntimeError("AutoCAD không ghi được thông tin: " + err)
        kq = dict(file=dwg, bien={}, layer=[], xref=[], text_style=[], dim_style=[], layout=[], doi_tuong_model={},
                  so_doi_tuong_theo_layer={})
        for ln in _doc_txt(outf).splitlines():
            p = ln.split("|")
            if p[0] == "VAR":
                kq["bien"][p[1]] = p[2]
            elif p[0] == "LAYER":
                mau, co = int(p[2]), int(p[3])
                kq["layer"].append(dict(ten=p[1], mau=abs(mau), tat=mau < 0, dong_bang=bool(co & 1), khoa=bool(co & 4),
                                        tu_xref="|" in p[1], linetype=p[4] if len(p) > 4 else ""))
            elif p[0] == "XREF":
                fl = int(p[3])
                kq["xref"].append(dict(ten=p[1], duong_dan=p[2], da_nap=bool(fl & 32), overlay=bool(fl & 8)))
            elif p[0] == "STYLE":
                kq["text_style"].append(dict(ten=p[1], font=p[2], cao=float(p[3])))
            elif p[0] == "DIMSTYLE":
                kq["dim_style"].append(p[1])
            elif p[0] == "LAYOUT":
                kq["layout"].append(p[1])
            elif p[0] == "TYPE":
                kq["doi_tuong_model"][p[1]] = int(p[2])
            elif p[0] == "ONLAYER":
                kq["so_doi_tuong_theo_layer"][p[1]] = int(p[2])
        ins = int(kq["bien"].get("INSUNITS", "0") or 0)
        kq["don_vi"] = DON_VI.get(ins, f"mã {ins}")
        kq["dung_chuan_mm"] = ins == 4 and kq["bien"].get("LUNITS") == "2"
        kq["doi_tuong_aec"] = {k: v for k, v in kq["doi_tuong_model"].items() if k.startswith("AEC_")}
        kq["xref_chua_nap"] = [x["ten"] for x in kq["xref"] if not x["da_nap"]]
        kq["so_doi_tuong_theo_layer"] = dict(sorted(kq["so_doi_tuong_theo_layer"].items(), key=lambda t: -t[1]))
        return kq
    finally:
        for d in (work, locals().get("tmp")):
            if d:
                shutil.rmtree(d, ignore_errors=True)


@mcp.tool()
def xuat_dxf(duong_dan_dwg: str, thu_muc_ra: str = "", no_doi_tuong_aec: bool = True) -> dict:
    """Xuất DWG sang DXF (DXF 2018) trên bản sao để Python đọc. Mặc định nổ từng đối tượng AutoCAD Architecture
    (Tường, Cửa đi, Cửa sổ…) trước khi xuất, vì DXF thường làm mất các đối tượng này. Trả về đường dẫn DXF và số
    đối tượng AEC trước/sau khi nổ. thu_muc_ra trống = thư mục tạm."""
    dwg = _can_file(duong_dan_dwg, ".dwg")
    out_dir = _thu_muc_ra(thu_muc_ra)
    if no_doi_tuong_aec:
        _ps("dwg_to_dxf_aec.ps1", "-Dwg", dwg, "-OutDir", out_dir)
        # script dat ten <ten dwg>.dxf trong out_dir (khong doc lai tu stdout vi PowerShell lam hong chu co dau)
        dxf = os.path.join(out_dir, os.path.splitext(os.path.basename(dwg))[0] + ".dxf")
        if not os.path.isfile(dxf):
            raise RuntimeError("Không tạo được DXF: " + dxf)
        rep = os.path.splitext(dxf)[0] + "_aec.txt"
        aec = _doc_txt(rep).splitlines() if os.path.isfile(rep) else []
        return dict(dxf=dxf, aec=aec)
    tmp = os.path.join(tempfile.gettempdir(), "acmcp_dxf_" + uuid.uuid4().hex[:8])
    os.makedirs(tmp)
    work = None
    try:
        tgt = os.path.join(tmp, "out.dxf").replace("\\", "/")
        work, log, _ = _chay_accore(dwg, f"FILEDIA\n0\n_.DXFOUT\n{tgt}\nV\n2018\n16\n_.QUIT\n_Y\n")
        if not os.path.isfile(tgt):
            raise RuntimeError("Không tạo được DXF. " + log[-1000:])
        dest = os.path.join(out_dir, os.path.splitext(os.path.basename(dwg))[0] + ".dxf")
        shutil.move(tgt, dest)
        return dict(dxf=dest, aec=[])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if work:
            shutil.rmtree(work, ignore_errors=True)


@mcp.tool()
def dung_polyline_phong(duong_dan_dxf: str, thu_muc_ra: str = "", tuy_chon: list[str] | None = None) -> dict:
    """Dựng polyline thông thủy từng phòng (layer 'A- Dien tich phong') từ DXF (skill dien-tich-ch,
    tao_polyline_phong.py). Không vẽ gì vào DWG: trả về JSON phòng dựng mới/đã có/không đóng được, đường dẫn
    ve_polyline_phong.scr, DienTichPhong.xlsx, xem_lai.png. tuy_chon: tham số thêm, ví dụ
    ["--layer-ten", "A-Dimension"], ["--them-ranh=x1,y1,x2,y2"], ["--nhan-tat-ca"], ["--lop-trat", "15"]."""
    dxf = _can_file(duong_dan_dxf, ".dxf")
    return _py("tao_polyline_phong.py", [dxf, "--out-dir", _thu_muc_ra(thu_muc_ra), *(tuy_chon or [])])


@mcp.tool()
def dung_duong_bo_can_ho(duong_dan_dxf: str, thu_muc_ra: str = "", tuy_chon: list[str] | None = None) -> dict:
    """Dựng đường bo thông thủy căn hộ (layer 'Dien tich thong thuy') + polyline loại trừ hộp kỹ thuật/cột + nhãn
    'DTCH: xx.x m2' cho từng căn trong DXF (tao_duong_bo_can_ho.py). Trả về JSON các căn, đường dẫn
    ve_duong_bo_can_ho.scr, DienTichCanHo.xlsx, ảnh xem lại. tuy_chon như dung_polyline_phong."""
    dxf = _can_file(duong_dan_dxf, ".dxf")
    return _py("tao_duong_bo_can_ho.py", [dxf, "--out-dir", _thu_muc_ra(thu_muc_ra), *(tuy_chon or [])])


@mcp.tool()
def ve_vao_ban_sao(duong_dan_dwg: str, file_scr: str, dwg_ket_qua: str) -> dict:
    """Chạy file .scr (do dung_polyline_phong / dung_duong_bo_can_ho sinh ra) trên BẢN SAO của DWG và lưu thành
    file mới dwg_ket_qua. Từ chối nếu dwg_ket_qua đã tồn tại hoặc trùng file gốc. Chỉ gọi khi người dùng đã đồng ý
    kết quả dựng polyline."""
    dwg = _can_file(duong_dan_dwg, ".dwg")
    scr = _can_file(file_scr, ".scr")
    out = _file_moi(dwg_ket_qua, dwg)
    _ps("ve_polyline_vao_dwg.ps1", "-Dwg", dwg, "-Scr", scr, "-OutDwg", out)
    return dict(dwg_ket_qua=out, da_tao=os.path.isfile(out), file_goc=dwg)


@mcp.tool()
def kiem_tra_nhan(duong_dan_dxf: str, layer_phong: str = "A- Dien tich phong",
                  layer_can: str = "Dien tich thong thuy") -> dict:
    """Kiểm tra bản sao (đã xuất DXF): mỗi polyline phòng/căn (trừ polyline loại trừ nằm trong) phải có đúng một
    nhãn diện tích ghi đúng số đã làm tròn 1 chữ số thập phân. Trả về số vùng đạt và danh sách lỗi."""
    dxf = _can_file(duong_dan_dxf, ".dxf")
    return _py("kiem_tra_nhan.py", [dxf, "--layer-phong", layer_phong, "--layer-can", layer_can])


TRAN_SCRIPTS = os.environ.get("TRAN_CH_SCRIPTS",
                              os.path.join(os.path.expanduser("~"), ".claude", "skills", "thiet-ke-tran-ch", "scripts"))


@mcp.tool()
def soat_tran(duong_dan_dxf: str, thu_muc_ra: str = "", du_an: str = "", tuy_chon: list[str] | None = None) -> dict:
    """Soát mặt bằng thiết bị trần căn hộ (skill thiet-ke-tran-ch, soat_tran.py) từ DXF đã xuất bằng xuat_dxf:
    nhận diện phòng, tủ áo, giường, thiết bị vệ sinh và thiết bị trần; kiểm tra đèn ≥1200 mm / cách tường ≥500 mm,
    tủ áo, vùng gối, trục WC, đèn thả, chồng lấn, PCCC; trả về JSON + BaoCaoSoatTran.xlsx, ảnh từng căn và
    ve_de_xuat_tran.scr (vẽ đề xuất vào bản sao: đọc nội dung file rồi gọi chay_script_tren_ban_sao)."""
    dxf = _can_file(duong_dan_dxf, ".dxf")
    args = [dxf, "--out-dir", _thu_muc_ra(thu_muc_ra)] + (["--du-an", du_an] if du_an else []) + list(tuy_chon or [])
    env_dir = SKILL_SCRIPTS
    r = subprocess.run([PY, os.path.join(TRAN_SCRIPTS, "soat_tran.py"), *args], capture_output=True, timeout=3600,
                       env=dict(os.environ, PYTHONUTF8="1", DIEN_TICH_CH_SCRIPTS=env_dir))
    out = r.stdout.decode("utf-8", "ignore").strip()
    err = "\n".join(l for l in r.stderr.decode("utf-8", "ignore").splitlines() if "copy process ignored" not in l)
    try:
        data = json.loads(out.lstrip("﻿"))
    except json.JSONDecodeError:
        data = out
    return dict(ma_thoat=r.returncode, ket_qua=data, loi=err[-3000:] or None)


def _tran_py(script, args, timeout=3600):
    r = subprocess.run([PY, os.path.join(TRAN_SCRIPTS, script), *args], capture_output=True, timeout=timeout,
                       env=dict(os.environ, PYTHONUTF8="1", DIEN_TICH_CH_SCRIPTS=SKILL_SCRIPTS))
    out = r.stdout.decode("utf-8", "ignore").strip()
    err = "\n".join(l for l in r.stderr.decode("utf-8", "ignore").splitlines() if "copy process ignored" not in l)
    try:
        data = json.loads(out.lstrip("﻿"))
    except json.JSONDecodeError:
        data = out
    return dict(ma_thoat=r.returncode, ket_qua=data, loi=err[-3000:] or None)


@mcp.tool()
def bo_tri_tran(duong_dan_dxf: str, thu_muc_ra: str = "", du_an: str = "", layer_ten_phong: str = "") -> dict:
    """BỐ TRÍ MỚI thiết bị trần cho căn hộ chưa có thiết bị (skill thiet-ke-tran-ch, bo_tri_tran.py) từ DXF bản sao:
    đèn (lưới theo trục giường / bàn ăn, WC theo trục thiết bị vệ sinh, lô gia), miệng gió cấp/hồi, quạt hút, sprinkler,
    đầu báo, lỗ thăm – thông số theo bản vẽ mẫu Archivina, PCCC/HVAC là phương án sơ bộ. Tự soát lại phương án.
    Trả về JSON + BaoCaoBoTriTran.xlsx, ảnh, bo_tri_tran.json (dùng cho ve_bo_tri_vao_ban_sao_mo) và .scr (bản sao chạy ngầm)."""
    dxf = _can_file(duong_dan_dxf, ".dxf")
    args = [dxf, "--out-dir", _thu_muc_ra(thu_muc_ra)] + (["--du-an", du_an] if du_an else []) + \
        (["--layer-ten", layer_ten_phong] if layer_ten_phong else [])
    return _tran_py("bo_tri_tran.py", args)


@mcp.tool()
def acad_dang_mo() -> dict:
    """Liệt kê bản vẽ đang mở trong AutoCAD / AutoCAD Architecture đang chạy (COM, chỉ đọc): tên, đường dẫn, đã lưu chưa."""
    import win32com.client
    app = win32com.client.GetActiveObject("AutoCAD.Application")
    return dict(phien_ban=app.Version, ban_ve=[dict(ten=d.Name, duong_dan=d.FullName, da_luu=bool(d.Saved)) for d in app.Documents],
                dang_hoat_dong=app.ActiveDocument.Name)


@mcp.tool()
def ban_sao_tu_ban_ve_dang_mo(ten_ban_ve: str, duong_dan_ra: str) -> dict:
    """Ghi toàn bộ bản vẽ ĐANG MỞ (kể cả thay đổi chưa lưu) ra file DWG MỚI bằng -WBLOCK * qua COM. Tab đang mở giữ nguyên
    đường dẫn, không bị lưu; FILEDIA đặt tạm 0 rồi trả lại. duong_dan_ra: file mới, không dấu cách (dòng lệnh AutoCAD)."""
    return _tran_py("ve_com.py", ["ban-sao", "--ten-ban-ve", ten_ban_ve, "--ra", duong_dan_ra], timeout=600)


@mcp.tool()
def ve_bo_tri_vao_ban_sao_mo(duong_dan_dwg_ban_sao: str, file_json: str, file_goc: str = "", json_cu: str = "") -> dict:
    """Mở BẢN SAO trong AutoCAD đang chạy (COM) và chèn thiết bị + trục (Defpoints) theo bo_tri_tran.json (block thư viện
    1:1, đúng layer), gom một nhóm UNDO, lưu bản sao, để mở cho người dùng xem. json_cu: bo_tri_tran.json của phương án đã
    vẽ trước trong chính file này -> xóa đúng các đối tượng đó trước khi vẽ (chỉnh lại bản sao). Từ chối nếu trùng file_goc.
    Chỉ gọi khi người dùng đồng ý."""
    args = ["ve", "--dwg", duong_dan_dwg_ban_sao, "--json", file_json] + (["--goc", file_goc] if file_goc else []) + \
        (["--xoa-cu", json_cu] if json_cu else [])
    return _tran_py("ve_com.py", args, timeout=600)


@mcp.tool()
def chay_script_tren_ban_sao(duong_dan_dwg: str, noi_dung_scr: str, dwg_ket_qua: str = "") -> dict:
    """Chạy một script AutoCAD (.scr, có thể chứa LISP dán trực tiếp) trên BẢN SAO tạm của DWG.
    - Trong script dùng chuỗi {OUT} cho thư mục ghi kết quả (ví dụ (open "{OUT}/kq.txt" "w")); mọi file .txt/.csv/
      .json ghi vào đó được trả về nội dung.
    - Không cần _.QUIT ở cuối (tự thêm). Muốn giữ bản sao đã sửa: kết thúc script bằng _.QSAVE và truyền
      dwg_ket_qua (file mới, không ghi đè, không trùng file gốc); bỏ trống = bỏ bản sao sau khi chạy.
    - (load "...lsp") bị SECURELOAD chặn: dán nội dung LISP vào script. Chỉ dùng ký tự ASCII; chữ Việt viết \\U+XXXX."""
    dwg = _can_file(duong_dan_dwg, ".dwg")
    out_path = _file_moi(dwg_ket_qua, dwg) if dwg_ket_qua else None
    tmp = os.path.join(tempfile.gettempdir(), "acmcp_out_" + uuid.uuid4().hex[:8])
    os.makedirs(tmp)
    work = None
    try:
        body = noi_dung_scr.replace("{OUT}", tmp.replace("\\", "/")).rstrip()
        if not re.search(r"_?\.?QUIT\s*\n\s*_?Y\s*$", body, re.I):
            body += "\n_.QUIT\n_Y"
        work, log, da_luu = _chay_accore(dwg, body + "\n")
        files = {}
        for fn in sorted(os.listdir(tmp)):
            fp = os.path.join(tmp, fn)
            if fn.lower().endswith((".txt", ".csv", ".json", ".log")) and os.path.getsize(fp) < 2_000_000:
                files[fn] = _doc_txt(fp)
        kq = dict(file_goc=dwg, file_ket_qua=files, nhat_ky_cuoi=log[-2500:], ban_sao_da_luu=da_luu)
        if out_path:
            if not da_luu:
                kq["canh_bao"] = "Bản sao không được lưu (script chưa có _.QSAVE?) nên không tạo dwg_ket_qua."
            else:
                shutil.copy2(os.path.join(work, "src.dwg"), out_path)
                kq["dwg_ket_qua"] = out_path
        return kq
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if work:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    mcp.run()

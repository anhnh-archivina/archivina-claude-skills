#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MCP server "revit-archivina": noi Claude voi REVIT 2026 DANG MO qua add-in ArchivinaRevitMcp (bridge\\Bridge.cs).

Muc dich : cho Claude doc du an Revit dang mo (thong tin, link Revit/CAD, phan tu, tham so, phong / vung dien tich
           kem bien, canh bao, bang thong ke, anh view), xuat DWG (mm) de dua vao pipeline AutoCAD, va - CHI KHI
           nguoi dung bat trong Revit - dat tham so phan tu.
Kien truc: Claude <-stdio-> revit_mcp.py <-TCP 127.0.0.1:9878, JSON moi dong-> ArchivinaRevitMcp.dll (trong Revit, ExternalEvent)
Nguyen tac (quy tac Archivina):
  - Mac dinh CHI DOC. Ghi (rv_dat_tham_so) bi khoa o phia Revit (tab Archivina MCP > Cho phep ghi) - Claude phai HOI
    nguoi dung truoc khi goi, va nguoi dung phai bat khoa.
  - Moi lan ghi la 1 Transaction "Claude MCP" => Ctrl+Z hoan tac. Khong luu, khong SaveAs, khong ghi de file.
  - Don vi vao/ra: dai mm, dien tich m2, the tich m3 (toa do theo goc noi bo cua Revit).
Dang ky voi Claude Code (stdio):
    claude mcp add --scope user revit-archivina -- "<python.exe>" "<duong dan>\\revit_mcp.py"
Bien moi truong (tuy chon): REVIT_MCP_PORT (mac dinh 9878), REVIT_MCP_TIMEOUT (giay cho Revit nhan lenh, mac dinh 60).
"""
import json
import os
import socket
import tempfile
import time
import uuid

from mcp.server.mcpserver import Image, MCPServer

HOST = "127.0.0.1"
PORT = int(os.environ.get("REVIT_MCP_PORT", "9878"))
TIMEOUT = float(os.environ.get("REVIT_MCP_TIMEOUT", "60"))
OUT_ROOT = os.path.join(tempfile.gettempdir(), "revit-mcp")
BUILD_PS1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build.ps1")

mcp = MCPServer(
    "revit-archivina",
    instructions=(
        "Noi voi Revit 2026 DANG MO (add-in ArchivinaRevitMcp, cong 127.0.0.1:9878). Mac dinh CHI DOC: rv_ket_noi -> "
        "rv_thong_tin (don vi, level, link Revit/CAD ~ xref, so canh bao) -> rv_liet_ke / rv_chi_tiet / rv_dang_chon -> "
        "rv_phong (Rooms/Areas, dien tich m2, bien thong thuy) -> rv_canh_bao / rv_bang_thong_ke / rv_chup_view. "
        "Xuat DWG mm cho pipeline AutoCAD: rv_xuat_dwg (thu muc moi). Ghi (rv_dat_tham_so) phai HOI nguoi dung truoc va "
        "nguoi dung phai bam 'Cho phep ghi' trong tab Archivina MCP cua Revit; Ctrl+Z hoan tac. Don vi: mm, m2. "
        "Phan tu dinh danh bang id (ElementId)."
    ),
)


# ---------------------------------------------------------------------------------------------------------------- tien ich
def _goi(cmd, cho_s=None, **params):
    """Gui 1 lenh toi add-in Revit, tra ve phan 'result'. Loi ket noi / loi phia Revit -> RuntimeError (tieng Viet)."""
    params["wait_s"] = cho_s or TIMEOUT
    req = (json.dumps({"cmd": cmd, "params": params}, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        with socket.create_connection((HOST, PORT), timeout=5) as s:
            # add-in tu huy lenh neu Revit khong nhan trong wait_s; khi da chay thi cho toi khi xong (xuat DWG co the lau)
            s.settimeout(None)
            s.sendall(req)
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(1 << 16)
                if not chunk:
                    break
                buf += chunk
    except (ConnectionRefusedError, socket.timeout, TimeoutError, OSError) as e:
        raise RuntimeError(
            f"Không kết nối được add-in Revit ({HOST}:{PORT}): {e}. Kiểm tra: (1) Revit 2026 đang mở; (2) add-in đã nạp – "
            f"có tab 'Archivina MCP' trên ribbon (chưa có: chạy {BUILD_PS1} rồi khởi động lại Revit, chọn 'Always Load' "
            f"khi Revit hỏi); (3) bấm 'Archivina MCP > Trạng thái' xem server có chạy / bị chiếm cổng {PORT} không."
        ) from e
    if not buf.strip():
        raise RuntimeError("Add-in Revit không trả lời.")
    resp = json.loads(buf.decode("utf-8"))
    if not resp.get("ok"):
        raise RuntimeError(resp.get("error", "Lỗi không rõ từ Revit"))
    return resp["result"]


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _thu_muc_moi(ten):
    d = os.path.join(OUT_ROOT, f"{ten}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}")
    return d


# ---------------------------------------------------------------------------------------------------------------- tool chi doc
@mcp.tool()
def rv_ket_noi() -> str:
    """Kiem tra ket noi toi Revit dang mo: phien ban Revit / add-in, du an dang active, cac du an dang mo, che do ghi
    dang KHOA hay MO."""
    return _json(_goi("ping"))


@mcp.tool()
def rv_thong_tin() -> str:
    """Thong tin du an Revit dang active (CHI DOC): duong dan, da sua chua luu, workshared, don vi hien thi dai/dien tich,
    Project Information, view dang mo, danh sach Level (cao do mm), Phase, so phan tu mo hinh theo category,
    link Revit (trang thai Loaded/NotFound/Unloaded, duong dan) va link/import CAD (tuong duong kiem tra xref),
    so canh bao (Warnings)."""
    return _json(_goi("info"))


@mcp.tool()
def rv_liet_ke(
    category: str = "",
    lop: str = "",
    level: str = "",
    view_id: int | None = None,
    ten_chua: str = "",
    loai_type: bool = False,
    gioi_han: int = 200,
) -> str:
    """Liet ke phan tu (CHI DOC): id, lop, category, family/type, level, vi tri (diem / 2 dau duong, mm), bbox mm,
    chieu day tuong.

    category : ten hien thi ('Walls', 'Doors', 'Rooms'...) hoac BuiltInCategory ('OST_Walls', 'OST_Doors'...).
    lop      : lop API Revit, vi du 'Wall', 'FamilyInstance', 'Floor', 'Ceiling', 'Room', 'RevitLinkInstance', 'ImportInstance'.
    level    : chi lay phan tu thuoc level nay (ten level).
    view_id  : chi lay phan tu nhin thay trong view nay.
    ten_chua : loc theo ten phan tu / ten family chua chuoi nay.
    loai_type: True = liet ke ElementType (kieu) thay vi phan tu.
    gioi_han : so phan tu toi da tra ve; 'tong_khop' cho biet tong so khop."""
    return _json(_goi(
        "list", category=category or None, **{"class": lop or None}, level=level or None,
        view_id=view_id, name_contains=ten_chua or None, types=loai_type, limit=gioi_han,
    ))


@mcp.tool()
def rv_chi_tiet(ids: list[int], tham_so_type: bool = False) -> str:
    """Chi tiet phan tu theo id (CHI DOC): tom tat + TOAN BO tham so (ten, gia tri theo mm/m2/m3/do, chuoi hien thi,
    builtin, chi doc hay khong). tham_so_type=True kem tham so cua Type."""
    return _json(_goi("element", ids=ids, type_params=tham_so_type))


@mcp.tool()
def rv_dang_chon(tham_so: bool = True, gioi_han: int = 100) -> str:
    """Cac phan tu nguoi dung DANG CHON trong Revit (CHI DOC), kem tham so. Dung cho cau hoi 'cai toi dang chon la gi'."""
    return _json(_goi("selection", params=tham_so, limit=gioi_han))


@mcp.tool()
def rv_chon(ids: list[int], zoom: bool = False) -> str:
    """Chon (highlight) phan tu tren giao dien Revit de nguoi dung xem – chi doi selection, KHONG sua mo hinh.
    zoom=True: phong to view toi cac phan tu (doi goc nhin cua nguoi dung – chi dung khi nguoi dung muon)."""
    return _json(_goi("select", ids=ids, zoom=zoom))


@mcp.tool()
def rv_phong(
    loai: str = "rooms",
    level: str = "",
    ids: list[int] | None = None,
    bien: bool = False,
    vi_tri_bien: str = "Finish",
) -> str:
    """Phong (Rooms) hoac vung dien tich (Areas) (CHI DOC): so, ten, level, dien tich m2 (theo cai dat tinh dien tich cua
    du an), chu vi mm, trang thai Not Placed / Not Enclosed, cao thong thuy, Area Scheme.

    loai       : 'rooms' hoac 'areas'.
    bien       : True = kem duong bien (list vong, toa do mm, cung da chia doan) va 'boundary_area_m2' tinh lai tu bien
                 (vong ngoai - lo) de doi chieu.
    vi_tri_bien: 'Finish' (mat hoan thien – thong thuy), 'Center' (tim tuong), 'CoreBoundary', 'CoreCenter'.
    Luu y: Room.Area cua Revit phu thuoc 'Area and Volume Computations'; doi chieu voi quy tac do Archivina (mat trat,
    HKT, lo gia...) truoc khi ket luan."""
    return _json(_goi("spatial", kind=loai, level=level or None, ids=ids or [], boundary=bien, boundary_location=vi_tri_bien))


@mcp.tool()
def rv_canh_bao(gioi_han_id: int = 20) -> str:
    """Canh bao (Warnings) cua du an, gom theo noi dung: so lan, muc do, id phan tu lien quan (CHI DOC).
    Vi du: phong chong lan, tuong trung, Room not enclosed, Room separation line chong..."""
    return _json(_goi("warnings", limit_ids=gioi_han_id))


@mcp.tool()
def rv_danh_sach_view(loai: str = "", template: bool = False) -> str:
    """Danh sach view / sheet (CHI DOC): id, ten, loai (FloorPlan, CeilingPlan, Section, DrawingSheet, Schedule...), level,
    ti le, view template, so sheet va view dat tren sheet. loai: loc theo ViewType; template=True liet ke view template."""
    return _json(_goi("views", type=loai or None, templates=template))


@mcp.tool()
def rv_bang_thong_ke(id: int | None = None, ten: str = "", so_dong_toi_da: int = 2000) -> str:
    """Bang thong ke (Schedule) (CHI DOC). Khong truyen id/ten -> liet ke cac bang. Co id hoac ten -> tra noi dung
    (header + body, moi dong la list o chu dung nhu hien thi tren Revit) de doi chieu dien tich / so luong."""
    return _json(_goi("schedule", id=id, name=ten or None, max_rows=so_dong_toi_da))


@mcp.tool()
def rv_khoi_luong(category: str = "OST_Walls", level: str = "", tung_phan_tu: bool = False) -> str:
    """Khoi luong theo category (mac dinh tuong), loc theo level, gom theo 'Family : Type' (CHI DOC): so luong, chieu dai m,
    dien tich m2, the tich m3 (tham so tinh san cua Revit: CURVE_ELEM_LENGTH / HOST_AREA_COMPUTED / HOST_VOLUME_COMPUTED),
    chieu day tuong mm. tung_phan_tu=True kem tung phan tu (id, dai, cao, dien tich, the tich, ket cau hay khong).
    Luu y: dien tich / the tich la gia tri Revit sau khi cat giao (tru lo cua), khong tru theo quy tac do boc tach rieng."""
    return _json(_goi("quantities", category=category, level=level or None, items=tung_phan_tu))


@mcp.tool()
def rv_chup_view(view_id: int | None = None, rong: int = 1600) -> Image:
    """Xuat anh PNG cua 1 view (mac dinh view dang mo) bang ExportImage – khong doi view / khong sua mo hinh.
    Anh ghi vao thu muc tam moi."""
    r = _goi("screenshot", cho_s=120, view_id=view_id, folder=_thu_muc_moi("anh"), width=rong)
    return Image(path=r["path"])


@mcp.tool()
def rv_xuat_dwg(view_ids: list[int] | None = None, thu_muc: str = "", ten: str = "rv", setup: str = "", gop_view: bool = True) -> str:
    """Xuat view / sheet ra DWG don vi MILIMET (TargetUnit = mm) vao thu muc MOI (tu choi neu thu muc da co file).
    view_ids: mac dinh view dang mo. thu_muc: de trong = thu muc tam. setup: ten DWG export setup cua du an (ket qua tra
    ve 'setups_co_san'). gop_view=True: gop view tham chieu vao 1 file (khong tao xref).
    File DWG xuat ra dung tiep voi MCP autocad-archivina (thong_tin_dwg, xuat_dxf, dung_polyline_phong...)."""
    folder = os.path.abspath(thu_muc) if thu_muc else _thu_muc_moi("dwg")
    return _json(_goi("export_dwg", cho_s=120, view_ids=view_ids or [], folder=folder, name=ten,
                      setup=setup or None, merged=gop_view))


# ---------------------------------------------------------------------------------------------------------------- tool ghi (khoa o Revit)
@mcp.tool()
def rv_dat_tham_so(muc: list[dict]) -> str:
    """DAT THAM SO phan tu trong Revit dang mo (GHI – phai HOI nguoi dung truoc; nguoi dung phai bam 'Cho phep ghi' trong
    tab Archivina MCP, neu khoa se bao loi). Tat ca trong 1 Transaction "Claude MCP - dat tham so" => Ctrl+Z hoan tac;
    muc nao loi thi bo qua, khong muc nao thanh cong thi RollBack. Khong luu file.

    muc: [{"id": 12345, "param": "Comments", "value": "..."}, ...]
      param: ten tham so (nhu tren Properties) hoac BuiltInParameter ('ALL_MODEL_INSTANCE_COMMENTS', 'ROOM_NAME'...).
      value: so -> theo mm / m2 / m3 / do voi tham so do luong; chuoi -> dat bang SetValueString (theo don vi du an)
             voi tham so so thuc, hoac gia tri chuoi. Ket qua tra 'truoc' / 'sau' tung muc."""
    return _json(_goi("set_params", items=muc))


if __name__ == "__main__":
    mcp.run()

# MCP server `autocad-archivina`

Nối Claude Code với AutoCAD / AutoCAD Architecture (2022+) bằng **AutoCAD Core Console chạy ngầm trên bản sao**.
Không sửa file DWG gốc, không đụng các bản vẽ đang mở trong AutoCAD.

## Công cụ
| Công cụ | Việc | Ghi file? |
|---|---|---|
| `thong_tin_dwg` | Đơn vị, phạm vi, layer, xref (đã nạp chưa), text/dim style, layout, số đối tượng theo loại (kể cả AEC_WALL/DOOR/WINDOW) và theo layer | Không |
| `xuat_dxf` | DWG → DXF 2018, mặc định nổ đối tượng AutoCAD Architecture | DXF mới |
| `dung_polyline_phong` | Dựng polyline thông thủy phòng (skill `dien-tich-ch`) | .scr, .xlsx, .png |
| `dung_duong_bo_can_ho` | Dựng đường bo căn hộ, loại trừ, nhãn DTCH | .scr, .xlsx, .png |
| `ve_vao_ban_sao` | Chạy .scr trên bản sao, lưu DWG **mới** (từ chối ghi đè/trùng gốc) | DWG mới |
| `kiem_tra_nhan` | Mọi nhãn diện tích khớp polyline chứa nó | Không |
| `chay_script_tren_ban_sao` | Chạy script/LISP tùy ý trên bản sao tạm; `{OUT}` = thư mục trả kết quả | Tùy chọn DWG mới |

## Cài đặt (đã làm trên máy này, phạm vi user)
```
claude mcp add autocad-archivina --scope user -e "DIEN_TICH_CH_SCRIPTS=C:\Users\Admin\.claude\skills\dien-tich-ch\scripts" -e "PYTHONUTF8=1" -- "<python.exe>" "<thư mục này>\autocad_mcp.py"
```
Yêu cầu: Python 3.10+ có `mcp` (SDK 2.x), `ezdxf`, `shapely`, `openpyxl`, `matplotlib`; skill `dien-tich-ch`; AutoCAD 2022+.
Biến tùy chọn: `ACCORECONSOLE` (đường dẫn accoreconsole.exe), `AUTOCAD_MCP_TIMEOUT` (giây, mặc định 240).
Gỡ: `claude mcp remove autocad-archivina -s user`.

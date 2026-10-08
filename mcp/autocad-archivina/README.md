# MCP server `autocad-archivina`

Nối Claude Code với AutoCAD / AutoCAD Architecture (2022+) bằng **AutoCAD Core Console chạy ngầm trên bản sao**,
và (từ 05/10/2026) với **AutoCAD đang mở** qua COM (pywin32) để lấy bản sao bản vẽ đang mở và vẽ vào bản sao mở trong
AutoCAD. Không sửa / không lưu file DWG gốc.

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
| `soat_tran` | Soát mặt bằng thiết bị trần từ DXF (skill `thiet-ke-tran-ch`; biến `TRAN_CH_SCRIPTS` nếu skill không ở `~\.claude\skills`) | .xlsx, .png, .scr |
| `bo_tri_tran` | Bố trí mới thiết bị trần (đèn, gió, PCCC sơ bộ, lỗ thăm) cho căn chưa có thiết bị, tự soát lại | .xlsx, .png, .json, .scr |
| `bo_tri_o_cam` | Bố trí mới mặt bằng cấp điện ổ cắm theo nội thất (skill `cap-dien-ch`, `cap_dien.py bo-tri`; biến `CAP_DIEN_CH_SCRIPTS`). **Phải hỏi người dùng số ổ mặt bếp, máy rửa bát, lò nướng trước**; `can_hoi` / thiếu nội thất → hỏi rồi chạy lại; chỉ vẽ `ve_o_cam.scr` bằng `ve_vao_ban_sao` khi người dùng đồng ý | .xlsx, .png, .json, .scr |
| `soat_o_cam` | Soát mặt bằng cấp điện ổ cắm đã vẽ so với phương án theo nguyên tắc (`cap_dien.py soat`) | .xlsx, .png, .json |
| `acad_dang_mo` | Liệt kê bản vẽ đang mở trong AutoCAD đang chạy (COM, chỉ đọc) | Không |
| `ban_sao_tu_ban_ve_dang_mo` | `-WBLOCK *` bản vẽ đang mở (kể cả chưa lưu) ra file mới; tab gốc không đổi | DWG mới |
| `ve_bo_tri_vao_ban_sao_mo` | Mở bản sao trong AutoCAD đang chạy, chèn thiết bị theo `bo_tri_tran.json`, 1 nhóm UNDO, lưu bản sao | Bản sao |

## Cài đặt (đã làm trên máy này, phạm vi user)
```
claude mcp add autocad-archivina --scope user -e "DIEN_TICH_CH_SCRIPTS=C:\Users\Admin\.claude\skills\dien-tich-ch\scripts" -e "PYTHONUTF8=1" -- "<python.exe>" "<thư mục này>\autocad_mcp.py"
```
Yêu cầu: Python 3.10+ có `mcp` (SDK 2.x), `ezdxf`, `shapely`, `openpyxl`, `matplotlib`; skill `dien-tich-ch` (và `thiet-ke-tran-ch`, `cap-dien-ch` cho công cụ trần / ổ cắm); AutoCAD 2022+.
Biến tùy chọn: `TRAN_CH_SCRIPTS`, `CAP_DIEN_CH_SCRIPTS` (thư mục scripts của skill nếu không ở `~\.claude\skills`), `ACCORECONSOLE` (đường dẫn accoreconsole.exe), `AUTOCAD_MCP_TIMEOUT` (giây, mặc định 240).
Gỡ: `claude mcp remove autocad-archivina -s user`.

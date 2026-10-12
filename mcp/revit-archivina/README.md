# MCP `revit-archivina` – nối Claude với Revit 2026 đang mở

```
Claude ⇄ (stdio) revit_mcp.py ⇄ (TCP 127.0.0.1:9878, JSON mỗi dòng) ⇄ addin\ArchivinaRevitMcp.dll (loader trong Revit, ExternalEvent)
                                                                   └─ nạp nóng addin\core\ArchivinaRevitMcp.Core.dll (các lệnh)
```
- `bridge\Bridge.cs` – **loader**: ribbon, server TCP, ExternalEvent. Đổi loader phải đóng Revit: `build.ps1 -Loader`.
- `core\Commands.cs` (đọc, đặt tham số), `core\Modeling.cs` (dựng mô hình), `core\Safety.cs` (**chốt chặn file gốc**) – **các lệnh**. Build lại bằng `build.ps1` (không tham số) khi Revit đang mở; lệnh kế tiếp tự nạp bản mới (AssemblyLoadContext riêng, đọc bytes – không khoá file).
- Lưu ý kỹ thuật: Revit 2026 tắt serializer JSON phản chiếu → `JsonSerializerOptions` phải có `TypeInfoResolver = new DefaultJsonTypeInfoResolver()`. `build.ps1` phải lưu UTF-8 **có BOM** (PowerShell 5.1).

## Cài đặt (đã làm 12/10/2026)
1. **Add-in** (.NET 8). Lần đầu (đóng Revit): `powershell -ExecutionPolicy Bypass -File build.ps1 -Loader` – biên dịch loader + core, ghi manifest.
   Dùng .NET SDK 8 cài riêng user tại `%LOCALAPPDATA%\Microsoft\dotnet-sdk\` (máy khác: cài SDK 8, sửa `-Dotnet` / `-RevitDir`).
   Manifest: `%APPDATA%\Autodesk\Revit\Addins\2026\ArchivinaRevitMcp.addin`.
2. **Khởi động lại Revit** → Revit hỏi add-in chưa ký → chọn **Always Load**. Ribbon có tab **Archivina MCP**.
3. **MCP** (phạm vi user) đã đăng ký:
   `claude mcp add --scope user revit-archivina -e PYTHONUTF8=1 -- "<python.exe>" "<thư mục>\revit_mcp.py"` → mở phiên Claude mới.

## Công cụ
| Tool | Loại | Việc |
|---|---|---|
| `rv_ket_noi` | đọc | ping, phiên bản, dự án đang mở, trạng thái khoá ghi |
| `rv_thong_tin` | đọc | đường dẫn, đơn vị, Project Info, level, phase, số phần tử theo category, **link Revit / CAD (≈ xref)**, số cảnh báo |
| `rv_liet_ke` | đọc | lọc theo category / lớp / level / view / tên; vị trí, bbox mm |
| `rv_chi_tiet` | đọc | toàn bộ tham số phần tử (mm / m² / m³ / độ) |
| `rv_dang_chon` | đọc | phần tử đang chọn |
| `rv_chon` | giao diện | highlight phần tử (không sửa mô hình) |
| `rv_phong` | đọc | Rooms / Areas: diện tích m², chu vi, Not Placed / Not Enclosed, biên Finish / Center + diện tích tính lại từ biên |
| `rv_canh_bao` | đọc | Warnings gom nhóm, kèm id phần tử |
| `rv_danh_sach_view` | đọc | view / sheet / template |
| `rv_khoi_luong` | đọc | khối lượng theo category + level, gom Family : Type; cấu tạo lớp tường; từng phần tử: thể tích / diện tích **theo vật liệu** (gạch / vữa, sau giao cắt, đã trừ lỗ), số cửa gắn trên tường |
| `rv_bang_thong_ke` | đọc | nội dung Schedule (đối chiếu bảng thống kê) |
| `rv_chup_view` | file mới | PNG của view (ExportImage) |
| `rv_xuat_dwg` | file mới | DWG **mm** vào thư mục mới → dùng tiếp MCP `autocad-archivina` |
| `rv_mo_file` | mở | mở file `.rvt` và kích hoạt (không sửa / không lưu); từ chối file workshared |
| `rv_luu_ban_sao` | file mới | SaveAs dự án đang mở ra `.rvt` MỚI (không ghi đè, không vào `02-Ban-Ve-Goc`) → Revit làm việc trên bản sao |
| `rv_dat_tham_so` | **ghi (khoá, bản sao)** | đặt tham số, 1 Transaction |
| `rv_tao_du_an` | **ghi (khoá)** | dự án mới từ template (mặc định `DefaultMetric.rte` hoặc `REVIT_MCP_TEMPLATE`), đơn vị **mm / m²** → `.rvt` mới, ghi sổ "Claude tạo" |
| `rv_dung_can_ho` | **ghi (khoá, bản sao)** | dựng level, tường, cột, cửa, vách kính, sàn, phòng theo spec JSON (mm), 1 TransactionGroup |
| `rv_tao_view_3d` | **ghi (khoá, bản sao)** | view 3D isometric |
| `rv_ve_2d` | **ghi (khoá, bản sao)** | nét chi tiết 2D + Detail Group |

## An toàn – không sửa / ghi đè dữ liệu gốc (12/10/2026, core 1.4.0)
- Mặc định **chỉ đọc**. Ghi chỉ chạy khi người dùng bấm **Archivina MCP > Cho phép ghi** (mỗi lần mở Revit lại về khoá).
- **Chốt chặn file gốc** (`core\Safety.cs`): lệnh ghi chỉ chạy khi dự án đang mở là **bản sao**:
  file do Claude tạo (`rv_tao_du_an`) hoặc lưu ra (`rv_luu_ban_sao`) – sổ `%LOCALAPPDATA%\ArchivinaRevitMcp\ban_sao.txt`;
  hoặc nằm trong `…\03-Ban-Sao-Lam-Viec\`, `03-Cong-Cu\05-Skill-Test\`, thư mục tạm; hoặc dự án mới chưa lưu.
  File trong `02-Ban-Ve-Goc\`, `@Archivina 2026\`… bị **từ chối** → `rv_luu_ban_sao` trước. Trạng thái: `rv_ket_noi` → `du_an_dang_mo`.
- Không bao giờ `Save` file đang mở; `SaveAs` chỉ ra file **mới** (`OverwriteExistingFile = false`); xuất ảnh / DWG từ chối thư mục đã có file.
- Phần tử Claude tạo được **đánh dấu** (Extensible Storage trên Project Information) → `delete` / `flip` chỉ tác dụng lên phần tử đã đánh dấu.
- Trên dự án không do Claude tạo: **không** đổi tên / cao độ / xoá level có sẵn, **không** đổi tên family, **không** sửa kiểu tường / sàn / cửa / vật liệu có sẵn trùng tên – báo trong `canh_bao`.
  Dự án do Claude tạo: chỉ xoá level template **không còn phần tử**.
- Cảnh báo Revit trong lệnh dựng được ghi vào kết quả (`canh_bao`), không xoá im lặng.
- Mỗi lệnh ghi là 1 Transaction / TransactionGroup "Claude MCP …" → `Ctrl+Z`.
- Cổng chỉ nghe `127.0.0.1`. Tắt: **Archivina MCP > Server**.
- Lệnh chạy qua ExternalEvent: Revit đang mở hộp thoại / đang trong lệnh thì chờ; quá 60 s chưa nhận → lệnh bị **huỷ** (không chạy muộn).

## Đã kiểm tra (12/10/2026, Revit 2026.0 build 26.0.4.409)
- File `6.SAPA-A-SDV2.rvt`: `rv_ket_noi`, `rv_thong_tin`, `rv_liet_ke`, `rv_khoi_luong`, nạp nóng core.
- **Chốt chặn file gốc (core 1.4.1) – 20/20 đạt**, trên file thử `05-Skill-Test\ket-qua-Safety-Revit\` (file gốc giả lập trong
  `02-Ban-Ve-Goc\`): từ chối `rv_dat_tham_so` / `rv_dung_can_ho` / `rv_tao_view_3d` trên file gốc; `rv_luu_ban_sao` mặc định vào
  `03-Ban-Sao-Lam-Viec\`, từ chối lưu vào `02-Ban-Ve-Goc` / trùng tên; trên bản sao: từ chối xoá level có sẵn (rollback toàn bộ),
  giữ nguyên cao độ level có sẵn, xoá được phần tử Claude dựng; file gốc **không đổi SHA-256**.
- **Tool đọc (core 1.4.2) – 13/13 đạt** trên phòng thử 4000 × 3000: `rv_phong` (Finish 12,0 m², tim tường 12,71 m², biên khớp),
  `rv_canh_bao`, `rv_danh_sach_view`, `rv_bang_thong_ke` (liệt kê), `rv_chi_tiet`, `rv_chon`, `rv_dang_chon`, `rv_chup_view`,
  `rv_xuat_dwg` (DWG `INSUNITS=4`, `LUNITS=2` – đúng chuẩn mm; từ chối thư mục đã có file); `rv_tao_du_an` ra Metric, mm / m².

## Chưa kiểm tra
- `rv_bang_thong_ke` đọc nội dung (dự án thử không có Schedule); `rv_luu_ban_sao` trên dự án có thay đổi chưa lưu / workshared (chỉ có nhánh từ chối trong code).
- `rv_phong`: `Room.Area` theo cài đặt *Area and Volume Computations* của dự án – chưa đối chiếu với quy tắc đo Archivina.

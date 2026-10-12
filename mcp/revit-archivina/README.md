# MCP `revit-archivina` – nối Claude với Revit 2026 đang mở

```
Claude ⇄ (stdio) revit_mcp.py ⇄ (TCP 127.0.0.1:9878, JSON mỗi dòng) ⇄ addin\ArchivinaRevitMcp.dll (loader trong Revit, ExternalEvent)
                                                                   └─ nạp nóng addin\core\ArchivinaRevitMcp.Core.dll (các lệnh)
```
- `bridge\Bridge.cs` – **loader**: ribbon, server TCP, ExternalEvent. Đổi loader phải đóng Revit: `build.ps1 -Loader`.
- `core\Commands.cs` – **các lệnh**. Build lại bằng `build.ps1` (không tham số) khi Revit đang mở; lệnh kế tiếp tự nạp bản mới (AssemblyLoadContext riêng, đọc bytes – không khoá file).
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
| `rv_dat_tham_so` | **ghi (khoá)** | đặt tham số, 1 Transaction |

## An toàn
- Mặc định **chỉ đọc**. Ghi chỉ chạy khi người dùng bấm **Archivina MCP > Cho phép ghi** (mỗi lần mở Revit lại về khoá).
- Mỗi lần ghi là 1 Transaction "Claude MCP – đặt tham số" → `Ctrl+Z`. Không Save / SaveAs; xuất ảnh / DWG từ chối thư mục đã có file.
- Cổng chỉ nghe `127.0.0.1`. Tắt: **Archivina MCP > Server**.
- Lệnh chạy qua ExternalEvent: Revit đang mở hộp thoại / đang trong lệnh thì chờ; quá 60 s chưa nhận → lệnh bị **huỷ** (không chạy muộn).

## Đã kiểm tra (12/10/2026, Revit 2026.0 build 26.0.4.409, file `6.SAPA-A-SDV2.rvt`)
- `rv_ket_noi`, `rv_thong_tin`, `rv_liet_ke`, `rv_khoi_luong`, nạp nóng core – chạy đúng.

## Chưa kiểm tra
- `rv_phong`, `rv_canh_bao`, `rv_bang_thong_ke`, `rv_danh_sach_view`, `rv_chup_view`, `rv_xuat_dwg`, `rv_dat_tham_so` chưa chạy thử.
- `rv_phong`: `Room.Area` theo cài đặt *Area and Volume Computations* của dự án – chưa đối chiếu với quy tắc đo Archivina.

---
name: dien-tich-ch
description: 'Dien tich CH – Dựng polyline bo diện tích thông thủy từng phòng và đường bo cả căn hộ (layer "Dien tich thong thuy", nhãn "DTCH: xx.x m2" là Field) từ mặt bằng căn hộ AutoCAD (.dwg/.dxf, kể cả đối tượng AutoCAD Architecture), xuất Excel, vẽ vào BẢN SAO. Dùng khi người dùng nhờ bo/vẽ/tạo polyline phòng hoặc đường bo căn hộ, đo diện tích từng phòng hay cả căn, "bo thông thủy", "DTCH", layer "A- Dien tich phong", hoặc soát polyline nhân viên đã bo có đúng nét hoàn thiện không. Cũng dùng cho MẶT BẰNG TẦNG nhiều căn (xref căn đã bind, mã CHxx ngoài cửa vào). Chỉ đối chiếu số liệu với bảng thống kê/hợp đồng thì dùng do-dien-tich-thong-thuy.'
---

# Dien tich CH – Diện tích thông thủy phòng và căn hộ (Archivina)

Từ mặt bằng căn hộ: (1) dựng polyline đóng kín thông thủy từng phòng, (2) dựng đường bo cả căn, (3) ghi nhãn diện tích lấy đúng từ polyline vừa vẽ (là **Field**), (4) mở lại bản sao kiểm từng nhãn. Người dùng là Phó TGĐ, kiến trúc sư: báo kết quả và điểm cần quyết định trước, ngắn gọn.

## Chọn luồng, chỉ đọc file cần dùng
| Tình huống | Đọc |
|---|---|
| Một căn hộ (hoặc vài căn thô, bản vẽ chi tiết căn) | `references/luong-can-don.md` |
| Mặt bằng tầng, xref căn đã bind, mã `CHxx` ngoài cửa | `references/luong-mat-bang-tang.md` (+ `quy-uoc-mat-bang-tang.md` mục 1, 3) |
| Sau bước vẽ cuối, mọi luồng | `references/field-va-kiem-tra.md` |
| Hỏi/gặp hình dạng lạ (cạnh xiên, kính ngoài tường, WC, đầu tường, lô gia) | `references/chinh-hinh.md` |
| Tình huống lạ khác, cần lý do/số liệu kiểm chứng | `references/quy-uoc-ve-polyline-phong.md`, `references/quy-tac-do.md` |

Không đọc script `.py` để hiểu cách dùng: chạy `--help` hoặc theo file luồng.

## Công cụ
- **Ưu tiên MCP `autocad-archivina`** (`xuat_dxf` → `dung_polyline_phong` → `ve_vao_ban_sao` → `dung_duong_bo_can_ho` → `ve_vao_ban_sao` → `xuat_dxf` bản sao → `kiem_tra_nhan`). Luồng mặt bằng tầng và gắn Field chạy script trong `<skill>\scripts\` (`<skill>` = "Base directory for this skill").
- `<python>`: `C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe` (ezdxf, shapely, openpyxl, matplotlib), `PYTHONUTF8=1`. AutoCAD `accoreconsole.exe` tự tìm trong `C:\Program Files\Autodesk\AutoCAD *\`.
- **Luôn chuyển DWG sang DXF bằng bản có nổ AEC** (`xuat_dxf` hoặc `dwg_to_dxf_aec.ps1`); DXF xuất thường làm mất Tường/Cửa ACA.

## Nguyên tắc
- **Không sửa DWG gốc**: đọc bản sao, vẽ vào bản sao mới (file gốc là bản nhân viên nộp).
- **Không đụng tab AutoCAD đang mở.** Việc chạy ngầm bằng Core Console; riêng gắn Field mở **bản sao kết quả** thành tab mới qua COM.
- **Không tự đoán đường đóng ranh** khi khe hở > 1,2 m hoặc cạnh không có nét: dừng, báo tọa độ kèm hình, hỏi. Chỉ vẽ sau khi người dùng đồng ý.
- Layer phòng **`A- Dien tich phong`** (giữ dấu cách, màu 222); layer đường bo căn **`Dien tich thong thuy`** (màu 6). Nhãn **1 chữ số thập phân**, bằng diện tích chính hình vẽ ra (đường bo − loại trừ), làm tròn 0,05 → 0,1.

## Đường bo bám nét nào (chốt 05/10/2026)
Chỉ bám nét **đã vẽ**: (1) tường Wall ACA sau khi nổ (`A-Wall`, `A-Vua trat`); (2) polyline bo cột (`A-Column`); (3) nét/polyline lớp hoàn thiện vữa (`A-Vua trat`), lan can/biên (`A-Line`); (4) nét bao khung cửa sổ/cửa đi nằm **trong chiều dày tường** (layer `A-Door`, `A-Window`, `A-Glaz`, `A-Cửa`; đổi bằng `--layer-cua`), **bỏ cánh mở và cung quay**.
- **Lớp trát:** có vẽ (`A-Vua trat` cách `A-Wall` 15 mm) thì bám nét vữa. **Không vẽ** thì **không lùi 15 mm**; script ghi Gợi ý "Lớp trát". Chỉ dùng `--lop-trat 15` khi người dùng yêu cầu rõ.
- **Chỉnh hình** (mặc định bật, `--khong-chinh-hinh` để tắt): nắn xiên thành bậc vuông, bỏ gai/khấc ≤ 60 mm, cắt kính lồi ngoài mặt tường, WC trừ ốp 10 mm, đầu tường (cạnh ≤ 350 mm) chưa trát lùi 15 mm, lô gia đo tới mặt trong bậu. Chi tiết: `references/chinh-hinh.md`.
- Chỉ **tự đóng ô cửa ≤ 1,2 m** (mặt bằng tầng: ô mở ≤ 2,6 m theo luồng B).

## Báo cáo cho người dùng
Bảng phòng (tên, m² 1 số lẻ, trạng thái dựng mới / đã có / không đóng được), việc cần quyết định, đường dẫn bản sao DWG + Excel; nêu **đã kiểm tra thực tế** (mở lại bản sao, đo, `kiem_tra_nhan` đạt x/y) và **chưa kiểm tra** (xref chưa mở, vùng chưa đối chiếu). Lỗi/Cảnh báo/Gợi ý ghi theo: file – tầng – căn/phòng – mô tả – mức độ.

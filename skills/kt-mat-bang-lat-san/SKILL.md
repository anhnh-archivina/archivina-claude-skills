---
name: kt-mat-bang-lat-san
description: KT-Mặt bằng lát sàn căn hộ – Điều phối dựng mặt bằng lát sàn căn hộ Archivina từ mặt bằng AutoCAD (.dwg, mm) bằng các subagent – (1) do-dien-tich (opus) dựng polyline thông thủy từng phòng theo skill dien-tich-ch, (2) 4 agent sonnet sinh hatch theo nhóm phòng – phòng ngủ DOLMIT 500, phòng khách/bếp/ăn ANSI37 5000 45°, WC/kho và ban công/lô gia ANSI37 2500 45° – layer A-Materials, điểm gốc hatch theo cửa đi / góc phòng tắm, (3) agent haiku gán nhãn Field diện tích, (4) agent haiku lập Excel tổng diện tích lát theo loại phòng; vẽ vào BẢN SAO. Dùng khi người dùng nhờ làm/vẽ/hatch mặt bằng lát sàn, mặt bằng hoàn thiện sàn, thống kê diện tích lát gạch/sàn căn hộ, kể cả khi không nhắc tên skill.
---

# KT-Mặt bằng lát sàn căn hộ

Phiên chính (em) **điều phối**, mỗi bước giao một subagent (subagent không gọi được subagent khác). Gọi người dùng là **anh**, trả lời tiếng Việt, ngắn gọn, nêu kết quả và việc cần quyết định trước.

Bảng nhóm phòng, pattern, layer, quy tắc nhận diện tên: `references/phan-loai-phong.md`.
Script (`<skill>` = Base directory của skill này): `scripts/tao_hatch_lat_san.py` (`tao` / `gop`), `scripts/thong_ke_lat_san.py`.

## Quy trình
| Bước | Subagent (`subagent_type`) | Model | Đầu ra |
|---|---|---|---|
| 1 | `do-dien-tich` | opus · medium | bản sao DWG có polyline phòng layer `A- Dien tich phong` (+ đường bo căn), nhãn chưa gắn Field |
| 2 | `lat-san-hatch-pn`, `lat-san-hatch-pk`, `lat-san-hatch-wc`, `lat-san-hatch-lg` (gọi **song song**, một tin nhắn) | sonnet · medium | `hatch_<NHOM>.scr` + `.json` mỗi nhóm |
| 3 | phiên chính | – | `<ten>_LatSan.dwg` (gộp 4 `.scr`, vẽ 1 lần) |
| 4 | `lat-san-gan-field` | haiku · medium | `<ten>_LatSan_Field.dwg`, kết quả `kiem_tra_nhan` |
| 5 | `lat-san-thong-ke` | haiku · medium | `YYYYMMDD_<MaDuAn>_<Tang>_ThongKeLatSan.xlsx` |

### 0. Chuẩn bị
- Xác nhận file nguồn, thư mục dự án (`02-Du-An\<du-an>\`), mã dự án, tầng. Thiếu → hỏi.
- File gốc chỉ đọc; mọi kết quả ở `03-Ban-Sao-Lam-Viec\Lat-San\` (Excel ở `04-Thong-Ke-Dien-Tich\`). Không có thư mục dự án → hỏi anh nơi lưu.
- Bản vẽ **đã có** polyline phòng `A- Dien tich phong` đúng → anh đồng ý thì bỏ bước 1.

### 1. Dựng polyline phòng – `do-dien-tich`
Lời giao: file nguồn, thư mục kết quả, "**chỉ dựng polyline phòng + đường bo căn và vẽ vào bản sao; chưa gắn Field** (bước sau làm)", và anh đã đồng ý vẽ hay chưa.
- Agent trả "dừng chờ quyết định" → đưa câu hỏi + ảnh cho anh (AskUserQuestion), gọi lại agent bằng SendMessage kèm trả lời.
- Hỏi anh trước khi để agent vẽ vào bản sao (nếu lời giao chưa có).

### 2. Sinh hatch – 4 agent song song
Mỗi agent nhận: DXF của bản sao bước 1 (xuất bằng MCP `xuat_dxf`, **`no_doi_tuong_aec=true`** – phải nổ AEC để script thấy cửa đi, đặt điểm gốc; do phiên chính làm **trước** để 4 agent dùng chung), thư mục ra. Agent **không vẽ**.
Gom kết quả: số phòng + Σ DT mỗi nhóm, điểm gốc từng phòng, danh sách `chua_phan_loai` (giống nhau ở cả 4 JSON – lấy một lần) và `chua_co_diem_goc`.

### 3. Duyệt và vẽ hatch (phiên chính)
- Báo anh bảng nhóm (số phòng, Σ m²) + phòng chưa phân loại (tên, tọa độ) + phòng chưa tìm được điểm gốc (hatch vẫn vẽ, gốc theo HPORIGIN hiện hành → anh chỉnh tay hoặc chỉ điểm). Phòng chưa phân loại → anh chỉ nhóm hoặc bỏ qua; có chỉ định thì sửa tên/nhóm bằng cách chạy lại agent nhóm đó với ghi chú, **không** tự gán.
- Anh đồng ý → `python <skill>/scripts/tao_hatch_lat_san.py gop --out <thu_muc>/ve_hatch_lat_san.scr hatch_PN.scr hatch_PK.scr hatch_WC.scr hatch_LG.scr` → MCP `ve_vao_ban_sao` (bản sao bước 1 → `<ten>_LatSan.dwg`).
- Kiểm: `xuat_dxf` bản `_LatSan` → số HATCH layer `A-Materials` = tổng số phòng 4 nhóm.

### 4. Gán Field – `lat-san-gan-field`
Lời giao: `<ten>_LatSan.dwg`, đích `<ten>_LatSan_Field.dwg`. Bước này mở bản sao trong AutoCAD GUI qua COM (tab mới, không đụng tab của anh); AutoCAD bận → agent báo lại, em nhờ anh nhấn Esc rồi gọi lại.

### 5. Thống kê – `lat-san-thong-ke`
Lời giao: bản sao cuối (`_Field`, nếu bước 4 không làm được thì `_LatSan`), đường dẫn Excel, mã dự án, tầng.

### Báo anh
1. Bảng: nhóm – pattern – số phòng – Σ DT lát (m², 1 số lẻ) – tổng.
2. Lỗi/cảnh báo (phòng chưa hatch, lệch > 0,01 m², nhãn sai).
3. Đường dẫn bản sao DWG + Excel; phần đã kiểm tra thực tế / chưa kiểm tra.

## An toàn
- Không sửa/ghi đè file gốc; mỗi bước lưu file **mới** (công cụ từ chối ghi đè).
- Không đổi layer/đối tượng ngoài phạm vi: chỉ thêm HATCH trên `A-Materials` (tạo layer nếu thiếu).
- Không đụng tab AutoCAD anh đang mở. Không tự quyết nhóm phòng mơ hồ – hỏi.
- Mọi con số do script tính; tính trên số chưa làm tròn, làm tròn 1 số lẻ khi hiển thị.

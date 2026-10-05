---
name: thiet-ke-tran-ch
description: 'Tran CH – Soát và đề xuất bố trí thiết bị trần (mặt bằng trần phản chiếu, RCP) căn hộ Archivina từ bản vẽ AutoCAD/AutoCAD Architecture: nhận diện phòng, tủ áo, giường, bàn ăn, sofa, thiết bị vệ sinh và thiết bị trần (đèn downlight D90, đèn rọi gương, đèn thả, đèn lô gia, đầu báo khói/nhiệt, sprinkler 68/93 độ, miệng gió cấp/hồi 1200x150, gió tươi, quạt hút, lỗ thăm 600x600); kiểm tra đèn cách nhau ≥1200 mm, cách tường ≥500 mm (ưu tiên 600), không đặt thiết bị trong tủ áo, đèn không trên vùng gối, WC theo trục thiết bị vệ sinh, đèn thả theo tâm bàn ăn, ưu tiên PCCC; báo vị trí không phù hợp, đề xuất vị trí mới, vẽ vào BẢN SAO DWG và xuất Excel. Kèm thư viện block thiết bị trần tỷ lệ 1:1. Dùng skill này bất cứ khi nào người dùng đưa mặt bằng trần / mặt bằng bố trí thiết bị trần căn hộ và nhờ soát, kiểm tra, bố trí, đề xuất vị trí đèn, miệng gió, sprinkler, đầu báo, lỗ thăm, hoặc cần lấy block thiết bị trần chuẩn, kể cả khi họ không nhắc tên skill.'
---

# Tran CH – Soát và đề xuất bố trí thiết bị trần căn hộ (Archivina)

Người dùng là Phó TGĐ, kiến trúc sư giàu kinh nghiệm: báo kết quả và điểm cần quyết định trước, ngắn gọn, tiếng Việt.

**Quy tắc thiết kế trần do người dùng soạn là gốc, đọc trước khi làm:**
- `references/quy_tac_tran_goc.md` – mục đích, phân loại luật (HARD_RULE / TECHNICAL_RULE / DESIGN_RULE / PREFERENCE), thứ tự ưu tiên P1–P6, quy trình 13 bước, danh mục kiểm tra, 4 mức cảnh báo, định dạng đầu ra.
- `references/room_rules.md`, `references/device_rules.md`, `references/coordination_rules.md`, `references/output_rules.md`.
- `references/thu-vien-thiet-bi-tran.md` – thư viện block, cách nhận diện, cách mở rộng cho dự án khác.

## Nguyên tắc
- **Không sửa DWG gốc.** Chỉ đọc bản sao; đề xuất vẽ vào bản sao mới. **Không đụng AutoCAD đang mở.**
- **Không tự dời/xóa thiết bị PCCC** (sprinkler, đầu báo): chỉ báo `CRITICAL` / `TECHNICAL REVIEW REQUIRED`, cần tư vấn PCCC.
- **Không ép đèn dưới 1200 mm** để giữ đối xứng: giảm số đèn. Không đặt hàng đèn gần tường hơn 500 mm.
- **Không suy đoán số liệu thiếu.** Ngưỡng chưa chốt nằm trong `scripts/cau_hinh_tran.json` (`_nguong_chua_chot`), báo rõ là ngưỡng tạm.
- Thiết bị đề xuất đặt trên layer gốc thêm hậu tố `-DX` (vd `A-Den-DX`), đánh dấu lỗi trên `A-Tran-Loi`.

## Quy trình
Có MCP `autocad-archivina` thì dùng `xuat_dxf`, `chay_script_tren_ban_sao`; không có thì gọi script tay như dưới.

1. **Chuyển DWG → DXF** (nổ tường/cửa AutoCAD Architecture, kể cả nằm trong block): script `dwg_to_dxf_aec.ps1` của skill `dien-tich-ch`:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File "<skills>\dien-tich-ch\scripts\dwg_to_dxf_aec.ps1" -Dwg "<file.dwg>" -OutDir "<thư mục tạm>"
   ```
2. **Soát và đề xuất:**
   ```powershell
   $env:PYTHONUTF8=1; & "<python>" "<skill>\scripts\soat_tran.py" "<file.dxf>" --out-dir "<thư mục kết quả>" --du-an "<tên dự án>"
   ```
   Script in JSON tóm tắt và tạo `BaoCaoSoatTran.xlsx`, `xem_tran_<căn>.png`, `ve_de_xuat_tran.scr`. Xem ảnh bằng Read trước khi báo cáo.
3. **Đọc kết quả:** từng phòng có trục thiết kế chính, số thiết bị, trạng thái `PASS` / `PASS WITH WARNING` / `REVISE` / `TECHNICAL REVIEW REQUIRED`. Sheet `Loi va de xuat` theo cột chuẩn báo cáo soát Archivina (Mức độ Lỗi/Cảnh báo/Gợi ý + loại cảnh báo của skill), sheet `Thiet bi` theo bản ghi AutoCAD (DEVICE_ID, ROOM, BLOCK_NAME, X, Y, ROTATION…), sheet `De xuat vi tri`.
4. **Hỏi người dùng** trước khi vẽ đề xuất nếu có phòng `TECHNICAL REVIEW REQUIRED`, phòng có ranh gần đúng ảnh hưởng kết luận, hoặc block chưa nhận diện (sheet `Block chua nhan dien`).
5. **Vẽ đề xuất vào bản sao** (khi người dùng đồng ý): chạy `ve_de_xuat_tran.scr` trên bản sao bằng `ve_polyline_vao_dwg.ps1` (skill `dien-tich-ch`) hoặc MCP `chay_script_tren_ban_sao` (cuối script đã có `_.QSAVE`). Script chèn block từ `assets/thu-vien/<MÃ>.dwg` lên layer `<layer>-DX`, vẽ vòng tròn R250 + mã lỗi `Lxx` trên `A-Tran-Loi` và đường nối vị trí cũ → mới. Thiết bị cũ không bị xóa. Layer, vòng, chữ, đường nối tạo bằng LISP `entmake` (tên layer có dấu cách, text style chiều cao cố định, OSNAP không làm lệch script); đường dẫn thư viện không được có dấu cách (script tự dừng nếu có). Sau khi vẽ: xuất DXF bản sao và kiểm tra số đối tượng trên `A-Tran-Loi`, `*-DX`.
6. **Báo cáo:** bảng theo phòng (trục, thiết bị, kiểm tra, cảnh báo, trạng thái) như mục 13 của quy tắc gốc; nêu rõ phần đã kiểm tra thực tế và phần chưa kiểm tra được (phòng không dựng được ranh, block chưa nhận diện, thiết bị PCCC chờ tư vấn).

## Script kiểm tra những gì (soat_tran.py)
| Kiểm tra | Mức |
|---|---|
| Đèn chung (downlight, downlight WC) tâm–tâm < 1200 mm; tâm đèn cách tường < 500 mm | HARD-RULE WARNING → đề xuất bố trí lại lưới đèn của phòng |
| Thiết bị trong vùng tủ áo (vùng = dải móc áo trong block tủ) | CONFLICT; PCCC → CRITICAL, TECHNICAL REVIEW REQUIRED |
| Thiết bị chồng nhau | COORDINATION; dời thiết bị ưu tiên thấp hơn (P5 trước P1), tìm chỗ trống tránh thiết bị khác; không có chỗ → "Không tìm được vị trí thay thế". PCCC và đèn thả (theo tâm bàn ăn/sofa) giữ nguyên, chỉ báo phối hợp |
| Hai block cùng mã trùng vị trí (< 50 mm) | COORDINATION "Thiết bị chèn trùng" – xóa bản trùng (OVERKILL) sau khi bộ môn xác nhận |
| Phòng ngủ: đèn trên vùng gối (700 mm từ đầu giường), gió cấp gần vùng gối, lỗ thăm trên giường | DESIGN / COORDINATION |
| WC: đèn rọi gương lệch trục gương > 50 mm; đèn không trùng trục chậu / bồn cầu / sen | DESIGN (đề xuất theo trục gương) |
| WC: đèn downlight WC lệch 1200/500 (chốt 05/10/2026: `luat_luoi_den_wc = theo_truc`) | DESIGN, không đề xuất lưới lại; đổi `cung` để áp như đèn chung |
| Đèn thả lệch tâm bàn ăn / bộ sofa > 100 mm | DESIGN (đề xuất về tâm) |
| Lỗ thăm ở 1/3 giữa phòng khách | DESIGN |
| Đầu báo cách miệng gió cấp < 1000 mm (ngưỡng Archivina, chốt 05/10/2026) | COORDINATION, PCCC/HVAC phối hợp; không tự dời đầu báo |

**Đề xuất lưới đèn:** vùng đặt = phòng lùi 600 mm (không được thì 500) trừ tủ áo và vùng tránh 300 mm quanh thiết bị khác; lưới nx × ny ≤ số đèn hiện có, khoảng cách ≥ 1200, đối xứng qua trục giường (phòng ngủ), bỏ điểm rơi vào vùng gối. Đây là **phương án tham khảo** cho kiến trúc sư chỉnh, không phải bố trí chiếu sáng có tính toán độ rọi.

## Nhận diện (cấu hình được, xem `references/thu-vien-thiet-bi-tran.md`)
- **Phòng:** Text tên phòng (layer `A-Text`) + nét ranh (`layer_ranh`, khung cửa `layer_cua`) bằng bộ dựng phòng của skill `dien-tich-ch`. Phòng chưa khép kín (mặt dựng/cửa sổ/vách kính vẽ ngắt quãng) được khép gần đúng theo các bước `dong_ranh_gan_dung_cac_buoc` (khe ≤ 0,5 / 1,0 / 1,6 / 2,6 m), chỉ nhận vùng chứa đúng một tên phòng và ≤ `dt_phong_gan_dung_toi_da` m²; ghi "Ranh phòng gần đúng" (Gợi ý) kèm khe đã khép. Phòng trùng tên trong một căn được đánh số (`Phòng ngủ 1`, `2`… từ trên xuống).
- **Căn hộ:** nối phòng qua **cửa đi** (hai phòng cùng chạm một cửa ≤ 4 m thì cùng căn; tường chung giữa hai căn không có cửa nên không gộp). Cụm không có phòng khách (phòng ngủ/WC không nhận được cửa) gộp vào căn kề có cạnh chung dài nhất. Tên căn: ghép cặp (cụm, Text `CHxx`) gần nhất trước, trong 3 m.
- **Thiết bị:** theo `assets/thu-vien/catalog.json` (`bi_danh` tên block sau khi bỏ tiền tố xref đã bind; `chu_ky` layer + kích thước cho block vô danh). Vị trí = tâm phần ký hiệu thật (không theo điểm chèn, bỏ vòng phủ R2000).
- **Nội thất:** `scripts/cau_hinh_tran.json` → `noi_that` (tủ áo = block có ≥ 6 móc áo; giường = block có 2 tab đầu giường; bàn ăn, sofa, bồn cầu, chậu rửa, tủ gương, sen, vách tắm theo tên).
- Dự án dùng tên block/layer khác: thêm bí danh vào catalog/cấu hình rồi chạy lại; không sửa code.

## Thư viện thiết bị trần
`assets/thu-vien/`: 16 block `<MÃ>.dwg` + `Thu-vien-thiet-bi-tran.dwg` (bản tổng hợp có nhãn) + `catalog.json`. Tỷ lệ 1:1 mm, điểm chèn tại tâm, chèn tỷ lệ 1, đối tượng bên trong layer 0 (theo layer khi chèn). Dựng lại thư viện từ bản vẽ mẫu: `scripts/tao_thu_vien.py` (xem file tham chiếu).

## Giới hạn
- Không thay thiết kế PCCC/HVAC/chiếu sáng có tính toán; không kết luận tuân thủ quy chuẩn.
- Hướng thổi miệng gió không có trong bản vẽ: chỉ cảnh báo theo khoảng cách.
- Trần nhiều cao độ, hộp kỹ thuật trần, dầm: chưa đọc (cần mặt cắt / cao độ trần) – nêu là "chưa kiểm tra".

---
name: cap-dien-ch
description: 'Cap dien CH – Vẽ (bố trí mới) và soát MẶT BẰNG CẤP ĐIỆN Ổ CẮM căn hộ Archivina từ mặt bằng căn hộ / tầng AutoCAD (.dwg/.dxf, kể cả ACA): ổ đôi G đầu giường, TV, ĐN, B mặt bếp, TL, ổ thường; ổ chống ẩm W/X (lavabo, bồn cầu, máy giặt); box chờ BT / HM / AC (dàn nóng) / BNL; tủ điện TĐ-CH, VDP, công tắc 20A và 3 phím ngoài cửa WC – theo NỘI THẤT và nguyên tắc vị trí đã chốt (cách khuôn cửa ≥ 200, không sau cửa / tủ áo, tránh vách BTCT); chia lộ (khách + WC chung, bếp, phòng ngủ, AC / BT / từng BNL riêng, F quạt hút), dây + mũi tên S1/TĐ.CH, dim từ mép tường tới tâm thiết bị; block, layer, bảng ký hiệu mẫu Archivina; vẽ vào BẢN SAO DWG, xuất Excel. Dùng khi người dùng nhờ vẽ, bố trí, soát, kiểm tra ổ cắm, hộp chờ, tủ điện căn hộ, mặt bằng cấp điện / điện động lực, chia lộ ổ cắm, hoặc cần block ổ cắm chuẩn – kể cả khi không nhắc tên skill. Không dùng cho chiếu sáng / thiết bị trần (thiet-ke-tran-ch).'
---

# Cap dien CH – Mặt bằng cấp điện ổ cắm căn hộ (Archivina)

Người dùng là Phó TGĐ, kiến trúc sư giàu kinh nghiệm: báo kết quả và điểm cần quyết định trước, ngắn gọn, tiếng Việt.

**Đọc trước khi làm:**
- `references/nguyen-tac-bo-tri.md` – nguyên tắc vị trí, chia lộ, kích thước người dùng đã chốt (07/10/2026) và các giá trị
  **chưa chốt** (phải nói rõ là tạm).
- `references/thu-vien-va-nhan-dien.md` – thư viện block, layer, cách nhận diện nền, cách bổ sung tên block, giới hạn.

## Nguyên tắc làm việc
- **Không sửa DWG gốc, không đụng AutoCAD đang mở.** Phân tích trên DXF xuất từ bản sao; vẽ vào bản sao mới.
- **Thiết bị bố trí theo nội thất.** Thiếu nội thất / tên phòng / cửa → **dừng lại hỏi**, không tự suy đoán. Script gom các
  điểm này vào `can_hoi` (JSON) và sheet `Loi va can hoi` (cột "Cần hỏi người dùng").
- Giá trị **chưa chốt** (`cau_hinh_o_cam.json` → `_chua_chot`) phải báo cho người dùng khi dùng.
- Không thay thiết kế điện có tính toán: số thiết bị mỗi lộ chỉ để kỹ sư điện kiểm tra tải / CB / dây.

## Quy trình BỐ TRÍ MỚI
Có MCP `autocad-archivina` thì dùng `xuat_dxf`, `ve_vao_ban_sao`, `chay_script_tren_ban_sao`, `ban_sao_tu_ban_ve_dang_mo`.

1. **Lấy DXF** từ bản sao (nổ đối tượng ACA): MCP `xuat_dxf` (hoặc `dien-tich-ch\scripts\dwg_to_dxf_aec.ps1`). Bản vẽ đang mở
   trong AutoCAD: `ban_sao_tu_ban_ve_dang_mo` trước.
2. **Chạy phân tích lần đầu** (chưa cần tham số) để biết căn, phòng, nội thất nhận được và các câu hỏi:
   ```powershell
   $env:PYTHONUTF8=1; & "<python>" "<skill>\scripts\cap_dien.py" bo-tri "<file.dxf>" --out-dir "<thư mục>" --du-an "<tên>"
   ```
   Đọc JSON in ra: `can_ho`, `phong`, `noi_that`, `block_chua_nhan_dien`, `can_hoi`. **Xem ảnh `xem_o_cam_<căn>.png` bằng Read.**
3. **Hỏi người dùng (AskUserQuestion), gộp một lượt:**
   - **Số ổ cắm mặt bếp** của từng bếp (BẮT BUỘC – script gợi ý theo chiều dài dải bếp) → `--so-o-bep 2` hoặc `"CH01=2,CH02=3"`.
   - Đế ổ cắm **chữ nhật (TV–ĐN 150) / vuông (100)** → `--de-o`.
   - Có block máy rửa bát / lò nướng → có bố trí ổ không (`--may-rua-bat`, `--lo-nuong`).
   - Phòng ngủ không có kệ TV → đặt ổ TV theo trục giường (`--tv-pn-theo-truc-giuong`) hay bỏ.
   - Block chưa nhận diện cần gán loại (bếp nấu, tủ lạnh, bình nóng lạnh, dàn nóng, bàn làm việc…): liệt kê `#n – tên – kích
     thước – vị trí` theo ảnh → ghi file JSON `{"<tên block>": "<loại>"}` → `--nhan-dien-bo-sung`.
   - Các mục `can_hoi` khác: cửa chính / cửa WC không có cung mở, sofa không sát tường, phòng đa năng, thiếu dàn nóng / BNL…
   - Mặt bằng tầng: căn điển hình nào (`--can CH01,CH02`).
4. **Chạy lại với câu trả lời**, xem lại ảnh + Excel `BaoCaoBoTriOCam.xlsx` (sheet `Tom tat`, `Loi va can hoi`,
   `Thiet bi bo tri`, `Lo`, `Noi that`). Báo người dùng: số thiết bị từng căn / phòng, các lộ, vị trí phải dời (BTCT → mây,
   dịch tránh cửa / tủ áo), câu hỏi còn lại, giá trị chưa chốt đã dùng. **Chờ người dùng đồng ý** trước khi vẽ.
5. **Vẽ vào bản sao:** MCP `ve_vao_ban_sao(duong_dan_dwg=<gốc>, file_scr=<thư mục>\ve_o_cam.scr, dwg_ket_qua=<file mới>)`
   (script đã có `_.QSAVE`; tự tạo layer, text style `AV-ME-Text`, dim style `A 1-50`, nạp block từ thư viện; chèn bảng ký
   hiệu bên phải bản vẽ – bỏ bằng `--khong-bang-ky-hieu`). Không có MCP: `dien-tich-ch\scripts\ve_polyline_vao_dwg.ps1`.
6. **Kiểm tra sau khi vẽ:** `xuat_dxf` bản kết quả → đếm block / thuộc tính / DIMENSION trên layer `AV-E-*` khớp
   `bo_tri_o_cam.json`; chạy `cap_dien.py soat` trên DXF đó (cùng tham số) – kết quả đúng là không còn "Lệch", "Thiếu thiết bị".
   Dựng ảnh vùng căn (ezdxf drawing) để xem ký hiệu đúng tỷ lệ.
7. **Báo cáo:** đường dẫn DWG bản sao, Excel, ảnh; phần đã kiểm tra thực tế / chưa kiểm tra được (phòng không dựng được ranh,
   cửa không có cung, block chưa nhận diện); lưu kết quả dự án vào `05-Soat-Loi\` (hoặc `03-Ban-Sao-Lam-Viec\` cho bản vẽ).

## Quy trình SOÁT bản vẽ nhân viên
```powershell
$env:PYTHONUTF8=1; & "<python>" "<skill>\scripts\cap_dien.py" soat "<file.dxf>" --out-dir "<thư mục>" --du-an "<tên>" [cùng tham số như bố trí]
```
- Đọc ký hiệu đã vẽ theo `catalog.json` → `bi_danh_block` + giá trị thuộc tính; gán vào phòng.
- **Lỗi:** vị trí vi phạm (cách khuôn cửa < 200, sau cánh cửa, sau tủ áo, trên cửa sổ / lan can), thiếu thiết bị bắt buộc
  (G, TV, TL, BT, HM, BNL, W, TĐ-CH, AC, B, 20A). **Cảnh báo:** lệch > 300 mm so với vị trí theo nguyên tắc (kèm tọa độ đề
  xuất), trên vách BTCT chưa đánh dấu mây, không bám tường, lộ riêng AC / BNL / BT chưa có nhãn. **Gợi ý:** thiếu kích thước
  định vị, thiết bị ngoài nguyên tắc. Mục không kiểm tra được (thiếu nội thất, cửa) ghi "Chưa kiểm tra được đầy đủ".
- Số ổ B: lấy theo người dùng (`--so-o-bep`), không có thì hỏi hoặc lấy số ổ B nhân viên đã vẽ để so vị trí.
- Excel `BaoCaoSoatOCam.xlsx` (cột chuẩn báo cáo soát Archivina) + ảnh: ô vuông xanh / đỏ = thiết bị hiện có đạt / lỗi, vòng
  xanh dương = vị trí đề xuất. Đặt tên khi lưu cho dự án: `YYYYMMDD_<MaDuAn>_<Tang>_BaoCaoSoat_OCam.xlsx`.

## Kết quả mẫu
`H:\@AI Claude Test\03-Cong-Cu\05-Skill-Test\ket-qua-OCam-mau\` – bản vẽ nội thất mẫu 2 căn (`Test Layout noi that CH.dwg`,
`--so-o-bep 2`): CH01 34 thiết bị (TĐ-CH, VDP ×2, G ×6, TV ×4, ĐN, B ×2, BT, HM, W ×5, X ×3, CT 3 phím ×2, AC), lộ S1–S3, AC1,
BT; CH02 27 thiết bị; ~19 câu hỏi (block bếp nấu `86786`, bình nóng lạnh `CT3-Tn-MEP` chưa nhận, cửa chính CH02 không có cung
mở…). Chạy ~20 s; vẽ bản sao bằng MCP `ve_vao_ban_sao` ~1 phút.

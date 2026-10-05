# Thư viện thiết bị trần căn hộ và cách nhận diện

## 1. Thư viện (`assets/thu-vien/`)
Nguồn: `H:\@Archivina 2026\@bản vẽ mẫu căn hộ\Test Layout noi that CH.dwg` (căn mẫu CH01, CH02; khối xref trần `CT1-T(3-21)-Xref Tran` đã bind).
Quy cách chung: **tỷ lệ 1:1 (mm), chèn tỷ lệ 1**, điểm chèn tại tâm ký hiệu, đối tượng bên trong ở layer `0` (lấy theo layer khi chèn), giữ nguyên màu/wipeout/hatch gốc. Kích thước đã nhân tỷ lệ chèn thật trong bản vẽ mẫu (đèn thả chèn ×40, đèn lô gia ×1,875).

| Mã block | Thiết bị | Kích thước (mm) | Layer | Hệ | Ưu tiên | Block gốc trong bản vẽ mẫu |
|---|---|---|---|---|---|---|
| LT-DL-D90 | Đèn downlight LED âm trần D90 | Ø110 (lỗ D90) | A-Den | Chiếu sáng | P5 | `E1` (chèn 0,991 ≈ 1) |
| LT-DL-WC-D90 | Đèn downlight LED âm trần WC D90 | 150×150 | A-Den | Chiếu sáng | P5 | `AV_DenDowlight WC…` (chỉ có ở chú giải) |
| LT-MIR-D65 | Đèn rọi gương D65 | Ø67,5 | A-Den | Chiếu sáng | P4 | `Đèn rọi gương` (bọc trong block vô danh) |
| LT-PEND | Đầu chờ đèn thả (P. khách, P. ăn) | 502×284 | A-Den | Chiếu sáng | P5 | `DEN BAN AN` ×40 |
| LT-OUT | Đèn ốp trần ngoài nhà (lô gia) | 187,5×187,5 | A-Den | Chiếu sáng | P4 | `dl04` ×1,875 |
| FA-SMOKE | Đầu báo khói địa chỉ | Ø125 (chữ S) | A-Thiet bi PCCC | Báo cháy | P1 | `ĐẦU BÁO KHÓI ĐỊA CHỈ` |
| FA-HEAT | Đầu báo nhiệt cố định địa chỉ | Ø125 (chữ H) | A-Thiet bi PCCC | Báo cháy | P1 | `ĐẦU BÁO NHIỆT CỐ ĐỊNH ĐỊA CHỈ` |
| SP-D15-68 | Sprinkler quay xuống D15, 68°C, K=5,6 US | Ø164,5 + vòng R2000 | A-Thiet bi PCCC | Chữa cháy | P1 | `Sprinkler quay xuống D15` |
| SP-D15-93 | Sprinkler quay xuống D15, 93°C, K=5,6 US | Ø112,5 + vòng R2000 | A-Thiet bi PCCC | Chữa cháy | P1 | `Sprinkler quay xuống D15 93 độ C` |
| HV-SAG-1200x150 | Miệng gió cấp điều hòa 150×1200 | 1200×150 | A-HVAC | ĐHKK | P2 | `SAG 1200x200` |
| HV-RAG-1200x150 | Miệng gió hồi điều hòa 150×1200 | 1200×150 | A-HVAC | ĐHKK | P2 | `RAG 1200x200` |
| HV-FAG-300 | Cửa cấp gió tươi 300×300 | 300×300 | A-HVAC | ĐHKK | P2 | `SAG 300x300` (chỉ có ở chú giải) |
| HV-EAG-200 | Quạt hút mùi 200×200 | 200×200 | A-HVAC1 | Thông gió | P2 | `EAG+OBD 200x200` |
| AC-AP-600 | Lỗ thăm trần 600×600 | 610×610 (panel 600) | A-Hoan thien tran | Bảo trì | P3 | block vô danh `A$C456554A7` |

- **Vòng phủ R2000** của sprinkler nằm trong block nhưng trên layer riêng `A-PCCC-Phu` (màu 250, **không in**). Tắt/đóng băng layer này để ẩn. Skill **không** dùng vòng 2 m làm quy tắc thiết kế (quy tắc gốc, device_rules mục 10), chỉ để tham khảo khi kiểm tra.
- Tên block giữ nguyên mã, catalog ghi kèm tên gốc để tra ngược.
- `Thu-vien-thiet-bi-tran.dwg`: bản tổng hợp mọi block trên đúng layer, có nhãn mã – tên – kích thước – layer (dùng làm palette / DesignCenter). `Thu-vien-thiet-bi-tran.png`: ảnh xem nhanh.
- Chèn vào bản vẽ khác: `-INSERT <MÃ>=<đường dẫn>\<MÃ>.dwg`, tỷ lệ 1, đặt layer hiện hành là layer trong bảng.
- `SVC-7654` (tròn Ø154, trên mặt bằng mẫu) = **đèn downlight WC** (người dùng xác nhận 05/10/2026): nhận diện là `LT-DL-WC-D90` qua bí danh; block thư viện vẫn lấy theo ký hiệu chú giải 150×150.
- Block không đưa vào thư viện: `LOA` (loa, có trong khối trần nhưng không thuộc danh mục skill), `3453` (200×200 trên `A-HVAC2`) – chưa xác nhận loại thiết bị.

## 2. Dựng lại / bổ sung thư viện
```powershell
$env:PYTHONUTF8=1; & "<python>" "<skill>\scripts\tao_thu_vien.py" --dwg "<bản vẽ mẫu.dwg>" --dxf "<DXF xuất thường của bản vẽ đó>" --khai-bao "<skill>\assets\thu-vien\khai_bao_mau.json" --out "<thư mục ra>"
```
`khai_bao_mau.json` liệt kê từng thiết bị: `ma`, `ten`, `tien_to` (tiền tố xref đã bind), `block_nguon`, `ti_le` (tỷ lệ chèn thật trong bản vẽ), `layer`, `them_vong_phu`. Script tự tính tâm/kích thước, tạo block, ghép bản tổng hợp và **đọc lại để so kích thước** (báo `so_dat / tong`). Thêm thiết bị mới: thêm dòng vào khai báo + thêm mục vào `catalog.json` (bí danh nhận diện).

## 3. Nhận diện thiết bị trong bản vẽ khác (`catalog.json`)
1. Tên block bỏ tiền tố xref đã bind (`A$0$B$0$Tên` → `Tên`), bỏ dấu, so với `bi_danh` (ký tự đại diện `*`, `?`).
2. Block vô danh chỉ bọc một block khác (vd đèn rọi gương lật gương) → nhận theo block con.
3. Không khớp tên nhưng nằm trên layer thiết bị → so `chu_ky` (layer + khoảng kích thước), vd lỗ thăm 580–640 mm trên `A-Hoan thien tran`.
4. Vẫn không nhận ra → liệt kê ở sheet `Block chua nhan dien` để người dùng gán mã; thêm bí danh vào catalog rồi chạy lại.
Vị trí thiết bị = tâm phần ký hiệu thật (bỏ vòng phủ, Defpoints), không dùng điểm chèn (một số block gốc có điểm chèn lệch xa ký hiệu).

## 4. Nhận diện phòng và nội thất (`scripts/cau_hinh_tran.json`)
- **Layer ranh phòng** mặc định thêm `A-Lancan`, `S-Wall`, `A_Wall BT` so với skill diện tích (lan can kính lô gia, vách/cột BTCT bao phòng); khung cửa gồm cả kính mặt dựng `玻璃层`, `A-Window-G`.
- **Tủ áo**: block chứa ≥ 6 block móc áo (`衣架`, hanger, móc áo) hoặc tên tủ áo/wardrobe; vùng cấm = dải móc áo nở 150 mm, cắt theo hộp bao tủ (tủ chữ L ra hình chữ L).
- **Giường**: block chứa 2 tab đầu giường (`don …`, nightstand). Đầu giường = phía có tab; trục giường = đường giữa hai tab; vùng gối = 700 mm từ đầu giường, rộng bằng khoảng giữa hai tab.
- **Bàn ăn / sofa / bồn cầu / chậu rửa / tủ gương / sen / vách tắm / bếp**: theo tên block (bảng `noi_that`). Trục gương lấy từ tủ gương (`Tuguong`).
- **Loại phòng**: theo Text tên phòng (bảng `loai_phong`); Text dạng `CH01` là tên căn hộ.

## 5. Kết quả trên bản vẽ mẫu
Xem `evals/evals.json` và phần báo cáo trong phiên tạo skill; con số cụ thể ghi trong `references/ket-qua-mau.md`.

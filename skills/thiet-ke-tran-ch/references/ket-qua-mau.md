# Kết quả chạy mẫu – `Test Layout noi that CH.dwg` (05/10/2026)

Nguồn: `H:\@Archivina 2026\@bản vẽ mẫu căn hộ\Test Layout noi that CH.dwg` (2 căn CH01, CH02; nền xref đã bind `CT1-T0-CH05A`, `CT1-T(3-10)-CH05A`, `CH03`; trần `CT1-T(3-21)-Xref Tran`). Kết quả lưu tại `H:\@AI Claude Test\03-Cong-Cu\05-Skill-Test\ket-qua-Tran-mau\`. Thời gian chạy `soat_tran.py`: ~11 s (dựng phòng 9 s).

## Nhận diện
- **Căn hộ:** CH02 (phía trên, 11 phòng: P. khách + bếp 61,1 m², 4 PN, 3 WC, đa năng, 2 lô gia) và CH01 (phía dưới, 9 phòng: P. khách + bếp 40,7 m², 3 PN, 3 WC, đa năng, lô gia đôi). Ranh hai căn ở tường y ≈ −16.300 (khớp nguồn xref: nội thất căn dưới thuộc `CH03$0$…`).
- **Phòng:** 20/20 vùng tên phòng có ranh; 4 PN của CH02 nằm ở mặt dựng vẽ ngắt quãng → ranh gần đúng (khép khe 1,0 / 1,0 / 1,6 / 2,6 m).
- **Thiết bị (178):** LT-DL-D90 74, LT-DL-WC-D90 16 (block `SVC-7654`, người dùng xác nhận là đèn downlight WC; 3 bản chèn trùng), HV-EXG-200 2 (`3453`), FA-SPK 1 (`LOA`), SP-D15-68 29, FA-SMOKE 11, AC-AP-600 8, HV-EAG-200 7, HV-SAG 6, HV-RAG 6, LT-MIR-D65 6, LT-OUT 4, LT-PEND 4, FA-HEAT 2, SP-D15-93 2.
- **Nội thất:** giường 7, tủ áo 7, bồn cầu 6, tủ gương 6, sen 6, bàn ăn 6, vách tắm 3, chậu rửa 2, sofa 2, bếp 1.
- **Block chưa nhận diện:** 0.

Lần chạy cuối (cấu hình chốt 05/10/2026: `luat_luoi_den_wc = theo_truc`, đầu báo cách gió cấp 1000 mm): 31 cảnh báo (CRITICAL 2, HARD-RULE 4, COORDINATION 7, DESIGN 18), 13 đèn đề xuất. So với bảng dưới, thêm: 3 cặp đèn WC chèn trùng (COORDINATION); đèn WC cách tường 416–495 mm / cách nhau 992–1130 mm và 3 đèn WC lệch trục thiết bị vệ sinh (DESIGN).

## Cảnh báo (16) và đề xuất (13 đèn mới) – trước khi nhận đèn WC
| Căn – phòng | Nội dung | Mức |
|---|---|---|
| CH02 – PN 4, CH01 – PN 1 | Sprinkler SP-D15-68 nằm trên vùng tủ áo – không tự dời, cần tư vấn PCCC | CRITICAL |
| CH02 – Đa năng | Đèn cách tường 348 mm < 500 → đề xuất 1 đèn thay 2 | HARD-RULE |
| CH01 – PN 3 | Đèn cách tường 340 mm < 500 → đề xuất lưới 3 đèn thay 5 | HARD-RULE |
| CH02 – PN 1, WC 3 | Hai block SP-D15-68 / HV-EAG-200 chèn trùng vị trí | COORDINATION |
| CH01 – P. khách | Sprinkler chồng đèn thả bàn ăn (giữ đèn thả theo tâm bàn) | COORDINATION |
| CH02 – P. khách | Đầu báo khói cách miệng gió cấp 493 mm (ngưỡng tạm 1000) | COORDINATION |
| CH02 – PN 4, CH01 – PN 1 | Đề xuất lưới đèn theo trục giường (5 thay 7, 4 thay 7) | DESIGN |
| CH02 – PN 1–4 | Ranh phòng gần đúng | DESIGN |

Vẽ thử `ve_de_xuat_tran.scr` trên bản sao: 8 vòng + 8 nhãn trên `A-Tran-Loi`, 13 block LT-DL-D90 (Ø110, tỷ lệ 1) trên `A-Den-DX`, chữ tiếng Việt hiển thị đúng → `Test-Layout-CH_de-xuat-tran.dwg`.

## Ví dụ 2 – mặt bằng tầng `CT1-Mat Bang Tang 5A-10 (test trần).dwg` (05/10/2026)
Mặt bằng cả tầng, nền + xref trần `CT1-T(3-21)-Xref Tran` đã bind, **không có Text tên phòng, không có Text mã căn**; 719 AEC_WALL, 208 AEC_DOOR, 36 AEC_WINDOW (28 block chứa ACA đã nổ). Kết quả: `H:\@AI Claude Test\03-Cong-Cu\05-Skill-Test\ket-qua-Tran-CT1-T5A-10\`. Thời gian ~5–6 phút (dựng phòng ~4,5 phút).
- 19 căn (`Căn n (xref CHxx…)`), 163 phòng suy theo nội thất (46 WC, 45 PN, 21 lô gia, 21 P. khách/ăn, 30 chưa đặt tên), 5 khu chung, 20 ranh gần đúng, 4 ô nghi gộp PN + P. khách.
- 1.444 thiết bị trong các căn; 0 block chưa nhận diện.
- 276 cảnh báo: CRITICAL 5, HARD-RULE 109 (chủ yếu đèn cách tường < 500, đèn < 1200), COORDINATION 42 (24 cặp thiết bị chèn trùng, 7 đầu báo gần gió cấp…), DESIGN 120; 117 đèn đề xuất, vẽ thử trên bản sao đạt (`CT1-T5A-10_de-xuat-tran.dwg`).
- **Không soát:** ~810 thiết bị ở các cụm khác trong Model (y −97 … −264 m) là **mặt bằng căn hộ phóng to** – người dùng xác nhận không cần soát (05/10/2026). Skill cũng không dựng được phòng ở đó nên không lẫn vào báo cáo.

## Ví dụ 3 – bố trí mới trên `Căn hộ mẫu Cần Thơ.dwg` đang mở (05/10/2026)
Bản sao lấy từ tab đang mở bằng `-WBLOCK *` (tab gốc giữ nguyên, chưa lưu), tên phòng trên layer `A-Dimension`, nội thất là block động (`A-WC-Boncau`, `A-WC-Bonrua`, `A-WC-Vachkinhtam`, `Tam vuong cua mo trong`) và block có trạng thái hiển thị (`Ban an 4 ghe`, `sofa 1600`: 85–93% phần tử ẩn). Kết quả `H:\@AI Claude Test\03-Cong-Cu\05-Skill-Test\ket-qua-Tran-Can-Tho\` – DWG `Can-ho-mau-Can-Tho_bo-tri-tran.dwg` (mở trong AutoCAD qua COM, 46 block, một nhóm UNDO).
- P. khách + Bếp 31 m²: 2 cặp gió cấp/hồi, 1 đèn thả (tâm mặt bàn), 8 đèn chung, 3 sprinkler 68°C + 1 sprinkler 93°C gần bếp, đầu báo khói, đầu báo nhiệt, miệng gió hút bếp, lỗ thăm máy điều hòa.
- PN master / PN: mỗi phòng 4 đèn (trục giường, tránh vùng gối, tủ áo), 2 sprinkler, 1 đầu báo khói.
- WC 1 / WC 2: đèn rọi gương, 2 đèn WC (trục bồn cầu, vùng tắm), quạt hút; lỗ thăm ở WC 1 (WC 2 không còn góc trống).
- Lô gia 1, 2: mỗi lô gia 1 đèn ngoài nhà.
- Tự soát lại: 0 CRITICAL / 0 HARD-RULE; 5 DESIGN (đèn WC lệch 1200/500 theo luật WC theo trục, ghi chú lỗ thăm WC 2).
- **Người dùng đánh giá chưa đạt** → chuyển sang bố trí THEO TRỤC (bản v2, `Can-ho-mau-Can-Tho_bo-tri-tran_v2-theo-truc.dwg`, thư mục `v2-theo-truc\`): 33 đoạn trục trên `Defpoints`, 48 thiết bị. P. khách + bếp: vòng trục 600 + trục giữa dải bếp; 1 cặp gió (cặp thứ 2 vướng sofa), 8 đèn chung (xen kẽ hai bên miệng gió, ≥ 1500), đèn thả tâm bàn, đầu báo khói / nhiệt ở khoảng giữa đèn, gió hút bếp trên trục bếp, 5 sprinkler 68°C + 1 sprinkler 93°C thẳng hàng thiết bị. PN master: vòng trục, 5 đèn đối xứng trục giường; PN: 3 đèn; mỗi PN 3 sprinkler. WC 1 vòng trục (vuông), WC 2 trục giữa (dài): 2 đèn + quạt hút xen giữa. 0 CRITICAL / 0 HARD-RULE; 9 DESIGN (gồm ghi chú: thiếu 1 cặp gió, 0,2 m² PN master ngoài R2000, WC 2 không còn chỗ lỗ thăm).
- **Chỉnh lần 2 trực tiếp trên v2** (hình chữ nhật trục, đèn ở góc, cửa gió giữa hai đèn > 1400, đầu báo phía chân giường): xóa 81/81 đối tượng cũ, vẽ 47 thiết bị + 19 đoạn trục. P. khách: hình chữ nhật 1,75 × 6,0 m (bỏ hốc bếp, sảnh), 7 đèn (4 góc + giữa cạnh dài), 2 cặp cửa gió (cạnh dài và cạnh ngắn, qua sofa), đầu báo khói + nhiệt giữa hai đèn; PN master / PN: 4 đèn góc (đèn đầu giường trượt khỏi vùng gối), đầu báo khói cạnh chân giường; WC giữ trục cũ. Ghi chú: P. khách và WC 2 không còn khoảng trống cho lỗ thăm, PN master 0,2 m² ngoài R2000.
- **Chỉnh lần 3 trực tiếp trên v2** (xóa 66/66 đối tượng cũ, vẽ 41 thiết bị + 20 đoạn trục): bỏ sprinkler; trục bếp giữa dải bếp song song tủ bếp (2 đèn + đầu báo nhiệt H); đèn tâm sảnh vào căn, tâm hốc vào PN master và PN; 2 cặp cửa gió cùng chiều dọc cạnh dài, chia đều (1 cửa cấp dịch tránh đèn thả); lỗ thăm P. khách ngoài trục gần gió hồi; đèn PN đúng 4 góc; WC vuông vòng trục 450, WC dài trục giữa đèn cách tường 450, hút mùi tâm phòng, D65 tâm chậu. Ngoại lệ: đèn tâm hốc PN master cách tường 421 (hốc rộng 843).

## Lỗi đã sửa khi chạy mẫu (để không lặp lại)
- Block có trạng thái hiển thị (block động): hộp bao gồm cả phần tử ẩn → nội thất lệch ra ngoài căn; nay bỏ phần tử `invisible`. Block động `*Uxx` đọc tên gốc qua `AcDbBlockRepBTag`.
- Bàn ăn dạng cụm (bàn + ghế + tủ): tâm hộp bao ≠ tâm bàn → tìm mặt bàn (chữ nhật 600–1300 × 700–2600) từ nét LINE/LWPOLYLINE.
- Lưới đèn: so khoảng cách có dung sai 1 mm (1499,2 mm từng làm mất lưới 2×2).
- Mặt bằng tầng: `pair_rays` / `snap_bridges` (skill `dien-tich-ch`) duyệt mọi cặp (24.500 tia → hàng trăm triệu phép thử) → dùng STRtree, kết quả không đổi (hồi quy Cần Thơ 70,9 m² và 7 phòng giữ nguyên); mạng ô dựng theo từng cụm.
- `_doan_cua` (skill `dien-tich-ch`) đọc đỉnh LWPOLYLINE theo OCS → cửa chèn lật gương (extrusion 0,0,−1) bị đảo dấu X, mất cửa sổ mặt dựng và nối nhầm phòng. Đã đổi sang `vertices_in_wcs()`.
- Khép ranh gần đúng: union toàn bộ nét rồi buffer (12.000 đoạn khung cửa chi tiết) mất > 10 phút → nong từng đoạn rồi union, tính một lần (1,5 s).
- Nhóm căn bằng nong ranh 400 mm làm dính hai căn qua tường chung → nối phòng qua cửa đi.
- `-LAYER` trong script với tên layer có dấu cách làm treo accoreconsole → tạo layer/đặt layer bằng LISP.

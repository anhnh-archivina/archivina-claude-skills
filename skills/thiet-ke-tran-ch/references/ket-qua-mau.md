# Kết quả chạy mẫu – `Test Layout noi that CH.dwg` (05/10/2026)

Nguồn: `H:\@Archivina 2026\@bản vẽ mẫu căn hộ\Test Layout noi that CH.dwg` (2 căn CH01, CH02; nền xref đã bind `CT1-T0-CH05A`, `CT1-T(3-10)-CH05A`, `CH03`; trần `CT1-T(3-21)-Xref Tran`). Kết quả lưu tại `H:\@AI Claude Test\03-Cong-Cu\05-Skill-Test\ket-qua-Tran-mau\`. Thời gian chạy `soat_tran.py`: ~11 s (dựng phòng 9 s).

## Nhận diện
- **Căn hộ:** CH02 (phía trên, 11 phòng: P. khách + bếp 61,1 m², 4 PN, 3 WC, đa năng, 2 lô gia) và CH01 (phía dưới, 9 phòng: P. khách + bếp 40,7 m², 3 PN, 3 WC, đa năng, lô gia đôi). Ranh hai căn ở tường y ≈ −16.300 (khớp nguồn xref: nội thất căn dưới thuộc `CH03$0$…`).
- **Phòng:** 20/20 vùng tên phòng có ranh; 4 PN của CH02 nằm ở mặt dựng vẽ ngắt quãng → ranh gần đúng (khép khe 1,0 / 1,0 / 1,6 / 2,6 m).
- **Thiết bị (159):** LT-DL-D90 74, SP-D15-68 29, FA-SMOKE 11, AC-AP-600 8, HV-EAG-200 7, HV-SAG 6, HV-RAG 6, LT-MIR-D65 6, LT-OUT 4, LT-PEND 4, FA-HEAT 2, SP-D15-93 2.
- **Nội thất:** giường 7, tủ áo 7, bồn cầu 6, tủ gương 6, sen 6, bàn ăn 6, vách tắm 3, chậu rửa 2, sofa 2, bếp 1.
- **Block chưa nhận diện (19):** `SVC-7654` (Ø154, layer `A-Den` / `A-Hoan thien tran`, chủ yếu trong WC và hành lang), `LOA` (loa), `3453` (200×200 trên `A-HVAC2`) – chờ người dùng xác nhận loại.

## Cảnh báo (16) và đề xuất (13 đèn mới)
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

## Lỗi đã sửa khi chạy mẫu (để không lặp lại)
- `_doan_cua` (skill `dien-tich-ch`) đọc đỉnh LWPOLYLINE theo OCS → cửa chèn lật gương (extrusion 0,0,−1) bị đảo dấu X, mất cửa sổ mặt dựng và nối nhầm phòng. Đã đổi sang `vertices_in_wcs()`.
- Khép ranh gần đúng: union toàn bộ nét rồi buffer (12.000 đoạn khung cửa chi tiết) mất > 10 phút → nong từng đoạn rồi union, tính một lần (1,5 s).
- Nhóm căn bằng nong ranh 400 mm làm dính hai căn qua tường chung → nối phòng qua cửa đi.
- `-LAYER` trong script với tên layer có dấu cách làm treo accoreconsole → tạo layer/đặt layer bằng LISP.

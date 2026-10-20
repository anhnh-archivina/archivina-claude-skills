# Quy luật bố trí thiết bị trần học từ MB trần CT1 / CT3 (20/10/2026)

Nguồn: `H:\@AI Claude Test\02-Du-An\mặt bằng trần căn hộ\` – `CT1-Mat Bang Tang 5A-10.dwg` (19 căn) và `CT3 - Mat bang tang 3-21.dwg` (20 căn); mm, `INSUNITS=4`. Đọc trên bản sao (xuất DXF, nổ ACA), dựng phòng bằng `soat_tran.py`, đo bằng script. Mẫu: 96 PN, 34 P. khách/ăn/bếp (+7 ô gộp), 95 WC, 48 lô gia, 56 phòng nhỏ chưa tên.

**Người dùng chốt 20/10/2026:** học **số đông**; giữ HARD-RULE đèn ≥ 1200 / cách tường ≥ 500 – ngoại lệ trong 2 bản vẽ vẫn là lỗi (soát lại: CT3 92, CT1 115 HARD-RULE, chủ yếu đèn < 1200 / < 500 và 16 cặp đèn PN chèn trùng).

## Phòng ngủ
| Quy luật | Số liệu |
|---|---|
| Đèn theo **hình chữ nhật trục cách tường / mặt tủ 600** | đèn–tường trung vị 600 (p25 599, p75 600); hàng chân giường → biên phòng trung vị 600 |
| **Không đối xứng trục giường** (giường lệch tâm phòng trung vị 452) | chỉ 24/195 cặp đèn đối xứng trục giường |
| **Không đèn trên thân giường** (kẹp hai bên / ngoài chân giường) | 95/96 phòng; cặp đèn kẹp giường cách 2000–2500 (giường 1600–1800) |
| Số đèn / hàng: ≤ 2500 → 2; 2500–4000 → 3; > 4000 → 4 | hàng 2000–2500: 2 đèn; 3300–3900: 3 (một khoảng 2200–2300 kẹp giường + khoảng 1100–1700); 4700–5200: 4 |
| Đầu báo khói 1/phòng, hàng đèn **phía chân giường, giữa hai đèn** | 86/95 giữa 2 đèn; lệch trục giường thường ≤ 200 |
| Sprinkler 1–2, trên đường giữa phòng, thẳng hàng đèn | 157/160 thẳng hàng; 1 đầu: HCN đèn dài trung vị 2200 (PN ~11 m²); 2 đầu: dài trung vị 3900 (PN ~16 m²) |
| Không gió, không lỗ thăm | 0/96 |

## P. khách + ăn + bếp
| Quy luật | Số liệu |
|---|---|
| 2 hàng đèn chính cách tường 600; khoảng đèn liền kề ~1400 | 14–21 đèn (~2,5 m²/đèn); khoảng trung vị 1400 (p25 1230); 31/141 khoảng < 1200 (lỗi theo luật giữ 1200) |
| Cửa gió 1200×150 **trên hàng đèn, xen giữa 2 đèn**; cấp / hồi thành cặp đối diện thẳng hàng | 191/206 trên hàng đèn; tâm cửa – tâm đèn ~700–750; 31–46 m²: 2 cấp + 2 hồi; 47–61 m²: 3–4 cấp + 2–4 hồi |
| **Đường giữa** hai hàng đèn: đèn thả, đầu báo khói, loa, miệng gió tươi / hút chung (HV-EXG-200), sprinkler | đầu báo / loa / EXG cách tường ~1600 |
| **Đèn thả 2**: bàn ăn + bàn trà / bộ sofa, nằm trên đường giữa tại **hình chiếu tâm bàn** | 32/34 phòng có 2 đèn thả; lệch tâm bàn ăn: dọc hàng trung vị 124, vuông góc trung vị 581 (max 955); 37/38 đèn thả sofa nằm trong hộp bao sofa |
| Đầu báo nhiệt 1/căn, thẳng hàng đèn bếp, gần bếp nấu | 39/39 thẳng hàng đèn; cách tâm bếp nấu trung vị 756 |
| Sprinkler 93°C cạnh đầu báo nhiệt | cách đầu báo nhiệt 300 / 450 / 600; cách tâm bếp nấu trung vị 808 |
| Loa báo cháy 1/căn, đường giữa, cách đầu báo khói ~1400 | 31/33 thẳng hàng đèn |
| **Lỗ thăm sát biên**: tâm cách tường 450, **gần khu WC / kho / sảnh** | 29/33 gần WC hoặc kho / sảnh nhất (cách 0,8–1,7 m); cách bếp nấu 1,8–6,3 m; không ở 1/3 giữa phòng |

## WC
| Quy luật | Số liệu |
|---|---|
| **2 đèn** WC (không 4 góc) | 87/95 (6 WC ~6,5–6,9 m² có 4 đèn) |
| Đèn 1 trên **trục bồn cầu**, cách tường sau bồn cầu ~850 | 80/87 lệch trục ≤ 60; cách tường sau bồn cầu trung vị 835 (p25 780, p75 972) |
| Đèn 2 trên **trục sen / vùng tắm**, cùng đường với đèn 1 | 48/87 lệch trục sen ≤ 60; khoảng 2 đèn 900–1500 hoặc 2100–2200 (WC: 1200/500 chỉ DESIGN) |
| **Quạt hút ngay trên tâm bồn cầu** (WC vuông lẫn dài) | lệch trung vị 52 mm, cách tường ~400 |
| **D65 trên trục chậu, cách tường gương 350** | lệch tâm block chậu trung vị 75; cách tường 350–360 |
| Lỗ thăm 600 tâm cách tường 450 (trên vùng cánh cửa – giữ luật 05/10/2026) | 86/95 WC có lỗ thăm; tâm cách tường trung vị 450 |
| Không sprinkler / đầu báo | 94/95 |

## Lô gia
- Đèn ngoài nhà trên trục giữa bề rộng. Dài ≤ 5,3 m: 1 đèn giữa (28 lô gia); ≥ 5,8 m: 2 đèn (19 lô gia). Người dùng chốt: **> 5,5 m chia đều theo chiều dài (1/4, 3/4)**.

## Phòng nhỏ
- Sảnh / hành lang / phòng chưa rõ 1,3–6 m²: ≤ 4,9 m² 1 đèn tâm; 5–6 m² 2–3 đèn; luôn 1 đầu báo khói + 1 sprinkler.
- **Kho / P. kỹ thuật** (người dùng xác nhận; 15 phòng 1,5–1,9 m²): 1 đèn tâm + quạt hút (HV-EAG-200) + miệng hút (HV-EXG-200) hai đầu trục dài + đầu báo khói + sprinkler. Nhận diện: theo tên phòng (kho / kỹ thuật); bản vẽ không tên → ô < 3 m² không có nội thất nhưng có quạt hút / miệng hút (CT3: 6 kho). **Kho chưa có đèn → bổ sung 01 downlight tại tâm phòng** (người dùng chốt 20/10/2026): soát báo DESIGN "Kho chưa có đèn" + đề xuất; bố trí mới chèn đèn kể cả khi kho đã có thiết bị khác. Thử giả lập bỏ đèn 6 kho CT3: soát 6/6 cảnh báo + đề xuất, bố trí 6/6 đèn.

## Nhận diện sửa theo dữ liệu
- Block đèn thả `den ban an` từng khớp mẫu bàn ăn `*ban an*` → thêm `loai_tru` cho `ban_an` (đèn thả không còn bị coi là bàn ăn).
- Bếp nấu trong CT1/CT3: block `86786`, `567` (5 vòng tròn R60–140 = vùng nấu) → thêm vào `noi_that.bep_nau`.

## Kiểm chứng (bố trí mới `--bo-qua-co-san` trên chính 2 bản vẽ, so với thiết bị thật)
| Phòng – thiết bị | Đúng số lượng | Trùng vị trí ≤ 300 mm |
|---|---|---|
| WC – quạt hút / D65 / đèn / lỗ thăm | 88/95 · 94/95 · 87/95 · 64/95 | 98% · 94% · 65% · 65% |
| Lô gia – đèn | 47/48 | 71% |
| PN – đèn / đầu báo / sprinkler | 57/97 · 91/97 · 71/97 | 58% · 55% · 40% |
| P. khách – đầu báo nhiệt / SP 93°C / đầu báo khói / loa / EXG / đèn thả | 28/34 · 32/34 · 31/34 · 27/34 · 32/34 · 25/34 | 0–32% (đường giữa khác vị trí cột đèn) |
| P. khách – đèn | 2/34 (thiếu TB 3,9 đèn: phòng chữ L, hốc) | 47% |
| P. khách – lỗ thăm | 29/34 | cách vị trí thật trung vị ~1,5 m |
- Tỷ lệ phủ sprinkler chọn **85 %** (99 % dư ~2 đầu / phòng; 90 %: PN +0,39, P. khách +0,61; 80 %: PN −0,02, P. khách −0,50).
- Chưa đạt: P. khách hình chữ L / nhiều hốc vẫn ít đèn hơn thiết kế thật; kho không tên không nhận được.

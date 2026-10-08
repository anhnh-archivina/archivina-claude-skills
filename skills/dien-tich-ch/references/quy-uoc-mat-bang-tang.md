# Quy ước đo mặt bằng tầng nhiều căn (Archivina)

Nguồn: bản vẽ `CT1-Mat Bang Tang 5A-10 (test DT).dwg` (19 căn CH01–CH19, đo ngày 06/10/2026) và các quyết định người dùng chốt cùng ngày. Script: `scripts/mat_bang_tang.py`. Quy tắc đo chung (mốc đo, HKT, làm tròn) vẫn theo `quy-tac-do.md`.

## Mục lục
1. Quyết định đã chốt
2. Đặc điểm bản vẽ tầng và cách script xử lý
3. Phân loại vùng chưa có tên
4. Gom căn và ghép mã căn
5. Nhãn
6. Việc chưa chốt / giới hạn
7. Kết quả kiểm chứng CT1

## 1. Quyết định đã chốt (06/10/2026)
1. **Vách kính / cửa sổ góc không có tường:** ranh phòng theo **mặt trong kính/khung** (quy tắc C: vách kính mặt dựng đo từ mặt trong). Không kéo thẳng mặt trát. Đố nhôm lồi vào ~130 mm không trừ. **Sửa 08/10/2026 (quyết định 11):** kính/khung đặt **ngoài** mặt phẳng tường thì đo theo đường kéo dài mặt tường, không theo kính.
2. **Ô mở chưa vẽ cửa rộng 1,2–2,6 m** (cửa trượt ra lô gia, cửa sổ ra giếng trời): đóng bằng đoạn thẳng nối **mặt trát hai bên**.
3. **Sinh hoạt chung + Bếp không có vách:** gộp **một polyline** "Sinh hoạt chung + Bếp" (như căn mẫu Cần Thơ).
4. **Lô gia không có text tên:** tự nhận (giáp lan can `A-Lancan` / lam nhôm `Nhom`, hoặc có máy giặt/cục nóng điều hòa), đặt tên "Lô gia", đo đến mặt trong lan can, tách dòng riêng, tính 100% vào DTCH. Báo Lỗi thiếu tên.
5. **Vùng có nội thất nhưng thiếu text tên:** đặt tên theo nội thất (thiết bị vệ sinh → Wc; máy giặt/cục nóng → Lô gia; giường/tủ áo → Phòng ngủ), vẽ polyline + tên + nhãn, báo **Lỗi thiếu tên phòng** để nhân viên bổ sung text. Luôn trình ảnh để người dùng duyệt trước khi vẽ.
6. **(07/10/2026, người dùng soát CT1 và khoanh lỗi) Không gian có cửa đi là PHÒNG.** Hộp kỹ thuật (HKT) phải được xây tường kín xung quanh, không có cửa. Vùng có cung quay cánh cửa mở vào:
   - cửa mở từ phòng của căn → phòng của căn (tên theo nội thất, không có nội thất thì "Phòng chưa tên", báo Lỗi thiếu tên);
   - cửa mở từ hành lang chung → phòng chung (phòng kỹ thuật/sinh hoạt chung), ngoài căn.
   Lỗi đã gặp: CH07 kho 1,26 m² có cửa bị coi là HKT.
7. **(07/10/2026) Hốc sảnh trước cửa phòng ngủ/WC** (không gian thông với phòng khách qua ô mở, không có cửa) **gộp vào phòng nó thông ra**, ưu tiên phòng khách/sinh hoạt chung. Không tách thành vùng riêng. Lỗi đã gặp: CH08, CH10 (và cùng loại CH06, CH11, CH12, CH14, CH17, CH19).
   - Chỉ gộp hốc rộng ≥ 600 mm. Dải hẹp hơn là tường/bậu, không gộp vào phòng; nếu là khối `S-Wall` thì không tính vào DTCH (quyết định 10).
   - Giữa hốc và phòng thường có khe 60–120 mm (các dải vữa trát): lấp bằng dải chữ nhật dọc theo đoạn đóng ô mở, rộng bằng khe.
8. **(07/10/2026) Góc đặt cục nóng / máy giặt cạnh lô gia** (giáp lan can/lam nhôm, hoặc có cục nóng/máy giặt) là **lô gia**, kể cả khi nhỏ hơn 2 m². Không phải HKT. Lỗi đã gặp: CH01 góc 1,5 m² bị loại, DTCH thiếu 2,0 m². Yêu cầu bề rộng ≥ 400 mm để loại dải tường/bậu sát lan can.
9. **(07/10/2026) Nhãn diện tích phòng và `DTCH` là Field** liên kết polyline (căn có HKT/cột dùng Field công thức trừ lỗ), để người dùng sửa tay đường bo. Gắn bằng `gan_field_dien_tich.py` sau khi vẽ (hoặc `ve_com_tab_mo.py` tự gắn). CT1 5A-10: 196/196 nhãn (177 phòng + 19 căn).
10. **(07/10/2026, vòng tròn CH03) Khối vách BTCT (`S-Wall`) không tính vào DTCH**, kể cả khi nằm giữa phòng và lô gia hay giữa hai phòng trong căn. Cách tính giống cột, hộp kỹ thuật và giống bản vẽ mẫu HGC (vách S-Wall nằm ngoài đường bo).
    - Vùng có ≥ 60% diện tích nằm trong polyline kín/hatch `S-Wall` (`--layer-vach`) được xếp loại **"vách BTCT"**. Loại này được xét trước mọi loại khác: không phải hành lang, không phải lô gia.
    - Khi dựng đường bo căn: trừ mọi khối S-Wall giao với căn > 0,05 m². Khối nằm giữa căn thành polyline loại trừ; khối ở biên thì đường bo đi vòng.
    - Báo cáo ghi Gợi ý "Vách BTCT" cho từng khối.
    - Lỗi đã gặp ở CT1: 12 khối S-Wall dày 350–500 mm bị xếp "hành lang" (lấp vào DTCH) ở CH01, CH02, CH03, CH05, CH16, CH18. Khối 500 mm ở CH02 còn bị nhận nhầm là "Lô gia 1,3 m²" (giáp lan can).
    - Dấu hiệu để rà: hai căn đối xứng lệch DTCH (CH01 170,8 so với CH02 172,3).

### Lỗi người dùng sửa tay trên CT1 (08/10/2026, file `CT1-T5A-10_dien-tich-thong-thuy sửa lỗi.dwg`, ghi chú 1–7)
Script `scripts/chinh_hinh.py` xử lý tự động; `mat_bang_tang.py xuat` gọi sau khi dựng phòng (bỏ bằng `--khong-chinh-hinh`). Nét nền phân lớp: trát (`A-Vua trat`), lõi tường (`A-Wall`, `S-Wall`, `A-Column`), bậu (`A_Wall BT`, `A-Line`, `A-Lancan`), kính/khung (`A-Door`, `A-Cửa`, `A-Window`, kính, nhôm, layer đố `4`).
11. **(lỗi 1, 2) Đo vuông góc theo nét, không đo chéo; vách kính đặt ngoài mặt tường.** Cửa sổ/vách kính (kể cả góc) có khung nằm ngoài mặt phẳng tường (CT1: kính ở y = 136, mặt tường y = 0): ranh theo **đường kéo dài mặt tường qua đầu tường**, hai mặt gặp nhau vuông góc ở góc; phần lồi ra kính (sâu ≤ 400 mm) không tính. Chỉ cắt khi biên phần bị cắt chủ yếu không bám tường và ≥ 30% bám nét kính/khung (không cắt nhầm đoạn đóng ô mở). Không dùng làm gọn Douglas–Peucker 10 mm: nó xóa bậc 10–15 mm trên cạnh dài thành cạnh xiên (đo chéo); cạnh lệch 1,5–40 mm được nắn thành bậc vuông, góc chọn theo nét nền.
12. **(lỗi 3) Không gấp khúc ở góc tường 90° hoặc chỗ tường vẫn thẳng:** bỏ gai/khấc ≤ 60 mm (đỉnh lệch khi hai đỉnh kề cùng trục), khấc 2 đỉnh ≤ 150 mm, vát chéo ≤ 120 mm ở góc vuông → góc vuông.
13. **(lỗi 4) WC trừ cả lớp ốp: 10 mm.** Cạnh WC đã nằm trên nét ốp (nét `A-Vua trat` song song cách mặt trát 6–14 mm phía tường) thì giữ; chưa có nét ốp thì lùi 10 mm (`--op-wc`). Người dùng mới sửa cạnh WC giáp tường bao (ảnh hưởng DTCH); script áp cho mọi cạnh tường của WC theo câu "các khu WC phải trừ cả lớp ốp".
14. **(lỗi 5) Mặt đầu tường gạch chưa vẽ trát cũng trừ trát 15 mm:** cạnh ngắn (≤ 350 mm) nằm trên nét lõi tường, không có nét trát → lùi 15 mm. Mặt tường **dài** không vẽ trát vẫn giữ nguyên (quy tắc 05/10/2026).
15. **(lỗi 6) Không tính tường bao ngoài:** đường bo căn = hợp phòng + **dải tường giữa hai mặt phòng đối diện** (cách ≤ `--day-tuong-max` + ốp) + lấp lỗ nhỏ < 0,15 m² ở chỗ giao tường (giữ lỗ là cột trong phòng). Không dùng khép hình (buffer +150/−150) vì nó lấp cả góc lõm ngoài nhà (CT1 CH04: tường 165 × 600 mm cạnh lô gia).
16. **(lỗi 7) Lô gia/ban công đo tới mặt trong bậu BT/lan can:** cạnh lô gia kéo ra nét bậu gần nhất phía ngoài (≤ 80 mm), CT1: −22695 → −22660, 22895 → 22930.
17. Kiểm chứng: CH02 tự động 167,553 m² so với người dùng sửa tay 167,549; CH04 83,804 so với 83,801 (chênh < 0,01 m², do dải 5–10 mm).

## 2. Đặc điểm bản vẽ tầng và cách script xử lý
- **Căn hộ là xref đã bind** (layer `CH15$0$A-Wall`, `CT1-T0-CH05$0$A-Vua trat`); có xref phụ `CT1-T(3-10)-CH12` (phần sửa cho tầng 3–10), `Tuong PCCC`, `Loi Thang`. DXF xuất có nổ ACA: 26 block chứa 719 tường, 208 cửa, 36 cửa sổ ACA.
- **Nét ở layer 0 trong block** lấy theo layer của INSERT chứa nó (quy ước AutoCAD). CT1 có khoảng 2.500 nét lan can như vậy. Đã sửa luôn trong `tpp.walk` (dùng chung cho mọi script), chạy hồi quy trên Cần Thơ / Test AI / Test đo dt: kết quả không đổi.
- **Layer ranh phụ** (`--layer-ranh-phu`): `A-Lancan, A_Wall BT, S-Wall, Nhom, 玻璃层, Kính, A-Wall-G, A-Window-G`. Chỉ lấy nét dài ≥ 200 mm (`--do-dai-phu-min`). Nếu lấy hết song lan can, đố kính thì chạy chậm hơn khoảng 15 lần và sinh hàng nghìn mặt vụn.
- **Đoạn đóng dài** (1,2–2,6 m, `--gap-dai`): dựng hết, rồi xét từng đoạn theo hai mặt ở hai bên:
  - hai bên đều là không gian mở (regex `--khong-gian-mo`: sinh hoạt/khách/bếp/ăn) → **bỏ**, gộp lại;
  - một bên là phòng có tên, bên kia là vùng chưa tên **không** giáp lan can/kính/nhôm và < 25 m² (hốc bếp, hành lang nhỏ trước WC, buồng xí trong WC) → **bỏ**, gộp vào phòng;
  - còn lại → **giữ** (tách phòng ngủ/WC khỏi không gian chung, tách lô gia).

  Kiểm chứng CT1: 4 đoạn cắt hốc và 2 đoạn chia không gian mở đã được gộp lại đúng. Ví dụ đã gặp: WC 4,75 m² bị cắt còn 3,38 m², Đa năng 5,91 m² bị cắt còn 3,60 m².
- **Mặt trong vách kính:** áp cho phòng còn hở sau lần dựng đầu.
  - Tấm kính nằm rời trên 2 layer xen kẽ: `玻璃层` trong block cửa sổ và `A-Door` ở Model. Nét kính trên `A-Door` nhận bằng **cặp nét song song cách 2–8 mm** (cánh cửa đi dày ~40 mm nên bị loại).
  - Gom tấm kính theo phương và độ lệch, lấy độ lệch gần phòng nhất, kéo liền qua đố (khe ≤ 300 mm).
  - Nối đầu vào tường gần nhất ≤ 300 mm. Khi tìm tường để nối, **không lấy chính layer kính**.
  - Cửa sổ góc chữ L: kéo hai đường vuông góc cho gặp nhau.
- **Nối khe vẽ 6–25 mm** giữa đầu nét tự do và nét gần nhất (mặt trát dừng cách tường 15 mm ở góc cửa sổ).
- Polyline làm gọn 10 mm (`--don-gian`), bỏ răng cưa đố kính; diện tích nhãn tính trên chính hình vẽ ra, lỗ < 0,01 m² bỏ.

## 3. Phân loại vùng chưa có tên (`phan_loai_vung.png`, số #)
| Loại | Điều kiện | Xử lý |
|---|---|---|
| ngoài căn | tiền tố xref < 60% nét bao (giáp 2 căn/hành lang) | không tính |
| phòng chung | có cửa mở từ hành lang chung | ngoài căn |
| lô gia | giáp lan can/lam nhôm hoặc có cục nóng/máy giặt, không có cửa, rộng ≥ 400 mm (kể cả góc máy < 2 m²) | polyline "Lô gia", tính 100% |
| phòng thiếu tên | nét nội thất ≥ 3 m và ≥ 2,5 m², **hoặc có cửa mở từ trong căn** | tên theo nội thất: TB vệ sinh ≥ 8 m → Wc; máy giặt/cục nóng → Lô gia; ≥ 6 m² → Phòng ngủ; còn lại "Phòng chưa tên"; vẽ polyline, báo Lỗi thiếu tên |
| hốc sảnh/hành lang | có ô mở (không cửa) sang phòng cùng căn, < 6 m² | rộng ≥ 600 mm: **gộp vào phòng thông ra** (ưu tiên sinh hoạt chung); hẹp hơn (tường/bậu): chỉ tính vào DTCH |
| vách BTCT | ≥ 60% diện tích nằm trong khối `S-Wall` (xét trước mọi loại khác) | không tính; khối S-Wall giao căn bị trừ khỏi đường bo |
| loại trừ | **xây kín, không cửa**, không nội thất, không giáp lan can (HKT, khoảng trống) | không tính; nằm trong căn thì thành polyline loại trừ; script báo Lỗi nếu phần loại trừ có cửa |

CT1: #23 (18,8 m²) và #84 (17,3 m²) có cửa đôi mở từ hành lang chung → phòng chung, ngoài căn. Hai căn đối xứng phân loại khác nhau → chỉnh cho thống nhất bằng `--doi` sau khi hỏi (CT1 #38/#76 trước phải đổi tay, nay tự nhận là vách BTCT).

## 4. Gom căn và ghép mã căn
- Không gom được theo khoảng cách: tường chung giữa hai căn dày ≤ 200 mm, bằng tường ngăn trong căn, nên khép hình 100–250 mm vẫn gộp 19 căn thành 9–11 khối. Cũng không gom được theo cửa: cửa chính thiếu, kính mặt ngoài nối nhầm các căn.
- Cách làm: mỗi phòng thuộc xref chiếm phần lớn chiều dài nét bao quanh (≤ 60 mm từ biên). Tên xref chuẩn hóa bằng regex `--xref-can` (`CH\d+[A-Z]?`), ví dụ `CT1-T0-CH05A` → CH05A, `CT1-T(3-10)-CH12` → CH12. Xref lõi thang, tường PCCC không có mã nên bị bỏ.
- Ghép mã căn (`--ma-can`, text trên `A-Text`): cặp xref–mã gần nhất trước, mỗi bên dùng một lần, ≤ 4 m. CT1: xref CH05A = CH01, CH05 = CH02, CH03 = CH03, CH06 = CH04, CH02 = CH05, CH08A = CH06, CH01 = CH07, CH19 = CH08, CH18 = CH09, CH08 = CH10, CH09 = CH11, CH10 = CH12, CH17 = CH13, CH16 = CH14, CH15 = CH15, CH15A = CH16, CH11 = CH17, CH12A = CH18, CH12 = CH19. Tên xref là loại căn, khác số căn trên mặt bằng.
- Đường bo căn = hợp phòng + lô gia + hành lang trong căn, khép hình `--day-tuong-max/2` = 150 mm (lấp tường ngăn ≤ 300 mm). Lỗ còn lại = polyline loại trừ (HKT 0,54–1,30 m²/căn ở CT1).

## 5. Nhãn
- Nhãn m² phòng: dưới tên phòng như skill gốc. Nếu không lọt hẳn trong phòng (phòng hẹp, tên sát tường), đặt phía trên tên; nếu vẫn không được thì đặt ở chỗ trống gần tên. Nhãn đặt dưới tên mà rơi ra ngoài polyline làm `kiem_tra_nhan.py` báo "không có nhãn" (CT1 lần 1: 7 lỗi).
- Phòng/lô gia không có text: ghi tên + nhãn m², cùng style/layer/cao với tên phòng khác trong căn.
- DTCH (cao 1,5 × chữ tên phòng): tìm chỗ không đè gì trong phòng sinh hoạt chung → nếu không có, cho đè nét nội thất (vẫn tránh tường, cửa, kính, chữ) → nếu vẫn không có, chỗ trống trong căn → cuối cùng đặt dưới nhãn m² phòng khách. Từ bước thứ hai trở đi ghi Cảnh báo. CT1: chữ tên phòng cao 250, nhãn DTCH cao 375, rộng ~3,9 m; 15/19 căn phải đè nội thất.
- Vật cản chỉ lấy tường/cửa/kính/nội thất/thiết bị. Nếu lấy cả nét khuất (`A-Hidden`), hoàn thiện sàn, hatch thì gần như không căn nào tìm được chỗ.

## 6. Chưa chốt / giới hạn
- **Ranh tại cửa chính** (quy tắc C: theo mặt ngoài tường hành lang): CT1 không vẽ cửa chính ở 12/19 căn nên chưa áp dụng thống nhất. Đường bo đang theo mặt tường trong (thiếu ~0,2 m²/căn); script báo Cảnh báo kèm danh sách căn. Hỏi người dùng.
- Tên đề xuất theo nội thất chỉ là đề xuất. Nhận giường còn yếu (CT1 #48 chỉ có 10,6 m nét không tên block), nên luôn trình ảnh.
- Bản vẽ không có xref căn hộ → script dừng, dùng `tao_duong_bo_can_ho.py`.

## 7. Kết quả kiểm chứng CT1 tầng 5A-10
Lần 1 (06/10/2026): người dùng soát và khoanh 5 vị trí sai (hốc sảnh CH08, CH10; kho có cửa CH07; góc máy cạnh lô gia CH01; một vị trí ở CH03 chưa rõ). Lần 2 (07/10/2026) theo quy tắc 6–8, DTCH (m²): CH01 170,8 · CH02 172,3 · CH03 122,9 · CH04 83,6 · CH05 122,8 · CH06 84,1 · CH07 131,2 · CH08 105,7 · CH09 118,7 · CH10 85,5 · CH11 88,6 · CH12 85,2 · CH13 118,8 · CH14 105,7 · CH15 130,9 · CH16 123,2 · CH17 84,3 · CH18 135,6 · CH19 109,6. Sinh hoạt chung tăng 1,3–2,4 m² ở 8 căn do gộp hốc sảnh; 8 kho/phòng có cửa thành phòng.
Lần 3 (07/10/2026), theo quyết định 10 (vách S-Wall), DTCH (m²):
- Đổi: CH01 168,3 · CH02 168,4 · CH03 121,3 · CH05 121,2 · CH16 121,6 · CH18 134,1.
- Còn lại như lần 2.
- 177 phòng + lô gia (bỏ lô gia giả ở CH02). Nhãn Field 196/196; `kiem_tra_nhan` đạt 196/196; không còn khối S-Wall nào nằm trong DTCH.
Lần 4 (08/10/2026), theo quyết định 11–16 (bản sửa lỗi 1–7 của người dùng), DTCH (m²):
- CH01 167,4 · CH02 167,6 · CH03 121,5 · CH04 83,8 · CH05 121,4 · CH06 84,3 · CH07 130,8 · CH08 105,8 · CH09 118,7 · CH10 85,8.
- CH11 88,9 · CH12 85,4 · CH13 118,8 · CH14 105,8 · CH15 130,4 · CH16 121,8 · CH17 84,5 · CH18 133,6 · CH19 109,1.
- Nhãn Field 196/196; `kiem_tra_nhan` 196/196.
- CH01 và CH02 lệch 0,2 m² do nền khác nhau: CH02 có khối S-Wall 2650×500 tại (23430, −13030), CH01 không có khối ở vị trí đối xứng.

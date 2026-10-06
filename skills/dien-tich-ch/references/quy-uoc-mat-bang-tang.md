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
1. **Vách kính / cửa sổ góc không có tường:** ranh phòng theo **mặt trong kính/khung** (quy tắc C: vách kính mặt dựng đo từ mặt trong). Không kéo thẳng mặt trát. Đố nhôm lồi vào ~130 mm không trừ.
2. **Ô mở chưa vẽ cửa rộng 1,2–2,6 m** (cửa trượt ra lô gia, cửa sổ ra giếng trời): đóng bằng đoạn thẳng nối **mặt trát hai bên**.
3. **Sinh hoạt chung + Bếp không có vách:** gộp **một polyline** "Sinh hoạt chung + Bếp" (như căn mẫu Cần Thơ).
4. **Lô gia không có text tên:** tự nhận (giáp lan can `A-Lancan` / lam nhôm `Nhom`, hoặc có máy giặt/cục nóng điều hòa), đặt tên "Lô gia", đo đến mặt trong lan can, tách dòng riêng, tính 100% vào DTCH. Báo Lỗi thiếu tên.
5. **Vùng có nội thất nhưng thiếu text tên:** đặt tên theo nội thất (thiết bị vệ sinh → Wc; máy giặt/cục nóng → Lô gia; giường/tủ áo → Phòng ngủ), vẽ polyline + tên + nhãn, báo **Lỗi thiếu tên phòng** để nhân viên bổ sung text. Luôn trình ảnh để người dùng duyệt trước khi vẽ.

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
| lô gia | giáp lan can/lam nhôm, ≥ 2 m² | polyline "Lô gia", tính 100% |
| phòng thiếu tên | nét nội thất ≥ 3 m, ≥ 2,5 m² | tên theo nội thất: TB vệ sinh ≥ 8 m → Wc; máy giặt/cục nóng → Lô gia; ≥ 6 m² → Phòng ngủ; còn lại "(chưa rõ)" (chỉ tính vào DTCH, hỏi tên) |
| hành lang/ô cửa | có ô mở sang phòng cùng căn, < 4,5 m² | tính vào DTCH, không vẽ polyline phòng |
| loại trừ | kín, không cửa, không nội thất (HKT, bệ máy lạnh, giếng trời) | không tính; nằm trong căn thì thành polyline loại trừ |

Vùng lớn kín không cửa (CT1: #23 18,8 m², #84 17,3 m²) → giếng trời/khoảng trống, báo Cảnh báo. Hai căn đối xứng phân loại khác nhau (CT1: #38/#76) → chỉnh cho thống nhất bằng `--doi` sau khi hỏi.

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
DTCH (m²): CH01 168,8 · CH02 170,9 · CH03 122,9 · CH04 83,6 · CH05 122,8 · CH06 84,1 · CH07 129,4 · CH08 105,7 · CH09 118,7 · CH10 85,5 · CH11 86,6 · CH12 85,2 · CH13 118,8 · CH14 105,7 · CH15 129,1 · CH16 123,2 · CH17 84,3 · CH18 135,6 · CH19 109,6. DTCH − Σ phòng − Σ lô gia dương ở cả 19 căn (5,2–9,7 m²). `kiem_tra_nhan.py`: 187/187 vùng đạt.

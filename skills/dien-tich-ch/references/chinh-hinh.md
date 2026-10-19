# Chỉnh hình theo bản sửa lỗi 1–7 (08/10/2026; áp cho căn đơn lẻ từ 10/10/2026)

`tao_polyline_phong.py`, `tao_duong_bo_can_ho.py`, `mat_bang_tang.py` dùng chung `scripts\chinh_hinh.py`. Mặc định bật; tắt bằng `--khong-chinh-hinh` (kết quả trùng bản trước 10/10/2026). Lý do từng bước và số liệu hồi quy: `quy-uoc-mat-bang-tang.md` (quyết định 11–17) và `quy-uoc-ve-polyline-phong.md` (mục 9).

## Nét nền phân lớp
- Trát: `A-Vua trat`.
- Lõi tường: `A-Wall`, `S-Wall`, `A-Column`.
- Bậu/lan can: `A_Wall BT`, `A-Line`, `A-Lancan`.
- Kính/khung: layer cửa (`--layer-cua`, gồm `A-Glaz`, `A-Window`) + các layer kính của CT1.

## Polygon từng phòng, theo thứ tự
1. Nắn cạnh xiên thành bậc vuông góc.
2. Bỏ gai, khấc ≤ 60 mm, vát chéo ở góc 90°.
3. Cắt phần lồi ra kính/khung nằm ngoài mặt tường: ranh theo đường kéo dài mặt tường.
4. Phòng tên WC / vệ sinh / tắm trừ ốp 10 mm (`--op-wc`, `--ten-wc`), trừ khi đã vẽ nét ốp.
5. **Mặt đầu tường** (cạnh ≤ 350 mm) nằm trên lõi tường, chưa vẽ trát: lùi 15 mm (`--trat-dau-tuong`).
6. Phòng tên lô gia / logia / ban công: kéo ra mặt trong bậu (≤ 80 mm).
7. Bỏ đỉnh thừa.

Mặt tường **dài** không vẽ trát vẫn **không** lùi (quy tắc 05/10/2026).

## Đường bo căn
Hợp các phòng đã chỉnh + dải tường giữa hai mặt phòng đối diện (≤ `--day-tuong-max` + ốp). Lỗ < 0,15 m² được lấp; lỗ là cột/HKT của phòng được giữ. Không lấp góc lõm nên không ăn vào tường bao ngoài. Sau đó chỉ nắn vuông và bỏ đỉnh thừa, không cắt kính trên đường bo. Không làm gọn Douglas–Peucker (`mat_bang_tang.py` chỉ dùng 0,5 mm khi bật chỉnh hình).

## Đầu ra
JSON có `chinh_hinh` (tổng và từng phòng); Excel ghi chú "Chỉnh hình: …"; `van_de` có dòng Gợi ý "Chỉnh hình".

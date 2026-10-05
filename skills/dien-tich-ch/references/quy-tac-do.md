# Quy tắc đo diện tích thông thủy Archivina

Nguồn gốc: người dùng đã chốt các quy tắc này, đối chiếu với bản vẽ mẫu HGC (căn CH15 – CT5), dẫn Điều 5 Thông tư 05/2024/TT-BXD (31/07/2024) và Luật Nhà ở 27/2023/QH15. `CLAUDE.md` ở thư mục gốc là bản chính; nếu hai nơi khác nhau thì theo `CLAUDE.md` và báo người dùng.

Chưa ai kiểm chứng lại với văn bản gốc. Khi cần kết luận pháp lý, hãy dặn người dùng đối chiếu `01-Quy-Chuan-Archivina\03-Quy-Dinh-Phap-Ly`.

## Mục lục
1. Mốc đo
2. Diện tích phòng
3. Diện tích căn hộ
4. Cách biểu diễn trên CAD (đường bo)
5. Làm tròn, ngưỡng sai lệch, đơn vị
6. Trường hợp phải dừng và hỏi
7. Ví dụ chuẩn: HGC CH15

## 1. Mốc đo
- Đo đến **mặt lớp trát hoàn thiện** của tường/vách, **theo nét đã vẽ**: đường bo bám tường Wall ACA, polyline bo cột, nét lớp hoàn thiện vữa, nét bao khung cửa sổ/cửa đi (không bám cánh mở). Bản vẽ không vẽ lớp trát 15 mm thì **không lùi 15 mm** (chốt 05/10/2026); ghi Gợi ý cho người vẽ.
- **Lớp ốp chỉ tính ở tường bên trong khu vệ sinh**; ốp ở vị trí khác không tính.

## 2. Diện tích phòng
- Đo thông thủy từng phòng theo mốc đo trên.
- Cột/vách BTCT **nhô vào phòng** (nằm trong căn): trừ khỏi diện tích phòng.
- Cột/vách **nằm trong chiều dày tường**: không trừ riêng.
- Hộp kỹ thuật (HKT) trong căn: không tính vào phòng, loại cả tường bao HKT.
- Ô cửa đi giữa hai phòng: không tính vào phòng nào, chỉ nằm trong diện tích căn.

## 3. Diện tích căn hộ (thông thủy)
- Tính từ **polyline ranh căn**, không cộng từ tổng phòng đã làm tròn.
- **Tính:** tường ngăn trong căn, ô cửa đi giữa các phòng, ban công/lô gia gắn liền với căn (100%, tách riêng một dòng trong bảng).
- **Không tính:** tường bao ngoài, vách kính mặt dựng (đo từ mặt trong); tường chung giữa hai căn (đo đến mặt tường); HKT trong căn; giếng trời/ô thông tầng.
- Cửa chính: ranh căn theo **mặt ngoài tường hành lang**.
- Ban công/lô gia: đo đến **mặt trong lan can/tường bao**; nếu có tường chung thì tính từ mép trong tường chung.
- Kiểm tra nội bộ: DT căn − Σ DT phòng (kể cả ban công/lô gia) ≈ tường ngăn trong căn + ô cửa đi. Âm hoặc quá lớn là bất thường (ranh chồng lấn hoặc sai).

## 4. Cách biểu diễn trên CAD (đường bo)
- **Đường bo thông thủy căn hộ** = **một polyline đóng** trên layer **`Dien tich thong thuy`**, chạy theo mặt trát trong của tường bao/tường chung/vách, ôm cả ban công/lô gia, tường ngăn trong căn nằm bên trong.
- **Phần loại trừ** (hộp kỹ thuật, cột trong căn): polyline đóng riêng, nằm **hoàn toàn trong** đường bo. Layer riêng chưa chốt; ưu tiên cùng layer `Dien tich thong thuy`, nhận diện bằng vị trí.
- **DT căn = DT đường bo − Σ DT phần loại trừ.**
- Đường bo ở layer khác (ví dụ `0`) là **Lỗi**.

## 5. Làm tròn, ngưỡng sai lệch, đơn vị
- Tính và so sánh trên giá trị chưa làm tròn; chỉ làm tròn khi hiển thị: **1 chữ số thập phân (m²), half-up** (86,1507 → 86,2).
- Đơn vị bản vẽ **mm** (`INSUNITS=4`, `LUNITS=2`); diện tích CAD là mm², chia 1.000.000 ra m². Khác chuẩn → báo Lỗi.
- Chênh lệch CAD so với bảng thống kê/hợp đồng: **> 0,5% là Lỗi; từ 0,3% đến 0,5% là Cảnh báo.**
- Nhãn diện tích trên bản vẽ phải bằng giá trị đo đã làm tròn.

## 6. Trường hợp phải dừng và hỏi (không tự suy đoán)
- Phòng/phần có trần thấp (< 1,5 m), phần dưới dầm, gầm cầu thang, mái dốc, tầng mái.
- Căn duplex/thông tầng, cầu thang trong căn.
- Cấu kiện chưa có quy tắc: vách kính nội bộ, lam, bậc cấp sàn, ô văng.
- Polyline loại trừ lồng nhiều cấp; hai đường bo chồng lấn; không rõ polyline nhỏ là loại trừ hay căn khác.

## 7. Ví dụ chuẩn: HGC CH15 – CT5
File: `05-Tham-Khao\01-Ban-Ve-Mau\HGC - Cach do dien tich can ho.dwg` (đơn vị mm).
- Đường bo: handle `202593`, polyline đóng 20 đỉnh, **86,7876 m²** (nằm ở layer `0`, chưa đúng chuẩn).
- Phần loại trừ: handle `202594`, hộp kỹ thuật 1355 × 470 mm, **0,6369 m²**.
- DT căn = 86,7876 − 0,6369 = 86,1507 m² → ghi **86,2 m²** (khớp nhãn trên bản vẽ).
- Đo thử theo handle: `--duong-bo 202593 --loai-tru 202594 --dt-thong-ke 86.2`.

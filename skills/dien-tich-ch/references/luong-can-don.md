# Luồng A – Căn hộ đơn lẻ: polyline phòng, đường bo căn, nhãn DTCH

Chỉ đọc khi làm luồng này. Quy ước chi tiết, số liệu kiểm chứng: `quy-uoc-ve-polyline-phong.md` (đọc khi gặp tình huống lạ). Lệnh dùng MCP `autocad-archivina` (tên tool) hoặc script tương đương trong `<skill>\scripts\`.

## Quy trình
1. **Đầu vào:** đường dẫn `.dwg`/`.dxf`, thư mục lưu kết quả (ưu tiên `03-Ban-Sao-Lam-Viec` của dự án). Thiếu thì hỏi.
2. **DWG → DXF có nhận diện đối tượng AutoCAD Architecture:** MCP `xuat_dxf` (mặc định nổ AEC) hoặc `scripts\dwg_to_dxf_aec.ps1 -Dwg … -OutDir …`. **Luôn dùng bản nổ AEC, không dùng `dwg_to_dxf.ps1`:** DXF xuất thường bỏ mất AEC_WALL/AEC_DOOR/AEC_WINDOW nên trông như bản vẽ không có tường. Tường nổ → INSERT chứa nét `A-Vua trat` (mặt hoàn thiện) và `A-Wall` (lõi); cửa đi → `A-Door`; cửa sổ → `A-Glaz`. File `<tên>_aec.txt` đếm AEC trước khi nổ (không có dòng `TRUOC` = bản vẽ không có AEC ở Model). AEC nằm trong xref/block không nổ được từ file này: mở chính file xref.
3. **Dựng polyline phòng:** MCP `dung_polyline_phong` hoặc `tao_polyline_phong.py <dxf> --out-dir …`.
   Tùy chọn hay dùng: `--layer-ranh "A-Vua trat,A-Wall,A-Column,A-Line"`, `--gap-max 1200`, `--them-ranh=x1,y1,x2,y2;…` (**có dấu `=`**, vì tọa độ âm bắt đầu bằng `-`), `--ve-lai`, `--nhan-tat-ca`, `--label-h 250` (chỉ cho phòng không có text tên), `--khong-chinh-hinh`, `--op-wc 10`, `--trat-dau-tuong 15`, `--ten-wc`. Đầu ra: JSON, `ve_polyline_phong.scr`, `DienTichPhong.xlsx`, `xem_lai.png`.
4. **Đọc JSON, xem `xem_lai.png`.** Phân loại:
   - `dung_moi`: phòng dựng polyline mới.
   - `da_co_doi_chieu`: đã có polyline trên layer phòng; chỉ so diện tích (chênh %), báo chưa Closed, trùng chồng.
   - `da_co_chua_doi_chieu`: có polyline của người dùng nhưng nét quanh phòng chưa đủ dựng lại độc lập (cửa sổ biên, lô-gia). **Không phải lỗi phòng**: báo diện tích polyline sẵn có, ghi "chưa đối chiếu được".
   - `khong_dong_duoc`: chưa có polyline và không đóng kín được (kèm đầu hở, khe hở gần nhất). Chỉ loại này là Lỗi.
   - `vung_chua_ten`: vùng kín không có text tên (WC chỉ có nhãn m²): hỏi tên phòng.
   - `van_de`: đơn vị khác mm, polyline trùng chồng/chưa Closed.
5. **Phòng không đóng được:** cho người dùng xem hình + tọa độ/độ rộng khe. Chỉ ranh bằng (a) vẽ LINE trên layer `A-Dong ranh phong`, hoặc (b) nói tọa độ để truyền `--them-ranh=`. Chạy lại bước 3 đến khi hết hở hoặc người dùng bỏ qua phòng đó.
6. **Vẽ vào bản sao** (chỉ khi người dùng đã đồng ý bước 4–5): MCP `ve_vao_ban_sao` hoặc `ve_polyline_vao_dwg.ps1 -Dwg <gốc> -Scr ve_polyline_phong.scr -OutDwg <03-Ban-Sao-Lam-Viec>\<tên>_polyline_phong.dwg` (không ghi đè, từ chối nếu OutDwg trùng gốc).
7. **Báo cáo:** bảng phòng (tên, m² 1 số lẻ, trạng thái), việc cần quyết định, đường dẫn bản sao + Excel; nói rõ đã kiểm tra thực tế / chưa kiểm tra.

## Đường bo căn hộ và nhãn DTCH
Chạy **sau** khi phòng đã dựng và được đồng ý: MCP `dung_duong_bo_can_ho` hoặc `tao_duong_bo_can_ho.py <dxf> --out-dir … [--layer-ten A-Dimension]`. Cùng tùy chọn nhận diện/chỉnh hình như bước 3 (thêm `--them-phong`, `--lop-trat`, `--block-bo-qua`). Đầu ra: `ve_duong_bo_can_ho.scr`, `DienTichCanHo.xlsx`, `xem_duong_bo_can_ho.png`, JSON. Vẽ vào bản sao đã có polyline phòng (không phải file gốc), `-Scr` là `ve_duong_bo_can_ho.scr`, `-OutDwg` là tên bản sao mới.

- **Đường bo** = một polyline đóng, layer `Dien tich thong thuy` (màu 6), theo mặt trát trong của tường bao/tường chung/vách, **ôm cả ban công, lô-gia**; tường ngăn trong căn nằm bên trong (được tính).
- **Dựng:** hợp các vùng phòng đã chỉnh hình + lấp dải tường ngăn/ô cửa giữa hai mặt phòng đối diện (≤ `--day-tuong-max` 300 mm + ốp WC). Không lấp góc lõm tường bao ngoài. `--khong-chinh-hinh`: cách cũ, khép hình buffer ±150 mm.
- **Loại trừ:** cột, HKT (kèm tường bao HKT) nằm trong căn là lỗ của vùng → polyline loại trừ riêng cùng layer. DT căn = đường bo − loại trừ. Mọi lỗ đều báo Cảnh báo để xác nhận (hành lang/kho kín không tên cũng thành lỗ).
- **Bản kiểm:** DT căn − Σ DT phòng phải **dương** (≈ tường ngăn + ô cửa); âm = ranh phòng chồng lấn.
- **Nhiều căn / chưa có tên phòng:** tự tách căn (đánh số trái → phải, JSON `can_ho`). Có tên phòng thì gộp phòng thành căn; không có thì mỗi vùng kín ≥ `--dt-toi-thieu-can` 15 m² là một căn, nhãn dùng style `Standard`, layer `A-Text`, cao 300 mm → **báo người dùng xác nhận**. Lô-gia/ban công/phòng phụ gắn vào căn **qua cửa đi/cửa sổ** (cụm nét `A-Window`, `A-Glaz`, `A-Door`, `A-Cửa` rộng ≥ 600 mm chạm cả hai bên, `--tol-cua` 60); vùng có cửa thông sang hai căn là khu vực chung, không tính.
- **Còn phòng có tên chưa đóng kín** hoặc phòng tạo nhiều khối rời: script **dừng, không vẽ** (`trang_thai: khong_dung_duoc`). Làm theo `huong_xu_ly`; chỉ dùng `--chap-nhan-thieu-phong` khi người dùng đồng ý bỏ qua.
- **Lớp trát:** bám nét đã vẽ, không tự lùi 15 mm (xem SKILL.md). Polyline người dùng bo tay theo cách cũ (lùi 15 mm khi lớp trát không vẽ) thì báo Lỗi chênh lệch bình thường, ghi rõ nguyên nhân.
- **Nhãn `DTCH: xx.x m2`:** ở giữa phòng khách (chỗ trống gần chữ tên phòng khách nhất), không đè tường, cửa, nội thất, chữ, nhãn phòng; cùng style, layer, màu, kiểu đối tượng với nhãn diện tích phòng; cao = 1,5 × cao chữ tên phòng. Lưới 50 mm, cách vật cản ≥ 80 mm (`--le`). Không tìm được chỗ thì Cảnh báo, không đặt bừa. Phòng khách nhận bằng regex không dấu `kh[a]ch` (`--phong-khach`); đổi tiêu đề `--tieu-de`.

## Bản vẽ có mặt bằng trong block/xref
Một số file (ví dụ `CT1-CH06-CTCH.dwg`) chỉ chứa khung bản vẽ, mặt bằng nằm trong xref. Script tự đi sâu block/xref, bỏ tiền tố layer xref (`CH06|A-Vua trat`, `$0$A-Vua trat` = `A-Vua trat`) và **bỏ qua** block tên chú thích/legend/khung/lưới/trần/lõi thang (`--block-bo-qua`, `''` = lấy hết). Tên phòng chỉ lấy từ text ở Model; phòng không có text tên khai bằng `--them-phong "Tên:x,y;Tên:x,y"` (một điểm trong phòng, xem `xem_lai.png`).
Kết quả gần như trống = bản vẽ chưa có nét tường/vữa trát (xref nền chưa nạp/thiếu file): **đừng bịa ranh**, báo cần nạp file nền có `A-Vua trat`, `A-Wall`, `A-Column`. Xref phải đang nạp khi chuyển DXF; đường dẫn xref tương đối sẽ hỏng nếu file nằm khác thư mục gốc.

## Lưu ý
- Script chỉ đọc ranh từ layer cho phép (`--layer-ranh`, `--layer-cua`); nội thất, thiết bị, cánh cửa mở, cung quay cánh không bao giờ làm ranh. Ranh bám nhầm: xem JSON `khung_cua` (số cửa, đoạn khung, cánh/cung đã bỏ, cửa không tìm được tường hai bên) và kiểm tra hai tùy chọn trên.
- **Nhãn phòng:** đọc Text tên phòng, tạo nhãn "xx.x m2" **cùng loại (TEXT/MTEXT), style, cao, layer, màu, góc xoay**, căn giữa theo tên (MC), nằm ngay dưới tên (tâm cách tâm tên 1,5 × cao một dòng). Trong `.scr` đặt Style **trước** Height (nếu không AutoCAD đặt lại cao 2,5).
  - Phòng khai bằng `--them-phong` dùng mặc định `A-Text`, cao 250 (`--label-h`, `--label-layer`).
  - Hai tên cùng một vùng (khách + bếp): một nhãn, dưới tên đầu.
  - Phòng đã có nhãn m² trên layer in được thì không ghi trùng (layer `Defpoints` không tính); số cũ khác polyline mới → **Lỗi "Nhãn diện tích sai"** (không tự sửa). Mặc định chỉ ghi nhãn phòng dựng mới; `--nhan-tat-ca` ghi cả phòng đã có polyline (số lấy theo polyline có sẵn).
  - Tên layer/style có dấu mã hóa `\U+XXXX` trong `.scr`; sau khi vẽ luôn mở lại bản sao kiểm tra layer, style, cao, vị trí.
- Cột/vách đứng riêng trong phòng: polyline loại trừ cùng layer phòng (nhãn = đường bo − cột), Cảnh báo, xác nhận theo quy tắc B.
- Đối chiếu bảng thống kê/hợp đồng: skill `do-dien-tich-thong-thuy` hoặc so Excel theo ngưỡng ±0,5%.

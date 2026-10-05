---
name: dien-tich-ch
description: 'Dien tich CH – Tự dựng polyline đóng kín bo diện tích thông thủy từng phòng VÀ đường bo thông thủy cả căn hộ (layer "Dien tich thong thuy", loại trừ hộp kỹ thuật/cột, nhãn "DTCH: xx.x m2" ở giữa phòng khách) từ mặt bằng căn hộ AutoCAD (.dwg/.dxf), kể cả bản vẽ dùng đối tượng AutoCAD Architecture (Tường, Cửa đi, Cửa sổ); bám tường Wall, polyline bo cột, nét vữa hoàn thiện và nét bao khung cửa sổ/cửa đi (không bám cánh mở), không tự lùi lớp trát khi bản vẽ không vẽ lớp trát, đóng ô cửa ≤ 1,2 m, ghi nhãn m² theo style tên phòng, xuất Excel, lưu vào BẢN SAO DWG. Dùng skill này bất cứ khi nào người dùng đưa mặt bằng căn hộ và nhờ bo/vẽ/tạo polyline phòng hoặc đường bo căn hộ, đo diện tích từng phòng hay cả căn, "bo thông thủy", "DTCH", tạo polyline lớp "A- Dien tich phong" hoặc "Dien tich thong thuy", hoặc soát xem polyline nhân viên đã bo có đúng nét hoàn thiện không, kể cả khi họ không nói "thông thủy" hay không nhắc tên skill.'
---

# Dien tich CH – Đo diện tích thông thủy phòng và căn hộ (Archivina)

Mục tiêu: từ một mặt bằng căn hộ, (1) dựng polyline đóng kín bo thông thủy từng phòng, (2) dựng đường bo thông thủy cả căn hộ, (3) ghi nhãn diện tích phòng và nhãn `DTCH` của căn **lấy đúng từ các polyline vừa vẽ**, rồi (4) mở lại bản sao để kiểm tra từng nhãn khớp polyline. Người dùng là Phó Tổng Giám đốc, kiến trúc sư giàu kinh nghiệm: báo kết quả và điểm cần quyết định trước, ngắn gọn.

**Yêu cầu và quy ước đường dẫn**
- `<skill>`: thư mục chứa file SKILL.md này (Claude Code báo ở dòng "Base directory for this skill").
- `<python>`: Python 3.10 trở lên có `ezdxf`, `shapely`, `openpyxl`, `matplotlib`. Máy Archivina hiện tại dùng `C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe`; máy khác dùng `python` hoặc `py` (thiếu gói thì `python -m pip install --user ezdxf shapely openpyxl matplotlib`). Đặt `PYTHONUTF8=1` khi đọc JSON tiếng Việt.
- AutoCAD 2022 trở lên có `accoreconsole.exe` (script tự tìm bản mới nhất trong `C:\Program Files\Autodesk\AutoCAD *\`).
- Nhãn diện tích = diện tích của chính hình sẽ vẽ (đường bo − các polyline loại trừ nằm trong nó), làm tròn 1 số thập phân kiểu 0,05 → 0,1. Không lấy từ nguồn nào khác.

Đọc `references/quy-uoc-ve-polyline-phong.md` trước khi làm lần đầu hoặc khi gặp tình huống lạ. Quy tắc đo diện tích (mốc đo, hộp kỹ thuật, cột, làm tròn) nằm ở `references/quy-tac-do.md`.

## Nguyên tắc
- **Không sửa DWG gốc.** Chỉ đọc bản sao; polyline chỉ được vẽ vào một bản sao mới. Lý do: file gốc là bản nhân viên nộp, cần giữ nguyên để kiểm soát.
- **Không đụng các tab AutoCAD đang mở của người dùng** (có thể chưa lưu). Mọi việc chạy bằng AutoCAD Core Console ngầm.
- **Không tự đoán đường đóng ranh** khi khe hở > 1,2 m hoặc cạnh không có nét. Dừng, báo tọa độ kèm hình, hỏi người dùng. Đề xuất được, nhưng chỉ vẽ sau khi người dùng đồng ý.
- Layer polyline phòng là **`A- Dien tich phong`** (giữ dấu cách), màu 222. Nhãn diện tích **1 chữ số thập phân**.

## Đường bo bám theo nét nào (đã chốt 05/10/2026)
Polyline phòng và đường bo căn hộ **chỉ bám các nét đã vẽ** trong bản vẽ:
1. **Tường dạng Wall của AutoCAD Architecture** (sau khi nổ: nét `A-Wall`, `A-Vua trat`) và tường vẽ tay trên các layer đó.
2. **Polyline bo cột** (`A-Column`).
3. **Polyline/nét lớp hoàn thiện vữa trát** (`A-Vua trat`), nét lan can/biên (`A-Line`).
4. **Nét bao khung cửa sổ, cửa đi** (Window/Door của AutoCAD Architecture sau khi nổ, hoặc block cửa trên layer `A-Door`, `A-Window`, `A-Glaz`, `A-Cửa`; đổi bằng `--layer-cua`). Script chỉ lấy các nét khung, kính, cánh đóng **nằm trong chiều dày tường** ở chỗ đặt cửa; **cánh cửa mở ra ngoài tường và cung quay cánh bị bỏ**. Nét khung không sinh đoạn đóng ô cửa. Ở chỗ nét mặt tường chạy liền qua ô cửa (tường ACA nổ ra), ranh theo mặt tường. Nét khung quyết định ranh ở chỗ không có nét tường: cửa hoặc vách kính đặt tự do, lô-gia, tường cắt hở.

**Lớp trát:** bản vẽ **có vẽ** lớp trát (nét `A-Vua trat` cách nét `A-Wall` 15 mm) thì đường bo tự bám nét vữa đó. **Không vẽ** lớp trát (nét `A-Vua trat` trùng mặt tường, hoặc chỉ có `A-Wall`) thì **không lùi 15 mm**, đường bo theo mặt tường đã vẽ; script ghi một dòng "Gợi ý – Lớp trát" để biết. Chỉ dùng `--lop-trat 15` khi người dùng yêu cầu rõ.

## Quy trình

1. **Xác định đầu vào:** đường dẫn `.dwg` (hoặc `.dxf`), thư mục lưu kết quả (ưu tiên `03-Ban-Sao-Lam-Viec` của dự án, nếu không có thì thư mục người dùng chỉ). Hỏi nếu thiếu.

2. **Chuyển DWG sang DXF trên bản sao, có nhận diện đối tượng AutoCAD Architecture** (bỏ qua nếu đã là DXF):
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File "<skill>\scripts\dwg_to_dxf_aec.ps1" -Dwg "<file.dwg>" -OutDir "<thư mục tạm hoặc 03-Ban-Sao-Lam-Viec>"
   ```
   **Luôn dùng script này thay cho `dwg_to_dxf.ps1`.** Lý do: bản vẽ làm bằng AutoCAD Architecture dùng đối tượng **Tường (AEC_WALL), Cửa đi (AEC_DOOR), Cửa sổ (AEC_WINDOW)**; DXF xuất thường **bỏ mất** các đối tượng này nên trông như bản vẽ không có tường (đã từng kết luận sai trên `Căn hộ mẫu Cần Thơ.dwg`). Script này nổ từng đối tượng AEC trên bản sao rồi mới xuất DXF; tường thành INSERT chứa nét `A-Vua trat` (mặt hoàn thiện) và `A-Wall` (lõi tường), cửa đi thành `A-Door`, cửa sổ thành `A-Glaz`. Nó ghi `<tên>_aec.txt` đếm đối tượng AEC trước khi nổ (không có file hoặc không có dòng `TRUOC` nghĩa là bản vẽ không có đối tượng AEC ở Model). Bản vẽ không có đối tượng AEC vẫn chạy bình thường.
   Đối tượng AEC nằm trong **xref** hoặc block không nổ được từ file này: mở/chuyển chính file xref đó.

3. **Dựng polyline:**
   ```powershell
   & "<python>" "<skill>\scripts\tao_polyline_phong.py" "<file.dxf>" --out-dir "<thư mục kết quả>"
   ```
   Tùy chọn hay dùng: `--layer-ranh "A-Vua trat,A-Wall,A-Column,A-Line"` (đổi nếu bản vẽ dùng layer khác), `--gap-max 1200`, `--them-ranh=x1,y1,x2,y2;...` (**có dấu `=`**, vì tọa độ âm bắt đầu bằng `-`), `--ve-lai`, `--nhan-tat-ca`, `--label-h 250` (chỉ dùng cho phòng không có text tên).
   Script in JSON (UTF-8) và tạo `ve_polyline_phong.scr`, `DienTichPhong.xlsx`, `xem_lai.png`.

4. **Đọc kết quả JSON và xem `xem_lai.png`** (dùng công cụ Read để xem ảnh). Phân loại:
   - `dung_moi`: phòng đã dựng polyline mới.
   - `da_co_doi_chieu`: phòng đã có polyline trên layer phòng; script chỉ so diện tích (chênh %), báo polyline chưa Closed, trùng chồng.
   - `da_co_chua_doi_chieu`: phòng đã có polyline của người dùng nhưng nét ranh quanh phòng chưa đủ để dựng lại độc lập (ví dụ phòng có cửa sổ biên, lô-gia). Đây **không phải lỗi của phòng**: báo diện tích polyline sẵn có, ghi rõ chưa đối chiếu được và cần đóng ranh chỗ hở nếu muốn đối chiếu.
   - `khong_dong_duoc`: phòng **chưa có polyline** và không đóng kín được; có đầu hở gần và khe hở gần nhất. Chỉ loại này mới là Lỗi.
   - `vung_chua_ten`: vùng kín không có text tên phòng (ví dụ WC chỉ có nhãn m²); hỏi tên phòng.
   - `van_de`: đơn vị bản vẽ khác mm, polyline trùng chồng, polyline chưa Closed.

5. **Xử lý phòng không đóng được.** Cho người dùng xem hình và các khe hở (tọa độ, độ rộng). Người dùng chỉ ranh bằng một trong hai cách (chi tiết trong file tham chiếu, mục 6): vẽ LINE trên layer `A-Dong ranh phong`, hoặc nói tọa độ để bạn truyền `--them-ranh=`. Chạy lại bước 3. Lặp đến khi hết hở hoặc người dùng chấp nhận bỏ qua phòng đó.

6. **Vẽ vào bản sao DWG** (chỉ khi người dùng đã đồng ý kết quả bước 4–5):
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File "<skill>\scripts\ve_polyline_vao_dwg.ps1" -Dwg "<file.dwg gốc>" -Scr "<ve_polyline_phong.scr>" -OutDwg "<03-Ban-Sao-Lam-Viec>\<tên>_polyline_phong.dwg"
   ```
   Script không ghi đè và từ chối nếu `-OutDwg` trùng file gốc. Kiểm tra lại theo mục "Kiểm tra nhãn sau khi vẽ".

7. **Báo cáo cho người dùng:** bảng phòng (tên, diện tích làm tròn 1 số, trạng thái dựng mới/đã có/không đóng được), các việc cần quyết định, đường dẫn bản sao DWG và Excel. Nói rõ phần đã kiểm tra thực tế (đã mở lại bản sao và đo) và phần chưa kiểm tra (ví dụ xref chưa mở).

## Đường bo thông thủy căn hộ và nhãn DTCH
Chạy **sau** khi các phòng đã dựng và đã đồng ý (đường bo căn hộ được suy ra từ các vùng phòng):
```powershell
& "<python>" "<skill>\scripts\tao_duong_bo_can_ho.py" "<file.dxf>" --out-dir "<thư mục kết quả>" [--layer-ten A-Dimension]
```
Cùng các tùy chọn nhận diện như bước dựng phòng (`--layer-ranh`, `--them-ranh=`, `--them-phong`, `--lop-trat`, `--block-bo-qua`). Sinh `ve_duong_bo_can_ho.scr`, `DienTichCanHo.xlsx`, `xem_duong_bo_can_ho.png`, JSON.
Rồi vẽ vào bản sao: chạy `ve_polyline_vao_dwg.ps1` với `-Dwg` là **bản sao đã có polyline phòng** (không phải file gốc) và `-Scr` là `ve_duong_bo_can_ho.scr`, `-OutDwg` là tên bản sao mới.

**Nhiều căn trong một bản vẽ và bản vẽ chưa có tên phòng:** script tự tách từng căn (đánh số từ trái sang phải; JSON có mảng `can_ho`, mỗi căn một polyline đường bo + loại trừ + nhãn). Có text tên phòng thì gộp các phòng thành căn; **không có text tên phòng** (căn hộ để thô, chưa chia phòng) thì mỗi vùng kín lớn (≥ `--dt-toi-thieu-can` 15 m²) là một căn, và nhãn DTCH dùng chữ mặc định (style `Standard`, tên phòng giả định cao 200 mm nên nhãn cao 300 mm, layer `A-Text`): **báo người dùng xác nhận** vì chưa có Text tên phòng để lấy style/layer. Lô-gia, ban công, phòng phụ nằm ngoài vùng chính được **gắn vào căn qua cửa đi/cửa sổ** (cụm nét trên layer `A-Window`, `A-Glaz`, `A-Door`, `A-Cửa` rộng ≥ 600 mm chạm cả hai bên, `--tol-cua` 60 mm); vùng có cửa thông sang hai căn coi là khu vực chung và không tính. Nếu có phòng có tên chưa đóng kín, script dừng (xem bên dưới).

**Cách dựng (đúng quy tắc đã chốt):**
- Đường bo là **một polyline đóng trên layer `Dien tich thong thuy`** (màu 6), đi theo mặt trát trong của tường bao/tường chung/vách, **ôm cả ban công, lô-gia**; tường ngăn trong căn nằm bên trong (được tính).
- Hợp các vùng phòng, lấp khe tường ngăn và ô cửa (khe ≤ `--day-tuong-max` 300 mm). Không lùi lớp trát (xem mục "Đường bo bám theo nét nào").
- **Cột, hộp kỹ thuật (kèm tường bao hộp kỹ thuật) nằm trong căn** là lỗ của vùng → thành polyline **loại trừ** riêng, cùng layer. DT căn = đường bo − loại trừ. Mọi lỗ đều báo Cảnh báo để người dùng xác nhận đó đúng là hộp kỹ thuật/cột, vì một hành lang hay kho kín không tên cũng thành lỗ.
- Bản kiểm: DT căn − Σ DT phòng phải **dương** (≈ tường ngăn + ô cửa); âm là ranh phòng chồng lấn.
- **Còn phòng chưa đóng kín** (có tên nhưng không thành vùng kín) hoặc các phòng tạo ra nhiều khối rời: script **dừng và không vẽ** (`trang_thai: khong_dung_duoc`), vì đường bo sẽ thiếu phòng đó. Làm theo `huong_xu_ly` (chỉ ranh, chạy lại); chỉ dùng `--chap-nhan-thieu-phong` khi người dùng đồng ý bỏ qua các phòng đó.

**Lớp trát:** đường bo căn hộ theo cùng quy tắc với phòng: bám nét đã vẽ, không tự lùi 15 mm. Ví dụ Căn hộ mẫu Cần Thơ (tường ACA, lớp trát không vẽ riêng): đường bo 71,39 m² − hộp kỹ thuật 0,52 m² = **70,87 → 70,9 m²**. Polyline `CB4` người dùng bo tay trong bản vẽ đó vẽ theo cách cũ (lùi 15 mm, 70,2745 m²); người dùng đã xác nhận (05/10/2026) **giữ kết quả 70,9 m²**. Polyline cũ lệch theo kiểu này thì báo Lỗi chênh lệch như bình thường, ghi rõ là vẽ theo cách cũ (lùi 15 mm khi lớp trát không vẽ).

**Nhãn `DTCH: xx.x m2`:** đặt **ở giữa phòng khách** (vị trí trống gần chữ tên phòng khách nhất), **không đè tường, cửa, nội thất, chữ tên phòng, nhãn phòng**; cùng **style, layer, màu, kiểu đối tượng** với nhãn diện tích phòng (tức theo Text tên phòng); **chiều cao = 1,5 lần chiều cao chữ tên phòng**. Vị trí tìm trên lưới 50 mm, nhãn cách mọi vật cản ≥ 80 mm (`--le`). Không tìm được chỗ thì báo Cảnh báo, không đặt bừa. Phòng khách nhận qua regex không dấu `kh[a]ch` (`--phong-khach`); đổi tiêu đề bằng `--tieu-de`.

## Kiểm tra nhãn sau khi vẽ (bắt buộc)
Sau mỗi lần vẽ vào bản sao, chuyển bản sao sang DXF (`dwg_to_dxf_aec.ps1`) rồi chạy:
```powershell
& "<python>" "<skill>\scripts\kiem_tra_nhan.py" "<ban_sao.dxf>" [--layer-phong "A- Dien tich phong"] [--layer-can "Dien tich thong thuy"]
```
Script ghép mỗi polyline phòng/căn với các polyline loại trừ cùng layer nằm trong nó, tìm nhãn `xx.x m2` (phòng) hoặc `DTCH: xx.x m2` (căn) nằm trong vùng, và báo Lỗi khi: nhãn ghi khác diện tích polyline đã làm tròn, vùng không có nhãn, một vùng có nhiều nhãn, polyline chưa Closed. Mã thoát 0 = đạt. Polyline có sẵn của người dùng sai layer (ví dụ đường bo căn nằm trên layer phòng) sẽ hiện thành "phòng không có nhãn": báo đúng nguyên nhân là sai layer. Ngoài ra kiểm tra bằng mắt nhãn DTCH không giao với tường, nội thất, chữ.
Báo cho người dùng số vùng đạt / tổng số vùng và từng lỗi (handle, giá trị ghi, giá trị đúng).

## Bản vẽ có mặt bằng nằm trong block/xref
Nhiều file (ví dụ `CT1-CH06-CTCH.dwg`, loại "chi tiết căn hộ") chỉ chứa khung bản vẽ, còn mặt bằng nằm trong xref. Script tự đi sâu vào block/xref, bỏ tiền tố layer của xref (`CH06|A-Vua trat`, `$0$A-Vua trat` đều tính là `A-Vua trat`) và **bỏ qua** block có tên chú thích/legend/khung/lưới/trần/lõi thang (đổi bằng `--block-bo-qua`, `''` = lấy hết). Tên phòng chỉ lấy từ text ở Model, không lấy trong block/xref vì thường là chú thích; phòng không có text tên thì khai bằng `--them-phong "Tên:x,y;Tên:x,y"` (tọa độ một điểm trong phòng, xem trên `xem_lai.png`).
Nếu kết quả gần như trống: bản vẽ **chưa có nét tường/vữa trát** của phòng (tường kiến trúc nằm ở xref khác chưa nạp hoặc thiếu file). Đừng bịa ranh; báo người dùng cần nạp/đưa file nền kiến trúc có `A-Vua trat`, `A-Wall`, `A-Column`.
Lưu ý khi chuyển DWG sang DXF: xref phải đang được nạp trong DWG; tên đường dẫn xref tương đối (`..\..\Xref\...`) sẽ hỏng nếu file nằm ở thư mục khác chỗ gốc.

## Lưu ý
- Script chỉ đọc ranh từ layer cho phép (`--layer-ranh`, `--layer-cua`). Nội thất, thiết bị, cánh cửa mở, cung quay cánh không bao giờ làm ranh phòng; nếu thấy ranh bám nhầm, xem JSON `khung_cua` (số cửa, số đoạn khung, số cánh/cung đã bỏ, số cửa không tìm được tường hai bên) và kiểm tra hai tùy chọn trên.
- **Nhãn diện tích (đã chốt):** script đọc Text tên phòng trong bản vẽ và tạo nhãn "xx.x m2" (1 chữ số thập phân) **cùng loại đối tượng (TEXT hay MTEXT), cùng style chữ, cùng chiều cao, cùng layer, cùng màu và góc xoay với Text tên phòng; căn giữa theo tên phòng (kiểu MC) và nằm ngay bên dưới tên, cách 0,5 lần chiều cao chữ** (tâm nhãn cách tâm tên 1,5 lần chiều cao một dòng; tên nhiều dòng thì cách thêm). Độ rộng chữ để căn giữa (khi tên canh lề trái/phải) lấy bằng số đo font thật, nên tên canh giữa hoặc canh lề đều đặt đúng. Trong script `.scr` thứ tự lệnh quan trọng: đặt Style **trước** Height, nếu không AutoCAD đặt lại chiều cao về 2,5.
  - Phòng khai báo bằng `--them-phong` (không có text tên) mới dùng mặc định `A-Text`, cao 250 mm (`--label-h`, `--label-layer`).
  - Hai tên cùng một vùng kín (phòng khách + bếp): chỉ một nhãn, đặt dưới tên đầu tiên.
  - Phòng đã có nhãn m² trên lớp in được thì không ghi trùng (nhãn ở layer `Defpoints` không tính vì không in); nếu số ghi trên nhãn cũ khác diện tích polyline vừa dựng thì báo **Lỗi "Nhãn diện tích sai"** (không tự sửa nhãn cũ). Mặc định chỉ ghi nhãn cho phòng dựng mới; thêm `--nhan-tat-ca` để ghi nhãn cả phòng đã có polyline (không vẽ lại polyline), khi đó số trên nhãn lấy theo **chính polyline có sẵn** trong bản vẽ.
  - Tên layer/style có dấu tiếng Việt được mã hóa `\U+XXXX` trong `.scr`; sau khi vẽ luôn mở lại bản sao DWG để kiểm tra nhãn đúng layer, style, chiều cao và vị trí.
- Cột/vách đứng riêng trong phòng được vẽ thành polyline loại trừ cùng layer phòng, trừ khỏi diện tích (nhãn = đường bo − cột) và báo Cảnh báo; xác nhận theo quy tắc B.
- Muốn đối chiếu với bảng thống kê/hợp đồng: dùng skill `do-dien-tich-thong-thuy` nếu đã cài, hoặc so Excel đầu ra với bảng theo ngưỡng ±0,5%.

# Quy ước dựng polyline phòng (Archivina)

Nguồn: bản vẽ mẫu `H:\@Archivina 2026\@bản vẽ mẫu căn hộ\Test đo dt can ho.dwg` (người dùng đã tự bo polyline các phòng đúng hướng dẫn) và các câu trả lời đã chốt. Quy tắc đo diện tích nằm ở `references/quy-tac-do.md` (cùng skill); file này chỉ nói về **cách dựng polyline**.

## Mục lục
1. Đã chốt với người dùng
2. Phòng được bo như thế nào trong bản mẫu
3. Thuật toán của script
4. Kết quả kiểm chứng trên bản mẫu
5. Việc script chưa làm được, cách xử lý
6. Cách chỉ ranh cho chỗ hở

## 1. Đã chốt với người dùng
- Layer polyline phòng: **`A- Dien tich phong`** (có dấu cách sau `A-`), màu ACI 222. Giữ nguyên tên này, không tự bỏ dấu cách.
- Polyline phòng phải **bám theo tường/nét hoàn thiện, khung cửa, cửa sổ**; **không bám cánh cửa mở, không bám nét nội thất**. Kết quả phải là **một polyline đóng kín**.
- **Chỉ tự đóng ô cửa ≤ 1,2 m.** Khoảng hở rộng hơn: dừng, báo tọa độ, hỏi người dùng (quy tắc D trong CLAUDE.md).
- Ô cửa đi giữa hai phòng **không thuộc phòng nào** (quy tắc B).
- Giao kết quả: **bản sao DWG có polyline và nhãn m² + Excel**. Không ghi vào bản gốc.
- Nhãn diện tích (**đã chốt với người dùng**): "xx.x m2", **1 chữ số thập phân**. Dùng **style chữ của Text tên phòng đã có trong bản vẽ**, đặt **bên dưới Text tên phòng, căn giữa theo tên phòng, cùng chiều cao chữ, cùng layer** (và cùng loại đối tượng TEXT/MTEXT, cùng màu, góc xoay). Bản vẽ Cần Thơ: tên là MTEXT canh giữa (attachment 5), style `ghi_chu VnArialNarowH`, cao 200 mm, layer `A-Dimension`, màu 2 → nhãn MTEXT cùng thông số, tâm cách tâm tên 300 mm (1,5 lần cao chữ). Chỉ phòng không có text tên mới dùng mặc định cao 250 mm layer `A-Text` (`--label-h`, `--label-layer`).

## 2. Phòng được bo như thế nào trong bản mẫu
- Polyline phòng chạy theo nét vữa trát **`A-Vua trat`**, cột **`A-Column`**, nét lô-gia **`A-Line`**, tường **`A-Wall`**.
- Tại ô cửa (794–914 mm trong bản mẫu) polyline **đóng bằng đoạn thẳng ngang mặt tường**. Hai đầu ô cửa là các **góc "má cửa"**: nét hoàn thiện rẽ vuông vào một đoạn ngắn (khoảng 85–135 mm) rồi tiếp tục.
- Đóng ô cửa ở **cả hai mặt tường** (mặt phòng này và mặt phòng kia) thì phần ô cửa tự thành một vùng riêng; hai phòng kề nhau không lấn vào đó.
- Tên phòng là text ở layer `A-Text` (đặt trong phòng). Nhãn m² trong bản mẫu nằm ở layer `Defpoints` (không in).
- Nét hoàn thiện nhiều chỗ là polyline **hở** (đầu và cuối chỉ trùng điểm, không bật Closed) hoặc chỉ cách nét kia vài mm; script tự nối các khe ≤ 6 mm.
- Cửa sổ biên (ví dụ phía tây phòng ngủ 1) nằm ngoài mặt hoàn thiện khoảng 150 mm nên **không dùng làm ranh**; người dùng đóng ranh bằng đoạn thẳng nối hai đầu nét hoàn thiện.

## 3. Thuật toán của script (`scripts/tao_polyline_phong.py`)
1. Đọc LINE/LWPOLYLINE trên các layer ranh: `A-Vua trat, A-Wall, A-Column, A-Line` (đổi bằng `--layer-ranh`), cộng **nét bao khung cửa đi/cửa sổ** trên `A-Door, A-Window, A-Glaz, A-Cửa…` (`--layer-cua`): mỗi block cửa, chỉ giữ nét nằm trong dải chiều dày tường ở chỗ đặt cửa; cánh mở ra ngoài tường và cung quay cánh bị bỏ; nét khung không sinh đoạn đóng ô cửa. **Không** đọc layer nội thất, thiết bị.
2. Tìm các "tia kéo dài" tại đầu mút nét và tại góc má cửa (góc ~90° kèm đoạn ngắn ≤ 400 mm).
3. Ghép hai tia đối diện, thẳng hàng (sai số 20 mm), cách nhau ≤ `--gap-max` (mặc định 1200 mm), đoạn nối không được cắt qua nét ranh khác.
4. Nối thêm khe ≤ 6 mm.
5. `polygonize` mạng nét: mỗi vùng kín là một mặt; mặt chứa điểm đặt tên phòng (text `A-Text`) là phòng đó.
6. Mặt có "đảo" bên trong (cột đứng riêng, hộp kỹ thuật) được trừ khỏi diện tích và báo Cảnh báo.
7. Xuất: `ve_polyline_phong.scr` (vẽ polyline + nhãn), `DienTichPhong.xlsx`, `xem_lai.png`, JSON tóm tắt.
8. Phòng đã có polyline trên layer phòng chứa điểm đặt tên thì **không vẽ trùng**; chỉ đối chiếu diện tích (chênh %) và báo polyline chưa Closed hoặc trùng chồng. Dùng `--ve-lai` để buộc vẽ lại.

## 4. Kết quả kiểm chứng trên bản mẫu
Script dựng từ nét hoàn thiện, không nhìn polyline của người dùng:

| Phòng | Script (m²) | Người dùng bo (m²) |
|---|---|---|
| Phòng ngủ master | 21,1232 | 21,1231 |
| Phòng ngủ 2 | 10,5639 | 10,5639 |
| WC (master) | 6,0992 | 6,0992 |
| WC (phòng khách) | 4,3215 | 4,3215 |
| Phòng ngủ 1 | 15,9837 (sau khi thêm 2 đoạn đóng ranh phía cửa sổ tây) | 15,9837 |
| Đa năng | 4,702 | chưa bo |

Không tự đóng được: **Phòng khách, Lô-gia 1, Lô-gia 2** (ranh là cửa trượt rộng hơn 3 m hoặc mép lô-gia không có nét). Script báo tọa độ đầu hở và khe hở gần nhất.
Ngoài ra script tìm ra vùng kín chưa đặt tên: WC phòng ngủ 1 (4,4 m²) và một đoạn hành lang (1,0 m²).

## 4b. Bản vẽ dùng đối tượng AutoCAD Architecture (Tường, Cửa đi, Cửa sổ)
- ACA lưu tường/cửa là đối tượng `AEC_WALL`, `AEC_DOOR`, `AEC_WINDOW` (không phải LINE/POLYLINE). DXF xuất thường (`DXFOUT`) **bỏ mất** chúng, nên ezdxf thấy bản vẽ "không có tường". Dấu hiệu: DXF có các lớp `AEC_*` trong CLASSES nhưng Model không có LINE tường; layer `A-Wall` trống.
- Cách xử lý (script `dwg_to_dxf_aec.ps1`): trên bản sao, `EXPLODE` **từng** đối tượng AEC một (lệnh EXPLODE trong core console chỉ nổ một đối tượng mỗi lần chọn), rồi `DXFOUT`. Kết quả: tường → INSERT chứa LINE `A-Vua trat` (mặt trát), LINE `A-Wall` (lõi/biên tường), HATCH `A-Material`; cửa đi → LWPOLYLINE + ARC `A-Door` (2 khung đứng trong chiều dày tường **dùng làm ranh**; cánh mở 90° thò vào phòng và cung quay cánh **bỏ**); cửa sổ → LINE/LWPOLYLINE `A-Glaz` (khung + kính trong chiều dày tường, dùng làm ranh). Nét mặt tường của tường ACA nổ ra chạy liền qua ô cửa, nên ở đó ranh vẫn là mặt tường.
- Script dựng polyline đã đi sâu vào INSERT nên dùng ngay `A-Vua trat` và `A-Wall` làm ranh, cửa đi tự thành ô cửa trong mạng nét (đóng bằng đoạn thẳng ≤ 1,2 m).
- Lỗi đã gặp và đã sửa: các đầu nét của tường nổ chỉ lệch ~1e-7 mm so với nét kế bên, `polygonize` coi là đầu tự do và gộp phòng ngủ với WC; sửa bằng ghép nút lưới 0,01 mm (`shapely.union_all(grid_size=0.01)`).
- Kiểm chứng trên `Căn hộ mẫu Cần Thơ.dwg` (23 tường, 7 cửa đi, 2 cửa sổ): dựng 7 polyline đóng kín: Phòng khách + Bếp 31,0 · Phòng ngủ master 11,0 · wc 1 3,5 · Logia 2 4,3 · Logia 1 3,0 · Phòng ngủ 11,1 · wc 2 3,8 m². Tổng 67,70 m²; đường bo căn hộ trừ loại trừ = 70,27 m²; chênh 2,57 m² là tường ngăn trong căn + ô cửa + cột (hợp lý, dương). **Chưa có đáp án người dùng bo tay** cho căn này nên chỉ kiểm tra tính hợp lý, chưa kiểm chứng độ chính xác như bản mẫu CT2.
- Phòng khách và Bếp nằm chung một vùng kín (không có vách): script dựng **một** polyline "Phòng khách + Bếp" và báo Cảnh báo không gian mở; muốn tách thì vẽ đoạn chia ranh trên layer `A-Dong ranh phong`.

## 4c. Đường bo căn hộ, lớp trát, nhãn DTCH (đã chốt)
- Đường bo thông thủy căn hộ: một polyline đóng, layer **`Dien tich thong thuy`** (màu 6); cột/hộp kỹ thuật trong căn là polyline loại trừ riêng cùng layer; DT căn = đường bo − loại trừ; làm tròn 1 số thập phân.
- **Quy tắc lớp trát (người dùng chốt 05/10/2026, thay quy tắc lùi 15 mm tự động trước đó):** đường bo chỉ bám nét đã vẽ: tường Wall ACA, polyline bo cột, nét/polyline lớp hoàn thiện vữa, nét bao khung cửa sổ/cửa đi. **Lớp trát 15 mm không vẽ thì không lùi 15 mm.** Bản vẽ có vẽ lớp trát (Test AI: `A-Vua trat` cách `A-Wall` 15 mm) thì đường bo tự bám nét vữa. Căn hộ mẫu Cần Thơ: `A-Vua trat` trùng `A-Wall` (lớp trát không vẽ) nên đường bo theo mặt tường; polyline `CB4` người dùng bo tay theo cách cũ (lùi 15 mm), chênh +0,85%; người dùng xác nhận 05/10/2026: **giữ 70,9 m²**, `CB4` là polyline cũ cần vẽ lại.
- Phòng Căn hộ mẫu Cần Thơ (theo mặt tường): Phòng khách + Bếp 31,0; master 11,0; wc 1 3,5; Logia 2 4,3; Logia 1 3,0; Phòng ngủ 11,0; wc 2 3,8 m² (người dùng đã duyệt bộ số này).
- Nhãn căn hộ "DTCH: xx.x m2": ở giữa phòng khách, không đè tường/nội thất/chữ, cùng style-layer-màu với nhãn diện tích phòng (theo Text tên phòng), cao = 1,5 × cao chữ tên phòng.
- Kết quả trên Căn hộ mẫu Cần Thơ: đường bo 71,39 m² (18 đỉnh), loại trừ 0,52 m² (hộp kỹ thuật 1300 × 400), **DT căn hộ 70,87 → 70,9 m²**; Σ phòng 67,63; chênh 3,24 m² (tường ngăn + ô cửa); nhãn "DTCH: 70.9 m2" cao 300 mm (= 1,5 × 200), layer `A-Dimension`, style `ghi_chu VnArialNarowH`, màu 2, không giao với vật nào; kiem_tra_nhan.py 8/8 vùng đạt.

## 4d. Bản vẽ nhiều căn, chưa có tên phòng (Test AI.dwg)
- File `Test AI.dwg`: 3 căn hộ để thô (không vách ngăn, không text), tường/cửa/cửa sổ là đối tượng ACA (50 tường, 11 cửa đi, 4 cửa sổ). Người dùng đã tự bo sẵn 3 đường bo + 3 hộp kỹ thuật, nhưng **đặt ở layer `A- Dien tich phong`** (layer phòng, không đúng chuẩn `Dien tich thong thuy`): Skill báo Lỗi layer.
- Đường bo của người dùng = hợp các vùng kín trong căn gồm vùng chính, **lô-gia (vùng sau cửa sổ ở mép trên, ngăn bằng tường kính dày 230 mm)** và phòng phụ cạnh tường chung, cộng phần tường ngăn/khe lấp; **không lùi lớp trát** (nét `A-Vua trat` là mặt hoàn thiện vì không trùng nét `A-Wall`).
- Khe tường kính giữa phòng và lô-gia (230 mm) bằng bề dày tường chung giữa hai căn (228 mm): chỉ phép đóng hình không phân biệt được. Vì vậy vùng phụ chỉ được gắn vào căn **qua cửa/cửa sổ**, không gắn theo khoảng cách.
- Hộp kỹ thuật có nét ngoài không chạm nhau ở góc (hở 57 mm giữa hai nét vuông góc): script đóng khe hở góc ≤ 150 mm (`GAP_GOC`) để vòng ngoài khép kín, nếu không hộp bị tính thiếu 0,195 m².
- Kết quả đối chiếu (script độc lập so với polyline người dùng): Căn 1 93,6574 (người dùng 93,6498, +0,008%), Căn 2 69,1684 (69,1715, −0,004%), Căn 3 69,1766 (69,1794, −0,004%); loại trừ 0,5989 / 0,7473 / 0,7579 m² trùng 100%. Làm tròn 1 số lẻ: 93,7 / 69,2 / 69,2 (Căn 1 chênh 0,1 so với 93,6 của người dùng vì giá trị nằm sát 93,65).

## 5. Việc script chưa làm được, cách xử lý
- **Khe hở > 1,2 m** hoặc cạnh không có nét (cửa sổ biên, mép lô-gia, vách kính): script dừng, ghi vào mục `khong_dong_duoc` kèm đầu hở. Hỏi người dùng đóng ranh thế nào (mục 6).
- **Phòng chưa có text tên**: liệt kê ở `vung_chua_ten`; hỏi tên phòng rồi chạy lại (hoặc người dùng thêm text vào `A-Text`).
- **Cửa sổ, cửa đi**: chỉ lấy nét bao khung trong chiều dày tường (xem bước 1); cánh mở và cung quay cánh không dùng. Nếu bản vẽ mới có cách vẽ khác (ví dụ ranh hoặc cửa nằm ở layer khác), xem layer thực tế bằng `ezdxf`, hỏi người dùng rồi truyền `--layer-ranh` / `--layer-cua`.
- **Cột/vách đứng riêng trong phòng** (đảo): đã trừ nhưng phải xác nhận theo quy tắc B (cột nhô vào phòng trừ khỏi diện tích).

## 6. Cách chỉ ranh cho chỗ hở
Có hai cách, đều chính xác và kiểm soát được:
1. **Người dùng vẽ LINE/PLINE** ngang chỗ hở trên layer **`A-Dong ranh phong`** trong bản vẽ (hoặc bản sao), script tự đọc.
2. Người dùng nói bằng lời, Claude truyền `--them-ranh=x1,y1,x2,y2;x1,y1,x2,y2`. **Viết `--them-ranh=` có dấu `=`**: tọa độ âm bắt đầu bằng `-` sẽ bị hiểu nhầm là tùy chọn.
Không tự đoán đường đóng ranh; chỉ đưa ra đề xuất kèm hình `xem_lai.png` rồi chờ người dùng xác nhận.

## 7. Mặt bằng tầng nhiều căn, nét layer 0 trong block (06/10/2026)
- `walk()` (dùng chung mọi script) nay cho **đối tượng layer 0 trong block lấy layer của INSERT chứa nó**, theo quy ước AutoCAD. Ví dụ lan can vẽ ở layer 0 trong block chèn trên `A-Lancan`. Chạy lại Cần Thơ, Test AI, Test đo dt: kết quả không đổi.
- Mặt bằng tầng (xref căn hộ đã bind, mã căn `CHxx` ngoài cửa, hành lang chung): dùng `scripts/mat_bang_tang.py`; quy tắc ở `references/quy-uoc-mat-bang-tang.md` (vách kính đo mặt trong, ô mở ≤ 2,6 m đóng theo mặt trát, bếp mở gộp, lô gia và phòng thiếu tên đặt theo nội thất, gom căn theo tiền tố xref).

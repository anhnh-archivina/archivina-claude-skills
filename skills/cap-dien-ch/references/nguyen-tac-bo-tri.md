# Nguyên tắc bố trí mặt bằng cấp điện ổ cắm căn hộ – Archivina

Nguồn: câu trả lời của người dùng trong `H:\@Archivina 2026\@bản vẽ mẫu căn hộ\Skill vẽ MB ổ cắm.docx` và các câu chọn trong
chat (chốt **07/10/2026**); quy ước vẽ lấy từ bản vẽ mẫu `E Mat bang cap dien o cam can ho.dwg`. Mục nào ghi **(chưa chốt)**
là giá trị tạm của skill – nói rõ cho người dùng, không coi là quy tắc.

## Mục lục
1. Phạm vi
2. Đầu vào – khi nào DỪNG HỎI
3. Ràng buộc chung
4. Theo phòng
5. Chia lộ, đi dây
6. Kích thước
7. Ký hiệu, cao độ (bảng ký hiệu mẫu)

## 1. Phạm vi
- Mặt bằng **ổ cắm + hộp chờ + tủ điện + VDP + công tắc 20A (bình nóng lạnh) + công tắc 3 phím ngoài cửa WC**, kèm dây theo lộ
  và mũi tên về `TĐ.CH`. **Chiếu sáng (đèn, công tắc phòng) không thuộc skill này.**
- Có chế độ **soát** bản vẽ nhân viên đã bố trí (Lỗi / Cảnh báo / Gợi ý, Excel).
- Mặt bằng tầng nhiều căn: bố trí theo **căn điển hình**; căn đối xứng dùng lại (skill chạy cùng quy tắc cho từng căn, kết quả
  tương đương đối xứng; người dùng có thể chỉ chọn căn điển hình bằng `--can`).

## 2. Đầu vào – khi nào DỪNG HỎI
- Thiết bị **bố trí theo nội thất**. Thiếu nội thất hoặc thiếu tên phòng → **dừng lại hỏi**, không tự đặt theo loại phòng.
- **Số ổ cắm mặt bếp (B): luôn hỏi trước khi làm** (script gợi ý số theo chiều dài dải bếp tự do, ~1 ổ / 1 m).
- **Ổ máy rửa bát, lò nướng: hỏi trước** (bố trí theo nội thất nếu người dùng đồng ý).
- Dàn lạnh lấy theo block nền kiến trúc; **hộp AC theo phương án đặt dàn nóng** của kiến trúc → không thấy dàn nóng thì hỏi.
- Đế ổ cắm vuông hay chữ nhật (quyết định khoảng cách TV – ĐN): hỏi nếu chưa biết (mặc định chữ nhật).

## 3. Ràng buộc chung
- Tâm ổ cách **khuôn cửa ≥ 200 mm**.
- **Không** bố trí ổ cắm **sau cánh cửa** (trong bán kính cánh quét phía bản lề) và **sau tủ áo**.
- **Ưu tiên tường xây, tránh vách bê tông.** Skill dời tối đa 400 mm dọc tường để tránh BTCT; không tránh được → giữ vị trí,
  chèn ký hiệu mây **"Vị trí cần đặt chờ khi đổ cột vách"** và ghi Cảnh báo.
- Không đặt trên ô cửa / cửa sổ / lan can / vách kính.
- Thiết bị bám mặt tường hoàn thiện (điểm chèn tại mặt tường).

## 4. Theo phòng
### Phòng ngủ
- **G** (đầu giường) ×2 hai bên đầu giường, **tâm cách mép giường 200–250** (skill dùng 200 – `g_cach_mep_giuong`). Mép giường =
  mép đệm (giữa hai tab đầu giường); giường không có tab → theo hộp bao block (Gợi ý kiểm tra).
  Phía ngoài mép giường vướng cửa sổ / thiết bị → đặt **vào trong mép giường 200** (sau đầu giường), ghi Gợi ý *(theo căn mẫu
  P5-(05-18).03 người dùng vẽ 08/10/2026 – chưa chốt thành quy tắc)*.
- **TV**: thẳng **tâm tivi / kệ TV**, bám tường. Không có kệ TV → hỏi (đặt theo trục giường `--tv-pn-theo-truc-giuong` hay bỏ).
- **1 ổ đôi thường** (H+0.4) gần cửa phòng, phía tay nắm, cách khuôn 300 (≥ 200). Phía tay nắm vướng → phía bản lề ngoài vùng
  cánh quét → tường kề (≤ 1,5 m). *(Vị trí 300 lấy từ bản vẽ mẫu)*.
- **Bàn làm việc**: 1 ổ theo tâm bàn. *(cao độ chưa chốt – tạm ổ đôi thường H+0.4)*. Bàn trang điểm: chưa có quy tắc.
- Công tắc đầu giường lắp cùng cao độ ổ cắm (ghi chú bảng ký hiệu; công tắc đèn không thuộc skill).
### Phòng khách
- **TV + ĐN** cạnh nhau theo tâm tivi: **đế vuông cách 100, đế chữ nhật cách 150** (`--de-o`).
- **2 ổ hai đầu sofa**, tâm cách mép sofa 200 *(khoảng cách chưa chốt, theo cách đo ổ G)*; sofa cách tường > 500 → hỏi.
- **Tủ điện TĐ-CH**: trong căn, cạnh cửa chính phía tay nắm, **tâm tủ cách khuôn cửa 500**. Sảnh trước cửa chật (căn DUAL KEY)
  → phía bản lề → tường kề gần cửa.
- **VDP**: ngoài cửa chính = chuông / camera (phía tay nắm, cách khuôn 200, mặt ngoài tường hành lang); trong căn = màn hình,
  cùng tường TĐ-CH cách tâm tủ 600 *(chưa chốt)*.
### Bếp
- **B** trên mặt bếp, **số lượng hỏi trước**; phân đều trên dải tự do của tường bếp nấu, tránh mép bếp nấu 150 và mép chậu
  rửa 200 *(chưa chốt)*; tối thiểu 1 ổ.
- **BT** dưới bếp từ, **HM** theo tâm máy hút mùi (= tâm bếp nấu). Ký hiệu BT vẽ lệch 200 vào phòng trước HM, ghi `H:+0.6`
  (theo bản vẽ mẫu).
- **TL** sau tủ lạnh theo tâm.
- Máy rửa bát / lò nướng: hỏi trước; nếu có: ổ đôi theo tâm thiết bị *(ký hiệu, cao độ chưa chốt)*.
### WC
- **W** (chống ẩm) cạnh lavabo, tâm cách tâm lavabo ~300, chọn phía xa vùng tắm.
- **X** (chống ẩm, bồn cầu điện tử) cạnh bồn cầu, tâm cách mép bồn cầu 150, trên tường sau bồn cầu, phía xa lavabo.
- **BNL** (box chờ bình nóng lạnh) trong WC theo vị trí bình; **công tắc 20A + công tắc 3 phím** (đèn / gương / quạt hút)
  **ngoài cửa WC, phía tay nắm** (công tắc 3 phím cách khuôn 200, 20A cách tiếp 150). Phía tay nắm vướng (cửa khác, ô kính) →
  phía bản lề (cửa WC mở vào trong) → tường kề.
- Nền **không vẽ bình nóng lạnh** (nền Revit): mặc định hỏi; `--bnl-mac-dinh` → box BNL trên tường vuông góc tường cửa, tại góc
  phía **bản lề** cửa WC, cách góc 200 (box cao +2.6, trên cửa) *(theo căn mẫu P5-(05-18).03 – chưa chốt)*. Chế độ soát vẫn báo
  "cửa / sau cánh cửa" cho box này vì chưa xét cao độ – chờ người dùng quyết định có miễn cho box cao (BNL, AC) không.
### Lô gia
- **W** chống ẩm cho **máy giặt** (theo tâm máy, tường sau máy).
- **Hộp AC** tại dàn nóng (phương án kiến trúc), **cách trần 300**; mỗi dàn nóng một hộp.
### Phòng đa năng / phòng chưa có quy tắc
- Không tự bố trí – hỏi người dùng.

## 5. Chia lộ, đi dây
Ưu tiên chia theo khu vực (vẫn phải đảm bảo tải theo thiết bị đóng cắt và dây – skill chỉ báo số thiết bị từng lộ, kỹ sư
điện kiểm tra):
- **Phòng khách + WC chung**: 1 lộ (kể cả VDP).
- **Khu bếp**: 1 lộ (ổ B, TL, HM; **máy giặt và tủ lạnh dùng chung lộ ổ cắm** – skill xếp máy giặt vào lộ bếp).
- **Các phòng ngủ**: 1 lộ (kể cả WC riêng trong phòng ngủ); **căn > 3 phòng ngủ tách 2 lộ**.
- **Lộ riêng**: điều hòa (mỗi hộp AC một lộ), bếp từ (BT), **mỗi bình nóng lạnh một lộ (HW1, HW2…)**; công tắc 20A đi cùng lộ HW của bình.
- **F1, F2…** = quạt hút mùi WC (nối công tắc 3 phím → quạt hút nếu nền có block quạt hút).
- Đặt tên: S1 khách + WC chung, S2 bếp, S3 (S4) phòng ngủ, AC1…, BT, HW1…; nhãn `<lộ>/TĐ.CH` + mũi tên về tủ (như mẫu).
- Dây: polyline trực giao nối các thiết bị cùng lộ (layer `AV-E-PW-Cáp điện`, CENTER2) – sơ đồ đi dây trên trần / âm tường,
  không phải tuyến thi công chi tiết. Ghi chú mẫu: toàn bộ dây luồn ống PVC đi âm tường, trên trần giả.

## 6. Kích thước
- **Toàn bộ kích thước đo từ mép tường đến tâm thiết bị điện** (mép tường = góc phòng hoặc mép ô cửa trên cùng tường).
- **Hai thiết bị gần nhau hơn khoảng cách đến tường → thêm kích thước giữa hai thiết bị** (chuỗi kích thước) để các nét dim
  không trùng, không chồng chéo. Skill: chia mỗi đoạn tường giữa hai mốc làm đôi, mỗi nửa đo chuỗi từ mốc gần.
- Dim style `A 1-50` (DIMSCALE 50, chữ 100, tick kiến trúc), layer `AV-E-Dim`, đường dim cách tường 600 (như mẫu).

## 7. Ký hiệu, cao độ (bảng ký hiệu mẫu)
| Ký hiệu | Block | Giá trị thuộc tính | Cao độ |
|---|---|---|---|
| Tủ điện âm tường dạng module | `AV-E-Tu dien phong` | TĐ-CH | H:+1.5 |
| Ổ cắm đôi 3 chấu 16A-220V âm tường | `AV-E-O cam doi 3 chau` | (trống) | H:+0.4 |
| … – Tivi / Khu bếp / Đầu giường / Tủ lạnh / Điện nhẹ | `AV-E-O cam doi 3 chau` | TV / B / G / TL / ĐN | +1.2 / +1.2 / +0.6 / +0.4 / +1.2 |
| Ổ cắm 3 chấu chống ẩm | `AV-E-O cam don 3 chau chong am` | W / X | +1.2 / +0.5 |
| Box chờ 80x80x60 bếp từ / hút mùi / điều hòa / BNL | `AV-E-Hop dau noi am tuong 80x80x50` | BT / HM / AC / BNL | +0.6 / +2.0 / +2.2 / +2.6 |
| Công tắc 20A/220V (BNL) | `AV-E-Cong tac 20A` (tỷ lệ 1.6) | – | +1.2 |
| Công tắc 1,2,3 một chiều 10A | `AV-E-Cong tac ba - 1 chieu` | – | +1.2 |
| Dây chờ cấp nguồn video doorphone | `BNN` + text `VDP` | – | +1.4 |

Hộp AC: bảng ký hiệu ghi H:+2.2; nguyên tắc người dùng: **cách trần 300** – báo cả hai khi trần thực tế khác 2,5 m.

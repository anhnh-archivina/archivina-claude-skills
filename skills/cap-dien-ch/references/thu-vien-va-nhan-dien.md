# Thư viện ký hiệu, layer và nhận diện – skill cap-dien-ch

## Thư viện (`assets/thu-vien/`)
Tách từ `H:\@Archivina 2026\@bản vẽ mẫu căn hộ\E Mat bang cap dien o cam can ho.dwg` (07/10/2026) bằng `-WBLOCK` trên bản sao.
Block 1:1 mm, `INSUNITS=4` (file `E-TU-DIEN.dwg` gốc là block động mang đơn vị inch – đã đặt lại mm, nếu không AutoCAD tự nhân 25,4).

| File | Block khi chèn | Ghi chú |
|---|---|---|
| `E-O-DOI.dwg` | `AV-E-O cam doi 3 chau` | thuộc tính `1` = TV / B / G / TL / ĐN / trống |
| `E-O-CHONG-AM.dwg` | `AV-E-O cam don 3 chau chong am` | thuộc tính `W` = W / X |
| `E-HOP-CHO.dwg` | `AV-E-Hop dau noi am tuong 80x80x50` | thuộc tính `1` = BT / HM / AC / BNL |
| `E-TU-DIEN.dwg` | `AV-E-Tu dien phong` | thuộc tính `1` = TĐ-CH |
| `E-VDP.dwg` | `BNN` | + TEXT "VDP" (AV-ME-Text, cao 110) |
| `E-CT-20A.dwg` | `AV-E-Cong tac 20A` | chèn tỷ lệ 1.6 (như mẫu) |
| `E-CT-BA.dwg`, `E-CT-DON.dwg`, `E-CT-DOI.dwg` | `AV-E-Cong tac ba / don / doi - 1 chieu` | layer chiếu sáng |
| `E-QUAT-HUT.dwg` | `AV_HutMuiWC1` | chỉ để nhận diện / nối F |
| `E-MUI-TEN.dwg` | `AV-E-Mui ten ve tu` | mũi tên dây về tủ, tỷ lệ 0.7, hướng +X |
| `E-MAY-CHO-VACH.dwg` | `AV-E-Cho cot vach` | mây 250×250 "vị trí cần đặt chờ khi đổ cột vách" |
| `E-BANG-KY-HIEU.dwg` | `AV-E-Bang ky hieu o cam` | bảng ký hiệu 10300×4600, điểm chèn góc dưới trái; đã sửa lỗi mã hóa "KƯ HIỆU" → "KÝ HIỆU", "ĐIỀU H̉A" → "ĐIỀU HÒA" |

**Quy ước hướng:** ổ cắm, hộp chờ, tủ điện, công tắc có điểm chèn tại **mặt tường hoàn thiện**, ký hiệu nhô theo **+Y cục bộ**
→ góc xoay = hướng pháp tuyến vào phòng − 90°. VDP: +X cục bộ hướng ra không gian đặt. `catalog.json` ghi mã, block, file,
layer, tag, giá trị, cao độ, kích thước ký hiệu; `bi_danh_block` là tên block tương đương khi SOÁT bản vẽ nhân viên.

**Chèn trong script:** `(command "_.-INSERT" (if (tblsearch "BLOCK" ten) ten "ten=file") "_S" k "_R" goc pt "giá trị")`
với `ATTREQ=1`, `ATTDIA=0`. Không dùng kiểu `-INSERT ten=file` rồi `(command)` để hủy – Core Console thoát ngang.
Block đã có trong bản vẽ thì dùng định nghĩa sẵn có (không định nghĩa lại).

## Layer (theo mẫu, tạo nếu thiếu)
`AV-E-PW-Thiết bị điện động lực` (50) · `AV-E-PW-Tủ điện` (50) · `AV-E-PW-Cáp điện` (10, CENTER2) ·
`AV-E-LT-Thiết bị chiếu sáng` (50, công tắc) · `AV-E-Dim` (8) · `AV-ME-Text` (3, style `AV-ME-Text` arial cao 100) · `M-EQPM` (50).
Tên có dấu tiếng Việt → trong `.scr` viết `\U+XXXX` (hàm `acad_str`).

## Nhận diện nền (cấu hình `scripts/cau_hinh_o_cam.json`)
- **Phòng / căn:** dùng bộ dựng phòng của `thiet-ke-tran-ch` (`soat_tran.dung_phong`, lõi `dien-tich-ch`): Text tên phòng
  (`layer_ten_phong`, mặc định `A-Text`; khác thì `--layer-ten`) + nét tường `layer_ranh` + khung cửa `layer_cua`. Không có tên
  phòng → loại phòng suy theo nội thất (ghi Cảnh báo "Thiếu tên phòng"). Không dựng được phòng nào → script dừng.
- **Nội thất:** `noi_that` (tên block, bỏ tiền tố xref, bỏ dấu, `*`/`?`), block động `*Uxx` lấy tên gốc. Giường nhận theo 2
  tab đầu giường, tủ áo theo ≥ 6 móc áo. Loại mới so với skill trần: `may_giat`, `tu_lanh`, `may_rua_bat`, `lo_nuong`,
  `binh_nong_lanh`, `dan_nong`, `dan_lanh`, `ke_tv`, `ban_lam_viec`, `quat_hut`.
- **Kệ TV suy theo hình dạng:** block chưa nhận diện dài 900–2800, sâu 150–500, sát tường (≤ 150) đối diện giường / sofa → coi
  là kệ TV, ghi Gợi ý để người dùng xác nhận.
- **Block chưa nhận diện** (layer nội thất `layer_noi_that_suy`) được đánh số `#n` trên ảnh và liệt kê ở sheet `Noi that` /
  JSON `block_chua_nhan_dien`. Người dùng cho biết loại → tạo file JSON bổ sung, chạy lại với `--nhan-dien-bo-sung`:
  ```json
  {"86786": "bep_nau", "CT3-Tn-MEP": "binh_nong_lanh", "A$C4b41b423": "ban_lam_viec"}
  ```
  Tên phải đúng như cột "Tên block" (sau khi bỏ tiền tố xref). Không sửa code.
- **Cửa:** cung `ARC` bán kính 500–1200 trên `layer_cua` (kể cả trong block / xref, kể cả nét Revit đã nổ). Đầu "đóng" của cung
  = đầu mà đoạn bản lề → đầu đó nằm trong ô cửa (ngoài mọi phòng). Cửa không có cung (cửa ACA nổ thiếu cung, cửa lùa) → không
  biết phía tay nắm → hỏi. Cửa chính = cửa nối căn với bên ngoài, ưu tiên cửa vào P. khách / hành lang, cửa rộng nhất.
- **Vách BTCT:** nét trên `layer_btct` (A-Column, S-Wall, A_Wall BT…) cách mặt tường ≤ 40 mm. Lan can / vách kính:
  `layer_lan_can` (cấm đặt).

## Giới hạn đã biết
- Bản vẽ xuất từ Revit nổ hết (nội thất là LINE/ARC, không có tên phòng) – ví dụ chính file mẫu E: không dựng được phòng →
  cần nền có Text tên phòng và nội thất dạng block.
- Kệ TV / sofa dạng cụm lớn: mép lấy theo hộp bao cụm – có Gợi ý kiểm tra.
- Không tính tải, tiết diện dây, CB: chỉ đếm thiết bị theo lộ.
- Soát lộ riêng (AC / BT / HW) dựa trên nhãn `<lộ>/TĐ.CH` trên bản vẽ – không lần theo nét dây.

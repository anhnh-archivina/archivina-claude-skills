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
| `E-MUI-TEN.dwg` | `AV-E-Mui ten ve tu` | mũi tên dây về tủ – **không vẽ nữa** (08/10/2026), chỉ để nhận diện khi soát |
| `E-MAY-CHO-VACH.dwg` | `AV-E-Cho cot vach` | mây 250×250 "vị trí cần đặt chờ khi đổ cột vách" |
| `E-BANG-KY-HIEU.dwg` | `AV-E-Bang ky hieu o cam` | bảng ký hiệu 10300×4600, điểm chèn góc dưới trái; đã sửa lỗi mã hóa "KƯ HIỆU" → "KÝ HIỆU", "ĐIỀU H̉A" → "ĐIỀU HÒA"; cao độ cập nhật theo chi tiết lắp đặt 08/10/2026 |

**Quy ước hướng:** ổ cắm, hộp chờ, tủ điện, công tắc có điểm chèn tại **mặt tường hoàn thiện**, ký hiệu nhô theo **+Y cục bộ**
→ góc xoay = hướng pháp tuyến vào phòng − 90°. VDP: +X cục bộ hướng ra không gian đặt. `catalog.json` ghi mã, block, file,
layer, tag, giá trị, cao độ, kích thước ký hiệu; `bi_danh_block` là tên block tương đương khi SOÁT bản vẽ nhân viên.

**Chèn trong script:** `(command "_.-INSERT" (if (tblsearch "BLOCK" ten) ten "ten=file") "_S" (/ k (hsdv ten)) "_R" goc pt "giá trị")`
với `ATTREQ=1`, `ATTDIA=0`. Không dùng kiểu `-INSERT ten=file` rồi `(command)` để hủy – Core Console thoát ngang.
Block đã có trong bản vẽ thì dùng định nghĩa sẵn có (không định nghĩa lại). **Định nghĩa sẵn có có thể mang đơn vị chèn khác mm**
(vd `AV-E-Tu dien phong` trong `E Mat bang cap dien o cam can ho test.dwg` là block động đơn vị inch → AutoCAD tự nhân 25,4, tủ
điện thành 10×13 m): hàm `hsdv` đọc đơn vị của BLOCK_RECORD (mã 70) so với `INSUNITS` bản vẽ và chia tỷ lệ chèn tương ứng.

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

## Nền xuất từ Revit (`--nen-revit co`, `scripts/nen_revit.py`, cấu hình `nen_revit`)
Mặt bằng tầng Revit đã bind (tường / cửa / nội thất nổ thành LINE/ARC, không có Text tên phòng, mã căn đặt ngoài căn trong khung
có đường dẫn). Kiểm chứng 08/10/2026: `E Mat bang cap dien o cam can ho test.dwg` (24 căn P5-(05-18).01…24).
- **Phòng:** mặt kín của nét `A-NETTUONG` + `A-NETCAT` + LINE `A-CUA`, đóng ô cửa ≤ 1200 bằng tia (`tpp.build_faces`). Mặt
  ≥ 0,5 m², rộng ≥ 500. Mặt tủ bếp hẹp (nét cắt tủ bếp tạo mặt riêng, chứa bếp / chậu / máy rửa bát / tủ lạnh) gộp vào phòng kề.
- **Căn:** điểm cuối đường dẫn mã căn (`ma_can`, khung chữ nhật quanh text, nét có một đầu trên khung) → mặt phòng chứa nó →
  loang đồng thời mọi căn qua: (a) cạnh chung không phải nét tường ≥ 300 (đoạn đóng ô cửa, nét kính), (b) chuỗi mặt mỏng
  < 400 (ô cửa trong bề dày tường, khung cửa trượt), (c) cung cửa: phòng chứa cung ↔ phòng bên kia ô cửa (ô cửa WC có nét
  ngưỡng trên layer tường nên (a) không đủ). Hành lang chung = mặt > 30 m² không nội thất → chặn; mặt không nội thất giáp căn khác
  → bỏ (sảnh tầng). Không có mã căn / đường dẫn → căn bị bỏ, ghi `van_de`.
- **Cung cửa:** `A-CUA` + `layer_cung_cua_them` (`A-KHUAT`: cửa 2 cánh căn DUAL KEY vẽ cung bằng nét khuất). Đầu "mở" của cung =
  đầu có **cánh cửa: ≥ 2 nét song song lệch nhau** (dày cánh ~40) chạy dọc từ bản lề (`dem_canh_cua`, dùng cả trong `doc_cua`);
  khung / ngưỡng dọc tường là các nét trùng một đường → không nhầm.
- **Nội thất theo hình dạng cụm nét** (cụm = nét chung đầu mút ≤ 1 mm, cùng layer):
  giường = cụm gối (≥ 3 cung, 380–820 × 280–560) gom ≤ 1100 không qua tường + 2 nét cạnh giường dài 1500–2500; trục theo cạnh dài
  gối lớn nhất; vùng gối 700 ở đầu có gối · tivi = hình chữ nhật mảnh 800–2200 × 15–120 (bỏ nẹp cửa tủ lạnh, cánh tủ trượt nối
  tiếp) · bếp nấu = khung 500–950 × 380–620 chứa ≥ 2 vòng tròn lệch tâm · máy giặt = ô vuông 520–720 chứa vòng r 130–260 · máy
  rửa bát = ô vuông 550–650 gạch chéo, cách bếp ≤ 1500 · chậu bếp = khung chứa hốc có cung · tủ lạnh = chữ nhật 650–1050 ×
  480–820 có nẹp cửa song song phía trước · sofa = 1500–3600 × 650–1800 có ≥ 2 cung hoặc ≥ 8 nét và sâu ≥ 720 · tủ áo = chữ nhật
  sâu 500–700, dài 900–3600, chỉ giữ trong phòng ngủ · bồn cầu (`A-NETTHAY`) = ≥ 6 cung 400–600 × 300–450 · lavabo = cụm có
  cung / polyline 330–700 × 280–560 · dàn nóng (`A-NETMANH`) = cụm ≥ 8 ELLIPSE 450–1300 × 150–600.
  Mọi đối tượng ghi "suy" (dấu ? trên ảnh). Loại phòng theo nội thất: giường → PN, bồn cầu → WC, sofa → khách, bếp nấu → bếp,
  máy giặt / dàn nóng → lô gia, không nội thất < 8 m² → sảnh / hành lang.
- **Không nhận được:** bình nóng lạnh (nền không vẽ) → hỏi hoặc `--bnl-mac-dinh`; quạt hút WC (không vẽ) → không có lộ F;
  vách BTCT (Revit không tách layer) → không đánh dấu mây – nói rõ khi báo cáo.
- DXF xuất trực tiếp bản vẽ có block khung tên lỗi bị cụt (`missing ENDSEC`): `-WBLOCK` toàn bộ Model ra file mới rồi `xuat_dxf`.
- Chạy ~4 phút / tầng 24 căn (đọc nét ~1,5 phút).

## Giới hạn đã biết
- Bản vẽ mẫu E (xuất Revit nhưng **không có mã căn / đường dẫn**, chỉ 1 căn): chưa thử chế độ `--nen-revit` – cần ít nhất mã căn
  có đường dẫn chỉ vào căn.
- Kệ TV / sofa dạng cụm lớn: mép lấy theo hộp bao cụm – có Gợi ý kiểm tra.
- Không tính tải, tiết diện dây, CB: chỉ đếm thiết bị theo lộ.
- Không vẽ / không soát dây, nhãn lộ (bỏ 08/10/2026): lộ chỉ ghi trong Excel để kỹ sư điện kiểm tra.

# Phân nhóm phòng lát sàn (chốt 21/10/2026; tỷ lệ + điểm gốc theo bản anh sửa trên CanTho_LatSan)

Hatch đặt trên layer **`A-Materials`** (layer chuẩn ISO - ARCHIVINA, màu 251), liên kết (associative) với polyline phòng layer `A- Dien tich phong`; polyline loại trừ (HKT/cột) nằm trong phòng được chọn kèm làm lỗ.

| Nhóm | Phòng | Pattern | Tỷ lệ | Góc |
|---|---|---|---|---|
| PN | phòng ngủ (kể cả master), phòng làm việc, phòng thay đồ | DOLMIT | 500 | 0° |
| PK | phòng khách, sinh hoạt chung, bếp, phòng ăn, sảnh, hành lang trong căn | ANSI37 | 5000 | 45° |
| WC | vệ sinh / WC / phòng tắm, kho | ANSI37 | 2500 | 45° |
| LG | ban công, lô gia (logia, loggia) | ANSI37 | 2500 | 45° |

## Điểm gốc hatch (HPORIGIN) – `phan_loai.diem_goc`
Cửa đi = block trên layer/tên chứa `Door` / `Cua` (AEC_DOOR đã nổ: DXF xuất với `no_doi_tuong_aec=true`); cửa thuộc phòng khi cách polyline phòng ≤ 150 mm; bản lề = tâm cung mở.
| Nhóm | Điểm gốc |
|---|---|
| PK | **Góc sảnh căn hộ**: cạnh polyline chứa cửa chính (cửa không thông sang phòng nào khác), lấy đầu cạnh **phía xa bản lề** |
| WC | **Góc phòng tắm**: đỉnh polyline nằm trong vùng tắm (block thiết bị WC bao block sen tắm `Sentam`/`shower`); nhiều đỉnh → gần cửa WC nhất; không có vùng tắm → đỉnh gần sen; kho (không sen) → đỉnh gần cửa |
| LG | **Góc trong gần cửa đi ra**: đỉnh polyline gần cửa ra lô gia nhất |
| PN | **Góc gần cửa đi vào phòng**: đỉnh gần cửa thông sang phòng nhóm PK (không xét cửa WC trong phòng) |
Không tìm được cửa → JSON `chua_co_diem_goc`, hỏi anh. Kiểm chứng CanTho: khớp điểm anh đặt tay ở PK, WC1, WC2, Logia 2; Logia 1 anh đặt tay góc xa cửa là nhầm – anh xác nhận giữ quy tắc góc trong gần cửa đi ra (21/10/2026).

## Nhận diện tên phòng (`scripts/phan_loai.py`)
- Tên phòng = Text/MText nằm trong polyline phòng; bỏ nhãn diện tích (có `m2`, `DTCH`, chỉ có số).
- So khớp trên tên đã bỏ dấu, viết thường, theo thứ tự **LG → WC → PN → PK** (để "ban công" không lọt vào "ăn"):
  - LG: `ban cong`, `lo gia`, `logia`, `loggia`, `LG1`, `BC1`
  - WC: `wc`, `ve sinh`, `VS1`, `tam`, `kho`
  - PN: `ngu`, `PN1`, `lam viec`, `thay do`, `master`
  - PK: `khach`, `PK`, `bep`, `an`, `sanh`, `hanh lang`, `sinh hoat`, `kitchen`, `living`, `dining`
- Một polyline có nhiều tên cùng nhóm (bếp mở gộp phòng khách) → một hatch nhóm đó.

## Không tự quyết – hỏi anh
- Phòng không có tên, tên không khớp nhóm nào, hoặc tên thuộc ≥ 2 nhóm (ví dụ phòng ngủ + WC trong một polyline).
- WC và LG cùng ANSI37 2500/45° → thống kê nhận nhóm theo tên phòng chứa hatch.
- Pattern/tỷ lệ/góc khác bảng trên, hoặc loại phòng mới (phòng giặt, phòng thờ, sân phơi…).
- Phòng không lát (ô kỹ thuật, sàn gỗ riêng…) → anh chỉ định.

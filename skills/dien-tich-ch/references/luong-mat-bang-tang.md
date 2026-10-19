# Luồng B – Mặt bằng tầng nhiều căn

Dấu hiệu: một file chứa cả tầng, mỗi căn là xref đã bind (layer `CH15$0$A-Wall`, `CT1-T0-CH05$0$A-Vua trat`), mã căn `CHxx` là text ở hành lang trước cửa vào, có hành lang/lõi thang chung. Dùng `scripts\mat_bang_tang.py` (chưa có MCP tương ứng) thay cho `tao_polyline_phong.py` + `tao_duong_bo_can_ho.py`, vì gom căn theo khoảng cách không dùng được (tường chung hai căn mỏng như tường ngăn).

**Quy tắc đo, phân loại vùng #, gom căn, nhãn, chỉnh hình, kết quả kiểm chứng CT1: `quy-uoc-mat-bang-tang.md`** (đọc mục 1, 3 khi trình ảnh duyệt; không chép lại ở đây).

## Quy trình
1. Chuyển DWG → DXF có nổ ACA (`xuat_dxf` hoặc `dwg_to_dxf_aec.ps1`). File tầng lớn (DXF ~60 MB) mỗi lần đọc 1–2 phút.
2. **Phân tích** (5–10 phút với 19 căn):
   `python mat_bang_tang.py phan-tich <dxf> --out-dir <thư mục>`
   Tự làm: thêm layer ranh phụ (lan can, tường BTCT, khung nhôm, kính; bỏ nét < 200 mm), đóng ô mở chưa vẽ cửa ≤ 2,6 m theo mặt trát rồi bỏ các đoạn đóng chia đôi không gian mở/cắt hốc trong phòng, dựng mặt trong vách kính cho phòng còn hở, nối khe 6–25 mm, gán phòng vào căn theo tiền tố xref, ghép mã căn gần nhất, phân loại vùng chưa tên. Đầu ra: `de_xuat_ranh_phong.png`, `phan_loai_vung.png` (số #), `mbt_phan_tich.json`.
3. **Trình người dùng duyệt hai ảnh (bắt buộc, không tự vẽ):** ghép mã căn ↔ xref; phòng còn hở (`phong_ho`); phân loại từng vùng # (lô gia / phòng thiếu tên + tên đề xuất theo nội thất / hành lang trong căn / ngoài căn / loại trừ). Chỉ ra chỗ không đối xứng giữa các căn cùng loại. Người dùng chỉnh bằng số #.
4. **Xuất** theo phân loại đã duyệt:
   `python mat_bang_tang.py xuat <dxf> --out-dir <thư mục> --du-an CT1 --tang T5A-10 [--doi "#76=ngoai;#48=Phòng ngủ;#41=loai-tru"]`
   `--doi`: `ngoai`, `loai-tru`, `hanh-lang` hoặc tên phòng bất kỳ. Đầu ra: `ve_dien_tich_tang.scr`, `<ngày>_<dự án>_<tầng>_BaoCaoDienTich.xlsx` (Tóm tắt / Diện tích / Vấn đề / Vùng chưa tên), `tong_dien_tich.png`, `ket_qua_dien_tich.json`. Chỉnh hình (`chinh_hinh.py`) tự chạy trong `xuat`.
5. Vẽ vào bản sao (`ve_polyline_vao_dwg.ps1` hoặc MCP `ve_vao_ban_sao`; file tầng lớn cần `-TimeoutSec 900`), **gắn Field** rồi xuất DXF bản sao **không nổ ACA** và chạy `kiem_tra_nhan.py` (bắt buộc, phải đạt hết). Xem `field-va-kiem-tra.md`.
   - **Sửa trực tiếp trên tab đang mở** (chỉ khi người dùng yêu cầu VÀ tab là bản sao kết quả, không phải bản gốc): `scripts\ve_com_tab_mo.py --ban-ve <tên tab> --json ve_dien_tich_tang.json --xoa-handle <handle cũ> --luu-handle <handle mới>`. Vẽ bằng COM, tự gắn Field (`--khong-field` để bỏ), một nhóm UNDO, không lưu (`--luu` chỉ khi là bản sao Claude tạo và người dùng muốn lưu).
   - **Không** dùng lệnh `SCRIPT` qua `SendCommand` vào tab đang mở: chữ có dấu "(" (ví dụ "Phòng (chưa tên)") bị AutoCAD hiểu là biểu thức LISP, giữ AutoCAD bận hơn 45 phút và kẹt cả Core Console (07/10/2026). Chữ ghi vào `.scr` không được chứa dấu ngoặc.

## Chưa chốt
Ranh tại cửa chính khi bản vẽ không vẽ cửa: đường bo theo mặt tường trong, script báo Cảnh báo kèm danh sách căn thiếu cửa; hỏi người dùng.

# Gắn Field cho nhãn diện tích và kiểm tra nhãn (bắt buộc cho mọi luồng)

## Gắn Field (chốt 07/10/2026)
Người dùng cần sửa tay đường bo mà nhãn tự cập nhật. Sau bước vẽ cuối (đã có cả polyline phòng và đường bo căn), đổi mọi nhãn `xx.x m2` / `DTCH: xx.x m2` thành **Field** liên kết polyline:
- `python gan_field_dien_tich.py --mo-file <bản sao kết quả.dwg>` → mở bản sao trong AutoCAD, gắn, lưu, đóng.
- `python gan_field_dien_tich.py --ban-ve "<tên tab đang mở.dwg>"` → tab đang mở (phải là bản sao kết quả): 1 nhóm UNDO, không lưu.

Quy tắc:
- Ghép nhãn ↔ vùng như `kiem_tra_nhan.py` (polyline ngoài cùng trên layer phòng/căn; polyline cùng layer nằm trong là loại trừ; điểm nhãn = tâm khung chữ). **Chỉ gắn khi số trên nhãn bằng diện tích vùng**; lệch thì báo Lỗi, giữ nguyên nhãn. Chữ khác có "m2" trong vùng (ghi chú cũ) bỏ qua khi vùng đã có nhãn đúng.
- Vùng không loại trừ: `%<\AcObjProp Object(%<\_ObjId …>%).Area \f "%lu2%pr1%ps[DTCH: , m2]%ds46%ct8[1E-06]">%`. Vùng có cột/HKT: Field công thức `%<\AcExpr (Area ngoài − Area lỗ …) \f "…">%`. Tiền tố/hậu tố, số chữ số thập phân, dấu thập phân lấy theo nhãn đang có.
- Cần AutoCAD GUI đang chạy hoặc khởi động được (COM). Core Console **không có** `vla-`/ActiveX nên không tạo được Field; không cố viết Field bằng `entmake`.
- Nhãn cập nhật khi REGEN/mở/lưu/in (`FIELDEVAL` mặc định 31). Copy cả polyline lẫn nhãn sang chỗ khác thì nhãn mới vẫn trỏ polyline cũ → gắn lại (chạy lại script, an toàn khi chạy nhiều lần).
- JSON: `da_gan`, `gan_phong`, `gan_can`, `co_cong_thuc`, `loi`, `canh_bao`, `chu_khac_bo_qua`, `lech_sau_regen` (phải rỗng), `vung_khong_nhan`.

## Kiểm tra nhãn sau khi vẽ (bắt buộc)
Sau mỗi lần vẽ vào bản sao: chuyển bản sao sang DXF (`xuat_dxf` / `dwg_to_dxf_aec.ps1`) rồi chạy MCP `kiem_tra_nhan` hoặc
`python kiem_tra_nhan.py <ban_sao.dxf> [--layer-phong "A- Dien tich phong"] [--layer-can "Dien tich thong thuy"]`.

Script ghép mỗi polyline phòng/căn với polyline loại trừ cùng layer nằm trong nó, tìm nhãn `xx.x m2` (phòng) hoặc `DTCH: xx.x m2` (căn) nằm trong vùng (TEXT căn lề lấy `align_point`; Field đọc theo giá trị hiển thị). Báo Lỗi khi: nhãn khác diện tích polyline đã làm tròn, vùng không có nhãn, một vùng nhiều nhãn, polyline chưa Closed. Mã thoát 0 = đạt.
- Polyline có sẵn sai layer (ví dụ đường bo căn nằm trên layer phòng) hiện thành "phòng không có nhãn": báo đúng nguyên nhân là sai layer.
- Kiểm bằng mắt nhãn DTCH không giao tường, nội thất, chữ.
- Báo người dùng số vùng đạt / tổng và từng lỗi (handle, giá trị ghi, giá trị đúng).

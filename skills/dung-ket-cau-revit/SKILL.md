---
name: dung-ket-cau-revit
description: Ket cau Revit – Dựng MÔ HÌNH KẾT CẤU BTCT trong Revit 2026 từ MẶT BẰNG KẾT CẤU AutoCAD (.dwg/.dxf, mm) của Archivina – mặt bằng định vị cột + mặt bằng kết cấu dầm sàn từng tầng (tên "MẶT BẰNG KẾT CẤU SÀN TẦNG n ( CỐT +x.xxx )"): level theo cốt, lưới trục (tên từ bóng trục), cột kết cấu (polyline layer cột, mã C1…, cột dựng), dầm (cặp nét song song thấy / khuất + nhãn "D1-22X40" theo cm), sàn kết cấu (biên ngoài, lỗ mở dấu X, vùng hạ / nâng cốt theo hatch + chú giải), family cột / dầm Archivina tự tạo từ .rft, Structural Plan mỗi tầng + view 3D. Dùng khi người dùng nhờ dựng / chuyển / mô hình hoá kết cấu, cột dầm sàn sang Revit từ bản vẽ CAD, "dựng mô hình KC", "model kết cấu", "đưa mặt bằng kết cấu vào Revit", kể cả khi không nhắc tên skill. Không dùng cho móng / cọc / vách / cầu thang (chưa thuộc phạm vi), không dùng cho kiến trúc căn hộ (rv_dung_can_ho).
---

# Dựng mô hình kết cấu Revit từ mặt bằng KC AutoCAD

Quy tắc chi tiết (đã chốt 12/10/2026): `references/quy-tac-dung-ket-cau.md` – **đọc trước khi chạy**.

## Phạm vi
- Đầu vào: **mặt bằng kết cấu KC** (MB định vị cột + MB kết cấu dầm sàn mỗi tầng). Không tự đề xuất hệ kết cấu từ MB kiến trúc.
- Dựng: **trục, level, cột, dầm, sàn** BTCT. Vách / lõi, móng / đài / cọc, cầu thang, dầm cong, cột tròn: **chưa dựng** – gặp thì ghi "chưa dựng" trong báo cáo.
- Dựng vào **dự án KC MỚI** (`Structural Analysis-DefaultMetric.rte`, mm), không dựng vào file gốc / file của người khác.

## Quy trình
1. **Đọc bản vẽ (chỉ đọc, bản sao):** `thong_tin_dwg` (đơn vị mm? xref thiếu?) → `xuat_dxf` (thư mục kết quả trong `03-Ban-Sao-Lam-Viec\` của dự án, hoặc `03-Cong-Cu\05-Skill-Test\` khi thử).
2. **Hỏi trước khi đọc** (không tự đặt):
   - Cấp bền bê tông **cột / dầm / sàn** (ví dụ B25 / B22.5). Thiếu → vật liệu "Archivina_BTCT (chua xac dinh)" và ghi trong báo cáo.
   - Nếu bản vẽ có **cột dựng** (layer `S-Cot dung`) ở tầng trên cùng: đỉnh cột ở cốt nào (level mái).
3. **Nhận diện:**
   ```
   python -I scripts/doc_mb_ket_cau.py <ban_ve.dxf> --ra <thu_muc> --vat-lieu "cot=B25;dam=B22.5;san=B22.5" [--tang-tren "Mai=17350"]
   ```
   Layer khác chuẩn: `--layer-cot`, `--layer-cot-dung`, `--layer-dam`, `--layer-truc` (regex). Kết quả: `ket_qua.json` (tóm tắt, `can_hoi`, `canh_bao`), `spec_ket_cau.json`, ảnh `xem_lai_<tầng>.png`.
4. **Duyệt với người dùng:** gửi ảnh xem lại (SendUserFile), tóm tắt level / số cột, dầm, sàn / loại tiết diện; **hỏi từng mục `can_hoi`** (dầm lệch nhãn, dầm thiếu nhãn, hatch không có chú giải, cột chồng khác tiết diện, cột không có tầng trên, thiếu cốt / chiều dày sàn). Sửa bằng tham số rồi chạy lại; mục không sửa được bằng tham số → sửa tay `spec_ket_cau.json` (ghi rõ đã sửa gì) hoặc báo người vẽ sửa bản vẽ.
5. **Dựng (GHI – hỏi trước):**
   - `rv_ket_noi` (Revit đang mở, tab Archivina MCP, server chạy).
   - `rv_tao_du_an(duong_dan_rvt=..., template="D:\Revit\Templates\English\Structural Analysis-DefaultMetric.rte")` → file .rvt mới (không ghi đè).
   - Người dùng bấm **Archivina MCP > Cho phép ghi**.
   - `rv_dung_ket_cau(spec_ket_cau.json)` – lần đầu tự tạo family `Archivina_Cot BTCT chu nhat` / `Archivina_Dam BTCT chu nhat` từ `Metric Structural Column.rft` / `Metric Structural Framing - Beams and Braces.rft` và lưu vào `revit-mcp\families\` (lần sau nạp lại). Lỗi → RollBack toàn bộ, Ctrl+Z hoàn tác được.
6. **Kiểm tra sau dựng (chỉ đọc):** `rv_thong_tin` (level, cảnh báo), `rv_khoi_luong` cho `OST_StructuralColumns`, `OST_StructuralFraming`, `OST_Floors` theo từng level – so số lượng / tiết diện với `ket_qua.json`; `rv_canh_bao`; `rv_chup_view` view `Archivina_3D KC` và 1–2 mặt bằng `KC - Tầng n`.

## Báo cáo (theo CLAUDE.md)
(1) Kết quả: đã dựng / dừng chờ trả lời; số trục, level, cột, dầm, sàn theo tầng; file .rvt. (2) Việc anh cần quyết định (`can_hoi` còn lại). (3) Chi tiết: loại tiết diện, vùng hạ / nâng cốt, cảnh báo Revit. (4) Chưa kiểm tra được / chưa dựng: móng, vách, cầu thang, xref chưa nạp, hatch lạ, font thiếu.

## Bẫy đã biết
- Bóng trục / nhãn nằm trong block lồng: ATTRIB phải nhân ma trận block cha (đã xử lý).
- Ô lỗ mở: chỉ nhận ô chữ nhật có **đúng 2 đường chéo** nối góc đối; polygonize phải bỏ đường chéo (không thì ô bị chia tam giác).
- Cột cắt (dưới sàn) và cột dựng (trên sàn) cùng vị trí là 2 đoạn cột khác nhau – không gộp.
- Dầm liên tục qua dầm phụ chỉ ghi nhãn 1 lần: nét dầm gộp qua khe ≤ 600 mm, nhịp chỉ chia theo cột; đầu dầm không tựa cột kéo về tim dầm vuông góc.
- Chú giải sàn khác nhau theo từng tờ (ANSI37 = hạ 335 ở T2 nhưng hạ 50 ở T5) – luôn đọc chú giải của đúng tờ.
- Revit: nạp family từ family document phải ở NGOÀI transaction của dự án (add-in làm trước TransactionGroup).

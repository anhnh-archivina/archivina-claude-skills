# Quy tắc dựng mô hình kết cấu Revit từ MB KC (chốt với người dùng 12/10/2026)

## 1. Đầu vào và phạm vi
| Mục | Quy tắc |
|---|---|
| Bản vẽ | MB kết cấu KC: MB định vị cột + MB kết cấu dầm sàn từng tầng. Đơn vị mm (`INSUNITS=4`), khác → hỏi. |
| Cấu kiện | Trục + level + cột; dầm + sàn. Vách, móng, cọc, cầu thang: chưa dựng (báo "chưa dựng"). |
| Dự án Revit | Dự án KC **mới** từ `Structural Analysis-DefaultMetric.rte` (mm / m²). Kiến trúc link sau. |
| Family | Claude tự tạo từ `.rft` (máy không có thư viện family): `Archivina_Cot BTCT chu nhat`, `Archivina_Dam BTCT chu nhat`, tham số kiểu `b`, `h`; kiểu `Cot bxh`, `Dam bxh`; sàn `Archivina_San BTCT <dày>`. |
| Vật liệu | Hỏi cấp bền theo dự án cho cột / dầm / sàn → vật liệu `Archivina_BT <cấp>`. Thiếu → `Archivina_BTCT (chua xac dinh)`. |
| Đầu ra kiểm tra | Structural Plan `KC - <level>` mỗi level + view 3D `Archivina_3D KC`. Trước khi ghi: ảnh `xem_lai_*.png` để người dùng duyệt. |

## 2. Level và cao độ
- Cốt ghi trên MB (`( CỐT +3.850 )`) = **cốt mặt sàn kết cấu** → level `Tầng n` cao độ 3850.
- MB định vị cột tầng 1 không ghi cốt → **chân cột tầng 1 tại ±0.000**.
- MB sàn không ghi cốt → hỏi.

## 3. Trục và gốc toạ độ
- Trục: nét layer `truc|grid|axis`, tên lấy từ bóng trục (text / attribute trong vòng tròn ở đầu trục).
- Gốc toạ độ Revit = giao **trục chữ đầu tiên × trục số đầu tiên** (A × 1). Các MB quy về gốc này; lưới trục MB nào khác MB đầu → cảnh báo.

## 4. Cột
- Polyline kín layer cột (`cot|column`), chữ nhật (mặt cắt b theo X, h theo Y trước khi xoay, góc chuẩn hoá về (-45°, 45°]).
- Mã cột: text `C1`, `CT2`… gần nhất ≤ 1,5 m; MB không ghi mã thì lấy mã cùng vị trí ở tầng khác.
- Đoạn cột tầng k → k+1 = cột trên **MB định vị cột tầng k** ∪ cột cắt trên **MB sàn tầng k+1** ∪ **cột dựng** (layer `cot dung`) trên MB sàn tầng k.
- Cột dựng ở tầng trên cùng → hỏi đỉnh cột (`--tang-tren "Mai=<cốt mm>"`).
- Hai polyline cột chồng nhau khác tiết diện ở cùng vị trí → hỏi (đang lấy cột lớn).
- Cùng mã, cùng tầng, khác tiết diện → hỏi. Tiết diện đổi giữa các tầng → cảnh báo, dùng tiết diện MB dưới.

## 5. Dầm
- Dầm = **cặp nét song song** (layer `thay|khuat|dam|beam`), khoảng cách = b; **tim dầm = giữa 2 nét** (dầm biên lệch trục vẫn đúng vị trí).
- Tiết diện lấy **từ nhãn** `[Mã-]bXh` (ví dụ `D1-22X40`, `22X50`, `15X52.5`); số ≤ 200 hiểu là **cm**, lớn hơn là mm.
- Nhãn và khoảng cách 2 nét lệch > 15 mm → **dừng, hỏi** (không tự chọn). Nhãn không ghép được cặp nét → hỏi. Cặp nét khuất giống dầm mà không có nhãn → hỏi.
- Nhịp: chia theo cột cắt qua dải dầm; dầm đi qua dầm phụ không bị chia (nhãn ghi 1 lần cho dầm liên tục). Đầu dầm tựa cột → về tim cột; tựa dầm → về tim dầm vuông góc; không tựa gì → giữ đầu nét (công xôn).
- **Đỉnh dầm = mặt sàn kết cấu** của level (offset 0). Vùng sàn hạ cốt chỉ hạ sàn, dầm giữ nguyên trừ khi bản vẽ ghi riêng.

## 6. Sàn
- Biên sàn = bao ngoài các ô khép bởi nét dầm / mép sàn.
- Lỗ mở / ô thông tầng = ô chữ nhật có dấu X (2 đường chéo nối góc đối) → khoét khỏi sàn.
- Chiều dày: chú giải "SÀN BTCT DÀY 150" (ô mẫu không hatch). Không có → hỏi.
- **Tấm theo vùng cốt**: vùng hatch trùng mẫu trong chú giải của **đúng tờ** đó ("HẠ CỐT 50" → offset −50, "NÂNG CỐT 35" → +35) tách thành tấm riêng; phần còn lại là tấm chính offset 0. Hatch trong sàn không có trong chú giải → hỏi.

## 7. An toàn
- Không sửa DWG gốc (đọc qua bản sao DXF). Không ghi vào file Revit gốc: chỉ dựng vào dự án Claude tạo / bản sao, người dùng bật "Cho phép ghi". Hỏi trước mỗi lần ghi.

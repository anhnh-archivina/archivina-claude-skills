# Archivina – Claude Code skills

Bộ skill Claude Code dùng nội bộ Archivina để kiểm soát hồ sơ bản vẽ căn hộ (AutoCAD, đơn vị mm).

| Skill | Mô tả |
|---|---|
| [`dien-tich-ch`](skills/dien-tich-ch/SKILL.md) (Dien tich CH) | Dựng polyline thông thủy từng phòng và đường bo căn hộ từ mặt bằng AutoCAD (kể cả đối tượng AutoCAD Architecture), loại trừ hộp kỹ thuật/cột, ghi nhãn m² và `DTCH` theo polyline vừa vẽ, xuất Excel, kiểm tra nhãn trên bản sao DWG. |

## Cài đặt
Chép thư mục skill vào thư mục skill của Claude Code:

- Dùng cho mọi dự án: `%USERPROFILE%\.claude\skills\<tên-skill>\`
- Chỉ một dự án: `<thư mục dự án>\.claude\skills\<tên-skill>\`

Mở phiên Claude Code mới để skill được nạp.

## Yêu cầu
- AutoCAD 2022 trở lên (dùng `accoreconsole.exe` chạy ngầm trên bản sao).
- Python 3.10+ với `ezdxf`, `shapely`, `openpyxl`, `matplotlib`:
  `python -m pip install --user ezdxf shapely openpyxl matplotlib`

## Nguyên tắc
- Không sửa file DWG gốc: mọi thao tác trên bản sao.
- Đường bo chỉ bám nét đã vẽ (tường Wall, polyline bo cột, nét vữa hoàn thiện, nét bao khung cửa sổ/cửa đi); lớp trát không vẽ thì không lùi.
- Diện tích làm tròn 1 chữ số thập phân (m²).

Thư mục `evals/` trong mỗi skill là các ca thử dùng khi sửa skill.

# Archivina – Claude Code skills

Bộ skill Claude Code dùng nội bộ Archivina để kiểm soát hồ sơ bản vẽ căn hộ (AutoCAD, đơn vị mm).

| Skill | Mô tả |
|---|---|
| [`dien-tich-ch`](skills/dien-tich-ch/SKILL.md) (Dien tich CH) | Dựng polyline thông thủy từng phòng và đường bo căn hộ từ mặt bằng AutoCAD (kể cả đối tượng AutoCAD Architecture), loại trừ hộp kỹ thuật/cột, ghi nhãn m² và `DTCH` theo polyline vừa vẽ, xuất Excel, kiểm tra nhãn trên bản sao DWG. |

## MCP server
| Server | Mô tả |
|---|---|
| [`autocad-archivina`](mcp/autocad-archivina/README.md) | Nối Claude Code với AutoCAD / AutoCAD Architecture qua AutoCAD Core Console chạy ngầm trên bản sao: đọc thông tin DWG, xuất DXF (nổ đối tượng ACA), dựng polyline phòng/căn hộ, vẽ vào bản sao, kiểm tra nhãn, chạy LISP trên bản sao. Dùng skill `dien-tich-ch`. |

Cài: `python -m pip install --user -r mcp/autocad-archivina/requirements.txt`, rồi
`claude mcp add autocad-archivina --scope user -e PYTHONUTF8=1 -- "<python.exe>" "<đường dẫn>\autocad_mcp.py"`
(skill `dien-tich-ch` phải nằm ở `%USERPROFILE%\.claude\skills\`, hoặc đặt biến `DIEN_TICH_CH_SCRIPTS`).

## Cài đặt skill
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

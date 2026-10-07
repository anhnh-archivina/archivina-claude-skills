# Archivina – Claude Code skills

Bộ skill Claude Code dùng nội bộ Archivina để kiểm soát hồ sơ bản vẽ căn hộ (AutoCAD, đơn vị mm).

| Skill | Mô tả |
|---|---|
| [`dien-tich-ch`](skills/dien-tich-ch/SKILL.md) (Dien tich CH) | Dựng polyline thông thủy từng phòng và đường bo căn hộ từ mặt bằng AutoCAD (kể cả đối tượng AutoCAD Architecture), loại trừ hộp kỹ thuật/cột, ghi nhãn m² và `DTCH` theo polyline vừa vẽ (nhãn là Field liên kết polyline, sửa tay đường bo thì nhãn tự cập nhật), xuất Excel, kiểm tra nhãn trên bản sao DWG. |
| [`thiet-ke-tran-ch`](skills/thiet-ke-tran-ch/SKILL.md) (Tran CH) | Soát mặt bằng bố trí thiết bị trần căn hộ theo quy tắc trần Archivina (đèn ≥1200 / ≥500 mm, tủ áo, vùng gối, trục WC, đèn thả, ưu tiên PCCC), báo Excel 4 mức cảnh báo + ảnh từng căn, đề xuất vị trí mới vẽ vào bản sao DWG. Kèm thư viện 16 block thiết bị trần tỷ lệ 1:1 (`assets/thu-vien/`). Cần skill `dien-tich-ch` (bộ dựng phòng). |
| [`cap-dien-ch`](skills/cap-dien-ch/SKILL.md) (Cap dien CH) | Vẽ (bố trí mới) và soát mặt bằng cấp điện ổ cắm căn hộ theo nội thất và nguyên tắc vị trí Archivina (G, TV, ĐN, B, TL, W/X, box BT/HM/AC/BNL, TĐ-CH, VDP, công tắc WC), chia lộ + dây + mũi tên về TĐ.CH, dim từ mép tường tới tâm thiết bị; hỏi lại khi thiếu nội thất / số ổ bếp; vẽ vào bản sao DWG, xuất Excel. Thư viện block + bảng ký hiệu tách từ bản vẽ mẫu (`assets/thu-vien/`). Cần skill `thiet-ke-tran-ch` và `dien-tich-ch` (bộ dựng phòng / nội thất). |

## MCP server
| Server | Mô tả |
|---|---|
| [`autocad-archivina`](mcp/autocad-archivina/README.md) | Nối Claude Code với AutoCAD / AutoCAD Architecture qua AutoCAD Core Console chạy ngầm trên bản sao: đọc thông tin DWG, xuất DXF (nổ đối tượng ACA), dựng polyline phòng/căn hộ, vẽ vào bản sao, kiểm tra nhãn, chạy LISP trên bản sao, soát trần (`soat_tran`). Dùng skill `dien-tich-ch`, `thiet-ke-tran-ch`. |

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

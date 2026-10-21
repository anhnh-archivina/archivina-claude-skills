# Archivina – Claude Code skills

Bộ skill Claude Code dùng nội bộ Archivina để kiểm soát hồ sơ bản vẽ căn hộ (AutoCAD, đơn vị mm).

| Skill | Mô tả |
|---|---|
| [`dien-tich-ch`](skills/dien-tich-ch/SKILL.md) (Dien tich CH) | Dựng polyline thông thủy từng phòng và đường bo căn hộ từ mặt bằng AutoCAD (kể cả đối tượng AutoCAD Architecture), loại trừ hộp kỹ thuật/cột, ghi nhãn m² và `DTCH` theo polyline vừa vẽ (nhãn là Field liên kết polyline, sửa tay đường bo thì nhãn tự cập nhật), xuất Excel, kiểm tra nhãn trên bản sao DWG. |
| [`thiet-ke-tran-ch`](skills/thiet-ke-tran-ch/SKILL.md) (Tran CH) | Soát mặt bằng bố trí thiết bị trần căn hộ theo quy tắc trần Archivina (đèn ≥1200 / ≥500 mm, tủ áo, vùng gối, trục WC, đèn thả, ưu tiên PCCC), báo Excel 4 mức cảnh báo + ảnh từng căn, đề xuất vị trí mới vẽ vào bản sao DWG; **bố trí mới** theo trục cho căn chưa có thiết bị. Quy luật cập nhật 20/10/2026 từ MB trần CT1/CT3 (PN theo hình chữ nhật 600, không đèn trên thân giường; P. khách đường giữa đèn thả / đầu báo / loa / gió tươi; WC 2 đèn trục bồn cầu + sen, quạt hút trên bồn cầu; kho chưa có đèn bổ sung 01 downlight tâm phòng; sprinkler sơ bộ). Kèm thư viện 16 block thiết bị trần tỷ lệ 1:1 (`assets/thu-vien/`). Cần skill `dien-tich-ch` (bộ dựng phòng). |
| [`cap-dien-ch`](skills/cap-dien-ch/SKILL.md) (Cap dien CH) | Vẽ (bố trí mới) và soát mặt bằng cấp điện ổ cắm căn hộ theo nội thất và nguyên tắc vị trí Archivina (G, TV, ĐN, B, TL, W/X, box BT/HM/AC/BNL, TĐ-CH, VDP, công tắc WC), chia lộ + dây + mũi tên về TĐ.CH, dim từ mép tường tới tâm thiết bị; hỏi lại khi thiếu nội thất / số ổ bếp; vẽ vào bản sao DWG, xuất Excel. Nhận được cả mặt bằng tầng xuất từ Revit (nét nổ, không tên phòng: dựng phòng / căn theo mã căn + đường dẫn, nội thất theo hình dạng). Thư viện block + bảng ký hiệu tách từ bản vẽ mẫu (`assets/thu-vien/`). Cần skill `thiet-ke-tran-ch` và `dien-tich-ch` (bộ dựng phòng / nội thất). |
| [`dung-ket-cau-revit`](skills/dung-ket-cau-revit/SKILL.md) (Ket cau Revit) | Dựng mô hình kết cấu BTCT trong Revit 2026 từ mặt bằng KC AutoCAD: level theo cốt, trục, cột (cột dựng), dầm (cặp nét + nhãn cm), sàn kết cấu tách tấm theo vùng hạ / nâng cốt và lỗ mở; ảnh xem lại + danh sách câu hỏi trước khi ghi; family cột / dầm Archivina tự tạo từ .rft. Cần MCP `revit-archivina` (core ≥ 1.5.1, tool `rv_dung_ket_cau`). |
| [`kt-mat-bang-lat-san`](skills/kt-mat-bang-lat-san/SKILL.md) (KT-Mặt bằng lát sàn căn hộ) | Điều phối dựng mặt bằng lát sàn căn hộ bằng subagent (thư mục `agents/`): `do-dien-tich` (opus) dựng polyline phòng → 4 agent sonnet hatch theo nhóm phòng trên layer `A-Materials` – phòng ngủ DOLMIT 500, phòng khách/bếp/ăn ANSI37 5000 45°, WC/kho và ban công/lô gia ANSI37 2500 45°; điểm gốc hatch theo cửa đi (góc sảnh, góc phòng tắm, góc trong gần cửa ra lô gia, góc gần cửa vào phòng ngủ) → `lat-san-gan-field` (haiku) gắn Field diện tích → `lat-san-thong-ke` (haiku) Excel tổng diện tích lát theo loại phòng. Cần skill `dien-tich-ch` và MCP `autocad-archivina`. |

## Subagent
Thư mục `agents/` – chép vào `%USERPROFILE%\.claude\agents\`, mở phiên mới để nạp. Dùng cho skill `kt-mat-bang-lat-san`:
`do-dien-tich` (opus · medium), `lat-san-hatch-pn|pk|wc|lg` (sonnet · medium), `lat-san-gan-field`, `lat-san-thong-ke` (haiku · medium).

## MCP server
| Server | Mô tả |
|---|---|
| [`autocad-archivina`](mcp/autocad-archivina/README.md) | Nối Claude Code với AutoCAD / AutoCAD Architecture qua AutoCAD Core Console chạy ngầm trên bản sao: đọc thông tin DWG, xuất DXF (nổ đối tượng ACA), dựng polyline phòng/căn hộ, vẽ vào bản sao, kiểm tra nhãn, chạy LISP trên bản sao, soát trần (`soat_tran`). Dùng skill `dien-tich-ch`, `thiet-ke-tran-ch`. |
| [`revit-archivina`](mcp/revit-archivina/README.md) | Nối Claude Code với **Revit 2026 đang mở** qua add-in C# (.NET 8, cổng 127.0.0.1:9878, core nạp nóng): thông tin dự án, link Revit/CAD, phần tử, tham số, Rooms/Areas kèm biên, khối lượng theo vật liệu, cảnh báo, Schedule, ảnh view, xuất DWG mm. Mặc định chỉ đọc; đặt tham số khi người dùng bật trong Revit. Cài: `mcp/revit-archivina/build.ps1 -Loader`. |

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

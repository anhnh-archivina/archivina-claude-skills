// Archivina Revit MCP – CORE (các lệnh). Loader ArchivinaRevitMcp.dll nạp nóng file này từ addin\core\ mỗi khi file đổi
// (build lại core KHÔNG cần khởi động lại Revit). Cầu nối giữa Revit 2026 ĐANG MỞ và MCP server "revit-archivina" (Claude).
//
// Mục đích : mở một cổng TCP CHỈ trên máy này (127.0.0.1) để Claude đọc dự án Revit đang mở (thông tin, link,
//            phần tử, tham số, phòng / vùng diện tích, cảnh báo, bảng thống kê, ảnh view, xuất DWG mm)
//            và – CHỈ KHI người dùng bật – đặt tham số phần tử.
// Nguyên tắc an toàn (quy tắc Archivina):
//   - Mặc định CHỈ ĐỌC. Ghi bị khoá tới khi người dùng bấm tab "Archivina MCP" > "Cho phép ghi".
//     Mỗi lần mở Revit lại về chế độ chỉ đọc.
//   - Mọi thao tác ghi nằm trong 1 Transaction "Claude MCP …" -> Ctrl+Z hoàn tác được; lỗi thì RollBack.
//   - Không lưu, không SaveAs, không ghi đè file: xuất ảnh / DWG từ chối nếu thư mục đích đã có file.
//   - Lệnh chạy trên luồng API của Revit qua ExternalEvent: Revit đang mở hộp thoại / đang chạy lệnh thì chờ.
// Giao thức: mỗi yêu cầu 1 dòng JSON {"cmd": "...", "params": {...}} kết thúc "\n";
//            trả 1 dòng JSON {"ok": true, "result": ...} hoặc {"ok": false, "error": "..."}.
// Đơn vị  : toạ độ / chiều dài vào-ra MILLIMET, diện tích m², thể tích m³ (Revit lưu nội bộ bằng feet).
// Cài đặt : ..\build.ps1 (biên dịch + ghi file .addin), rồi khởi động lại Revit.

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using System.Text.Json.Serialization.Metadata;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.UI;

namespace ArchivinaRevitMcp.Core
{
    internal static class Ctx
    {
        public static bool WriteEnabled;
        public static string BridgeVersion;
        public static int Port;
    }

    internal static class Json
    {
        // Revit tắt serializer phản chiếu mặc định -> phải chỉ định TypeInfoResolver
        public static readonly JsonSerializerOptions Opts = new JsonSerializerOptions
            { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping, TypeInfoResolver = new DefaultJsonTypeInfoResolver() };

        public static string Err(string msg) =>
            new JsonObject { ["ok"] = false, ["error"] = msg }.ToJsonString(Opts);
    }

    // Điểm vào loader gọi qua reflection (chữ ký cố định – đổi phải sửa CoreLoader trong Bridge.cs)
    public static class Entry
    {
        public static string Run(UIApplication ui, string requestJson, bool writeEnabled, string bridgeVersion, int port)
        {
            Ctx.WriteEnabled = writeEnabled;
            Ctx.BridgeVersion = bridgeVersion;
            Ctx.Port = port;
            try
            {
                JsonObject req = JsonNode.Parse(requestJson).AsObject();
                JsonNode res = Commands.Run(ui, req);
                return new JsonObject { ["ok"] = true, ["result"] = res }.ToJsonString(Json.Opts);
            }
            catch (Exception ex)
            {
                return Json.Err(ex.Message);
            }
        }
    }

    // ------------------------------------------------------------------------------------------ các lệnh
    internal static class Commands
    {
        const double FT = 304.8;              // feet -> mm
        const double FT2 = 0.09290304;        // ft² -> m²
        const double FT3 = 0.028316846592;    // ft³ -> m³

        public static JsonNode Run(UIApplication ui, JsonObject req)
        {
            string cmd = (string)req["cmd"];
            JsonObject p = req["params"] as JsonObject ?? new JsonObject();
            switch (cmd)
            {
                case "ping": return Ping(ui);
                case "info": return Info(ui);
                case "list": return List(ui, p);
                case "element": return ElementDetails(ui, p);
                case "selection": return Selection(ui, p);
                case "select": return Select(ui, p);
                case "spatial": return Spatial(ui, p);
                case "warnings": return Warnings(ui, p);
                case "views": return Views(ui, p);
                case "schedule": return Schedule(ui, p);
                case "screenshot": return Screenshot(ui, p);
                case "export_dwg": return ExportDwg(ui, p);
                case "quantities": return Quantities(ui, p);
                case "set_params": return SetParams(ui, p);
                default: throw new Exception("Lệnh không hỗ trợ: " + cmd);
            }
        }

        // ---------------------------------------------------------------- tiện ích
        static Document Doc(UIApplication ui)
        {
            Document d = ui.ActiveUIDocument?.Document;
            if (d == null) throw new Exception("Revit chưa mở dự án nào.");
            return d;
        }

        static string S(JsonObject p, string k, string def = null) => p[k] == null ? def : p[k].ToString();
        static int I(JsonObject p, string k, int def) => p[k] == null ? def : (int)(double)p[k];
        static bool B(JsonObject p, string k, bool def) => p[k] == null ? def : (bool)p[k];

        static List<ElementId> Ids(JsonObject p, string k)
        {
            var res = new List<ElementId>();
            if (p[k] is JsonArray a)
                foreach (JsonNode n in a) res.Add(new ElementId((long)(double)n));
            else if (p[k] != null)
                res.Add(new ElementId((long)(double)p[k]));
            return res;
        }

        static double R(double v, int d = 1) => Math.Round(v, d);
        static JsonArray Pt(XYZ q) => new JsonArray(R(q.X * FT), R(q.Y * FT), R(q.Z * FT));
        static long Id(ElementId id) => id.Value;

        static string SafeName(Element e)
        {
            try { return e.Name; } catch { return null; }
        }

        static string LevelName(Document doc, Element e)
        {
            ElementId lid = ElementId.InvalidElementId;
            try { lid = e.LevelId; } catch { }
            if (lid == ElementId.InvalidElementId)
            {
                Parameter lp = e.get_Parameter(BuiltInParameter.FAMILY_LEVEL_PARAM)
                               ?? e.get_Parameter(BuiltInParameter.WALL_BASE_CONSTRAINT)
                               ?? e.get_Parameter(BuiltInParameter.SCHEDULE_LEVEL_PARAM);
                if (lp != null && lp.StorageType == StorageType.ElementId) lid = lp.AsElementId();
            }
            return lid == ElementId.InvalidElementId ? null : doc.GetElement(lid)?.Name;
        }

        static JsonObject Summary(Document doc, Element e)
        {
            var o = new JsonObject
            {
                ["id"] = Id(e.Id),
                ["class"] = e.GetType().Name,
                ["category"] = e.Category?.Name,
                ["name"] = SafeName(e),
            };
            if (doc.GetElement(e.GetTypeId()) is ElementType t)
            {
                o["family"] = t.FamilyName;
                o["type"] = t.Name;
            }
            string lv = LevelName(doc, e);
            if (lv != null) o["level"] = lv;
            if (e.Location is LocationPoint lp)
            {
                o["point_mm"] = Pt(lp.Point);
                try { o["rotation_deg"] = R(lp.Rotation * 180 / Math.PI, 2); } catch { }
            }
            else if (e.Location is LocationCurve lc && lc.Curve != null)
            {
                o["start_mm"] = Pt(lc.Curve.GetEndPoint(0));
                o["end_mm"] = Pt(lc.Curve.GetEndPoint(1));
                o["length_mm"] = R(lc.Curve.Length * FT);
            }
            BoundingBoxXYZ bb = e.get_BoundingBox(null);
            if (bb != null) o["bbox_mm"] = new JsonArray(Pt(bb.Min), Pt(bb.Max));
            if (e is Wall w)
            {
                try { o["width_mm"] = R(w.Width * FT); } catch { }
            }
            return o;
        }

        static string SpecKey(Parameter prm)
        {
            try
            {
                string tid = prm.Definition.GetDataType()?.TypeId ?? "";
                int dash = tid.LastIndexOf('-');
                return dash > 0 ? tid.Substring(0, dash) : tid;
            }
            catch { return ""; }
        }

        // Giá trị tham số theo đơn vị Archivina: dài mm, diện tích m², thể tích m³, góc độ
        static JsonNode ParamValue(Parameter prm)
        {
            switch (prm.StorageType)
            {
                case StorageType.String: return prm.AsString();
                case StorageType.Integer: return prm.AsInteger();
                case StorageType.ElementId: return Id(prm.AsElementId());
                case StorageType.Double:
                    double v = prm.AsDouble();
                    switch (SpecKey(prm))
                    {
                        case "autodesk.spec.aec:length": return R(v * FT, 2);
                        case "autodesk.spec.aec:area": return R(v * FT2, 4);
                        case "autodesk.spec.aec:volume": return R(v * FT3, 4);
                        case "autodesk.spec.aec:angle": return R(v * 180 / Math.PI, 4);
                        default: return v;
                    }
                default: return null;
            }
        }

        static string UnitLabel(Parameter prm)
        {
            if (prm.StorageType != StorageType.Double) return null;
            switch (SpecKey(prm))
            {
                case "autodesk.spec.aec:length": return "mm";
                case "autodesk.spec.aec:area": return "m2";
                case "autodesk.spec.aec:volume": return "m3";
                case "autodesk.spec.aec:angle": return "deg";
                default: return "noi_bo";
            }
        }

        static JsonArray Params(Element e)
        {
            var arr = new JsonArray();
            foreach (Parameter prm in e.Parameters.Cast<Parameter>().OrderBy(x => x.Definition?.Name))
            {
                if (prm.Definition == null) continue;
                var o = new JsonObject
                {
                    ["name"] = prm.Definition.Name,
                    ["value"] = ParamValue(prm),
                    ["text"] = SafeValueString(prm),
                    ["storage"] = prm.StorageType.ToString(),
                    ["readonly"] = prm.IsReadOnly,
                };
                string u = UnitLabel(prm);
                if (u != null) o["unit"] = u;
                if (prm.Definition is InternalDefinition idf && idf.BuiltInParameter != BuiltInParameter.INVALID)
                    o["builtin"] = idf.BuiltInParameter.ToString();
                if (prm.IsShared) o["shared"] = true;
                arr.Add(o);
            }
            return arr;
        }

        static string SafeValueString(Parameter prm)
        {
            try { return prm.AsValueString(); } catch { return null; }
        }

        static Category FindCategory(Document doc, string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            if (Enum.TryParse(name, true, out BuiltInCategory bic))
            {
                Category c = Category.GetCategory(doc, bic);
                if (c != null) return c;
            }
            foreach (Category c in doc.Settings.Categories)
                if (string.Equals(c.Name, name, StringComparison.OrdinalIgnoreCase)) return c;
            throw new Exception($"Không tìm thấy category '{name}' (dùng tên hiển thị, ví dụ 'Walls', hoặc BuiltInCategory, ví dụ 'OST_Walls').");
        }

        static Type FindClass(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            Assembly asm = typeof(Element).Assembly;
            Type t = asm.GetType("Autodesk.Revit.DB." + name) ?? asm.GetType("Autodesk.Revit.DB.Architecture." + name)
                     ?? asm.GetType("Autodesk.Revit.DB.Mechanical." + name) ?? asm.GetType("Autodesk.Revit.DB.Plumbing." + name)
                     ?? asm.GetType("Autodesk.Revit.DB.Electrical." + name);
            if (t == null || !typeof(Element).IsAssignableFrom(t)) throw new Exception($"Không có lớp phần tử Revit '{name}'.");
            return t;
        }

        static string FilePath(Element e)
        {
            try
            {
                if (!e.IsExternalFileReference()) return null;
                ExternalFileReference r = e.GetExternalFileReference();
                return ModelPathUtils.ConvertModelPathToUserVisiblePath(r.GetAbsolutePath());
            }
            catch { return null; }
        }

        static JsonArray Polyline(IList<XYZ> pts)
        {
            var a = new JsonArray();
            XYZ last = null;
            foreach (XYZ q in pts)
            {
                if (last != null && last.DistanceTo(q) < 1e-6) continue;
                a.Add(new JsonArray(R(q.X * FT), R(q.Y * FT)));
                last = q;
            }
            return a;
        }

        static double ShoelaceFt2(IList<XYZ> pts)
        {
            double s = 0;
            for (int i = 0; i < pts.Count; i++)
            {
                XYZ a = pts[i], b = pts[(i + 1) % pts.Count];
                s += a.X * b.Y - b.X * a.Y;
            }
            return s / 2;
        }

        static string NewFolder(string folder)
        {
            if (string.IsNullOrWhiteSpace(folder)) throw new Exception("Thiếu thư mục đích.");
            folder = Path.GetFullPath(folder);
            if (Directory.Exists(folder) && Directory.EnumerateFileSystemEntries(folder).Any())
                throw new Exception($"Thư mục '{folder}' đã có file – không ghi đè. Chọn thư mục mới / trống.");
            Directory.CreateDirectory(folder);
            return folder;
        }

        // ---------------------------------------------------------------- lệnh chỉ đọc
        static JsonNode Ping(UIApplication ui)
        {
            Document d = ui.ActiveUIDocument?.Document;
            return new JsonObject
            {
                ["bridge"] = Ctx.BridgeVersion,
                ["core"] = typeof(Commands).Assembly.GetName().Version.ToString(),
                ["revit"] = ui.Application.VersionName,
                ["build"] = ui.Application.VersionBuild,
                ["sub_version"] = ui.Application.SubVersionNumber,
                ["language"] = ui.Application.Language.ToString(),
                ["port"] = Ctx.Port,
                ["write_enabled"] = Ctx.WriteEnabled,
                ["active_document"] = d?.Title,
                ["open_documents"] = new JsonArray(ui.Application.Documents.Cast<Document>()
                    .Select(x => (JsonNode)(x.Title + (x.IsLinked ? " (link)" : ""))).ToArray()),
            };
        }

        static JsonNode Info(UIApplication ui)
        {
            Document doc = Doc(ui);
            var o = new JsonObject
            {
                ["title"] = doc.Title,
                ["path"] = doc.PathName,
                ["is_modified"] = doc.IsModified,
                ["is_family"] = doc.IsFamilyDocument,
                ["is_workshared"] = doc.IsWorkshared,
                ["is_read_only"] = doc.IsReadOnly,
            };
            try
            {
                Units u = doc.GetUnits();
                o["unit_length"] = LabelUtils.GetLabelForUnit(u.GetFormatOptions(SpecTypeId.Length).GetUnitTypeId());
                o["unit_area"] = LabelUtils.GetLabelForUnit(u.GetFormatOptions(SpecTypeId.Area).GetUnitTypeId());
                o["area_accuracy"] = u.GetFormatOptions(SpecTypeId.Area).Accuracy;
            }
            catch { }
            ProjectInfo pi = doc.ProjectInformation;
            if (pi != null)
                o["project"] = new JsonObject
                {
                    ["name"] = pi.Name, ["number"] = pi.Number, ["client"] = pi.ClientName,
                    ["building"] = pi.BuildingName, ["address"] = pi.Address, ["status"] = pi.Status,
                    ["issue_date"] = pi.IssueDate, ["author"] = pi.Author,
                };
            View av = ui.ActiveUIDocument.ActiveView;
            if (av != null)
                o["active_view"] = new JsonObject
                {
                    ["id"] = Id(av.Id), ["name"] = av.Name, ["type"] = av.ViewType.ToString(),
                    ["scale"] = av.Scale, ["level"] = av.GenLevel?.Name,
                };

            var levels = new JsonArray();
            foreach (Level l in new FilteredElementCollector(doc).OfClass(typeof(Level)).Cast<Level>().OrderBy(l => l.Elevation))
                levels.Add(new JsonObject { ["id"] = Id(l.Id), ["name"] = l.Name, ["elevation_mm"] = R(l.Elevation * FT) });
            o["levels"] = levels;

            var phases = new JsonArray();
            foreach (Phase ph in doc.Phases) phases.Add(ph.Name);
            o["phases"] = phases;

            // số phần tử mô hình theo category
            var counts = new Dictionary<string, int>();
            foreach (Element e in new FilteredElementCollector(doc).WhereElementIsNotElementType())
            {
                Category c = e.Category;
                if (c == null || c.CategoryType != CategoryType.Model || e.ViewSpecific) continue;
                counts[c.Name] = counts.TryGetValue(c.Name, out int n) ? n + 1 : 1;
            }
            var co = new JsonObject();
            foreach (var kv in counts.OrderByDescending(k => k.Value)) co[kv.Key] = kv.Value;
            o["model_counts"] = co;

            // link Revit / CAD (tương đương kiểm tra xref)
            var rlinks = new JsonArray();
            foreach (RevitLinkType lt in new FilteredElementCollector(doc).OfClass(typeof(RevitLinkType)))
            {
                var lo = new JsonObject { ["id"] = Id(lt.Id), ["name"] = lt.Name, ["nested"] = lt.IsNestedLink, ["path"] = FilePath(lt) };
                try { lo["status"] = lt.GetLinkedFileStatus().ToString(); } catch { }
                try { lo["path_type"] = lt.GetExternalFileReference().PathType.ToString(); } catch { }
                lo["instances"] = new FilteredElementCollector(doc).OfClass(typeof(RevitLinkInstance))
                    .Count(x => x.GetTypeId() == lt.Id);
                rlinks.Add(lo);
            }
            o["revit_links"] = rlinks;

            var cads = new JsonArray();
            var cadInst = new FilteredElementCollector(doc).OfClass(typeof(ImportInstance)).Cast<ImportInstance>().ToList();
            foreach (CADLinkType ct in new FilteredElementCollector(doc).OfClass(typeof(CADLinkType)))
            {
                var lo = new JsonObject { ["id"] = Id(ct.Id), ["name"] = ct.Name, ["path"] = FilePath(ct) };
                try { if (ct.IsExternalFileReference()) lo["status"] = ct.GetExternalFileReference().GetLinkedFileStatus().ToString(); } catch { }
                var mine = cadInst.Where(x => x.GetTypeId() == ct.Id).ToList();
                lo["instances"] = mine.Count;
                lo["linked"] = mine.Any(x => x.IsLinked);
                lo["imported"] = mine.Any(x => !x.IsLinked);
                cads.Add(lo);
            }
            o["cad_links"] = cads;
            o["warnings_count"] = doc.GetWarnings().Count;
            return o;
        }

        static JsonNode List(UIApplication ui, JsonObject p)
        {
            Document doc = Doc(ui);
            int limit = I(p, "limit", 200);
            FilteredElementCollector col;
            List<ElementId> viewIds = Ids(p, "view_id");
            col = viewIds.Count > 0 ? new FilteredElementCollector(doc, viewIds[0]) : new FilteredElementCollector(doc);
            if (B(p, "types", false)) col.WhereElementIsElementType(); else col.WhereElementIsNotElementType();
            Category cat = FindCategory(doc, S(p, "category"));
            if (cat != null) col.OfCategoryId(cat.Id);

            IEnumerable<Element> els = col;
            Type cls = FindClass(S(p, "class"));
            if (cls != null) els = els.Where(e => cls.IsInstanceOfType(e));
            string level = S(p, "level");
            if (!string.IsNullOrEmpty(level))
                els = els.Where(e => string.Equals(LevelName(doc, e), level, StringComparison.OrdinalIgnoreCase));
            string nm = S(p, "name_contains");
            if (!string.IsNullOrEmpty(nm))
                els = els.Where(e =>
                {
                    string s = (SafeName(e) ?? "") + " " + ((doc.GetElement(e.GetTypeId()) as ElementType)?.FamilyName ?? "");
                    return s.IndexOf(nm, StringComparison.OrdinalIgnoreCase) >= 0;
                });

            var arr = new JsonArray();
            int total = 0;
            foreach (Element e in els)
            {
                total++;
                if (arr.Count < limit) arr.Add(Summary(doc, e));
            }
            return new JsonObject { ["tong_khop"] = total, ["tra_ve"] = arr.Count, ["elements"] = arr };
        }

        static JsonNode ElementDetails(UIApplication ui, JsonObject p)
        {
            Document doc = Doc(ui);
            var arr = new JsonArray();
            foreach (ElementId id in Ids(p, "ids"))
            {
                Element e = doc.GetElement(id);
                if (e == null) { arr.Add(new JsonObject { ["id"] = Id(id), ["error"] = "không tồn tại" }); continue; }
                JsonObject o = Summary(doc, e);
                o["params"] = Params(e);
                if (B(p, "type_params", false) && doc.GetElement(e.GetTypeId()) is ElementType t)
                    o["type_params"] = Params(t);
                arr.Add(o);
            }
            return arr;
        }

        static JsonNode Selection(UIApplication ui, JsonObject p)
        {
            Document doc = Doc(ui);
            int limit = I(p, "limit", 100);
            ICollection<ElementId> ids = ui.ActiveUIDocument.Selection.GetElementIds();
            var arr = new JsonArray();
            foreach (ElementId id in ids.Take(limit))
            {
                Element e = doc.GetElement(id);
                if (e == null) continue;
                JsonObject o = Summary(doc, e);
                if (B(p, "params", true)) o["params"] = Params(e);
                arr.Add(o);
            }
            return new JsonObject { ["count"] = ids.Count, ["elements"] = arr };
        }

        // Chọn phần tử trên giao diện (không sửa mô hình)
        static JsonNode Select(UIApplication ui, JsonObject p)
        {
            Doc(ui);
            List<ElementId> ids = Ids(p, "ids");
            UIDocument uidoc = ui.ActiveUIDocument;
            uidoc.Selection.SetElementIds(ids);
            if (B(p, "zoom", false) && ids.Count > 0) uidoc.ShowElements(ids);
            return new JsonObject { ["selected"] = ids.Count };
        }

        // Phòng (Rooms) hoặc vùng diện tích (Areas), kèm biên theo mặt hoàn thiện / tim tường
        static JsonNode Spatial(UIApplication ui, JsonObject p)
        {
            Document doc = Doc(ui);
            string kind = (S(p, "kind", "rooms") ?? "rooms").ToLowerInvariant();
            BuiltInCategory bic = kind.StartsWith("area") ? BuiltInCategory.OST_Areas : BuiltInCategory.OST_Rooms;
            bool withBoundary = B(p, "boundary", false);
            string locName = S(p, "boundary_location", "Finish");
            if (!Enum.TryParse(locName, true, out SpatialElementBoundaryLocation loc))
                throw new Exception("boundary_location: Finish | Center | CoreBoundary | CoreCenter");
            var opt = new SpatialElementBoundaryOptions { SpatialElementBoundaryLocation = loc };
            string level = S(p, "level");
            List<ElementId> only = Ids(p, "ids");

            var arr = new JsonArray();
            double sum = 0;
            foreach (SpatialElement se in new FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType().Cast<SpatialElement>())
            {
                if (only.Count > 0 && !only.Contains(se.Id)) continue;
                string lv = se.Level?.Name;
                if (!string.IsNullOrEmpty(level) && !string.Equals(lv, level, StringComparison.OrdinalIgnoreCase)) continue;
                var o = new JsonObject
                {
                    ["id"] = Id(se.Id),
                    ["number"] = se.Number,
                    ["name"] = se.get_Parameter(BuiltInParameter.ROOM_NAME)?.AsString() ?? SafeName(se),
                    ["level"] = lv,
                    ["area_m2"] = R(se.Area * FT2, 4),
                    ["perimeter_mm"] = R(se.Perimeter * FT),
                    ["placed"] = se.Location != null,
                };
                if (se.Location == null) o["trang_thai"] = "Not Placed";
                else if (se.Area <= 0) o["trang_thai"] = "Not Enclosed / Redundant";
                sum += se.Area * FT2;
                if (se is Room rm)
                {
                    try { o["unbounded_height_mm"] = R(rm.UnboundedHeight * FT); } catch { }
                    o["department"] = rm.get_Parameter(BuiltInParameter.ROOM_DEPARTMENT)?.AsString();
                    o["phase"] = doc.GetElement(rm.get_Parameter(BuiltInParameter.ROOM_PHASE)?.AsElementId() ?? ElementId.InvalidElementId)?.Name;
                }
                if (se is Area ar)
                {
                    try { o["area_scheme"] = ar.AreaScheme?.Name; } catch { }
                }
                if (withBoundary && se.Location != null)
                {
                    IList<IList<BoundarySegment>> loops = se.GetBoundarySegments(opt);
                    var la = new JsonArray();
                    double polyFt2 = 0;
                    if (loops != null)
                        foreach (IList<BoundarySegment> loop in loops)
                        {
                            var pts = new List<XYZ>();
                            foreach (BoundarySegment bs in loop)
                            {
                                IList<XYZ> tp = bs.GetCurve().Tessellate();
                                for (int i = 0; i < tp.Count - 1; i++) pts.Add(tp[i]);
                            }
                            polyFt2 += ShoelaceFt2(pts);
                            la.Add(Polyline(pts));
                        }
                    o["boundary_mm"] = la;
                    o["boundary_area_m2"] = R(Math.Abs(polyFt2) * FT2, 4);
                }
                arr.Add(o);
            }
            return new JsonObject
            {
                ["kind"] = bic == BuiltInCategory.OST_Areas ? "areas" : "rooms",
                ["boundary_location"] = loc.ToString(),
                ["count"] = arr.Count,
                ["tong_area_m2"] = R(sum, 4),
                ["items"] = arr,
            };
        }

        static JsonNode Warnings(UIApplication ui, JsonObject p)
        {
            Document doc = Doc(ui);
            int limitIds = I(p, "limit_ids", 20);
            var groups = new Dictionary<string, (string sev, int n, List<long> ids)>();
            foreach (FailureMessage fm in doc.GetWarnings())
            {
                string key = fm.GetDescriptionText();
                if (!groups.TryGetValue(key, out var g)) g = (fm.GetSeverity().ToString(), 0, new List<long>());
                g.n++;
                foreach (ElementId id in fm.GetFailingElements().Concat(fm.GetAdditionalElements()))
                    if (g.ids.Count < limitIds && !g.ids.Contains(Id(id))) g.ids.Add(Id(id));
                groups[key] = g;
            }
            var arr = new JsonArray();
            foreach (var kv in groups.OrderByDescending(k => k.Value.n))
                arr.Add(new JsonObject
                {
                    ["mo_ta"] = kv.Key, ["severity"] = kv.Value.sev, ["so_lan"] = kv.Value.n,
                    ["element_ids"] = new JsonArray(kv.Value.ids.Select(x => (JsonNode)x).ToArray()),
                });
            return new JsonObject { ["tong"] = groups.Values.Sum(g => g.n), ["nhom"] = arr };
        }

        static JsonNode Views(UIApplication ui, JsonObject p)
        {
            Document doc = Doc(ui);
            string type = S(p, "type");
            bool templates = B(p, "templates", false);
            var arr = new JsonArray();
            foreach (View v in new FilteredElementCollector(doc).OfClass(typeof(View)).Cast<View>().OrderBy(v => v.ViewType.ToString()).ThenBy(v => v.Name))
            {
                if (v.IsTemplate != templates) continue;
                if (!string.IsNullOrEmpty(type) && !string.Equals(v.ViewType.ToString(), type, StringComparison.OrdinalIgnoreCase)) continue;
                var o = new JsonObject
                {
                    ["id"] = Id(v.Id), ["name"] = v.Name, ["type"] = v.ViewType.ToString(),
                    ["level"] = v.GenLevel?.Name, ["printable"] = v.CanBePrinted,
                };
                try { o["scale"] = v.Scale; } catch { }
                if (v is ViewSheet sh)
                {
                    o["sheet_number"] = sh.SheetNumber;
                    o["views_on_sheet"] = new JsonArray(sh.GetAllPlacedViews().Select(x => (JsonNode)Id(x)).ToArray());
                }
                if (v.ViewTemplateId != ElementId.InvalidElementId) o["template"] = doc.GetElement(v.ViewTemplateId)?.Name;
                arr.Add(o);
            }
            return new JsonObject { ["count"] = arr.Count, ["views"] = arr };
        }

        static JsonNode Schedule(UIApplication ui, JsonObject p)
        {
            Document doc = Doc(ui);
            var all = new FilteredElementCollector(doc).OfClass(typeof(ViewSchedule)).Cast<ViewSchedule>()
                .Where(s => !s.IsTemplate && !s.IsTitleblockRevisionSchedule && !s.IsInternalKeynoteSchedule).ToList();
            List<ElementId> ids = Ids(p, "id");
            string name = S(p, "name");
            ViewSchedule vs = ids.Count > 0 ? all.FirstOrDefault(s => s.Id == ids[0])
                : !string.IsNullOrEmpty(name) ? all.FirstOrDefault(s => string.Equals(s.Name, name, StringComparison.OrdinalIgnoreCase)) : null;
            if (vs == null)
            {
                if (ids.Count > 0 || !string.IsNullOrEmpty(name)) throw new Exception("Không tìm thấy bảng thống kê.");
                return new JsonObject
                {
                    ["schedules"] = new JsonArray(all.OrderBy(s => s.Name).Select(s => (JsonNode)new JsonObject
                    {
                        ["id"] = Id(s.Id), ["name"] = s.Name,
                        ["category"] = Category.GetCategory(doc, s.Definition.CategoryId)?.Name,
                    }).ToArray()),
                };
            }
            int maxRows = I(p, "max_rows", 2000);
            TableData td = vs.GetTableData();
            JsonArray Section(SectionType st)
            {
                var rows = new JsonArray();
                TableSectionData sd = td.GetSectionData(st);
                if (sd == null) return rows;
                for (int r = sd.FirstRowNumber; r <= sd.LastRowNumber && rows.Count < maxRows; r++)
                {
                    var row = new JsonArray();
                    for (int c = sd.FirstColumnNumber; c <= sd.LastColumnNumber; c++) row.Add(vs.GetCellText(st, r, c));
                    rows.Add(row);
                }
                return rows;
            }
            return new JsonObject
            {
                ["id"] = Id(vs.Id), ["name"] = vs.Name,
                ["header"] = Section(SectionType.Header),
                ["body"] = Section(SectionType.Body),
            };
        }

        static JsonNode Screenshot(UIApplication ui, JsonObject p)
        {
            Document doc = Doc(ui);
            List<ElementId> ids = Ids(p, "view_id");
            ElementId vid = ids.Count > 0 ? ids[0] : ui.ActiveUIDocument.ActiveView.Id;
            string folder = NewFolder(S(p, "folder"));
            var opt = new ImageExportOptions
            {
                ExportRange = ExportRange.SetOfViews,
                FilePath = Path.Combine(folder, "rv"),
                ZoomType = ZoomFitType.FitToPage,
                PixelSize = I(p, "width", 1600),
                FitDirection = FitDirectionType.Horizontal,
                HLRandWFViewsFileType = ImageFileType.PNG,
                ShadowViewsFileType = ImageFileType.PNG,
                ImageResolution = ImageResolution.DPI_150,
            };
            opt.SetViewsAndSheets(new List<ElementId> { vid });
            doc.ExportImage(opt);
            string png = Directory.GetFiles(folder, "*.png").OrderByDescending(File.GetLastWriteTime).FirstOrDefault();
            if (png == null) throw new Exception("Revit không xuất được ảnh view này (view không in được?).");
            return new JsonObject { ["path"] = png, ["view"] = doc.GetElement(vid)?.Name };
        }

        static JsonNode ExportDwg(UIApplication ui, JsonObject p)
        {
            Document doc = Doc(ui);
            List<ElementId> ids = Ids(p, "view_ids");
            if (ids.Count == 0) ids.Add(ui.ActiveUIDocument.ActiveView.Id);
            string folder = NewFolder(S(p, "folder"));
            string setup = S(p, "setup");
            DWGExportOptions opt = string.IsNullOrEmpty(setup) ? new DWGExportOptions() : DWGExportOptions.GetPredefinedOptions(doc, setup);
            if (opt == null) throw new Exception($"Không có setup xuất DWG '{setup}'.");
            opt.TargetUnit = ExportUnit.Millimeter; // quy chuẩn Archivina: mm
            opt.MergedViews = B(p, "merged", true);
            bool ok = doc.Export(folder, S(p, "name", "rv"), ids, opt);
            return new JsonObject
            {
                ["ok"] = ok,
                ["folder"] = folder,
                ["files"] = new JsonArray(Directory.GetFiles(folder).Select(f => (JsonNode)f).ToArray()),
                ["setups_co_san"] = new JsonArray(BaseExportOptions.GetPredefinedSetupNames(doc).Select(s => (JsonNode)s).ToArray()),
            };
        }

        // Thể tích / diện tích theo từng vật liệu của phần tử (sau giao cắt, đã trừ lỗ mở)
        static JsonObject MaterialQty(Document doc, Element e)
        {
            var o = new JsonObject();
            try
            {
                foreach (ElementId mid in e.GetMaterialIds(false))
                    o[doc.GetElement(mid)?.Name ?? Id(mid).ToString()] = new JsonObject
                    {
                        ["volume_m3"] = R(e.GetMaterialVolume(mid) * FT3, 4),
                        ["area_m2"] = R(e.GetMaterialArea(mid, false) * FT2, 4),
                    };
            }
            catch { }
            return o;
        }

        // Số cửa / cửa sổ (vách kính) gắn trên tường
        static JsonObject OpeningCount(Document doc, Element e)
        {
            var o = new JsonObject();
            if (!(e is HostObject ho)) return o;
            foreach (ElementId id in ho.FindInserts(true, false, true, true))
            {
                string c = doc.GetElement(id)?.Category?.Name ?? "?";
                o[c] = (o[c] == null ? 0 : (int)o[c]) + 1;
            }
            return o;
        }

        // Khối lượng theo category (+ level), gom theo Family : Type – dùng tham số tính sẵn của Revit
        static JsonNode Quantities(UIApplication ui, JsonObject p)
        {
            Document doc = Doc(ui);
            Category cat = FindCategory(doc, S(p, "category", "OST_Walls"));
            string level = S(p, "level");
            bool items = B(p, "items", false);
            double Get(Element e, BuiltInParameter bip)
            {
                Parameter prm = e.get_Parameter(bip);
                return prm != null && prm.HasValue && prm.StorageType == StorageType.Double ? prm.AsDouble() : 0;
            }
            var groups = new SortedDictionary<string, JsonObject>();
            var list = new JsonArray();
            double tl = 0, ta = 0, tv = 0; int tn = 0;
            foreach (Element e in new FilteredElementCollector(doc).OfCategoryId(cat.Id).WhereElementIsNotElementType())
            {
                string lv = LevelName(doc, e);
                if (!string.IsNullOrEmpty(level) && !string.Equals(lv, level, StringComparison.OrdinalIgnoreCase)) continue;
                var t = doc.GetElement(e.GetTypeId()) as ElementType;
                string key = (t?.FamilyName ?? "") + " : " + (t?.Name ?? SafeName(e));
                double len = Get(e, BuiltInParameter.CURVE_ELEM_LENGTH) * FT;
                double area = Get(e, BuiltInParameter.HOST_AREA_COMPUTED) * FT2;
                double vol = Get(e, BuiltInParameter.HOST_VOLUME_COMPUTED) * FT3;
                double width = e is Wall w ? w.Width * FT : 0;
                double h = Get(e, BuiltInParameter.WALL_USER_HEIGHT_PARAM) * FT;
                if (!groups.TryGetValue(key, out JsonObject g))
                {
                    g = new JsonObject { ["type"] = key, ["class"] = e.GetType().Name, ["width_mm"] = R(width), ["count"] = 0, ["length_m"] = 0.0, ["area_m2"] = 0.0, ["volume_m3"] = 0.0 };
                    if (e is Wall ww)
                    {
                        g["wall_kind"] = ww.WallType.Kind.ToString();
                        CompoundStructure cs = ww.WallType.GetCompoundStructure();
                        if (cs != null)
                        {
                            var la = new JsonArray();
                            foreach (CompoundStructureLayer ly in cs.GetLayers())
                                la.Add(new JsonObject
                                {
                                    ["function"] = ly.Function.ToString(), ["width_mm"] = R(ly.Width * FT),
                                    ["material"] = doc.GetElement(ly.MaterialId)?.Name,
                                });
                            g["layers"] = la;
                        }
                    }
                    else
                    {
                        // in-place / family trong category: lấy vật liệu từ hình học
                        try
                        {
                            var mats = e.GetMaterialIds(false).Select(m => (JsonNode)doc.GetElement(m)?.Name).ToArray();
                            g["materials"] = new JsonArray(mats);
                        }
                        catch { }
                    }
                    groups[key] = g;
                }
                g["count"] = (int)g["count"] + 1;
                g["length_m"] = (double)g["length_m"] + len / 1000;
                g["area_m2"] = (double)g["area_m2"] + area;
                g["volume_m3"] = (double)g["volume_m3"] + vol;
                tn++; tl += len / 1000; ta += area; tv += vol;
                if (items)
                    list.Add(new JsonObject
                    {
                        ["id"] = Id(e.Id), ["type"] = key, ["level"] = lv, ["width_mm"] = R(width), ["length_mm"] = R(len),
                        ["unconnected_height_mm"] = R(h), ["area_m2"] = R(area, 4), ["volume_m3"] = R(vol, 4),
                        ["structural"] = e.get_Parameter(BuiltInParameter.WALL_STRUCTURAL_SIGNIFICANT)?.AsInteger() == 1,
                        ["base_offset_mm"] = R(Get(e, BuiltInParameter.WALL_BASE_OFFSET) * FT),
                        ["top_constraint"] = doc.GetElement(e.get_Parameter(BuiltInParameter.WALL_HEIGHT_TYPE)?.AsElementId() ?? ElementId.InvalidElementId)?.Name,
                        ["top_offset_mm"] = R(Get(e, BuiltInParameter.WALL_TOP_OFFSET) * FT),
                        ["comments"] = e.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)?.AsString(),
                        ["materials"] = MaterialQty(doc, e),
                        ["openings"] = OpeningCount(doc, e),
                    });
            }
            var ga = new JsonArray();
            foreach (JsonObject g in groups.Values)
            {
                g["length_m"] = R((double)g["length_m"], 3);
                g["area_m2"] = R((double)g["area_m2"], 3);
                g["volume_m3"] = R((double)g["volume_m3"], 3);
                ga.Add(g);
            }
            var o = new JsonObject
            {
                ["category"] = cat.Name, ["level"] = level,
                ["tong"] = new JsonObject { ["count"] = tn, ["length_m"] = R(tl, 3), ["area_m2"] = R(ta, 3), ["volume_m3"] = R(tv, 3) },
                ["theo_type"] = ga,
            };
            if (items) o["items"] = list;
            return o;
        }

        // ---------------------------------------------------------------- lệnh ghi (khoá)
        static JsonNode SetParams(UIApplication ui, JsonObject p)
        {
            if (!Ctx.WriteEnabled)
                throw new Exception("Ghi đang KHOÁ. Người dùng phải bấm tab 'Archivina MCP' > 'Cho phép ghi' trong Revit.");
            Document doc = Doc(ui);
            if (doc.IsReadOnly) throw new Exception("Dự án đang mở chỉ đọc.");
            if (!(p["items"] is JsonArray items) || items.Count == 0) throw new Exception("Thiếu items.");
            var res = new JsonArray();
            int okCount = 0;
            using (var t = new Transaction(doc, "Claude MCP - đặt tham số"))
            {
                t.Start();
                foreach (JsonNode n in items)
                {
                    var it = n.AsObject();
                    long id = (long)(double)it["id"];
                    string pname = it["param"]?.ToString();
                    JsonNode val = it["value"];
                    var r = new JsonObject { ["id"] = id, ["param"] = pname };
                    try
                    {
                        Element e = doc.GetElement(new ElementId(id)) ?? throw new Exception("phần tử không tồn tại");
                        Parameter prm = null;
                        if (Enum.TryParse(pname, out BuiltInParameter bip)) prm = e.get_Parameter(bip);
                        prm ??= e.LookupParameter(pname) ?? throw new Exception("không có tham số này");
                        if (prm.IsReadOnly) throw new Exception("tham số chỉ đọc");
                        r["truoc"] = ParamValue(prm);
                        bool done;
                        switch (prm.StorageType)
                        {
                            case StorageType.String:
                                done = prm.Set(val?.ToString() ?? "");
                                break;
                            case StorageType.Integer:
                                done = prm.Set((int)(double)val);
                                break;
                            case StorageType.ElementId:
                                done = prm.Set(new ElementId((long)(double)val));
                                break;
                            case StorageType.Double:
                                if (val is JsonValue jv && jv.TryGetValue(out string sv)) { done = prm.SetValueString(sv); break; }
                                double d = (double)val;
                                switch (SpecKey(prm))
                                {
                                    case "autodesk.spec.aec:length": d /= FT; break;
                                    case "autodesk.spec.aec:area": d /= FT2; break;
                                    case "autodesk.spec.aec:volume": d /= FT3; break;
                                    case "autodesk.spec.aec:angle": d *= Math.PI / 180; break;
                                }
                                done = prm.Set(d);
                                break;
                            default: throw new Exception("kiểu tham số không hỗ trợ");
                        }
                        if (!done) throw new Exception("Revit từ chối giá trị");
                        r["sau"] = ParamValue(prm);
                        r["ok"] = true;
                        okCount++;
                    }
                    catch (Exception ex)
                    {
                        r["ok"] = false;
                        r["error"] = ex.Message;
                    }
                    res.Add(r);
                }
                if (okCount > 0) t.Commit(); else t.RollBack();
            }
            return new JsonObject { ["thanh_cong"] = okCount, ["tong"] = items.Count, ["ket_qua"] = res };
        }
    }
}

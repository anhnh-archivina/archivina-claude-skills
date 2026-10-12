// Archivina Revit MCP – CORE: lệnh DỰNG MÔ HÌNH (ghi). Gọi từ Commands.Run:
//   "new_project"     : tạo dự án mới từ template, lưu ra file MỚI (không ghi đè) rồi mở + kích hoạt trong Revit.
//   "build_apartment" : dựng căn hộ theo spec JSON (mm) vào dự án đang active: level, kiểu tường / sàn / cửa
//                       (tên "Archivina_…"), tường, vách BTCT, vách kính (curtain wall nhúng tường), cửa đi, cửa sổ,
//                       sàn, phòng, đường phân chia phòng.
// An toàn: cần "Cho phép ghi" (tab Archivina MCP) VÀ dự án đang mở là BẢN SAO (Safety.RequireWritableCopy) – file gốc
//          bị từ chối; build_apartment gói trong 1 TransactionGroup "Claude MCP - dựng căn hộ" (Ctrl+Z hoàn tác), lỗi
//          bất kỳ bước bắt buộc nào -> RollBack toàn bộ. Phần tử tạo ra được đánh dấu; "delete" chỉ xoá phần tử đã đánh
//          dấu. Trên dự án KHÔNG do Claude tạo: không đổi tên / cao độ / xoá level có sẵn, không đổi tên family có sẵn.
//          Cảnh báo Revit được ghi vào kết quả (không xoá im lặng).
//          Không lưu đè: new_project từ chối nếu file đích đã tồn tại / nằm trong 02-Ban-Ve-Goc; build_apartment không lưu file.

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json.Nodes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.DB.Structure;
using Autodesk.Revit.UI;

namespace ArchivinaRevitMcp.Core
{
    internal static class Modeling
    {
        const double FT = 304.8;

        static void RequireWrite()
        {
            if (!Ctx.WriteEnabled)
                throw new Exception("Ghi đang KHOÁ. Người dùng phải bấm tab 'Archivina MCP' > 'Cho phép ghi' trong Revit.");
        }

        static double D(JsonNode n) => (double)n;
        static XYZ P(JsonNode a, double z = 0) => new XYZ(D(a[0]) / FT, D(a[1]) / FT, z);
        static string S(JsonObject o, string k, string def = null) => o[k] == null ? def : o[k].ToString();
        static double N(JsonObject o, string k, double def) => o[k] == null ? def : (double)o[k];

        // ------------------------------------------------------------------------------------------ new_project
        public static JsonNode NewProject(UIApplication ui, JsonObject p)
        {
            RequireWrite();
            string template = S(p, "template");
            string path = S(p, "path") ?? throw new Exception("Thiếu path (file .rvt mới).");
            path = Path.GetFullPath(path);
            if (File.Exists(path)) throw new Exception($"File '{path}' đã tồn tại – không ghi đè, chọn tên khác.");
            if (Safety.IsOriginalLocation(path)) throw new Exception("Không tạo dự án trong thư mục 02-Ban-Ve-Goc (bản vẽ gốc).");
            if (string.IsNullOrEmpty(template)) template = ui.Application.DefaultProjectTemplate;
            if (!File.Exists(template)) throw new Exception($"Không thấy template '{template}'.");
            Directory.CreateDirectory(Path.GetDirectoryName(path));

            Document doc = ui.Application.NewProjectDocument(template);
            string projName = S(p, "project_name");
            if (!string.IsNullOrEmpty(projName))
            {
                using (var t = new Transaction(doc, "Claude MCP - thông tin dự án"))
                {
                    t.Start();
                    try { doc.ProjectInformation.Name = projName; } catch { }
                    t.Commit();
                }
            }
            doc.SaveAs(path, new SaveAsOptions { OverwriteExistingFile = false });
            Safety.Register("new", path);
            doc.Close(false);
            UIDocument uidoc = ui.OpenAndActivateDocument(path);
            return new JsonObject
            {
                ["file"] = path,
                ["template"] = template,
                ["active_document"] = uidoc?.Document?.Title,
            };
        }

        // ------------------------------------------------------------------------------------------ create_3d
        // tạo view 3D isometric (tên "name"), không đổi view đang mở trừ khi open = true
        public static JsonNode Create3D(UIApplication ui, JsonObject p)
        {
            Document doc = ui.ActiveUIDocument?.Document ?? throw new Exception("Revit chưa mở dự án nào.");
            Safety.RequireWritableCopy(doc);
            string name = S(p, "name", "Archivina_3D");
            View3D v;
            using (var t = new Transaction(doc, "Claude MCP - tạo view 3D"))
            {
                t.Start();
                ViewFamilyType vft = new FilteredElementCollector(doc).OfClass(typeof(ViewFamilyType)).Cast<ViewFamilyType>()
                    .First(x => x.ViewFamily == ViewFamily.ThreeDimensional);
                v = View3D.CreateIsometric(doc, vft.Id);
                string nm = name;
                for (int i = 2; new FilteredElementCollector(doc).OfClass(typeof(View)).Cast<View>().Any(x => x.Name == nm); i++)
                    nm = name + " " + i;
                v.Name = nm;
                try { v.DetailLevel = ViewDetailLevel.Fine; } catch { }
                try { v.DisplayStyle = DisplayStyle.ShadingWithEdges; } catch { }
                Safety.MarkCreated(doc, new[] { v.Id.Value });
                t.Commit();
            }
            if (p["open"] != null && (bool)p["open"]) ui.ActiveUIDocument.ActiveView = v;
            return new JsonObject { ["id"] = v.Id.Value, ["name"] = v.Name };
        }

        // ------------------------------------------------------------------------------------------ draw_2d
        // vẽ đường chi tiết 2D (Detail Lines) vào 1 view mặt bằng, gom mỗi nhóm thành Detail Group.
        //   view_id | level (tên level -> mặt bằng của level); styles [{name, color [r,g,b], weight}]
        //   groups [{name, style, items [{t:"l", p:[x0,y0,x1,y1]} | {t:"a", p:[x0,y0,xm,ym,x1,y1]}]}]  (mm)
        public static JsonNode Draw2D(UIApplication ui, JsonObject p)
        {
            Document doc = ui.ActiveUIDocument?.Document ?? throw new Exception("Revit chưa mở dự án nào.");
            Safety.RequireWritableCopy(doc);
            View view;
            if (p["view_id"] != null) view = doc.GetElement(new ElementId((long)(double)p["view_id"])) as View;
            else
            {
                string lvName = S(p, "level");
                view = new FilteredElementCollector(doc).OfClass(typeof(ViewPlan)).Cast<ViewPlan>()
                    .FirstOrDefault(v => !v.IsTemplate && v.ViewType == ViewType.FloorPlan && (lvName == null || v.GenLevel?.Name == lvName));
            }
            if (view == null) throw new Exception("Không tìm thấy view mặt bằng để vẽ.");
            var res = new JsonArray();
            var warn = new JsonArray();
            var created = new List<long>();
            int nCurve = 0, nSkip = 0;
            using (var t = new Transaction(doc, "Claude MCP - vẽ nội thất 2D"))
            {
                FailureHandlingOptions fo = t.GetFailureHandlingOptions();
                fo.SetFailuresPreprocessor(new LogWarnings(warn));
                t.SetFailureHandlingOptions(fo);
                t.Start();
                // kiểu nét
                Category lines = doc.Settings.Categories.get_Item(BuiltInCategory.OST_Lines);
                var gs = new Dictionary<string, GraphicsStyle>();
                foreach (JsonNode n in p["styles"] as JsonArray ?? new JsonArray())
                {
                    var o = n.AsObject();
                    string nm = S(o, "name");
                    Category sub = lines.SubCategories.Contains(nm) ? lines.SubCategories.get_Item(nm)
                                                                     : doc.Settings.Categories.NewSubcategory(lines, nm);
                    if (o["color"] is JsonArray col) sub.LineColor = new Color((byte)D(col[0]), (byte)D(col[1]), (byte)D(col[2]));
                    sub.SetLineWeight((int)N(o, "weight", 1), GraphicsStyleType.Projection);
                    gs[nm] = sub.GetGraphicsStyle(GraphicsStyleType.Projection);
                }
                double z = (view as ViewPlan)?.GenLevel?.Elevation ?? 0;
                double tol = doc.Application.ShortCurveTolerance;
                var groupTypeNames = new HashSet<string>(new FilteredElementCollector(doc).OfClass(typeof(GroupType)).Select(x => x.Name));
                foreach (JsonNode gn in p["groups"] as JsonArray ?? new JsonArray())
                {
                    var g = gn.AsObject();
                    GraphicsStyle style = gs.TryGetValue(S(g, "style", ""), out var st) ? st : null;
                    var ids = new List<ElementId>();
                    foreach (JsonNode itn in g["items"] as JsonArray ?? new JsonArray())
                    {
                        var it = itn.AsObject();
                        var a = (JsonArray)it["p"];
                        try
                        {
                            Curve cv;
                            XYZ p0 = new XYZ(D(a[0]) / FT, D(a[1]) / FT, z);
                            if (S(it, "t") == "a")
                            {
                                XYZ pm = new XYZ(D(a[2]) / FT, D(a[3]) / FT, z), p1 = new XYZ(D(a[4]) / FT, D(a[5]) / FT, z);
                                if (p0.DistanceTo(p1) < tol || p0.DistanceTo(pm) < tol) { nSkip++; continue; }
                                cv = Arc.Create(p0, p1, pm);
                            }
                            else
                            {
                                XYZ p1 = new XYZ(D(a[2]) / FT, D(a[3]) / FT, z);
                                if (p0.DistanceTo(p1) < tol) { nSkip++; continue; }
                                cv = Line.CreateBound(p0, p1);
                            }
                            DetailCurve dc = doc.Create.NewDetailCurve(view, cv);
                            if (style != null) dc.LineStyle = style;
                            ids.Add(dc.Id);
                            created.Add(dc.Id.Value);
                            nCurve++;
                        }
                        catch { nSkip++; }
                    }
                    var r = new JsonObject { ["name"] = S(g, "name"), ["so_net"] = ids.Count };
                    if (ids.Count > 1 && !(g["group"] != null && !(bool)g["group"]))
                    {
                        Group grp = doc.Create.NewGroup(ids);
                        string nm = S(g, "name", "Archivina_Noi that");
                        string un = nm;
                        for (int i = 2; groupTypeNames.Contains(un); i++) un = nm + " " + i;
                        try { grp.GroupType.Name = un; groupTypeNames.Add(un); } catch { }
                        r["group_id"] = grp.Id.Value;
                        created.Add(grp.Id.Value);
                        r["group_type"] = grp.GroupType.Name;
                    }
                    res.Add(r);
                }
                Safety.MarkCreated(doc, created);
                t.Commit();
            }
            return new JsonObject { ["view"] = view.Name, ["so_net"] = nCurve, ["bo_qua"] = nSkip, ["nhom"] = res, ["canh_bao"] = warn };
        }

        // ------------------------------------------------------------------------------------------ build_apartment
        class Ctx2
        {
            public Document Doc;
            public bool ClaudeProject;   // dự án do Claude tạo (new_project): được dọn level / đổi tên family của template
            public HashSet<long> Created = new HashSet<long>();
            public List<Level> Levels = new List<Level>();
            public Dictionary<string, Wall> WallsByTag = new Dictionary<string, Wall>();
            public JsonArray Log = new JsonArray();
            public JsonArray Warn = new JsonArray();
            public Dictionary<string, List<long>> Ids = new Dictionary<string, List<long>>();
            public void Add(string k, ElementId id)
            {
                if (!Ids.TryGetValue(k, out var l)) Ids[k] = l = new List<long>();
                l.Add(id.Value);
            }
        }

        public static JsonNode BuildApartment(UIApplication ui, JsonObject spec)
        {
            Document doc = ui.ActiveUIDocument?.Document ?? throw new Exception("Revit chưa mở dự án nào.");
            if (doc.IsFamilyDocument) throw new Exception("Đang mở family, không phải dự án.");
            Safety.RequireWritableCopy(doc);
            var c = new Ctx2 { Doc = doc, ClaudeProject = Safety.IsClaudeProject(doc), Created = Safety.CreatedIds(doc) };

            using (var tracker = new Safety.Tracker(doc))
            using (var tg = new TransactionGroup(doc, "Claude MCP - dựng căn hộ"))
            {
                tg.Start();
                try
                {
                    Step(c, "Claude MCP - sửa", () => Edits(c, spec));
                    Step(c, "Claude MCP - level", () => Levels(c, spec));
                    Step(c, "Claude MCP - tường", () => Walls(c, spec));
                    Step(c, "Claude MCP - vách BTCT", () => Columns(c, spec));
                    Step(c, "Claude MCP - cửa", () => Openings(c, spec));
                    Step(c, "Claude MCP - vách kính", () => Curtains(c, spec));
                    Step(c, "Claude MCP - sàn", () => Floors(c, spec));
                    Step(c, "Claude MCP - phòng", () => Rooms(c, spec));
                    Step(c, "Claude MCP - đánh dấu phần tử", () =>
                        Safety.MarkCreated(doc, tracker.Added.Concat(c.Ids.Values.SelectMany(v => v))));
                    tg.Assimilate();
                }
                catch
                {
                    tg.RollBack();
                    throw;
                }
            }
            var ids = new JsonObject();
            foreach (var kv in c.Ids) ids[kv.Key] = new JsonArray(kv.Value.Select(v => (JsonNode)v).ToArray());
            return new JsonObject { ["ids"] = ids, ["log"] = c.Log, ["canh_bao"] = c.Warn };
        }

        // mỗi bước 1 transaction; cảnh báo Revit (warning) được nuốt và ghi lại, lỗi thật -> exception
        static void Step(Ctx2 c, string name, Action a)
        {
            using (var t = new Transaction(c.Doc, name))
            {
                FailureHandlingOptions fo = t.GetFailureHandlingOptions();
                fo.SetFailuresPreprocessor(new LogWarnings(c.Warn));
                t.SetFailureHandlingOptions(fo);
                t.Start();
                try { a(); }
                catch (Exception ex) { t.RollBack(); throw new Exception($"{name}: {ex.Message}"); }
                TransactionStatus st = t.Commit();
                if (st != TransactionStatus.Committed) throw new Exception($"{name}: Revit không commit ({st}).");
            }
        }

        // ---------------------------------------------------------------- sửa phần tử đã dựng: xoá, lật cửa
        //   delete: [id...]; flip: [{id, facing: true, hand: true}]
        static void Edits(Ctx2 c, JsonObject spec)
        {
            Document doc = c.Doc;
            foreach (JsonNode n in spec["delete"] as JsonArray ?? new JsonArray())
            {
                var id = new ElementId((long)(double)n);
                if (doc.GetElement(id) == null) throw new Exception($"Không có phần tử {id.Value} để xoá.");
                if (!c.ClaudeProject && !c.Created.Contains(id.Value))
                    throw new Exception($"Từ chối xoá {id.Value}: phần tử không do Claude tạo (chỉ xoá được phần tử Claude dựng trên bản sao).");
                doc.Delete(id);
                c.Log.Add($"Xoá {id.Value}");
            }
            // materials: [{name, color [r,g,b], transparency 0-100}] – tạo nếu chưa có
            foreach (JsonNode n in spec["materials"] as JsonArray ?? new JsonArray())
            {
                var o = n.AsObject();
                var existed = new FilteredElementCollector(doc).OfClass(typeof(Material)).Cast<Material>().FirstOrDefault(x => x.Name == S(o, "name"));
                if (existed != null && !c.ClaudeProject && !c.Created.Contains(existed.Id.Value))
                {
                    c.Warn.Add($"Vật liệu '{existed.Name}' có sẵn trong dự án – không đổi màu / độ trong suốt.");
                    continue;
                }
                Material m = Mat(doc, S(o, "name"));
                if (o["color"] is JsonArray col) m.Color = new Color((byte)D(col[0]), (byte)D(col[1]), (byte)D(col[2]));
                if (o["transparency"] != null) m.Transparency = (int)N(o, "transparency", 0);
                c.Log.Add($"Vật liệu {m.Name}");
            }
            foreach (JsonNode n in spec["flip"] as JsonArray ?? new JsonArray())
            {
                var o = n.AsObject();
                long id = (long)(double)o["id"];
                var fi = doc.GetElement(new ElementId(id)) as FamilyInstance ?? throw new Exception($"{id} không phải family instance.");
                if (!c.ClaudeProject && !c.Created.Contains(id))
                    throw new Exception($"Từ chối lật {id}: phần tử không do Claude tạo.");
                if (o["facing"] != null && (bool)o["facing"]) fi.flipFacing();
                if (o["hand"] != null && (bool)o["hand"]) fi.flipHand();
                c.Log.Add($"Lật {id}");
            }
        }

        // ---------------------------------------------------------------- level: dùng lại level có sẵn của template, đổi tên / cao độ
        static void Levels(Ctx2 c, JsonObject spec)
        {
            Document doc = c.Doc;
            var exist = new FilteredElementCollector(doc).OfClass(typeof(Level)).Cast<Level>().OrderBy(l => l.Elevation).ToList();
            if (!(spec["levels"] is JsonArray arr))
            {
                // không khai báo levels: dùng level hiện có theo thứ tự cao độ
                c.Levels.AddRange(exist);
                return;
            }
            for (int i = 0; i < arr.Count; i++)
            {
                var o = arr[i].AsObject();
                string name = S(o, "name");
                double elev = N(o, "elev", 0) / FT;
                Level lv = exist.FirstOrDefault(l => l.Name == name);
                bool mine = lv != null && (c.ClaudeProject || c.Created.Contains(lv.Id.Value));
                if (lv == null && c.ClaudeProject && i < exist.Count) { lv = exist[i]; mine = true; } // dùng lại level của template
                if (lv == null)
                {
                    lv = Level.Create(doc, elev);
                    try { lv.Name = name; } catch (Exception ex) { c.Warn.Add($"Không đặt được tên level '{name}': {ex.Message}"); }
                    c.Levels.Add(lv);
                    c.Add("level", lv.Id);
                    continue;
                }
                if (!mine)
                {
                    // level có sẵn của dự án: KHÔNG đổi tên / cao độ
                    if (Math.Abs(lv.Elevation - elev) > 1e-6)
                        c.Warn.Add($"Level '{name}' có sẵn ở cao độ {Math.Round(lv.Elevation * FT)} mm (spec {Math.Round(elev * FT)} mm) – giữ nguyên level của dự án.");
                    c.Levels.Add(lv);
                    continue;
                }
                lv.Elevation = elev;
                string old = lv.Name;
                if (old != name)
                {
                    lv.Name = name;
                    // đổi tên view mặt bằng cùng tên level
                    foreach (ViewPlan v in new FilteredElementCollector(doc).OfClass(typeof(ViewPlan)).Cast<ViewPlan>()
                                 .Where(v => !v.IsTemplate && v.GenLevel?.Id == lv.Id && v.Name == old))
                        try { v.Name = name; } catch { }
                }
                c.Levels.Add(lv);
                c.Add("level", lv.Id);
            }
            // level thừa của template -> chỉ xoá trên dự án do Claude tạo, và chỉ khi level KHÔNG có phần tử nào (trừ view)
            if (!c.ClaudeProject) return;
            foreach (Level l in exist.Where(l => !c.Levels.Any(k => k.Id == l.Id)))
            {
                bool used = new FilteredElementCollector(doc).WherePasses(new ElementLevelFilter(l.Id))
                    .WhereElementIsNotElementType().Any(e => !(e is View));
                if (used) { c.Warn.Add($"Giữ level '{l.Name}': còn phần tử."); continue; }
                try { c.Doc.Delete(l.Id); c.Log.Add($"Xoá level thừa (trống) của template: {l.Name}"); } catch { }
            }
        }

        static Level Lv(Ctx2 c, JsonObject o, string k = "level") => c.Levels[(int)N(o, k, 0)];

        // ---------------------------------------------------------------- kiểu tường / sàn 1 lớp
        static Material Mat(Document doc, string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            var m = new FilteredElementCollector(doc).OfClass(typeof(Material)).Cast<Material>().FirstOrDefault(x => x.Name == name);
            if (m != null) return m;
            ElementId id = Material.Create(doc, name);
            var nm = doc.GetElement(id) as Material;
            nm.Color = new Color(210, 210, 205); // mặc định Material.Create có thể ra màu tối
            return nm;
        }

        static WallType BasicWallType(Ctx2 c, string name, double widthMm, string material)
        {
            Document doc = c.Doc;
            var all = new FilteredElementCollector(doc).OfClass(typeof(WallType)).Cast<WallType>().ToList();
            WallType wt = all.FirstOrDefault(w => w.Name == name);
            if (wt != null && !c.ClaudeProject && !c.Created.Contains(wt.Id.Value))
            {
                c.Warn.Add($"Kiểu tường '{name}' có sẵn trong dự án – dùng nguyên, không sửa cấu tạo.");
                return wt;
            }
            if (wt == null)
            {
                WallType src = all.Where(w => w.Kind == WallKind.Basic).OrderBy(w => w.Name.Contains("Generic") ? 0 : 1).First();
                wt = (WallType)src.Duplicate(name);
            }
            Material m = Mat(doc, material);
            var cs = CompoundStructure.CreateSingleLayerCompoundStructure(MaterialFunctionAssignment.Structure, widthMm / FT,
                m?.Id ?? ElementId.InvalidElementId);
            wt.SetCompoundStructure(cs);
            try { wt.get_Parameter(BuiltInParameter.FUNCTION_PARAM)?.Set(0); } catch { }
            return wt;
        }

        static FloorType FloorTypeNamed(Ctx2 c, string name, double widthMm, string material)
        {
            Document doc = c.Doc;
            var all = new FilteredElementCollector(doc).OfClass(typeof(FloorType)).Cast<FloorType>().Where(f => !f.IsFoundationSlab).ToList();
            FloorType ft = all.FirstOrDefault(f => f.Name == name);
            if (ft != null && !c.ClaudeProject && !c.Created.Contains(ft.Id.Value))
            {
                c.Warn.Add($"Kiểu sàn '{name}' có sẵn trong dự án – dùng nguyên, không sửa cấu tạo.");
                return ft;
            }
            if (ft == null)
            {
                FloorType src = all.OrderBy(f => f.Name.Contains("Generic") ? 0 : 1).First();
                ft = (FloorType)src.Duplicate(name);
            }
            Material m = Mat(doc, material);
            var cs = CompoundStructure.CreateSingleLayerCompoundStructure(MaterialFunctionAssignment.Structure, widthMm / FT,
                m?.Id ?? ElementId.InvalidElementId);
            cs.EndCap = EndCapCondition.NoEndCap; // sàn không nhận end cap mặc định của cấu trúc tường
            ft.SetCompoundStructure(cs);
            return ft;
        }

        // ---------------------------------------------------------------- tường (đường tim)
        static void Walls(Ctx2 c, JsonObject spec)
        {
            if (!(spec["walls"] is JsonArray arr)) return;
            var types = new Dictionary<string, WallType>();
            foreach (JsonNode n in spec["wall_types"] as JsonArray ?? new JsonArray())
            {
                var o = n.AsObject();
                types[S(o, "name")] = BasicWallType(c, S(o, "name"), N(o, "width", 100), S(o, "material"));
                c.Add("wall_type", types[S(o, "name")].Id);
            }
            foreach (JsonNode n in arr)
            {
                var o = n.AsObject();
                WallType wt = types.TryGetValue(S(o, "type"), out var x) ? x : throw new Exception("Không có kiểu tường " + S(o, "type"));
                Level lv = Lv(c, o);
                Line ln = Line.CreateBound(P(o["p0"], lv.Elevation), P(o["p1"], lv.Elevation));
                double h = N(o, "height", 3000) / FT;
                Wall w = Wall.Create(c.Doc, ln, wt.Id, lv.Id, h, 0, false, false);
                w.get_Parameter(BuiltInParameter.WALL_KEY_REF_PARAM)?.Set((int)WallLocationLine.WallCenterline);
                if (o["top_level"] != null)
                {
                    w.get_Parameter(BuiltInParameter.WALL_HEIGHT_TYPE).Set(Lv(c, o, "top_level").Id);
                    w.get_Parameter(BuiltInParameter.WALL_TOP_OFFSET).Set(0.0);
                }
                if (o["room_bounding"] != null)
                    w.get_Parameter(BuiltInParameter.WALL_ATTR_ROOM_BOUNDING)?.Set((bool)o["room_bounding"] ? 1 : 0);
                string tag = S(o, "tag");
                if (tag != null) c.WallsByTag[tag] = w;
                try { w.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)?.Set(tag ?? ""); } catch { }
                c.Add("wall", w.Id);
            }
        }

        // ---------------------------------------------------------------- vách / cột BTCT: family cột nếu có, không thì tường
        static void Columns(Ctx2 c, JsonObject spec)
        {
            if (!(spec["columns"] is JsonArray arr) || arr.Count == 0) return;
            Document doc = c.Doc;
            string famName = S(spec, "column_family", "Archivina_Cot BTCT chu nhat");
            string material = S(spec, "column_material", "Archivina_BTCT");
            var syms = new FilteredElementCollector(doc).OfClass(typeof(FamilySymbol)).OfCategory(BuiltInCategory.OST_Columns)
                .Cast<FamilySymbol>().ToList();
            FamilySymbol src = syms.FirstOrDefault(s => s.Family.Name == famName)
                               ?? syms.FirstOrDefault(s => s.Family.Name.IndexOf("Rectangular", StringComparison.OrdinalIgnoreCase) >= 0)
                               ?? syms.FirstOrDefault();
            if (src != null && src.Family.Name != famName && !c.ClaudeProject)
                c.Warn.Add($"Dùng family cột có sẵn '{src.Family.Name}' (không đổi tên family của dự án).");
            else if (src != null && src.Family.Name != famName)
            {
                string old = src.Family.Name;
                try { src.Family.Name = famName; c.Log.Add($"Đổi tên family cột '{old}' -> '{famName}'"); }
                catch (Exception ex) { c.Warn.Add($"Không đổi được tên family cột '{old}': {ex.Message}"); }
            }
            foreach (JsonNode n in arr)
            {
                var o = n.AsObject();
                double b = N(o, "b", 300), h = N(o, "h", 300); // b theo trục X cục bộ, h theo Y
                Level lv = Lv(c, o), top = Lv(c, o, "top_level");
                if (src != null)
                {
                    string tn = $"Archivina_Cot {Math.Round(b)}x{Math.Round(h)}";
                    FamilySymbol sym = syms.FirstOrDefault(s => s.Family.Id == src.Family.Id && s.Name == tn)
                                       ?? src.Family.GetFamilySymbolIds().Select(id => (FamilySymbol)doc.GetElement(id)).FirstOrDefault(s => s.Name == tn);
                    if (sym == null)
                    {
                        sym = (FamilySymbol)src.Duplicate(tn);
                        SetLen(sym, b, "b", "Width", "Chiều rộng");
                        SetLen(sym, h, "h", "Depth", "Chiều sâu");
                        syms.Add(sym);
                        c.Add("column_type", sym.Id);
                    }
                    if (!sym.IsActive) sym.Activate();
                    FamilyInstance fi = doc.Create.NewFamilyInstance(P(o["pt"], lv.Elevation), sym, lv, StructuralType.NonStructural);
                    fi.get_Parameter(BuiltInParameter.FAMILY_TOP_LEVEL_PARAM)?.Set(top.Id);
                    fi.get_Parameter(BuiltInParameter.FAMILY_TOP_LEVEL_OFFSET_PARAM)?.Set(0.0);
                    double rot = N(o, "rot", 0);
                    if (Math.Abs(rot) > 1e-6)
                        ElementTransformUtils.RotateElement(doc, fi.Id, Line.CreateBound(P(o["pt"]), P(o["pt"]) + XYZ.BasisZ), rot * Math.PI / 180);
                    Material m = Mat(doc, material);
                    if (m != null) fi.LookupParameter("Material")?.Set(m.Id);
                    c.Add("column", fi.Id);
                }
                else
                {
                    // không có family cột trong template -> vách BTCT bằng tường dọc trục dài
                    WallType wt = BasicWallType(c, $"Archivina_Vach BTCT {Math.Round(Math.Min(b, h))}", Math.Min(b, h), material);
                    double rot = N(o, "rot", 0) * Math.PI / 180;
                    XYZ ax = b >= h ? new XYZ(Math.Cos(rot), Math.Sin(rot), 0) : new XYZ(-Math.Sin(rot), Math.Cos(rot), 0);
                    double half = Math.Max(b, h) / 2 / FT;
                    XYZ ctr = P(o["pt"], lv.Elevation);
                    Wall w = Wall.Create(doc, Line.CreateBound(ctr - ax * half, ctr + ax * half), wt.Id, lv.Id, 3000 / FT, 0, false, true);
                    w.get_Parameter(BuiltInParameter.WALL_HEIGHT_TYPE).Set(top.Id);
                    c.Add("column_wall", w.Id);
                    c.Warn.Add("Template không có family cột – vách BTCT dựng bằng tường.");
                }
            }
        }

        static bool SetLen(Element e, double mm, params string[] names)
        {
            foreach (string nm in names)
            {
                Parameter p = e.LookupParameter(nm);
                if (p != null && !p.IsReadOnly && p.StorageType == StorageType.Double) { p.Set(mm / FT); return true; }
            }
            return false;
        }

        // ---------------------------------------------------------------- cửa đi / cửa sổ
        static FamilySymbol OpeningType(Ctx2 c, BuiltInCategory cat, JsonObject o, Dictionary<string, FamilySymbol> cache)
        {
            Document doc = c.Doc;
            string famName = S(o, "family_name");
            string typeName = S(o, "type_name");
            if (cache.TryGetValue(typeName, out var hit)) return hit;
            var syms = new FilteredElementCollector(doc).OfClass(typeof(FamilySymbol)).OfCategory(cat).Cast<FamilySymbol>().ToList();
            string[] prefer = (o["source_family"] as JsonArray)?.Select(x => x.ToString()).ToArray() ?? new string[0];
            FamilySymbol src = syms.FirstOrDefault(s => s.Family.Name == famName);
            if (src == null)
                foreach (string pf in prefer)
                {
                    src = syms.FirstOrDefault(s => s.Family.Name.IndexOf(pf, StringComparison.OrdinalIgnoreCase) >= 0);
                    if (src != null) break;
                }
            src ??= syms.FirstOrDefault() ?? throw new Exception($"Dự án không có family {cat} nào để dùng.");
            Family fam = src.Family;
            if (fam.Name != famName && !c.ClaudeProject)
                c.Warn.Add($"Dùng family có sẵn '{fam.Name}' cho '{famName}' (không đổi tên family của dự án).");
            else if (fam.Name != famName)
            {
                string old = fam.Name;
                fam.Name = famName;
                c.Log.Add($"Đổi tên family '{old}' -> '{famName}'");
            }
            FamilySymbol sym = fam.GetFamilySymbolIds().Select(id => (FamilySymbol)doc.GetElement(id)).FirstOrDefault(s => s.Name == typeName);
            if (sym != null && !c.ClaudeProject && !c.Created.Contains(sym.Id.Value))
            {
                c.Warn.Add($"Kiểu '{typeName}' có sẵn trong dự án – dùng nguyên, không đổi kích thước.");
                if (!sym.IsActive) sym.Activate();
                cache[typeName] = sym;
                return sym;
            }
            if (sym == null)
            {
                sym = (FamilySymbol)src.Duplicate(typeName);
                c.Add(cat == BuiltInCategory.OST_Doors ? "door_type" : "window_type", sym.Id);
            }
            double w = N(o, "width", 900), h = N(o, "height", 2200);
            bool okW = SetBip(sym, w, BuiltInParameter.DOOR_WIDTH, BuiltInParameter.WINDOW_WIDTH, BuiltInParameter.FAMILY_WIDTH_PARAM)
                       || SetLen(sym, w, "Width", "Rough Width");
            bool okH = SetBip(sym, h, BuiltInParameter.DOOR_HEIGHT, BuiltInParameter.WINDOW_HEIGHT, BuiltInParameter.FAMILY_HEIGHT_PARAM)
                       || SetLen(sym, h, "Height", "Rough Height");
            if (!okW || !okH) c.Warn.Add($"Kiểu {typeName}: không đặt được {(okW ? "" : "rộng ")}{(okH ? "" : "cao")} – kiểm tra family '{famName}'.");
            if (!sym.IsActive) sym.Activate();
            cache[typeName] = sym;
            return sym;
        }

        static bool SetBip(Element e, double mm, params BuiltInParameter[] bips)
        {
            foreach (var b in bips)
            {
                Parameter p = e.get_Parameter(b);
                if (p != null && !p.IsReadOnly && p.StorageType == StorageType.Double) { p.Set(mm / FT); return true; }
            }
            return false;
        }

        static void Openings(Ctx2 c, JsonObject spec)
        {
            if (!(spec["openings"] is JsonArray arr)) return;
            Document doc = c.Doc;
            var cache = new Dictionary<string, FamilySymbol>();
            foreach (JsonNode n in arr)
            {
                var o = n.AsObject();
                bool isDoor = S(o, "cat", "door") == "door";
                FamilySymbol sym = OpeningType(c, isDoor ? BuiltInCategory.OST_Doors : BuiltInCategory.OST_Windows, o, cache);
                Wall host = c.WallsByTag.TryGetValue(S(o, "host") ?? "", out var hw) ? hw : throw new Exception($"Không thấy tường chủ '{S(o, "host")}'.");
                Level lv = Lv(c, o);
                FamilyInstance fi = doc.Create.NewFamilyInstance(P(o["pt"], lv.Elevation), sym, host, lv, StructuralType.NonStructural);
                double sill = N(o, "sill", isDoor ? 0 : 450);
                fi.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)?.Set(sill / FT);
                doc.Regenerate();
                if (o["facing"] != null && fi.CanFlipFacing)
                {
                    XYZ f = new XYZ(D(o["facing"][0]), D(o["facing"][1]), 0);
                    if (fi.FacingOrientation.DotProduct(f) < 0) fi.flipFacing();
                }
                if (o["hand"] != null && fi.CanFlipHand)
                {
                    XYZ hnd = new XYZ(D(o["hand"][0]), D(o["hand"][1]), 0);
                    if (fi.HandOrientation.DotProduct(hnd) < 0) fi.flipHand();
                }
                try { fi.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)?.Set(S(o, "mark", "")); } catch { }
                c.Add(isDoor ? "door" : "window", fi.Id);
            }
        }

        // ---------------------------------------------------------------- vách kính: curtain wall nhúng vào tường chủ
        static void Curtains(Ctx2 c, JsonObject spec)
        {
            if (!(spec["curtains"] is JsonArray arr) || arr.Count == 0) return;
            Document doc = c.Doc;
            var all = new FilteredElementCollector(doc).OfClass(typeof(WallType)).Cast<WallType>().ToList();
            foreach (JsonNode n in arr)
            {
                var o = n.AsObject();
                string name = S(o, "type_name");
                WallType wt = all.FirstOrDefault(w => w.Name == name);
                if (wt == null)
                {
                    WallType src = all.Where(w => w.Kind == WallKind.Curtain)
                        .OrderBy(w => w.Name.Contains("Storefront") ? 0 : w.Name.Contains("Curtain Wall") ? 1 : 2).FirstOrDefault()
                        ?? throw new Exception("Template không có kiểu Curtain Wall.");
                    wt = (WallType)src.Duplicate(name);
                    all.Add(wt);
                    c.Add("curtain_type", wt.Id);
                }
                wt.get_Parameter(BuiltInParameter.ALLOW_AUTO_EMBED)?.Set(1);
                Level lv = Lv(c, o);
                Line ln = Line.CreateBound(P(o["p0"], lv.Elevation), P(o["p1"], lv.Elevation));
                Wall w = Wall.Create(doc, ln, wt.Id, lv.Id, N(o, "height", 2400) / FT, N(o, "base_offset", 0) / FT, false, false);
                try { w.get_Parameter(BuiltInParameter.ALL_MODEL_MARK)?.Set(S(o, "mark", "")); } catch { }
                c.Add("curtain", w.Id);
            }
        }

        // ---------------------------------------------------------------- sàn
        static void Floors(Ctx2 c, JsonObject spec)
        {
            if (!(spec["floors"] is JsonArray arr)) return;
            foreach (JsonNode n in arr)
            {
                var o = n.AsObject();
                FloorType ft = FloorTypeNamed(c, S(o, "type_name"), N(o, "width", 200), S(o, "material"));
                c.Add("floor_type", ft.Id);
                Level lv = Lv(c, o);
                var pts = (o["loop"] as JsonArray).Select(q => P(q, lv.Elevation)).ToList();
                var loop = new CurveLoop();
                for (int i = 0; i < pts.Count; i++) loop.Append(Line.CreateBound(pts[i], pts[(i + 1) % pts.Count]));
                Floor f = Floor.Create(c.Doc, new List<CurveLoop> { loop }, ft.Id, lv.Id);
                f.get_Parameter(BuiltInParameter.FLOOR_PARAM_IS_STRUCTURAL)?.Set(0);
                c.Add("floor", f.Id);
            }
        }

        // ---------------------------------------------------------------- phòng + đường phân chia
        static void Rooms(Ctx2 c, JsonObject spec)
        {
            Document doc = c.Doc;
            if (spec["separations"] is JsonArray seps && seps.Count > 0)
            {
                foreach (var grp in seps.Select(x => x.AsObject()).GroupBy(o => (int)N(o, "level", 0)))
                {
                    Level lv = c.Levels[grp.Key];
                    ViewPlan vp = new FilteredElementCollector(doc).OfClass(typeof(ViewPlan)).Cast<ViewPlan>()
                        .FirstOrDefault(v => !v.IsTemplate && v.ViewType == ViewType.FloorPlan && v.GenLevel?.Id == lv.Id)
                        ?? throw new Exception($"Không có mặt bằng cho level {lv.Name}.");
                    SketchPlane sp = SketchPlane.Create(doc, Plane.CreateByNormalAndOrigin(XYZ.BasisZ, new XYZ(0, 0, lv.Elevation)));
                    var ca = new CurveArray();
                    foreach (var o in grp) ca.Append(Line.CreateBound(P(o["p0"], lv.Elevation), P(o["p1"], lv.Elevation)));
                    foreach (ModelCurve mc in doc.Create.NewRoomBoundaryLines(sp, ca, vp)) c.Add("separation", mc.Id);
                }
                doc.Regenerate();
            }
            if (!(spec["rooms"] is JsonArray arr)) return;
            foreach (JsonNode n in arr)
            {
                var o = n.AsObject();
                Level lv = Lv(c, o);
                Room r = doc.Create.NewRoom(lv, new UV(D(o["pt"][0]) / FT, D(o["pt"][1]) / FT));
                r.Name = S(o, "name", "Phòng");
                if (o["number"] != null) r.Number = S(o, "number");
                if (o["top_level"] != null)
                {
                    r.UpperLimit = Lv(c, o, "top_level");
                    r.LimitOffset = 0;
                }
                c.Add("room", r.Id);
            }
            doc.Regenerate();
            foreach (long id in c.Ids.TryGetValue("room", out var l) ? l : new List<long>())
            {
                var r = (Room)doc.GetElement(new ElementId(id));
                if (r.Area <= 0) c.Warn.Add($"Phòng '{r.Name}' (id {id}) chưa khép kín (Not Enclosed).");
            }
        }
    }
}

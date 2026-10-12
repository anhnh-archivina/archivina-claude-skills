// Archivina Revit MCP – CORE: lệnh DỰNG MÔ HÌNH KẾT CẤU (ghi). Gọi từ Commands.Run:
//   "build_structure" : dựng kết cấu BTCT theo spec JSON (mm) vào dự án đang active – level, trục, cột kết cấu, dầm,
//                       sàn kết cấu (tách tấm theo vùng hạ / nâng cốt, lỗ mở), Structural Plan mỗi level, view 3D.
// Family: "Archivina_Cot BTCT chu nhat" / "Archivina_Dam BTCT chu nhat" – tham số kiểu b, h (mm), vật liệu theo
//         "Structural Material" của phần tử. Có sẵn trong dự án -> dùng; có .rfa trong thư viện (family_dir) -> nạp;
//         không có -> TỰ TẠO từ template Metric Structural Column.rft / Metric Structural Framing - Beams and Braces.rft
//         (khoá mặt khối vào reference plane / level, nhãn kích thước b, h) rồi lưu .rfa vào thư viện để lần sau dùng lại.
// An toàn: như build_apartment – cần "Cho phép ghi" + dự án là BẢN SAO; nạp family làm trước (Revit không cho nạp
//          family từ family document khi dự án đang trong transaction), phần dựng gói trong 1 TransactionGroup
//          "Claude MCP - dựng kết cấu" (Ctrl+Z hoàn tác, lỗi -> RollBack). Không lưu file dự án.

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json.Nodes;
using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Structure;
using Autodesk.Revit.UI;

namespace ArchivinaRevitMcp.Core
{
    internal static partial class Modeling
    {
        const string ColFamily = "Archivina_Cot BTCT chu nhat";
        const string BeamFamily = "Archivina_Dam BTCT chu nhat";
        const string ColRft = "Metric Structural Column.rft";
        const string BeamRft = "Metric Structural Framing - Beams and Braces.rft";

        // ------------------------------------------------------------------------------------------ build_structure
        public static JsonNode BuildStructure(UIApplication ui, JsonObject spec)
        {
            Document doc = ui.ActiveUIDocument?.Document ?? throw new Exception("Revit chưa mở dự án nào.");
            if (doc.IsFamilyDocument) throw new Exception("Đang mở family, không phải dự án.");
            Safety.RequireWritableCopy(doc);
            var c = new Ctx2 { Doc = doc, ClaudeProject = Safety.IsClaudeProject(doc), Created = Safety.CreatedIds(doc) };

            bool needCol = (spec["columns"] as JsonArray)?.Count > 0;
            bool needBeam = (spec["beams"] as JsonArray)?.Count > 0;
            Family colFam = null, beamFam = null;
            using (var tracker = new Safety.Tracker(doc))
            {
                // family nạp NGOÀI transaction group (ghi nhận để đánh dấu ở bước cuối)
                if (needCol) colFam = EnsureFamily(ui.Application, c, spec, ColFamily, ColRft, BuiltInCategory.OST_StructuralColumns, BuildColumnFamily);
                if (needBeam) beamFam = EnsureFamily(ui.Application, c, spec, BeamFamily, BeamRft, BuiltInCategory.OST_StructuralFraming, BuildBeamFamily);

                using (var tg = new TransactionGroup(doc, "Claude MCP - dựng kết cấu"))
                {
                    tg.Start();
                    try
                    {
                        Step(c, "Claude MCP - sửa", () => Edits(c, spec));
                        Step(c, "Claude MCP - level", () => Levels(c, spec));
                        Step(c, "Claude MCP - mặt bằng kết cấu", () => StructuralPlans(c));
                        Step(c, "Claude MCP - trục", () => Grids(c, spec));
                        Step(c, "Claude MCP - cột kết cấu", () => StructColumns(c, spec, colFam));
                        Step(c, "Claude MCP - dầm", () => Beams(c, spec, beamFam));
                        Step(c, "Claude MCP - sàn kết cấu", () => StructFloors(c, spec));
                        if (spec["view_3d"] != null)
                            Step(c, "Claude MCP - view 3D", () => View3DKc(c, S(spec, "view_3d")));
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
            }
            var ids = new JsonObject();
            foreach (var kv in c.Ids) ids[kv.Key] = new JsonArray(kv.Value.Select(v => (JsonNode)v).ToArray());
            var count = new JsonObject();
            foreach (var kv in c.Ids) count[kv.Key] = kv.Value.Count;
            return new JsonObject { ["so_luong"] = count, ["ids"] = ids, ["log"] = c.Log, ["canh_bao"] = c.Warn };
        }

        // ---------------------------------------------------------------- Structural Plan cho mỗi level của spec
        static void StructuralPlans(Ctx2 c)
        {
            Document doc = c.Doc;
            ViewFamilyType vft = new FilteredElementCollector(doc).OfClass(typeof(ViewFamilyType)).Cast<ViewFamilyType>()
                .FirstOrDefault(x => x.ViewFamily == ViewFamily.StructuralPlan);
            if (vft == null) { c.Warn.Add("Template không có kiểu view Structural Plan – bỏ qua tạo mặt bằng kết cấu."); return; }
            var plans = new FilteredElementCollector(doc).OfClass(typeof(ViewPlan)).Cast<ViewPlan>().Where(v => !v.IsTemplate).ToList();
            var names = new HashSet<string>(new FilteredElementCollector(doc).OfClass(typeof(View)).Cast<View>().Select(v => v.Name));
            foreach (Level lv in c.Levels)
            {
                // mặt bằng kết cấu có sẵn của template trùng tên level -> đổi tên theo chuẩn "KC - <level>" (chỉ dự án Claude tạo)
                ViewPlan co = plans.FirstOrDefault(v => v.ViewType == ViewType.EngineeringPlan && v.GenLevel?.Id == lv.Id && v.Name == lv.Name);
                if (co != null && c.ClaudeProject && !names.Contains("KC - " + lv.Name))
                    try { co.Name = "KC - " + lv.Name; names.Add(co.Name); } catch { }
                if (plans.Any(v => v.ViewType == ViewType.EngineeringPlan && v.GenLevel?.Id == lv.Id)) continue;
                ViewPlan vp = ViewPlan.Create(doc, vft.Id, lv.Id);
                string nm = "KC - " + lv.Name;
                for (int i = 2; names.Contains(nm); i++) nm = "KC - " + lv.Name + " " + i;
                try { vp.Name = nm; names.Add(nm); } catch { }
                try { vp.DetailLevel = ViewDetailLevel.Fine; } catch { }
                c.Add("view", vp.Id);
            }
        }

        // ---------------------------------------------------------------- trục: grids [{name, p0, p1}]
        static void Grids(Ctx2 c, JsonObject spec)
        {
            if (!(spec["grids"] is JsonArray arr)) return;
            var exist = new FilteredElementCollector(c.Doc).OfClass(typeof(Grid)).Cast<Grid>().ToDictionary(g => g.Name, g => g);
            foreach (JsonNode n in arr)
            {
                var o = n.AsObject();
                string name = S(o, "name");
                if (name != null && exist.ContainsKey(name))
                {
                    c.Warn.Add($"Trục '{name}' đã có trong dự án – không tạo lại.");
                    continue;
                }
                Grid g = Grid.Create(c.Doc, Line.CreateBound(P(o["p0"]), P(o["p1"])));
                if (c.Levels.Count > 0)
                    try { g.SetVerticalExtents(c.Levels.Min(l => l.Elevation) - 1000 / FT, c.Levels.Max(l => l.Elevation) + 3000 / FT); } catch { }
                if (name != null) try { g.Name = name; exist[name] = g; } catch (Exception ex) { c.Warn.Add($"Không đặt được tên trục '{name}': {ex.Message}"); }
                c.Add("grid", g.Id);
            }
        }

        // ---------------------------------------------------------------- loại cột / dầm theo b x h
        static FamilySymbol SectionType(Ctx2 c, Family fam, string prefix, double b, double h, Dictionary<string, FamilySymbol> cache)
        {
            string tn = $"{prefix} {Math.Round(b)}x{Math.Round(h)}";
            if (cache.TryGetValue(tn, out var hit)) return hit;
            Document doc = c.Doc;
            var syms = fam.GetFamilySymbolIds().Select(id => (FamilySymbol)doc.GetElement(id)).ToList();
            FamilySymbol sym = syms.FirstOrDefault(s => s.Name == tn);
            if (sym != null && !c.ClaudeProject && !c.Created.Contains(sym.Id.Value))
            {
                c.Warn.Add($"Kiểu '{tn}' có sẵn trong dự án – dùng nguyên, không đổi kích thước.");
            }
            else
            {
                if (sym == null)
                {
                    sym = (FamilySymbol)syms.First().Duplicate(tn);
                    c.Add("type", sym.Id);
                }
                if (!SetLen(sym, b, "b") || !SetLen(sym, h, "h"))
                    throw new Exception($"Family '{fam.Name}' không có tham số kiểu b / h – kiểm tra family.");
            }
            if (!sym.IsActive) sym.Activate();
            cache[tn] = sym;
            return sym;
        }

        static void SetStructMaterial(Ctx2 c, Element e, string material)
        {
            if (string.IsNullOrEmpty(material)) return;
            Material m = Mat(c.Doc, material);
            // Structural Material (phân tích / thống kê) + "Vat lieu KC" (vật liệu hình khối của family Archivina)
            bool ok = false;
            foreach (Parameter p in new[] { e.get_Parameter(BuiltInParameter.STRUCTURAL_MATERIAL_PARAM), e.LookupParameter("Vat lieu KC") })
                if (p != null && !p.IsReadOnly) { p.Set(m.Id); ok = true; }
            if (!ok) c.Warn.Add($"Phần tử {e.Id.Value}: không gán được vật liệu '{material}'.");
        }

        // mã cấu kiện (C1, D1…) lặp lại nhiều phần tử -> ghi vào Comments (Mark trùng sinh cảnh báo Revit)
        static void SetMark(Element e, string mark)
        {
            if (string.IsNullOrEmpty(mark)) return;
            try { e.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)?.Set(mark); } catch { }
        }

        // ---------------------------------------------------------------- cột: columns [{mark, b, h, pt, rot, level, top_level,
        //                                                                   base_offset, top_offset, material}]
        static void StructColumns(Ctx2 c, JsonObject spec, Family fam)
        {
            if (!(spec["columns"] is JsonArray arr) || arr.Count == 0) return;
            Document doc = c.Doc;
            var cache = new Dictionary<string, FamilySymbol>();
            foreach (JsonNode n in arr)
            {
                var o = n.AsObject();
                double b = N(o, "b", 300), h = N(o, "h", 300);
                FamilySymbol sym = SectionType(c, fam, "Cot", b, h, cache);
                Level lv = Lv(c, o), top = Lv(c, o, "top_level");
                FamilyInstance fi = doc.Create.NewFamilyInstance(P(o["pt"], lv.Elevation), sym, lv, StructuralType.Column);
                fi.get_Parameter(BuiltInParameter.FAMILY_BASE_LEVEL_PARAM)?.Set(lv.Id);
                fi.get_Parameter(BuiltInParameter.FAMILY_TOP_LEVEL_PARAM)?.Set(top.Id);
                fi.get_Parameter(BuiltInParameter.FAMILY_BASE_LEVEL_OFFSET_PARAM)?.Set(N(o, "base_offset", 0) / FT);
                fi.get_Parameter(BuiltInParameter.FAMILY_TOP_LEVEL_OFFSET_PARAM)?.Set(N(o, "top_offset", 0) / FT);
                double rot = N(o, "rot", 0);
                if (Math.Abs(rot) > 1e-6)
                    ElementTransformUtils.RotateElement(doc, fi.Id, Line.CreateBound(P(o["pt"]), P(o["pt"]) + XYZ.BasisZ), rot * Math.PI / 180);
                SetStructMaterial(c, fi, S(o, "material"));
                SetMark(fi, S(o, "mark"));
                c.Add("column", fi.Id);
            }
        }

        // ---------------------------------------------------------------- dầm: beams [{mark, b, h, p0, p1, level, offset, material}]
        //   p0, p1: tim dầm (mm); đỉnh dầm = cao độ level + offset (mặc định 0 = mặt sàn kết cấu)
        static void Beams(Ctx2 c, JsonObject spec, Family fam)
        {
            if (!(spec["beams"] is JsonArray arr) || arr.Count == 0) return;
            Document doc = c.Doc;
            var cache = new Dictionary<string, FamilySymbol>();
            foreach (JsonNode n in arr)
            {
                var o = n.AsObject();
                double b = N(o, "b", 220), h = N(o, "h", 400);
                FamilySymbol sym = SectionType(c, fam, "Dam", b, h, cache);
                Level lv = Lv(c, o);
                Line ln = Line.CreateBound(P(o["p0"], lv.Elevation), P(o["p1"], lv.Elevation));
                FamilyInstance fi = doc.Create.NewFamilyInstance(ln, sym, lv, StructuralType.Beam);
                fi.get_Parameter(BuiltInParameter.Z_JUSTIFICATION)?.Set((int)ZJustification.Top);
                fi.get_Parameter(BuiltInParameter.Y_JUSTIFICATION)?.Set((int)YJustification.Center);
                double off = N(o, "offset", 0) / FT;
                fi.get_Parameter(BuiltInParameter.STRUCTURAL_BEAM_END0_ELEVATION)?.Set(off);
                fi.get_Parameter(BuiltInParameter.STRUCTURAL_BEAM_END1_ELEVATION)?.Set(off);
                SetStructMaterial(c, fi, S(o, "material"));
                SetMark(fi, S(o, "mark"));
                c.Add("beam", fi.Id);
            }
        }

        // ---------------------------------------------------------------- sàn: floors [{type_name, thickness, material, level,
        //                                                                   offset, loops [[pt..] (vòng ngoài), [pt..] (lỗ)...], mark}]
        static void StructFloors(Ctx2 c, JsonObject spec)
        {
            if (!(spec["floors"] is JsonArray arr)) return;
            foreach (JsonNode n in arr)
            {
                var o = n.AsObject();
                double th = N(o, "thickness", 150);
                FloorType ft = FloorTypeNamed(c, S(o, "type_name", $"Archivina_San BTCT {Math.Round(th)}"), th, S(o, "material"));
                c.Add("floor_type", ft.Id);
                Level lv = Lv(c, o);
                var loops = new List<CurveLoop>();
                foreach (JsonNode ln in o["loops"] as JsonArray ?? new JsonArray())
                {
                    var pts = (ln as JsonArray).Select(q => P(q, lv.Elevation)).ToList();
                    var loop = new CurveLoop();
                    for (int i = 0; i < pts.Count; i++) loop.Append(Line.CreateBound(pts[i], pts[(i + 1) % pts.Count]));
                    loops.Add(loop);
                }
                if (loops.Count == 0) throw new Exception("Sàn thiếu loops.");
                Floor f = Floor.Create(c.Doc, loops, ft.Id, lv.Id, true, null, 0.0);
                f.get_Parameter(BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM)?.Set(N(o, "offset", 0) / FT);
                SetMark(f, S(o, "mark"));
                c.Add("floor", f.Id);
            }
        }

        static void View3DKc(Ctx2 c, string name)
        {
            Document doc = c.Doc;
            ViewFamilyType vft = new FilteredElementCollector(doc).OfClass(typeof(ViewFamilyType)).Cast<ViewFamilyType>()
                .First(x => x.ViewFamily == ViewFamily.ThreeDimensional);
            View3D v = View3D.CreateIsometric(doc, vft.Id);
            string nm = string.IsNullOrEmpty(name) ? "Archivina_3D KC" : name;
            string un = nm;
            for (int i = 2; new FilteredElementCollector(doc).OfClass(typeof(View)).Cast<View>().Any(x => x.Name == un); i++) un = nm + " " + i;
            v.Name = un;
            try { v.DetailLevel = ViewDetailLevel.Fine; } catch { }
            try { v.DisplayStyle = DisplayStyle.ShadingWithEdges; } catch { }
            c.Add("view", v.Id);
        }

        // ================================================================ FAMILY: tìm / nạp / tự tạo
        delegate void FamilyBuilder(Document famDoc);

        class LoadOpts : IFamilyLoadOptions
        {
            public bool OnFamilyFound(bool familyInUse, out bool overwriteParameterValues) { overwriteParameterValues = false; return false; }
            public bool OnSharedFamilyFound(Family sharedFamily, bool familyInUse, out FamilySource source, out bool overwriteParameterValues)
            { source = FamilySource.Family; overwriteParameterValues = false; return false; }
        }

        static Family EnsureFamily(Application app, Ctx2 c, JsonObject spec, string famName, string rft, BuiltInCategory cat, FamilyBuilder build)
        {
            Document doc = c.Doc;
            Family fam = new FilteredElementCollector(doc).OfClass(typeof(Family)).Cast<Family>().FirstOrDefault(f => f.Name == famName);
            if (fam != null) return fam;

            string libDir = S(spec, "family_dir");
            string rfa = string.IsNullOrEmpty(libDir) ? null : Path.Combine(libDir, famName + ".rfa");
            if (rfa != null && File.Exists(rfa))
            {
                using (var t = new Transaction(doc, "Claude MCP - nạp family " + famName))
                {
                    t.Start();
                    if (!doc.LoadFamily(rfa, new LoadOpts(), out fam) || fam == null) throw new Exception($"Không nạp được '{rfa}'.");
                    t.Commit();
                }
                c.Log.Add($"Nạp family từ thư viện: {rfa}");
                c.Add("family", fam.Id);
                return fam;
            }

            string tpl = FindRft(app, spec, rft) ?? throw new Exception(
                $"Không tìm thấy template family '{rft}'. Truyền family_template_dir (thư mục chứa {rft}).");
            Document famDoc = app.NewFamilyDocument(tpl);
            try
            {
                if (famDoc.OwnerFamily.FamilyCategory?.Id.Value != (long)cat)
                    throw new Exception($"Template '{tpl}' không thuộc category {cat}.");
                using (var t = new Transaction(famDoc, "Archivina - dựng family"))
                {
                    var warn = new JsonArray();
                    FailureHandlingOptions fo = t.GetFailureHandlingOptions();
                    fo.SetFailuresPreprocessor(new LogWarnings(warn));
                    t.SetFailureHandlingOptions(fo);
                    t.Start();
                    try { famDoc.OwnerFamily.get_Parameter(BuiltInParameter.FAMILY_STRUCT_MATERIAL_TYPE)?.Set((int)StructuralMaterialType.Concrete); } catch { }
                    build(famDoc);
                    if (t.Commit() != TransactionStatus.Committed) throw new Exception("Family không commit được.");
                    foreach (var w in warn) c.Warn.Add($"Family {famName}: {w}");
                }
                if (rfa != null)
                {
                    Directory.CreateDirectory(libDir);
                    famDoc.SaveAs(rfa, new SaveAsOptions { OverwriteExistingFile = false, MaximumBackups = 1 });
                    c.Log.Add($"Tạo family {famName} từ '{tpl}', lưu thư viện: {rfa}");
                }
                else c.Log.Add($"Tạo family {famName} từ '{tpl}' (không lưu thư viện)");
                fam = famDoc.LoadFamily(doc, new LoadOpts());
            }
            finally { famDoc.Close(false); }
            if (fam == null) throw new Exception($"Không nạp được family {famName} vào dự án.");
            using (var t = new Transaction(doc, "Claude MCP - đổi tên family"))
            {
                t.Start();
                if (fam.Name != famName) try { fam.Name = famName; } catch { }
                t.Commit();
            }
            c.Add("family", fam.Id);
            return fam;
        }

        static string FindRft(Application app, JsonObject spec, string rft)
        {
            var dirs = new List<string>();
            if (S(spec, "family_template_dir") is string d0) dirs.Add(d0);
            try { dirs.Add(app.FamilyTemplatePath); } catch { }
            string pd = Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData);
            foreach (string sub in new[] { @"Autodesk\RVT 2026\Family Templates\English", @"Autodesk\RVT 2026\Family Templates\English_I",
                                           @"Autodesk\Revit Steel Connections 2026\en-US\Family Templates\English Metric",
                                           @"Autodesk\Revit Steel Connections 2026\en-UK\Family Templates" })
                dirs.Add(Path.Combine(pd, sub));
            foreach (string d in dirs.Where(x => !string.IsNullOrEmpty(x) && Directory.Exists(x)))
            {
                string f = Path.Combine(d, rft);
                if (File.Exists(f)) return f;
                try
                {
                    string hit = Directory.EnumerateFiles(d, rft, SearchOption.AllDirectories).FirstOrDefault();
                    if (hit != null) return hit;
                }
                catch { }
            }
            return null;
        }

        // ---------------------------------------------------------------- tiện ích dựng family
        static FamilyParameter LenParam(FamilyManager fm, string name)
            => fm.get_Parameter(name) ?? fm.AddParameter(name, GroupTypeId.Geometry, SpecTypeId.Length, false);

        static ReferencePlane RefPlane(Document fd, View v, XYZ a, XYZ b, XYZ cut, string name)
        {
            ReferencePlane rp = fd.FamilyCreate.NewReferencePlane(a, b, cut, v);
            rp.Name = name;
            return rp;
        }

        // kích thước gắn nhãn tham số (+ EQ quanh tâm nếu có)
        static void LabelDim(Document fd, View v, Line line, ReferencePlane r0, ReferencePlane r1, FamilyParameter prm, ReferencePlane center)
        {
            var ra = new ReferenceArray();
            ra.Append(r0.GetReference());
            ra.Append(r1.GetReference());
            Dimension dim = fd.FamilyCreate.NewLinearDimension(v, line, ra);
            dim.FamilyLabel = prm;
            if (center == null) return;
            var rq = new ReferenceArray();
            rq.Append(r0.GetReference());
            rq.Append(center.GetReference());
            rq.Append(r1.GetReference());
            Dimension eq = fd.FamilyCreate.NewLinearDimension(v, line.CreateOffset(1.0, XYZ.BasisZ) as Line ?? line, rq);
            eq.AreSegmentsEqual = true;
        }

        static IEnumerable<PlanarFace> Faces(Element e)
        {
            var opt = new Options { ComputeReferences = true };
            foreach (GeometryObject go in e.get_Geometry(opt))
                if (go is Solid s)
                    foreach (Face f in s.Faces)
                        if (f is PlanarFace pf) yield return pf;
        }

        static PlanarFace FaceToward(Element e, XYZ normal)
            => Faces(e).FirstOrDefault(f => f.FaceNormal.IsAlmostEqualTo(normal)) ?? throw new Exception("Không tìm thấy mặt khối hướng " + normal);

        static ReferencePlane FindPlane(Document fd, Func<ReferencePlane, bool> pred)
            => new FilteredElementCollector(fd).OfClass(typeof(ReferencePlane)).Cast<ReferencePlane>().FirstOrDefault(pred);

        static void SetMaterialAssoc(Document fd, GenericForm form)
        {
            FamilyManager fm = fd.FamilyManager;
            Parameter mp = form.get_Parameter(BuiltInParameter.MATERIAL_ID_PARAM);
            if (mp == null) return;
            FamilyParameter sm = null;
            try { sm = fm.get_Parameter(BuiltInParameter.STRUCTURAL_MATERIAL_PARAM); } catch { }
            if (sm != null && fm.CanElementParameterBeAssociated(mp))
                try { fm.AssociateElementParameterToFamilyParameter(mp, sm); return; } catch { }
            FamilyParameter own = fm.get_Parameter("Vat lieu KC") ?? fm.AddParameter("Vat lieu KC", GroupTypeId.Materials, SpecTypeId.Reference.Material, true);
            fm.AssociateElementParameterToFamilyParameter(mp, own);
        }

        static void DeleteTemplateSolids(Document fd)
        {
            var ids = new FilteredElementCollector(fd).OfClass(typeof(GenericForm)).ToElementIds();
            if (ids.Count > 0) fd.Delete(ids);
        }

        // ---------------------------------------------------------------- family CỘT: hộp b (X) x h (Y), chân / đỉnh khoá vào
        //                                                                   Lower / Upper Ref. Level, 4 mặt khoá vào reference plane
        static void BuildColumnFamily(Document fd)
        {
            FamilyManager fm = fd.FamilyManager;
            if (fm.CurrentType == null) fm.NewType("Cot 400x400");
            FamilyParameter pb = LenParam(fm, "b"), ph = LenParam(fm, "h");
            double b = 400 / FT, h = 400 / FT;
            fm.Set(pb, b);
            fm.Set(ph, h);
            DeleteTemplateSolids(fd);

            var levels = new FilteredElementCollector(fd).OfClass(typeof(Level)).Cast<Level>().OrderBy(l => l.Elevation).ToList();
            if (levels.Count < 2) throw new Exception("Template cột không có Lower / Upper Ref. Level.");
            Level lo = levels.First(), up = levels.Last();
            ViewPlan plan = new FilteredElementCollector(fd).OfClass(typeof(ViewPlan)).Cast<ViewPlan>()
                .FirstOrDefault(v => !v.IsTemplate && v.GenLevel?.Id == lo.Id)
                ?? new FilteredElementCollector(fd).OfClass(typeof(ViewPlan)).Cast<ViewPlan>().First(v => !v.IsTemplate);
            View elev = new FilteredElementCollector(fd).OfClass(typeof(View)).Cast<View>()
                .First(v => !v.IsTemplate && v.ViewType == ViewType.Elevation && Math.Abs(v.ViewDirection.Z) < 1e-6
                            && Math.Abs(v.ViewDirection.Y) > 0.9);

            double z = lo.Elevation, big = 2.0;
            ReferencePlane cLR = FindPlane(fd, r => r.Normal.IsAlmostEqualTo(XYZ.BasisX, 1e-6) || r.Normal.IsAlmostEqualTo(-XYZ.BasisX, 1e-6)
                                                    ? Math.Abs(r.BubbleEnd.X) < 1e-6 : false);
            ReferencePlane cFB = FindPlane(fd, r => r.Normal.IsAlmostEqualTo(XYZ.BasisY, 1e-6) || r.Normal.IsAlmostEqualTo(-XYZ.BasisY, 1e-6)
                                                    ? Math.Abs(r.BubbleEnd.Y) < 1e-6 : false);
            ReferencePlane rL = RefPlane(fd, plan, new XYZ(-b / 2, -big, z), new XYZ(-b / 2, big, z), XYZ.BasisZ, "Archivina_Trai");
            ReferencePlane rR = RefPlane(fd, plan, new XYZ(b / 2, -big, z), new XYZ(b / 2, big, z), XYZ.BasisZ, "Archivina_Phai");
            ReferencePlane rF = RefPlane(fd, plan, new XYZ(-big, -h / 2, z), new XYZ(big, -h / 2, z), XYZ.BasisZ, "Archivina_Truoc");
            ReferencePlane rB = RefPlane(fd, plan, new XYZ(-big, h / 2, z), new XYZ(big, h / 2, z), XYZ.BasisZ, "Archivina_Sau");
            fd.Regenerate();
            LabelDim(fd, plan, Line.CreateBound(new XYZ(-b, h, z), new XYZ(b, h, z)), rL, rR, pb, cLR);
            LabelDim(fd, plan, Line.CreateBound(new XYZ(b, -h, z), new XYZ(b, h, z)), rF, rB, ph, cFB);

            var prof = new CurveArray();
            XYZ q0 = new XYZ(-b / 2, -h / 2, z), q1 = new XYZ(b / 2, -h / 2, z), q2 = new XYZ(b / 2, h / 2, z), q3 = new XYZ(-b / 2, h / 2, z);
            prof.Append(Line.CreateBound(q0, q1)); prof.Append(Line.CreateBound(q1, q2));
            prof.Append(Line.CreateBound(q2, q3)); prof.Append(Line.CreateBound(q3, q0));
            var caa = new CurveArrArray(); caa.Append(prof);
            SketchPlane sp = SketchPlane.Create(fd, Plane.CreateByNormalAndOrigin(XYZ.BasisZ, new XYZ(0, 0, z)));
            Extrusion ext = fd.FamilyCreate.NewExtrusion(true, caa, sp, up.Elevation - lo.Elevation);
            fd.Regenerate();

            fd.FamilyCreate.NewAlignment(plan, rL.GetReference(), FaceToward(ext, -XYZ.BasisX).Reference);
            fd.FamilyCreate.NewAlignment(plan, rR.GetReference(), FaceToward(ext, XYZ.BasisX).Reference);
            fd.FamilyCreate.NewAlignment(plan, rF.GetReference(), FaceToward(ext, -XYZ.BasisY).Reference);
            fd.FamilyCreate.NewAlignment(plan, rB.GetReference(), FaceToward(ext, XYZ.BasisY).Reference);
            fd.FamilyCreate.NewAlignment(elev, up.GetPlaneReference(), FaceToward(ext, XYZ.BasisZ).Reference);
            fd.FamilyCreate.NewAlignment(elev, lo.GetPlaneReference(), FaceToward(ext, -XYZ.BasisZ).Reference);
            SetMaterialAssoc(fd, ext);

            // thử co giãn: đổi b, h rồi trả lại (lỗi ràng buộc -> exception ngay khi dựng family)
            fm.Set(pb, 300 / FT); fm.Set(ph, 220 / FT); fd.Regenerate();
            fm.Set(pb, b); fm.Set(ph, h); fd.Regenerate();
        }

        // ---------------------------------------------------------------- family DẦM: tiết diện b (Y) x h (xuống dưới Ref. Level),
        //                                                                   2 đầu khoá vào Member Left / Member Right
        static void BuildBeamFamily(Document fd)
        {
            FamilyManager fm = fd.FamilyManager;
            if (fm.CurrentType == null) fm.NewType("Dam 220x400");
            FamilyParameter pb = LenParam(fm, "b"), ph = LenParam(fm, "h");
            double b = 220 / FT, h = 400 / FT;
            fm.Set(pb, b);
            fm.Set(ph, h);
            DeleteTemplateSolids(fd);

            var xPlanes = new FilteredElementCollector(fd).OfClass(typeof(ReferencePlane)).Cast<ReferencePlane>()
                .Where(r => Math.Abs(Math.Abs(r.Normal.X) - 1) < 1e-6).ToList();
            ReferencePlane mL = xPlanes.FirstOrDefault(r => r.Name.IndexOf("Member Left", StringComparison.OrdinalIgnoreCase) >= 0);
            ReferencePlane mR = xPlanes.FirstOrDefault(r => r.Name.IndexOf("Member Right", StringComparison.OrdinalIgnoreCase) >= 0);
            if (mL == null || mR == null)
            {
                var ord = xPlanes.OrderBy(r => r.BubbleEnd.X).ToList();
                if (ord.Count < 2) throw new Exception("Template dầm không có reference plane Member Left / Member Right.");
                mL = ord.First(); mR = ord.Last();
            }
            double xL = Math.Min(mL.BubbleEnd.X, mR.BubbleEnd.X), xR = Math.Max(mL.BubbleEnd.X, mR.BubbleEnd.X);
            if (mL.BubbleEnd.X > mR.BubbleEnd.X) (mL, mR) = (mR, mL);
            ReferencePlane cFB = FindPlane(fd, r => Math.Abs(Math.Abs(r.Normal.Y) - 1) < 1e-6 && Math.Abs(r.BubbleEnd.Y) < 1e-6);

            ViewPlan plan = new FilteredElementCollector(fd).OfClass(typeof(ViewPlan)).Cast<ViewPlan>().First(v => !v.IsTemplate);
            View side = new FilteredElementCollector(fd).OfClass(typeof(View)).Cast<View>()
                .First(v => !v.IsTemplate && v.ViewType == ViewType.Elevation && Math.Abs(Math.Abs(v.ViewDirection.X) - 1) < 1e-6);
            double z = plan.GenLevel?.Elevation ?? 0, xm = (xL + xR) / 2, big = 2.0;

            ReferencePlane rF = RefPlane(fd, plan, new XYZ(xL, -b / 2, z), new XYZ(xR, -b / 2, z), XYZ.BasisZ, "Archivina_Truoc");
            ReferencePlane rB = RefPlane(fd, plan, new XYZ(xL, b / 2, z), new XYZ(xR, b / 2, z), XYZ.BasisZ, "Archivina_Sau");
            ReferencePlane rT = RefPlane(fd, side, new XYZ(xm, -big, z), new XYZ(xm, big, z), XYZ.BasisX, "Archivina_Dinh");
            ReferencePlane rD = RefPlane(fd, side, new XYZ(xm, -big, z - h), new XYZ(xm, big, z - h), XYZ.BasisX, "Archivina_Day");
            fd.Regenerate();
            LabelDim(fd, plan, Line.CreateBound(new XYZ(xm, -b, z), new XYZ(xm, b, z)), rF, rB, pb, cFB);
            LabelDim(fd, side, Line.CreateBound(new XYZ(xm, b, z - h), new XYZ(xm, b, z)), rD, rT, ph, null);

            var prof = new CurveArray();
            XYZ q0 = new XYZ(xL, -b / 2, z - h), q1 = new XYZ(xL, b / 2, z - h), q2 = new XYZ(xL, b / 2, z), q3 = new XYZ(xL, -b / 2, z);
            prof.Append(Line.CreateBound(q0, q1)); prof.Append(Line.CreateBound(q1, q2));
            prof.Append(Line.CreateBound(q2, q3)); prof.Append(Line.CreateBound(q3, q0));
            var caa = new CurveArrArray(); caa.Append(prof);
            SketchPlane sp = SketchPlane.Create(fd, Plane.CreateByNormalAndOrigin(XYZ.BasisX, new XYZ(xL, 0, 0)));
            Extrusion ext = fd.FamilyCreate.NewExtrusion(true, caa, sp, xR - xL);
            fd.Regenerate();

            fd.FamilyCreate.NewAlignment(plan, mL.GetReference(), FaceToward(ext, -XYZ.BasisX).Reference);
            fd.FamilyCreate.NewAlignment(plan, mR.GetReference(), FaceToward(ext, XYZ.BasisX).Reference);
            fd.FamilyCreate.NewAlignment(plan, rF.GetReference(), FaceToward(ext, -XYZ.BasisY).Reference);
            fd.FamilyCreate.NewAlignment(plan, rB.GetReference(), FaceToward(ext, XYZ.BasisY).Reference);
            fd.FamilyCreate.NewAlignment(side, rT.GetReference(), FaceToward(ext, XYZ.BasisZ).Reference);
            fd.FamilyCreate.NewAlignment(side, rD.GetReference(), FaceToward(ext, -XYZ.BasisZ).Reference);
            SetMaterialAssoc(fd, ext);

            fm.Set(pb, 300 / FT); fm.Set(ph, 600 / FT); fd.Regenerate();
            fm.Set(pb, b); fm.Set(ph, h); fd.Regenerate();
        }
    }
}

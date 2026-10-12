// Archivina Revit MCP – CORE: CHỐT CHẶN DỮ LIỆU GỐC (quy tắc Archivina: không sửa / ghi đè / xoá file gốc).
//
//   1. Lệnh GHI (set_params, build_apartment, draw_2d, create_3d) chỉ chạy khi:
//        (a) người dùng đã bấm "Cho phép ghi" trong Revit, VÀ
//        (b) dự án đang active là BẢN SAO: file do Claude tạo (new_project) hoặc lưu ra (save_copy) – ghi trong sổ
//            %LOCALAPPDATA%\ArchivinaRevitMcp\ban_sao.txt; hoặc nằm trong thư mục làm việc
//            (…\03-Ban-Sao-Lam-Viec\, <WorkRoot>\03-Cong-Cu\05-Skill-Test\, thư mục tạm); hoặc dự án mới chưa lưu.
//        Mọi file khác (02-Ban-Ve-Goc\, @Archivina 2026\, ổ dự án…) -> TỪ CHỐI, yêu cầu save_copy trước.
//   2. save_copy: SaveAs dự án đang mở ra file .rvt MỚI (không ghi đè, không lưu vào 02-Ban-Ve-Goc\). Sau lệnh, Revit
//      làm việc trên bản sao; file gốc trên đĩa giữ nguyên.
//   3. Phần tử do Claude tạo được đánh dấu (Extensible Storage trên Project Information) -> lệnh xoá chỉ xoá được
//      phần tử đã đánh dấu (trừ dự án do Claude tạo bằng new_project).
// WorkRoot mặc định "H:\@AI Claude Test", đổi bằng biến môi trường REVIT_MCP_WORK_ROOT.

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json.Nodes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.DB.ExtensibleStorage;
using Autodesk.Revit.UI;

namespace ArchivinaRevitMcp.Core
{
    internal static class Safety
    {
        static readonly string WorkRoot = Environment.GetEnvironmentVariable("REVIT_MCP_WORK_ROOT") ?? @"H:\@AI Claude Test";
        static readonly string RegistryFile = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ArchivinaRevitMcp", "ban_sao.txt");
        static readonly Guid SchemaGuid = new Guid("8B1E5C2A-3F47-4D9B-A6E1-2C7D9F0B4E35");
        const string OriginalSegment = @"\02-Ban-Ve-Goc\";
        const string CopySegment = @"\03-Ban-Sao-Lam-Viec\";

        // ---------------------------------------------------------------- sổ bản sao
        static string Norm(string p) => string.IsNullOrEmpty(p) ? "" : Path.GetFullPath(p).TrimEnd('\\').ToLowerInvariant();

        static Dictionary<string, string> Registry()
        {
            var d = new Dictionary<string, string>();
            try
            {
                if (File.Exists(RegistryFile))
                    foreach (string line in File.ReadAllLines(RegistryFile))
                    {
                        int i = line.IndexOf('|');
                        if (i > 0) d[Norm(line.Substring(i + 1))] = line.Substring(0, i);
                    }
            }
            catch { }
            return d;
        }

        public static void Register(string kind, string path)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(RegistryFile));
            File.AppendAllLines(RegistryFile, new[] { kind + "|" + Path.GetFullPath(path) });
        }

        static bool Under(string path, string root) =>
            !string.IsNullOrEmpty(root) && Norm(path).StartsWith(Norm(root) + "\\", StringComparison.Ordinal);

        public static bool IsOriginalLocation(string path) =>
            (Path.GetFullPath(path) + "\\").IndexOf(OriginalSegment, StringComparison.OrdinalIgnoreCase) >= 0;

        // trả về (ghi được?, lý do)
        public static (bool ok, string why) WriteStatus(Document doc)
        {
            if (doc == null) return (false, "chưa mở dự án");
            if (doc.IsReadOnly) return (false, "dự án mở chỉ đọc");
            string path = doc.PathName;
            if (string.IsNullOrEmpty(path)) return (true, "dự án mới chưa lưu (không phải file gốc)");
            if (IsOriginalLocation(path)) return (false, "file nằm trong 02-Ban-Ve-Goc (bản vẽ gốc)");
            if (Registry().TryGetValue(Norm(path), out string kind))
                return (true, kind == "new" ? "dự án do Claude tạo (new_project)" : "bản sao do Claude lưu (save_copy)");
            if ((path + "\\").IndexOf(CopySegment, StringComparison.OrdinalIgnoreCase) >= 0) return (true, "nằm trong 03-Ban-Sao-Lam-Viec");
            if (Under(path, Path.Combine(WorkRoot, "03-Cong-Cu", "05-Skill-Test"))) return (true, "nằm trong 05-Skill-Test");
            if (Under(path, Path.GetTempPath())) return (true, "nằm trong thư mục tạm");
            return (false, "không phải bản sao làm việc (có thể là file gốc)");
        }

        public static bool IsClaudeProject(Document doc) =>
            !string.IsNullOrEmpty(doc.PathName) && Registry().TryGetValue(Norm(doc.PathName), out string k) && k == "new";

        public static JsonObject StatusJson(Document doc)
        {
            var (ok, why) = WriteStatus(doc);
            return new JsonObject
            {
                ["la_ban_sao"] = ok,
                ["ly_do"] = why,
                ["du_an_claude_tao"] = doc != null && IsClaudeProject(doc),
            };
        }

        // Chốt chặn chung cho mọi lệnh ghi
        public static void RequireWritableCopy(Document doc)
        {
            if (!Ctx.WriteEnabled)
                throw new Exception("Ghi đang KHOÁ. Người dùng phải bấm tab 'Archivina MCP' > 'Cho phép ghi' trong Revit.");
            if (doc == null) throw new Exception("Revit chưa mở dự án nào.");
            var (ok, why) = WriteStatus(doc);
            if (!ok)
                throw new Exception($"TỪ CHỐI GHI – '{doc.PathName}': {why}. Quy tắc Archivina: không sửa file gốc. " +
                                    "Lưu bản sao trước (rv_luu_ban_sao), rồi thực hiện lại trên bản sao.");
        }

        // ---------------------------------------------------------------- save_copy
        public static JsonNode SaveCopy(UIApplication ui, JsonObject p)
        {
            Document doc = ui.ActiveUIDocument?.Document ?? throw new Exception("Revit chưa mở dự án nào.");
            if (doc.IsFamilyDocument) throw new Exception("Đang mở family, không phải dự án.");
            if (doc.IsWorkshared)
                throw new Exception("Dự án workshared – không SaveAs từ MCP (ảnh hưởng file central). Anh mở bằng 'Detach from Central' rồi lưu bản sao.");
            bool allowUnsaved = p["cho_phep_chua_luu"] != null && (bool)p["cho_phep_chua_luu"];
            if (doc.IsModified && !allowUnsaved)
                throw new Exception("Dự án có thay đổi CHƯA LƯU. Lưu bản sao lúc này sẽ đưa các thay đổi đó sang bản sao, file gốc giữ bản lưu lần cuối. " +
                                    "Người dùng tự quyết: lưu file gốc trước, hoặc gọi lại với cho_phep_chua_luu=true.");
            string src = doc.PathName;
            string path = p["path"]?.ToString();
            if (string.IsNullOrWhiteSpace(path)) path = DefaultCopyPath(src, doc.Title);
            path = Path.GetFullPath(path);
            if (!path.EndsWith(".rvt", StringComparison.OrdinalIgnoreCase)) path += ".rvt";
            if (File.Exists(path)) throw new Exception($"File '{path}' đã tồn tại – không ghi đè, chọn tên khác.");
            if (IsOriginalLocation(path)) throw new Exception("Không lưu bản sao vào thư mục 02-Ban-Ve-Goc (bản vẽ gốc).");
            if (!string.IsNullOrEmpty(src) && Norm(src) == Norm(path)) throw new Exception("Đường dẫn bản sao trùng file gốc.");
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            doc.SaveAs(path, new SaveAsOptions { OverwriteExistingFile = false, MaximumBackups = 1 });
            Register("copy", path);
            return new JsonObject
            {
                ["file_goc"] = string.IsNullOrEmpty(src) ? "(chưa lưu)" : src,
                ["ban_sao"] = path,
                ["dang_mo"] = doc.PathName,
                ["ghi_chu"] = "Revit đang làm việc trên BẢN SAO. File gốc trên đĩa không đổi – muốn quay lại file gốc thì mở lại file đó.",
            };
        }

        static string DefaultCopyPath(string src, string title)
        {
            string stamp = DateTime.Now.ToString("yyyyMMdd_HHmm");
            string name = (string.IsNullOrEmpty(src) ? title : Path.GetFileNameWithoutExtension(src)) + "_BanSao_" + stamp + ".rvt";
            if (!string.IsNullOrEmpty(src))
            {
                int i = src.IndexOf(OriginalSegment, StringComparison.OrdinalIgnoreCase);
                if (i >= 0) return Path.Combine(src.Substring(0, i) + CopySegment.TrimEnd('\\'), name);
            }
            return Path.Combine(WorkRoot, "03-Cong-Cu", "05-Skill-Test", "ban-sao-revit", name);
        }

        // ---------------------------------------------------------------- đánh dấu phần tử do Claude tạo
        static Schema GetSchema()
        {
            Schema s = Schema.Lookup(SchemaGuid);
            if (s != null) return s;
            var b = new SchemaBuilder(SchemaGuid);
            b.SetSchemaName("ArchivinaMcpCreated");
            b.SetReadAccessLevel(AccessLevel.Public);
            b.SetWriteAccessLevel(AccessLevel.Public);
            b.AddSimpleField("ids", typeof(string));
            return b.Finish();
        }

        public static HashSet<long> CreatedIds(Document doc)
        {
            var res = new HashSet<long>();
            try
            {
                Entity ent = doc.ProjectInformation.GetEntity(GetSchema());
                if (ent.IsValid())
                    foreach (string s in (ent.Get<string>("ids") ?? "").Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries))
                        if (long.TryParse(s, out long v)) res.Add(v);
            }
            catch { }
            return res;
        }

        // gọi TRONG transaction đang mở
        public static void MarkCreated(Document doc, IEnumerable<long> ids)
        {
            HashSet<long> all = CreatedIds(doc);
            foreach (long id in ids) all.Add(id);
            all.RemoveWhere(id => doc.GetElement(new ElementId(id)) == null);
            var ent = new Entity(GetSchema());
            ent.Set("ids", string.Join(",", all));
            doc.ProjectInformation.SetEntity(ent);
        }

        // ghi lại id phần tử được thêm vào doc trong lúc chạy lệnh (sự kiện DocumentChanged)
        public sealed class Tracker : IDisposable
        {
            readonly Document _doc;
            public readonly HashSet<long> Added = new HashSet<long>();
            public Tracker(Document doc) { _doc = doc; doc.Application.DocumentChanged += OnChanged; }
            void OnChanged(object s, DocumentChangedEventArgs e)
            {
                if (!e.GetDocument().Equals(_doc)) return;
                foreach (ElementId id in e.GetAddedElementIds()) Added.Add(id.Value);
            }
            public void Dispose() { try { _doc.Application.DocumentChanged -= OnChanged; } catch { } }
        }
    }

    // Cảnh báo Revit trong transaction: xoá khỏi hộp thoại (không chặn lệnh) nhưng GHI LẠI vào kết quả trả về
    internal class LogWarnings : IFailuresPreprocessor
    {
        readonly JsonArray _sink;
        public LogWarnings(JsonArray sink) { _sink = sink; }
        public FailureProcessingResult PreprocessFailures(FailuresAccessor fa)
        {
            foreach (FailureMessageAccessor f in fa.GetFailureMessages())
                if (f.GetSeverity() == FailureSeverity.Warning)
                {
                    string ids = string.Join(",", f.GetFailingElementIds().Select(x => x.Value));
                    _sink?.Add($"Revit: {f.GetDescriptionText()}" + (ids.Length > 0 ? $" (id {ids})" : ""));
                    fa.DeleteWarning(f);
                }
            return FailureProcessingResult.Continue;
        }
    }
}

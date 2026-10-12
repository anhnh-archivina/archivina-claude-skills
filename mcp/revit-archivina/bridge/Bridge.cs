// Archivina Revit MCP Bridge – cầu nối giữa Revit 2026 ĐANG MỞ và MCP server "revit-archivina" (Claude).
//
// Mục đích : mở một cổng TCP CHỈ trên máy này (127.0.0.1) để Claude đọc dự án Revit đang mở (thông tin, link,
//            phần tử, tham số, phòng / vùng diện tích, cảnh báo, bảng thống kê, ảnh view, xuất DWG mm)
//            và – CHỈ KHI người dùng bật – đặt tham số phần tử.
// Nguyên tắc an toàn (quy tắc Archivina):
//   - Mặc định CHỈ ĐỌC. Ghi bị khoá tới khi người dùng bấm tab "Archivina MCP" > "Cho phép ghi".
//     Mỗi lần mở Revit lại về chế độ chỉ đọc.
//   - Mọi thao tác ghi nằm trong 1 Transaction "Claude MCP …" -> Ctrl+Z hoàn tác được; lỗi thì RollBack.
//   - Không Save / ghi đè file đang mở. Lệnh ghi chỉ chạy trên BẢN SAO (core\Safety.cs) – file gốc bị từ chối.
//     Xuất ảnh / DWG từ chối nếu thư mục đích đã có file.
//   - Lệnh chạy trên luồng API của Revit qua ExternalEvent: Revit đang mở hộp thoại / đang chạy lệnh thì chờ.
// Giao thức: mỗi yêu cầu 1 dòng JSON {"cmd": "...", "params": {...}} kết thúc "\n";
//            trả 1 dòng JSON {"ok": true, "result": ...} hoặc {"ok": false, "error": "..."}.
// Đơn vị  : toạ độ / chiều dài vào-ra MILLIMET, diện tích m², thể tích m³ (Revit lưu nội bộ bằng feet).
// Cấu trúc: file này là LOADER (ribbon, server, ExternalEvent) – đổi phải khởi động lại Revit.
//            Các lệnh nằm ở ..\core\Commands.cs -> addin\core\ArchivinaRevitMcp.Core.dll, loader nạp nóng
//            (AssemblyLoadContext riêng, đọc từ bytes – không khoá file) mỗi khi file đổi: build lại core không cần tắt Revit.
// Cài đặt : ..\build.ps1 (biên dịch + ghi file .addin), rồi khởi động lại Revit (chỉ lần đầu / khi đổi loader).

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.Loader;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization.Metadata;
using System.Threading;
using System.Threading.Tasks;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.UI;

namespace ArchivinaRevitMcp
{
    // ------------------------------------------------------------------------------------------ ứng dụng / ribbon
    public class App : IExternalApplication
    {
        public const string Version = "1.0.2";
        public const string Tab = "Archivina MCP";
        public static int Port = 9878;
        // Revit 2026 có thể nạp lớp nút ribbon (IExternalCommand) vào ngữ cảnh assembly KHÁC với IExternalApplication
        // -> biến static không dùng chung. Trạng thái để ở AppDomain (chung toàn tiến trình), nút gọi server qua delegate.
        const string KeyWrite = "ArchivinaMcp.WriteEnabled", KeyStatus = "ArchivinaMcp.Status", KeyToggleServer = "ArchivinaMcp.ToggleServer";
        public static bool WriteEnabled
        {
            get => AppDomain.CurrentDomain.GetData(KeyWrite) is bool b && b;
            set => AppDomain.CurrentDomain.SetData(KeyWrite, value);
        }
        internal static string SharedStatus() =>
            AppDomain.CurrentDomain.GetData(KeyStatus) is Func<string> f ? f() : StatusText();
        internal static void SharedToggleServer()
        {
            if (AppDomain.CurrentDomain.GetData(KeyToggleServer) is Action a) a();
            else throw new Exception("Không tìm thấy server của add-in (chưa khởi động?).");
        }
        internal static Server Server;
        internal static ExternalEvent Event;
        internal static string LastError;

        public Result OnStartup(UIControlledApplication app)
        {
            if (int.TryParse(Environment.GetEnvironmentVariable("REVIT_MCP_PORT"), out int p) && p > 0) Port = p;
            Event = ExternalEvent.Create(new RequestHandler());
            Server = new Server(Port);
            WriteEnabled = false; // mỗi lần mở Revit về chỉ đọc
            AppDomain.CurrentDomain.SetData(KeyStatus, (Func<string>)StatusText);
            AppDomain.CurrentDomain.SetData(KeyToggleServer, (Action)(() =>
            {
                try
                {
                    if (Server.Running) Server.Stop(); else Server.Start();
                    LastError = null;
                }
                catch (Exception ex) { LastError = ex.Message; }
            }));
            try { Server.Start(); } catch (Exception ex) { LastError = ex.Message; }

            try { app.CreateRibbonTab(Tab); } catch { }
            RibbonPanel panel = app.CreateRibbonPanel(Tab, "Claude");
            string asm = typeof(App).Assembly.Location;
            panel.AddItem(new PushButtonData("amcp_status", "Trạng thái", asm, typeof(CmdStatus).FullName)
                { ToolTip = "Trạng thái cầu Claude MCP (cổng, chế độ ghi)" });
            panel.AddItem(new PushButtonData("amcp_write", "Cho phép ghi\n(bật / tắt)", asm, typeof(CmdToggleWrite).FullName)
                { ToolTip = "Cho phép Claude GHI vào dự án đang mở: đặt tham số, dựng tường / cửa / sàn / phòng, vẽ 2D, tạo view 3D, xoá / lật phần tử do Claude dựng. "
                          + "Chỉ chạy trên BẢN SAO (file gốc bị từ chối – lưu bản sao trước). Mỗi lệnh là 1 Transaction, Ctrl+Z hoàn tác." });
            panel.AddItem(new PushButtonData("amcp_server", "Server\n(bật / tắt)", asm, typeof(CmdToggleServer).FullName)
                { ToolTip = "Bật / tắt cổng 127.0.0.1 cho Claude" });
            return Result.Succeeded;
        }

        public Result OnShutdown(UIControlledApplication app)
        {
            try { Server?.Stop(); } catch { }
            try { Event?.Dispose(); } catch { }
            return Result.Succeeded;
        }

        internal static string StatusText()
        {
            var sb = new StringBuilder();
            sb.AppendLine($"Archivina Revit MCP {Version}");
            sb.AppendLine($"Server: {(Server != null && Server.Running ? $"ĐANG CHẠY – 127.0.0.1:{Port}" : "TẮT")}");
            sb.AppendLine($"Core: {CoreLoader.LoadedVersion ?? "(chưa nạp – nạp ở lệnh đầu tiên)"}");
            sb.AppendLine($"Chế độ: {(WriteEnabled ? "CHO PHÉP GHI (chỉ trên bản sao)" : "CHỈ ĐỌC")}");
            if (!string.IsNullOrEmpty(LastError)) sb.AppendLine($"Lỗi gần nhất: {LastError}");
            return sb.ToString();
        }
    }

    [Transaction(TransactionMode.ReadOnly)]
    public class CmdStatus : IExternalCommand
    {
        public Result Execute(ExternalCommandData d, ref string message, ElementSet elements)
        {
            TaskDialog.Show("Archivina MCP", App.SharedStatus());
            return Result.Succeeded;
        }
    }

    [Transaction(TransactionMode.ReadOnly)]
    public class CmdToggleWrite : IExternalCommand
    {
        public Result Execute(ExternalCommandData d, ref string message, ElementSet elements)
        {
            App.WriteEnabled = !App.WriteEnabled;
            TaskDialog.Show("Archivina MCP", App.WriteEnabled
                ? "Đã CHO PHÉP Claude GHI: đặt tham số, dựng mô hình (tường, cửa, sàn, phòng), vẽ 2D, tạo view 3D, xoá / lật phần tử do Claude dựng.\n"
                  + "Chỉ chạy trên BẢN SAO – file gốc bị từ chối. Mỗi lệnh là 1 Transaction \"Claude MCP\" – Ctrl+Z hoàn tác.\nBấm lại để khoá."
                : "Đã KHOÁ ghi – Claude chỉ đọc.");
            return Result.Succeeded;
        }
    }

    [Transaction(TransactionMode.ReadOnly)]
    public class CmdToggleServer : IExternalCommand
    {
        public Result Execute(ExternalCommandData d, ref string message, ElementSet elements)
        {
            try { App.SharedToggleServer(); }
            catch (Exception ex) { App.LastError = ex.Message; }
            TaskDialog.Show("Archivina MCP", App.SharedStatus());
            return Result.Succeeded;
        }
    }

    // ------------------------------------------------------------------------------------------ server TCP
    internal class Pending
    {
        public string Line;
        public int State; // 0 chờ, 1 đang chạy / xong, 2 huỷ (client hết giờ chờ)
        public readonly TaskCompletionSource<string> Tcs = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
    }

    internal class Server
    {
        public static readonly ConcurrentQueue<Pending> Queue = new ConcurrentQueue<Pending>();
        private readonly int _port;
        private TcpListener _listener;
        private volatile bool _running;
        public bool Running => _running;

        public Server(int port) { _port = port; }

        public void Start()
        {
            if (_running) return;
            _listener = new TcpListener(IPAddress.Loopback, _port);
            _listener.Start();
            _running = true;
            new Thread(Loop) { IsBackground = true, Name = "ArchivinaRevitMcp" }.Start();
        }

        public void Stop()
        {
            _running = false;
            try { _listener?.Stop(); } catch { }
        }

        private void Loop()
        {
            while (_running)
            {
                TcpClient c;
                try { c = _listener.AcceptTcpClient(); }
                catch { break; }
                ThreadPool.QueueUserWorkItem(_ => Serve(c));
            }
        }

        private static void Serve(TcpClient c)
        {
            using (c)
            {
                try
                {
                    c.ReceiveTimeout = 15000;
                    NetworkStream ns = c.GetStream();
                    var reader = new StreamReader(ns, new UTF8Encoding(false));
                    string line = reader.ReadLine();
                    if (string.IsNullOrWhiteSpace(line)) return;
                    string resp;
                    try
                    {
                        JsonObject req = JsonNode.Parse(line).AsObject();
                        double waitS = 60;
                        if (req["params"] is JsonObject po && po["wait_s"] != null) waitS = (double)po["wait_s"];
                        var pend = new Pending { Line = line };
                        Queue.Enqueue(pend);
                        App.Event.Raise();
                        // chờ Revit nhận lệnh; quá giờ mà lệnh chưa chạy -> huỷ (không để lệnh chạy muộn sau khi client bỏ đi)
                        if (!pend.Tcs.Task.Wait(TimeSpan.FromSeconds(waitS))
                            && Interlocked.CompareExchange(ref pend.State, 2, 0) == 0)
                            resp = Json.Err("Revit đang bận (hộp thoại / lệnh đang chạy / đang ở chế độ sửa) – lệnh đã huỷ, chưa chạy. Đóng hộp thoại, bấm Esc rồi thử lại.");
                        else
                        {
                            pend.Tcs.Task.Wait(TimeSpan.FromMinutes(30));
                            resp = pend.Tcs.Task.IsCompleted ? pend.Tcs.Task.Result : Json.Err("Lệnh chạy quá 30 phút.");
                        }
                    }
                    catch (Exception ex) { resp = Json.Err("Yêu cầu không hợp lệ: " + ex.Message); }
                    byte[] bytes = Encoding.UTF8.GetBytes(resp + "\n");
                    ns.Write(bytes, 0, bytes.Length);
                    ns.Flush();
                }
                catch { }
            }
        }
    }

    internal class RequestHandler : IExternalEventHandler
    {
        public string GetName() => "Archivina MCP";

        public void Execute(UIApplication ui)
        {
            while (Server.Queue.TryDequeue(out Pending p))
            {
                if (Interlocked.CompareExchange(ref p.State, 1, 0) != 0) continue; // đã huỷ
                string resp;
                try
                {
                    resp = CoreLoader.Run(ui, p.Line);
                }
                catch (Exception ex)
                {
                    resp = Json.Err(ex.Message);
                }
                p.Tcs.TrySetResult(resp);
            }
        }
    }

    internal static class Json
    {
        // Revit tắt serializer phản chiếu mặc định -> phải chỉ định TypeInfoResolver
        public static readonly JsonSerializerOptions Opts = new JsonSerializerOptions
            { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping, TypeInfoResolver = new DefaultJsonTypeInfoResolver() };

        public static string Err(string msg) =>
            new JsonObject { ["ok"] = false, ["error"] = msg }.ToJsonString(Opts);
    }

    // Nạp nóng core: mỗi lần file DLL đổi thì nạp vào AssemblyLoadContext mới (collectible), bỏ context cũ
    internal static class CoreLoader
    {
        private static DateTime _stamp;
        private static MethodInfo _run;
        private static AssemblyLoadContext _alc;
        public static string LoadedVersion;

        private static string CorePath =>
            Path.Combine(Path.GetDirectoryName(typeof(App).Assembly.Location), "core", "ArchivinaRevitMcp.Core.dll");

        public static string Run(UIApplication ui, string line)
        {
            string path = CorePath;
            if (!File.Exists(path)) throw new Exception("Thiếu core: " + path + " – chạy build.ps1.");
            DateTime t = File.GetLastWriteTimeUtc(path);
            if (_run == null || t != _stamp)
            {
                AssemblyLoadContext old = _alc;
                var alc = new AssemblyLoadContext("ArchivinaMcpCore_" + t.Ticks, isCollectible: true);
                Assembly asm;
                using (var ms = new MemoryStream(File.ReadAllBytes(path))) asm = alc.LoadFromStream(ms);
                _run = asm.GetType("ArchivinaRevitMcp.Core.Entry", true).GetMethod("Run");
                _alc = alc;
                _stamp = t;
                LoadedVersion = asm.GetName().Version + " (" + t.ToLocalTime().ToString("dd/MM HH:mm:ss") + ")";
                try { old?.Unload(); } catch { }
            }
            return (string)_run.Invoke(null, new object[] { ui, line, App.WriteEnabled, App.Version, App.Port });
        }
    }
}

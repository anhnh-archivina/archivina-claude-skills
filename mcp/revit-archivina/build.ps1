# build.ps1 – Biên dịch add-in ArchivinaRevitMcp (Revit 2026) và ghi file .addin cho Revit.
# Cách dùng :
#   powershell -ExecutionPolicy Bypass -File build.ps1            # chỉ CORE (các lệnh) – Revit đang mở vẫn build được, lệnh sau tự nạp bản mới
#   powershell -ExecutionPolicy Bypass -File build.ps1 -Loader    # cả LOADER (ribbon / server) – ĐÓNG Revit trước (DLL bị khoá)
# Kết quả   : addin\ArchivinaRevitMcp.dll, addin\core\ArchivinaRevitMcp.Core.dll,
#             %APPDATA%\Autodesk\Revit\Addins\2026\ArchivinaRevitMcp.addin
param(
    [switch]$Loader,
    [string]$RevitDir = "D:\Revit\Revit 2026",
    [string]$Dotnet = "$env:LOCALAPPDATA\Microsoft\dotnet-sdk\dotnet.exe"
)
$ErrorActionPreference = "Stop"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = 1
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = Join-Path $root "addin"
if (-not (Test-Path $Dotnet)) { $Dotnet = "dotnet" }
$dll = Join-Path $out "ArchivinaRevitMcp.dll"

if ($Loader -or -not (Test-Path $dll)) {
    & $Dotnet build (Join-Path $root "bridge\ArchivinaRevitMcp.csproj") -c Release -o $out "-p:RevitDir=$RevitDir" -nologo
    if ($LASTEXITCODE -ne 0) { throw "Biên dịch loader lỗi (Revit đang mở thì DLL bị khoá – đóng Revit rồi chạy lại)." }

    $addinDir = Join-Path $env:APPDATA "Autodesk\Revit\Addins\2026"
    New-Item -ItemType Directory -Force $addinDir | Out-Null
    $manifest = @"
<?xml version="1.0" encoding="utf-8"?>
<RevitAddIns>
  <AddIn Type="Application">
    <Name>Archivina MCP</Name>
    <Assembly>$dll</Assembly>
    <AddInId>6F3C2A51-8D4E-4B7A-9E21-A7C1B0D4E926</AddInId>
    <FullClassName>ArchivinaRevitMcp.App</FullClassName>
    <VendorId>ARCHIVINA</VendorId>
    <VendorDescription>Archivina - cau noi Claude MCP (127.0.0.1)</VendorDescription>
  </AddIn>
</RevitAddIns>
"@
    [IO.File]::WriteAllText((Join-Path $addinDir "ArchivinaRevitMcp.addin"), $manifest, (New-Object Text.UTF8Encoding($false)))
    Write-Host "Loader: $dll  (manifest $addinDir\ArchivinaRevitMcp.addin) -> khoi dong lai Revit de nap."
}

# core: build ra thư mục tạm rồi chép đè 1 file (loader đọc bytes nên file không bị khoá)
$tmp = Join-Path $root "core\bin\out"
& $Dotnet build (Join-Path $root "core\ArchivinaRevitMcp.Core.csproj") -c Release -o $tmp "-p:RevitDir=$RevitDir" -nologo
if ($LASTEXITCODE -ne 0) { throw "Biên dịch core lỗi." }
New-Item -ItemType Directory -Force (Join-Path $out "core") | Out-Null
Copy-Item (Join-Path $tmp "ArchivinaRevitMcp.Core.dll") (Join-Path $out "core\ArchivinaRevitMcp.Core.dll") -Force
Write-Host "Core: $out\core\ArchivinaRevitMcp.Core.dll (Revit tu nap ban moi o lenh ke tiep)"

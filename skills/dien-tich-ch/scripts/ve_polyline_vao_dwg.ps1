<#
.SYNOPSIS
    Ve polyline phong + nhan m2 vao BAN SAO cua DWG bang AutoCAD Core Console (chay ngam).
    Khong dong vao file goc, khong dong vao cac ban ve dang mo trong AutoCAD cua nguoi dung.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File ve_polyline_vao_dwg.ps1 -Dwg "H:\...\a.dwg" -Scr ".\ve_polyline_phong.scr" -OutDwg "H:\...\03-Ban-Sao-Lam-Viec\a_polyline_phong.dwg"
#>
param(
    [Parameter(Mandatory = $true)][string]$Dwg,
    [Parameter(Mandatory = $true)][string]$Scr,
    [Parameter(Mandatory = $true)][string]$OutDwg,
    [int]$TimeoutSec = 180
)
$ErrorActionPreference = 'Stop'

$acc = Get-ChildItem 'C:\Program Files\Autodesk\AutoCAD *\accoreconsole.exe' -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
if (-not $acc) { throw 'Khong tim thay accoreconsole.exe (AutoCAD Core Console).' }
if (-not (Test-Path -LiteralPath $Dwg)) { throw "Khong thay file: $Dwg" }
if (-not (Test-Path -LiteralPath $Scr)) { throw "Khong thay file script: $Scr" }
if ((Resolve-Path -LiteralPath $Dwg).Path -eq (Join-Path (Resolve-Path (Split-Path $OutDwg -Parent)).Path (Split-Path $OutDwg -Leaf))) {
    throw 'OutDwg trung voi file goc: khong duoc ghi de ban ve goc.'
}
if (Test-Path -LiteralPath $OutDwg) { throw "Da ton tai, khong ghi de: $OutDwg" }

$work = Join-Path $env:TEMP ('dwgdraw_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $work | Out-Null
try {
    Copy-Item -LiteralPath $Dwg -Destination (Join-Path $work 'src.dwg')
    Copy-Item -LiteralPath $Scr -Destination (Join-Path $work 'run.scr')
    $p = Start-Process -FilePath $acc.FullName -WorkingDirectory $work -WindowStyle Hidden -PassThru `
        -ArgumentList "/i `"$work\src.dwg`" /s `"$work\run.scr`" /l en-US"
    if (-not $p.WaitForExit($TimeoutSec * 1000)) { $p.Kill(); throw "Qua $TimeoutSec giay, da dung AutoCAD Core Console." }
    $src = Join-Path $work 'src.dwg'
    $orig = Get-Item -LiteralPath $Dwg
    $new = Get-Item -LiteralPath $src
    if ($new.LastWriteTime -le $orig.LastWriteTime) { throw 'AutoCAD khong luu duoc ban sao (QSAVE khong chay).' }
    New-Item -ItemType Directory -Force -Path (Split-Path $OutDwg -Parent) | Out-Null
    Move-Item -LiteralPath $src -Destination $OutDwg
    Write-Output $OutDwg
}
finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}

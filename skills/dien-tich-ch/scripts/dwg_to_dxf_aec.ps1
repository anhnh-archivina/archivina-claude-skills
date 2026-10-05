<#
.SYNOPSIS
    Chuyen DWG sang DXF, KEM bien cac doi tuong AutoCAD Architecture (AEC_WALL, AEC_DOOR, AEC_WINDOW...)
    thanh hinh hoc AutoCAD thuong (INSERT chua LINE/LWPOLYLINE/HATCH) tren BAN SAO. Khong dong vao file goc.

.DESCRIPTION
    Vi sao can: DXFOUT thuong cua AutoCAD BO MAT cac doi tuong AEC (tuong/cua/cua so cua ACA), nen ezdxf khong thay
    tuong du ban ve co. Giai phap: tren ban sao, EXPLODE tung doi tuong AEC (mot lan mot doi tuong) roi DXFOUT.
    Sau khi no, tuong thanh INSERT chua LINE layer 'A-Vua trat' (net hoan thien), LINE 'A-Wall' (loi tuong), HATCH;
    cua thanh LWPOLYLINE/ARC 'A-Door'; cua so thanh LINE/LWPOLYLINE 'A-Glaz'.
    Ghi them bao cao <ten>_aec.txt (dem doi tuong AEC truoc va sau khi no) canh file DXF.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File dwg_to_dxf_aec.ps1 -Dwg "H:\...\a.dwg" -OutDir "H:\...\03-Ban-Sao-Lam-Viec"
#>
param(
    [Parameter(Mandatory = $true)][string]$Dwg,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [string]$Loai = 'AEC_WALL,AEC_DOOR,AEC_WINDOW,AEC_OPENING,AEC_CURTAIN*,AEC_*ASSEMBLY',
    [int]$TimeoutSec = 240
)
$ErrorActionPreference = 'Stop'

$acc = Get-ChildItem 'C:\Program Files\Autodesk\AutoCAD *\accoreconsole.exe' -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
if (-not $acc) { throw 'Khong tim thay accoreconsole.exe (AutoCAD Core Console).' }
if (-not (Test-Path -LiteralPath $Dwg)) { throw "Khong thay file: $Dwg" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$work = Join-Path $env:TEMP ('dwg2dxfaec_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $work | Out-Null
try {
    Copy-Item -LiteralPath $Dwg -Destination (Join-Path $work 'src.dwg')
    $fw = $work.Replace('\', '/')
    $lisp = @"
(defun aec-types ( / ss i d lst c)
  (setq ss (ssget "X" '((0 . "AEC_*"))) lst nil i 0)
  (if ss (repeat (sslength ss) (setq d (cdr (assoc 0 (entget (ssname ss i))))) (if (setq c (assoc d lst)) (setq lst (subst (cons d (1+ (cdr c))) c lst)) (setq lst (cons (cons d 1) lst))) (setq i (1+ i))))
  lst)
(defun write-types (fn tag lst / f) (setq f (open fn "a")) (foreach c lst (write-line (strcat tag " " (car c) " " (itoa (cdr c))) f)) (close f))
(defun expl-all ( / ss i n e)
  (setq ss (ssget "X" '((0 . "$Loai"))) i 0 n 0)
  (if ss (repeat (sslength ss) (setq e (ssname ss i)) (if (entget e) (progn (command "_.EXPLODE" e) (setq n (1+ n)))) (setq i (1+ i))))
  n)
(write-types "$fw/aec.txt" "TRUOC" (aec-types))
(setq nn (vl-catch-all-apply 'expl-all))
(write-types "$fw/aec.txt" "SAU" (aec-types))
"@
    $lines = $lisp -split "`r?`n" | Where-Object { $_.Trim() -ne '' }
    $scr = ($lines -join "`r`n") + "`r`nFILEDIA`r`n0`r`n_.DXFOUT`r`n$fw/out.dxf`r`nV`r`n2018`r`n16`r`n_.QUIT`r`n_Y`r`n"
    Set-Content -Path (Join-Path $work 'run.scr') -Value $scr -Encoding ASCII
    $p = Start-Process -FilePath $acc.FullName -WorkingDirectory $work -WindowStyle Hidden -PassThru `
        -ArgumentList "/i `"$work\src.dwg`" /s `"$work\run.scr`" /l en-US"
    if (-not $p.WaitForExit($TimeoutSec * 1000)) { $p.Kill(); throw "Qua $TimeoutSec giay, da dung AutoCAD Core Console." }
    $out = Join-Path $work 'out.dxf'
    if (-not (Test-Path -LiteralPath $out)) { throw 'Khong tao duoc DXF.' }
    $base = [IO.Path]::GetFileNameWithoutExtension($Dwg)
    $dest = Join-Path $OutDir ($base + '.dxf')
    Move-Item -LiteralPath $out -Destination $dest -Force
    $rep = Join-Path $work 'aec.txt'
    if (Test-Path -LiteralPath $rep) { Copy-Item -LiteralPath $rep -Destination (Join-Path $OutDir ($base + '_aec.txt')) -Force }
    Write-Output $dest
}
finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}

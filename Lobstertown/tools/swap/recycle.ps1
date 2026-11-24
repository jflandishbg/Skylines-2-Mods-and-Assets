# Sends every path listed in a plan file to the Recycle Bin (never permanent). Skips any .Texture path.
# usage: powershell -File recycle.ps1 plan.txt      (game must be closed)
param([string]$Plan)
Add-Type -AssemblyName Microsoft.VisualBasic
$L = Get-Content -Encoding utf8 $Plan | Where-Object { $_ -and $_ -notmatch '\.Texture' }
$d=0; $f=0
foreach ($p in $L) {
  if (Test-Path -LiteralPath $p -PathType Container) { [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($p,'OnlyErrorDialogs','SendToRecycleBin'); $d++ }
  elseif (Test-Path -LiteralPath $p) { [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($p,'OnlyErrorDialogs','SendToRecycleBin'); $f++ }
}
"folders $d files $f"

# Install the newspeak skill into the Claude Code user skills folder.
# Usage:  .\install.ps1            (installs to ~\.claude\skills\newspeak)
#         .\install.ps1 -Dest D:\somewhere\newspeak
# Works on Windows PowerShell 5.1 and PowerShell 7.
param(
    [string]$Dest = (Join-Path (Join-Path $HOME ".claude\skills") "newspeak")
)
$ErrorActionPreference = "Stop"
$Src = $PSScriptRoot

$srcFull = (Resolve-Path $Src).Path.TrimEnd('\')
$destFull = [System.IO.Path]::GetFullPath($Dest).TrimEnd('\')

if ($srcFull -ieq $destFull) {
    Write-Host "Already in place: $destFull"
} else {
    if (Test-Path $destFull) {
        # keep the backup outside the skills folder, or Claude Code would load it as a second skill
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $backupRoot = Join-Path (Join-Path $HOME ".claude") "skill-backups"
        New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
        $backup = Join-Path $backupRoot ("newspeak-" + $stamp)
        Move-Item -Path $destFull -Destination $backup
        Write-Host "Moved the previous copy to $backup"
    }
    New-Item -ItemType Directory -Force -Path $destFull | Out-Null
    Get-ChildItem -Path $srcFull -Force |
        Where-Object { $_.Name -ne ".git" -and $_.Name -ne "__pycache__" } |
        ForEach-Object { Copy-Item -Path $_.FullName -Destination $destFull -Recurse -Force }
    Write-Host "Installed to $destFull"
}

$py = $null
foreach ($name in @("python", "python3", "py")) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { $py = $cmd.Source; break }
}
if (-not $py) {
    Write-Warning "Python was not found. Install Python 3.9+ to use lint.py and gate.py."
    exit 0
}
$env:PYTHONIOENCODING = "utf-8"
& $py (Join-Path $destFull "scripts\selftest.py") | Select-Object -Last 1
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Some self-tests failed. Run: $py `"$destFull\scripts\selftest.py`""
    exit 1
}
Write-Host "Done. Restart Claude Code, then type /newspeak or ask Claude to remove the AI tells from a text."

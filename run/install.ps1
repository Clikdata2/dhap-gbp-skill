# One-time install: makes "Run DHAP GBP for ..." work in Claude Code and Codex on this Windows PC.
#   powershell -ExecutionPolicy Bypass -File $HOME\dhap-gbp-skill\run\install.ps1
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$skills = Join-Path $HOME ".claude\skills"; New-Item -ItemType Directory -Force -Path $skills | Out-Null
$target = Join-Path $skills "dhap-gbp-run"
if (Test-Path $target) {
  $item = Get-Item $target -Force
  if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { $item.Delete() }
  else { Rename-Item $target ("dhap-gbp-run.backup-" + (Get-Date -Format yyyyMMddHHmmss)) }
}
New-Item -ItemType Junction -Path $target -Target (Join-Path $repo "run") | Out-Null   # updates itself with every git pull
$codex = Join-Path $HOME ".codex"; New-Item -ItemType Directory -Force -Path $codex | Out-Null
$agents = Join-Path $codex "AGENTS.md"; if (-not (Test-Path $agents)) { New-Item -ItemType File -Path $agents | Out-Null }
$t = Get-Content $agents -Raw; if ($null -eq $t) { $t = "" }
$t = [regex]::Replace($t, "(?s)<!-- >>> DHAP GBP >>> -->.*?<!-- <<< DHAP GBP <<< -->\r?\n?", "")
$t += "<!-- >>> DHAP GBP >>> -->`nWhen the user says ""Run DHAP GBP for ..."", read $repo\run\SKILL.md and follow it exactly (it pulls the latest rules first).`n<!-- <<< DHAP GBP <<< -->`n"
Set-Content -Path $agents -Value $t -NoNewline
Write-Host "Done. In Claude Code or Codex, just type:  Run DHAP GBP for [Dealership] [website]"
Write-Host "(Restart Claude Code and Codex once so they pick it up.)"

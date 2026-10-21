# DHAP key service — set up one employee's Windows PC for Claude Code and Codex. Run once per PC in PowerShell:
#   powershell -ExecutionPolicy Bypass -File service\setup-employee.ps1
# It asks for the service address and the person's team code (shown by the gcloud line the CTO sent them),
# tests the connection, and saves both as Windows user environment variables (read by Claude Code and Codex).
$ErrorActionPreference = "Stop"

$url = (Read-Host "Paste the service address (starts with https://)").Trim().TrimEnd("/")
$sec = Read-Host "Paste your team code (starts with dhap_), then press Enter" -AsSecureString
$code = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)).Trim()

if (-not $url.StartsWith("https://")) { Write-Host "That address should start with https://"; exit 1 }
if (-not $code.StartsWith("dhap_")) { Write-Host "That team code should start with dhap_"; exit 1 }

Write-Host "Testing the connection..."
try {
  $r = Invoke-WebRequest -UseBasicParsing -Uri "$url/lookup?q=Google%20Mountain%20View" -Headers @{ "X-DHAP-Code" = $code } -TimeoutSec 30
  $status = [int]$r.StatusCode
} catch {
  $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
}
if ($status -eq 401) { Write-Host "The service says the team code is wrong. Check it and run this again."; exit 1 }
if ($status -ne 200) { Write-Host "Could not reach the service (got $status). Check the address and your internet, then run this again."; exit 1 }
Write-Host "Connection works."

[Environment]::SetEnvironmentVariable("DHAP_SERVICE_URL", $url, "User")
[Environment]::SetEnvironmentVariable("DHAP_TEAM_CODE", $code, "User")

Write-Host ""
Write-Host "Done. Close every PowerShell, Command Prompt, Claude Code and Codex window and open them again so they pick this up."
Write-Host "To check later, open PowerShell and run:  echo `$env:DHAP_SERVICE_URL"

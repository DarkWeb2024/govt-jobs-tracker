# One-command setup for Windows.
# Installs dependencies, runs the first pipeline pass, and registers the
# 11:40 PM daily task in Windows Task Scheduler.

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

Write-Host "[1/3] Installing Python dependencies..."
python -m pip install -r requirements.txt

Write-Host "[2/3] First run (seeds the database and builds all outputs)..."
python main.py

Write-Host "[3/3] Registering local tasks (6 AM, 12 PM, 6 PM, 10 PM)..."
$python = (Get-Command python).Source
$action = New-ScheduledTaskAction -Execute $python -Argument "`"$here\main.py`"" -WorkingDirectory $here
$triggers = @(
    New-ScheduledTaskTrigger -Daily -At 6:00AM
    New-ScheduledTaskTrigger -Daily -At 12:00PM
    New-ScheduledTaskTrigger -Daily -At 6:00PM
    New-ScheduledTaskTrigger -Daily -At 10:00PM
)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
Register-ScheduledTask -TaskName "GovtJobsTracker" -Action $action -Trigger $triggers `
    -Settings $settings -Description "Government jobs tracker - runs 4x daily" -Force | Out-Null

Write-Host ""
Write-Host "Done. The tracker runs 4x daily locally, and the cloud (GitHub Actions)"
Write-Host "runs the same 4 times independently - so it keeps working with the PC off."
Write-Host "Optional next steps (see docs-src\CONFIGURATION.md):"
Write-Host "  - Create .env with TRACKER_SMTP_USER / TRACKER_SMTP_PASS for email"
Write-Host "  - Set TRACKER_MS_CLIENT_ID then run: python main.py --login-mstodo"
Write-Host "  - WhatsApp: CallMeBot setup, then TRACKER_CALLMEBOT_* vars"

# One-command setup for Windows.
# Installs dependencies, runs the first pipeline pass, and registers the
# 11:40 PM daily task in Windows Task Scheduler.

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

Write-Host "[1/3] Installing Python dependencies..."
python -m pip install -r requirements.txt

Write-Host "[2/3] First run (seeds the database and builds all outputs)..."
python main.py

Write-Host "[3/3] Registering daily task at 23:40..."
$python = (Get-Command python).Source
$action = New-ScheduledTaskAction -Execute $python -Argument "`"$here\main.py`"" -WorkingDirectory $here
$trigger = New-ScheduledTaskTrigger -Daily -At 23:40
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
Register-ScheduledTask -TaskName "GovtJobsTracker" -Action $action -Trigger $trigger `
    -Settings $settings -Description "Daily government jobs tracker run" -Force | Out-Null

Write-Host ""
Write-Host "Done. The tracker runs daily at 11:40 PM (or next boot if the PC was off)."
Write-Host "Optional next steps (see docs-src\CONFIGURATION.md):"
Write-Host "  - Create .env with TRACKER_SMTP_USER / TRACKER_SMTP_PASS for email"
Write-Host "  - Set TRACKER_MS_CLIENT_ID then run: python main.py --login-mstodo"
Write-Host "  - WhatsApp: CallMeBot setup, then TRACKER_CALLMEBOT_* vars"

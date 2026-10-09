# Usage: .\make_zip.ps1 Firstname_Lastname   -> ..\Firstname_Lastname_Immersive_Storytelling_Agent.zip
# Excludes .venv (not portable), .env (secrets), caches and .git.
param([Parameter(Mandatory)][string]$Name)
$stage = Join-Path $env:TEMP "$Name`_Immersive_Storytelling_Agent"
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
robocopy $PSScriptRoot $stage /E /XD .venv .git __pycache__ .pytest_cache /XF .env make_zip.ps1 *.pyc | Out-Null
$zip = Join-Path (Split-Path $PSScriptRoot) "$Name`_Immersive_Storytelling_Agent.zip"
Compress-Archive -Path $stage -DestinationPath $zip -Force
Write-Host "Created $zip"

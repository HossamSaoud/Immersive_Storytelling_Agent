# Usage: .\make_zip.ps1 Firstname_Lastname   -> ..\Firstname_Lastname_Immersive_Storytelling_Agent.zip
# Excludes .venv (not portable), .env (secrets), caches and .git.
param([Parameter(Mandatory)][string]$Name)
$stage = Join-Path $env:TEMP "$Name`_Immersive_Storytelling_Agent"
Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
robocopy $PSScriptRoot $stage /E /XD .venv .git __pycache__ .pytest_cache .gradio /XF .env make_zip.ps1 Story_Runs.zip *.pyc | Out-Null
$zip = Join-Path (Split-Path $PSScriptRoot) "$Name`_Immersive_Storytelling_Agent.zip"
Remove-Item $zip -Force -ErrorAction SilentlyContinue
Add-Type -AssemblyName System.IO.Compression.FileSystem
# Compress-Archive in Windows PowerShell 5.1 writes backslash paths, which unpack wrongly on macOS/Linux; this writes forward slashes.
[IO.Compression.ZipFile]::CreateFromDirectory($stage, $zip, [IO.Compression.CompressionLevel]::Optimal, $true)
Write-Host "Created $zip"

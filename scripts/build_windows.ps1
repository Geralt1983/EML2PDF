param(
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

& $Python -m pip install -e .
& $Python -m pip install pyinstaller

& $Python -m pyinstaller --onefile -n eml2pdf src/eml2pdf/cli.py

Write-Host "Built: dist/eml2pdf.exe"

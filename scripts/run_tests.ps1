param(
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

& $Python -m pip install -e .[dev]
& $Python -m pytest

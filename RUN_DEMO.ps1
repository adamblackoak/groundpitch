$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    py -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not $env:NUTRIENT_API_KEY) {
    Write-Host ""
    Write-Host "NUTRIENT_API_KEY is not set."
    Write-Host "The app will still start; paste the key into the sidebar."
    Write-Host ""
}

& .\.venv\Scripts\python.exe -m streamlit run app.py


for ($i = 1; $i -le 3; $i++) {
    Write-Host "--- RUN $i ---"
    .\venv\Scripts\python.exe -m pytest tests/ -v | Select-String "test_full_end_to_end_launch_scenario"
}


@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3.13 -m venv .venv
    if errorlevel 1 (
        echo Python 3.13 is required. Run py -3.13 --version to check.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -c "import streamlit, pandas" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Installation failed.
        pause
        exit /b 1
    )
)
echo LifeOS: http://127.0.0.1:8501
".venv\Scripts\python.exe" -m streamlit run app.py --server.address=127.0.0.1
if errorlevel 1 pause

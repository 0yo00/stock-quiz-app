@echo off
REM Use ASCII only in BAT to avoid encoding issues on Traditional Chinese Windows
cd /d "%~dp0"

echo ============================================
echo   Stock Quiz App MVP
echo ============================================
echo.

REM Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ first.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/2] Installing dependencies...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo [WARN] pip install failed. Trying user install...
    python -m pip install -r requirements.txt --quiet --user --disable-pip-version-check
)

echo.
echo [2/2] Starting Streamlit on http://localhost:8600
echo.
echo (Browser will open automatically. Press Ctrl+C in this window to stop.)
echo.

REM Use python -m streamlit to avoid PATH issues
python -m streamlit run stock_quiz.py --server.port 8600

pause

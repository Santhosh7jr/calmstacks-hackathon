@echo off
setlocal
cd /d "%~dp0"

if not exist venv (
  echo Creating virtual environment...
  python -m venv venv
)

call venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .

if errorlevel 1 (
  echo.
  echo Installation failed. Check the error above.
  pause
  exit /b 1
)

echo.
echo RecoverAI API is starting on http://127.0.0.1:5001
python run.py

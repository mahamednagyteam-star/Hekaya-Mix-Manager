@echo off
setlocal
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm HekayaMixManager.spec
echo.
echo Build complete: dist\HekayaMixManager.exe
endlocal

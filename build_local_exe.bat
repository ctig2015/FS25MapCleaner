@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found.
  echo Install Python 3 from python.org first, then run this file again.
  pause
  exit /b 1
)

py -m pip install --upgrade pip
py -m pip install pyinstaller

if not exist dist mkdir dist

py -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name FS25MapCleaner ^
  --icon assets\fs25_map_cleaner.ico ^
  fs25_map_cleaner.py

if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Force -Path '.\dist\FS25MapCleaner.exe' -DestinationPath '.\dist\FS25MapCleaner_Portable.zip'"

echo Done. Files are in dist\
pause

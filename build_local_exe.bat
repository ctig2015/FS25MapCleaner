@echo off
setlocal
cd /d "%~dp0"

echo Building FS25 Map Cleaner EXE...
where py >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=py
) else (
    set PY_CMD=python
)

%PY_CMD% -m pip install --upgrade pip
if errorlevel 1 goto :fail

%PY_CMD% -m pip install pyinstaller
if errorlevel 1 goto :fail

%PY_CMD% -m PyInstaller --noconfirm --clean --onefile --windowed --name FS25MapCleaner fs25_map_cleaner.py
if errorlevel 1 goto :fail

echo.
echo Done.
echo EXE location:
echo %cd%\dist\FS25MapCleaner.exe
pause
exit /b 0

:fail
echo.
echo Build failed.
pause
exit /b 1

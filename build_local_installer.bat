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
echo Checking for Inno Setup compiler...
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
) else (
    echo Inno Setup 6 was not found.
    echo Install it with:
    echo winget install --id JRSoftware.InnoSetup -e -s winget -i
    echo Then run this file again.
    goto :done
)

"%ISCC%" "installer\FS25MapCleaner.iss"
if errorlevel 1 goto :fail

echo.
echo Installer created here:
echo %cd%\installer\output\FS25MapCleaner_Setup.exe
pause
exit /b 0

:done
echo.
echo EXE created here:
echo %cd%\dist\FS25MapCleaner.exe
pause
exit /b 0

:fail
echo.
echo Build failed.
pause
exit /b 1

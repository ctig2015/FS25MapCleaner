\
    @echo off
    setlocal
    cd /d "%~dp0"

    if not exist dist\FS25MapCleaner.exe (
      echo dist\FS25MapCleaner.exe not found.
      echo Run build_local_exe.bat first.
      pause
      exit /b 1
    )

    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

    if not exist "%ISCC%" (
      echo Inno Setup not found. Trying winget install...
      winget install --id JRSoftware.InnoSetup -e --source winget --accept-package-agreements --accept-source-agreements --silent
      set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
      if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
    )

    if not exist "%ISCC%" (
      echo Could not find ISCC.exe after install.
      pause
      exit /b 1
    )

    "%ISCC%" "installer\FS25MapCleaner.iss"

    if errorlevel 1 (
      echo Installer build failed.
      pause
      exit /b 1
    )

    echo Done. Installer is in installer\output\
    pause

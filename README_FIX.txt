Replace these files in your repo:
- build_local_exe.bat
- build_local_installer.bat
- installer/FS25MapCleaner.iss

Then:
1. Run build_local_exe.bat to rebuild FS25MapCleaner.exe
2. Run build_local_installer.bat only if you want FS25MapCleaner_Setup.exe

This fix removes the stray leading backslash in the batch files and updates the installer version to 1.0.1.

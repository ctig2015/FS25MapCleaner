# FS25 Map Cleaner v1.1.1

## Download
Download the file below:

**FS25MapCleaner.exe**

## What's fixed
This patch fixes the v1.1.0 layout issue where the final remove section was missing in the new interface.

### Fixed
- restored **Step 4 – Remove Files**
- restored **Remove Map + Unused Dependencies**
- restored the visible **Delete permanently** option
- improved layout so remove controls remain visible on normal window sizes

### Included from v1.1.x
- optional savegame protection scan
- dependency checks against other installed maps and mods
- protection for dependency mods still referenced by selected savegames
- clearer review panel before removing files

## How to use
1. Select your FS25 `mods` folder
2. Add any savegames you want protected
3. Click **Scan Mods**
4. Select the map
5. Click **Analyze Map**
6. Review the result
7. Click **Remove Map + Unused Dependencies**

## Notes
- close Farming Simulator 25 before using the app
- Windows may show a warning because the EXE is not code-signed
- savegame protection depends on detectable XML references

# FS25 Map Cleaner

## Download

[**Download FS25MapCleaner.exe**](https://github.com/ctig2015/FS25MapCleaner/releases/latest/download/FS25MapCleaner.exe)

Portable Windows app for removing a selected Farming Simulator 25 map and only the dependency mods that are no longer used by other installed maps or mods.

## Important
**Close Farming Simulator 25 before using this app.**

## What this app does
FS25 Map Cleaner scans your Farming Simulator 25 `mods` folder, lets you choose a map, reads that map’s dependency mods, and checks whether any other installed maps or mods still need those same files.

The app removes:
- the selected map
- dependency mods that are no longer used by anything else

The app keeps:
- any dependency mods still required by another installed map or mod

## How to use
1. Download `FS25MapCleaner.exe` from the **Releases** section
2. Run the app
3. Select your FS25 `mods` folder
4. Click **Scan**
5. Choose the map you want to remove
6. Click **Analyze selected**
7. Review the results
8. Delete the selected map and unused dependencies

## Testing feedback
Please leave feedback here:
- [Discussions](https://github.com/ctig2015/FS25MapCleaner/discussions)
- [Issues](https://github.com/ctig2015/FS25MapCleaner/issues)

Use **Issues** for bugs, crashes, or wrong delete results.  
Use **Discussions** for general feedback, ideas, and testing results.

## What testers should report
Helpful things to mention:
- map name
- approximate number of mods in the folder
- what the app said it would remove
- whether the result was correct
- whether anything was removed that should have been kept
- whether anything was kept that should have been removed
- screenshots if possible

## Notes
- Windows may show a warning because this app is not code-signed
- Large mod folders may take a few seconds to scan
- This is an early public test release

## Current version
**Version 1.0.1**  
**Build 2026-04-09**
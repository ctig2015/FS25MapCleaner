# FS25 Map Cleaner

## Download
Download the latest Windows build from the **Releases** section.

## What it does
FS25 Map Cleaner scans your Farming Simulator 25 `mods` folder, lets you choose a map, reads that map's dependency mods, and checks whether any other installed maps or mods still need those same files.

The app removes:
- the selected map
- dependency mods that are no longer used by anything else

The app keeps:
- any dependency mods still required by another installed map or mod

## Version info in the app
This update adds build information inside the app:
- window title shows the version
- **About** button shows version and build date
- analysis reports include version/build info

## How to rebuild
1. Copy these updated files into your existing `FS25MapCleaner` project folder
2. Replace the old files
3. Run `build_local_exe.bat`
4. Upload the new `FS25MapCleaner.exe` to a new GitHub release

## Notes
- Users can keep downloading the same filename: `FS25MapCleaner.exe`
- After you rebuild, the EXE will contain the new version/build information

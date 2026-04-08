# Download FS25 Map Cleaner

FS25 Map Cleaner removes a selected map and only the dependency mods that are unique to that map.

## Download
- [Download Installer](https://github.com/YOURNAME/FS25MapCleaner/releases/latest/download/FS25MapCleaner_Setup.exe)
- [Download Portable ZIP](https://github.com/YOURNAME/FS25MapCleaner/releases/latest/download/FS25MapCleaner_Portable.zip)

## Features
- No Python needed
- Normal Windows installer
- Choose install folder/drive
- Optional desktop icon
- Scans other mods first so shared dependencies are not removed

## How it works
The app reads `modDesc.xml` files in your FS25 mods folder, builds the selected map's dependency tree, then checks the rest of your installed mods before deleting anything.

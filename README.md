# FS25 Map Cleaner

FS25 Map Cleaner is a simple Windows app for **Farming Simulator 25** that helps remove a map and its **unused** required mods.

It is made for people who download large maps that may need a lot of extra mods. When you remove a map, the app checks the map's dependency list and then checks your **other installed mods and maps** before deleting anything extra.

## What the app does

When you pick a map and click delete, the app will:

1. scan your FS25 `mods` folder
2. read each mod's `modDesc.xml`
3. build the full dependency tree for the selected map
4. check whether any other installed map or mod still uses those dependencies
5. delete the selected map
6. delete only the extra dependency mods that are **not used anywhere else**
7. keep anything that another installed map or mod still needs

## Example

- You delete **Map A**
- Map A needs `Mod1`, `Mod2`, and `Mod3`
- The app checks all your other installed maps and mods
- If **Map B** still needs `Mod2`, then `Mod2` is kept
- If nobody else needs `Mod1` or `Mod3`, those can be removed too

## What the user sees

- Download `FS25MapCleaner_Setup.exe`
- Double-click it
- Choose where to install it, including another drive or folder if wanted
- Choose whether to create a desktop icon
- Finish setup
- Open the app from the desktop or Start menu
- Pick the FS25 `mods` folder
- Scan, choose a map, analyze it, then remove it

No Python install is needed for the end user.

## Main features

- Simple Windows app
- Installer with install-location picker
- Optional desktop shortcut
- Scans ZIP mods and folder mods
- Shows probable maps first
- Lets the user analyze before deleting
- Deletes only the selected map and dependencies that are not shared
- Keeps shared dependencies used by other installed maps or mods
- Can use permanent delete or quarantine mode

## Safe deletion logic

The app does **not** blindly remove every dependency.

It removes a dependency only when:

- the selected map depends on it, and
- no other installed mod or map depends on it

It keeps a dependency when:

- another installed mod or map still depends on it

Read more here:
- [How the dependency check works](docs/HOW_IT_WORKS.md)
- [Frequently asked questions](docs/FAQ.md)

## Download for normal users

Normal users should download:

- **`FS25MapCleaner_Setup.exe`**

Optional:

- **`FS25MapCleaner_Portable.zip`**

## Repository layout

- `fs25_map_cleaner.py` - main app
- `installer/FS25MapCleaner.iss` - Windows installer script
- `.github/workflows/build-release.yml` - automatic Windows builds on GitHub
- `assets/fs25_map_cleaner.ico` - app icon
- `docs/HOW_IT_WORKS.md` - plain-English explanation of the delete logic
- `docs/FAQ.md` - common user questions
- `CHANGELOG.md` - version history
- `CONTRIBUTING.md` - how to report bugs and suggest changes

## Quick publish on GitHub

1. Create a new GitHub repo named `FS25MapCleaner`
2. Upload everything from this folder
3. Push to `main`
4. Open the **Actions** tab and allow workflows if GitHub asks
5. Create and push a tag such as `v1.1.0`

```bash
git tag v1.1.0
git push origin v1.1.0
```

GitHub Actions will build:

- `FS25MapCleaner.exe`
- `FS25MapCleaner_Portable.zip`
- `FS25MapCleaner_Setup.exe`

Then attach them to the GitHub Release for that tag.

## Suggested GitHub release text

Use this short summary in your releases:

> FS25 Map Cleaner removes a selected map and only the dependency mods that are not used by any other installed map or mod. Shared dependencies are kept automatically.

## Best files to show on your GitHub page

Pin these in the README near the top:

- What the app does
- Screenshot of the app
- Big **Download Installer** link
- Short example of shared dependency checking
- FAQ

## Local Windows build

If you want to build it yourself on Windows:

- `build_local_exe.bat`
- `build_local_installer.bat`

## Notes

The app decides what is shared by checking dependency declarations in installed mods. If a mod author did not declare dependencies correctly, the result can only be as accurate as the installed mod metadata.

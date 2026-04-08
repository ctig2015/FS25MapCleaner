# FS25 Map Cleaner

!!!IMPORT FARMING SIMULATOR NEED TO BE CLOSED WHEN YOU DO THIS!!

FS25 Map Cleaner is a simple Windows app for **Farming Simulator 25** that helps remove a map and its **unused** required mods.

It is made for people who download maps that may need a lot of extra mods. When you remove a map, the app checks the map's dependency list and then checks your **other installed mods and maps** before deleting anything extra.

TEST IT OUT AND LEAVE COMMANTS IN https://github.com/ctig2015/FS25MapCleaner/discussions

SCREENSHOTS i just used this as an example to see at min it only has the map but it show what mods it shoul have once you bro

<img width="1000" height="500" alt="FS25MapCleaner_IymoZ5PGiA" src="https://github.com/user-attachments/assets/a5fd7f18-ef89-4ddf-a90e-bc40f339d9b4" />




## What the app does

When you pick a map and click delete, the app will:

1.  browse to you mod folder as it is not alway default location scan your FS25 `mods` folder
2. read each mod's `modDesc.xml`
3. build the full dependency tree for the selected map
4. check whether any other installed map or mod still uses those dependencies
5. delete the selected map
6. delete only the extra dependency mods that are **not used anywhere else**
7. keep anything that another installed map or mod still needs
8. 

## Example

- You delete **Map A**
- Map A needs `Mod1`, `Mod2`, and `Mod3`
- The app checks all your other installed maps and mods
- If **Map B** still needs `Mod2`, then `Mod2` is kept
- If nobody else needs `Mod1` or `Mod3`, those can be removed too

## What the user sees

- Download `FS25MapCleaner_Setup.exe`
- Double-click it
- will show message on first start up but allow and it will open 
-  browse to the folder where your mods is Scan, choose a map, analyze it, then remove it

No Python install is needed for the end user.

## Main features

- Simple Windows app
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







The app decides what is shared by checking dependency declarations in installed mods. If a mod author did not declare dependencies correctly, the result can only be as accurate as the installed mod metadata.

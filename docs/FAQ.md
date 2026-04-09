# FAQ

## Does the app remove every dependency from the selected map?
No. It removes only the dependencies that are no longer needed by another installed mod, map, or protected savegame.

## What does **Scan Mods** do?
It scans the selected FS25 `mods` folder, reads dependency data, and fills the map/mod list.

## What does **Analyze Map** do?
It checks the selected map's dependency tree and works out what can be removed safely and what must be kept.

## What does **Add Savegame…** do?
It adds a savegame folder to the protection list so the app can check whether dependency mods are still used in that save.

## What does **Remove Selected** in the savegame section do?
It removes the highlighted savegame from the protection list only. It does not delete the savegame itself.

## What does **Clear** in the savegame section do?
It clears the whole savegame protection list. It does not delete any savegames.

## What does **Delete permanently** do?
It tells the app to delete files directly instead of using quarantine. Use it only if you are sure.

## What does **Remove Map + Unused Dependencies** do?
It removes the selected map and any dependency mods the app believes are no longer needed anywhere else.

## Why would I use savegame protection?
Because you might remove one map but still use a vehicle, building, or placeable from one of that map's dependency mods in another save.

## Is the savegame scan perfect?
No. It is a best-effort safety feature based on XML references the app can detect.

## Do I still need to review the results before deleting?
Yes. The review panel is there to help you double-check what will be removed and what will be kept.

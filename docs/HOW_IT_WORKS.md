# How FS25 Map Cleaner works

## Overview

FS25 Map Cleaner is built to answer one simple question safely:

**If I remove this map, which extra mods can go too, and which ones must stay?**

To do that, the app performs two checks:

1. a **mods/dependency check**
2. an optional **savegame protection check**

---

## 1. Mods and dependency check

When you select a map and click **Analyze Map**, the app:

1. reads the selected map's dependencies from `modDesc.xml`
2. follows those dependencies to build the full dependency tree
3. checks every other installed item in your `mods` folder
4. works out which dependencies are shared
5. keeps shared dependencies and marks only unused ones for removal

### In simple terms

If another installed map or mod still needs a dependency, the app keeps it.

---

## 2. Savegame protection check

If you add one or more savegame folders, the app also scans XML files inside those savegames.

This is to catch cases where a dependency mod is still in use in a different save through:

- vehicles
- placeables
- buildings
- other saved references in XML files

### Files that may be scanned

Examples include:
- `vehicles.xml`
- `placeables.xml`
- other XML files found inside the selected savegame folders

### In simple terms

If the app finds signs that a dependency mod is still used in a protected savegame, it keeps that mod instead of removing it.

---

## Final decision rules

A dependency is **kept** if any of these are true:

- another installed map depends on it
- another installed mod depends on it
- one of the selected savegames still appears to reference it

A dependency is **removed** only if none of those checks say it is still needed.

---

## Example

You want to remove **Map A**.

Map A depends on:
- Pack 1
- Pack 2
- Pack 3

The app checks:
- does another installed map use Pack 1, 2, or 3?
- does another installed mod use Pack 1, 2, or 3?
- do your protected savegames still reference Pack 1, 2, or 3?

Possible result:
- Pack 1 = remove
- Pack 2 = keep because another map still uses it
- Pack 3 = keep because a savegame still references it

That means the app removes only:
- the selected map
- Pack 1

---

## Important limitation

The result can only be as accurate as the information the app can see.

That means accuracy depends on:

- whether mod authors declared dependencies correctly in `modDesc.xml`
- whether the savegame still shows the relevant mod usage in XML text

If a mod has missing dependency metadata, or a save references something in a way that does not appear clearly in XML, the app may not detect every relationship perfectly.

That is why the review step is important.

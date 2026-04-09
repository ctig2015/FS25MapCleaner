# How FS25 Map Cleaner Works

FS25 Map Cleaner reads installed mods from your FS25 `mods` folder, parses `modDesc.xml`, and builds a dependency tree for the selected map or mod.

It then checks each dependency against:

- other installed maps and mods
- any savegames you selected for protection

A dependency is kept if:
- another installed mod/map still depends on it
- a selected savegame still references it in XML content

A dependency is removed only if it is no longer needed anywhere else.

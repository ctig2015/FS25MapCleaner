# How FS25 Map Cleaner works

This page explains the delete logic in plain English.

## The goal

When a player removes a large FS25 map, they often want to remove the extra required mods that came with that map too.

But there is a problem:

Some of those required mods may also be used by other installed maps.

So the app must answer this question for every dependency:

**Is this mod only for the selected map, or is something else still using it?**

## Step-by-step logic

### 1. Scan the mods folder

The app scans the folder the user chooses.

It reads:
- ZIP mods
- folder mods

### 2. Read each mod's `modDesc.xml`

For each installed mod, the app reads the dependency list from `modDesc.xml`.

### 3. Build the selected map's dependency tree

When the user picks a map, the app starts with that map and follows its dependencies.

If the map depends on `A`, and `A` depends on `B`, then the tree includes:
- the map itself
- `A`
- `B`

### 4. Check every other installed mod and map

For each dependency in the selected map's tree, the app checks the rest of the installed mods.

If another installed mod still depends on that dependency, it is marked as **shared**.

### 5. Decide what to delete

The app removes:
- the selected map
- dependencies that are not used by anything else

The app keeps:
- dependencies still used by another installed mod or map

## Example

Selected map:
- `FS25_BigMap`

Dependencies:
- `RequiredPack_A`
- `RequiredPack_B`
- `RequiredPack_C`

Other installed maps:
- `FS25_CountryMap` uses `RequiredPack_B`

Delete result:
- delete `FS25_BigMap`
- delete `RequiredPack_A`
- keep `RequiredPack_B`
- delete `RequiredPack_C`

## What counts as shared

A dependency counts as shared when another installed mod or map lists it as a dependency too.

## Why this is safer than deleting everything

A lot of map packs reuse the same support mods.

If the app deleted every required mod without checking other installed maps, it could break maps the player still wants to keep.

## Limit

The result depends on how correctly the installed mods declare their dependencies.

If a mod is missing dependency information or uses unusual custom behavior outside normal dependency declarations, no cleanup tool can detect that perfectly.

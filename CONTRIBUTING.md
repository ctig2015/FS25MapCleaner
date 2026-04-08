# Contributing

Thanks for helping improve FS25 Map Cleaner.

## How to report a bug

Please include:

- what you tried to remove
- what the app deleted
- what the app kept
- whether the mod was a ZIP or folder
- a screenshot of the analysis window if possible
- the `modDesc.xml` files involved if you can share them

## Good feature requests

Useful feature requests include:

- clearer map detection
- restore from quarantine
- better filter/search tools
- better warnings before delete
- exportable analysis reports

## Before opening an issue

Please check:

- that you scanned the correct FS25 `mods` folder
- that the selected item is really the map you meant to remove
- that the dependency exists in `modDesc.xml`

## Development notes

Main file:
- `fs25_map_cleaner.py`

Windows installer:
- `installer/FS25MapCleaner.iss`

Automatic release build:
- `.github/workflows/build-release.yml`

# Release Notes

This repository is set up for local Windows builds and public version drops.

Recommended flow:

1. Build the onedir app locally:

   ```powershell
   packaging\windows\build_onedir.ps1
   ```

2. Compile the Inno Setup installer:

   ```powershell
   iscc packaging\windows\innosetup\SolarExpanseFleetManager.iss
   ```

3. Stage the generated installer from `dist\installer\`.

4. Commit the version bump, release notes, and installer, or attach the installer to a GitHub Release.

The app is read-only against save files. Do not commit user save files, game decompilation output, or private research/workbench artifacts.


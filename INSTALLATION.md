# Installation Guide

## Method 1: Install as Blender Add-on (Recommended)

1. **Download the addon file**
   - Download `__init__.py` from this repository
   - Save it to a location you can easily find

2. **Open Blender Preferences**
   - Launch Blender (version 3.0 or higher required)
   - Go to `Edit` → `Preferences` (or `Blender` → `Preferences` on macOS)
   - Click on the `Add-ons` tab on the left sidebar

3. **Install the addon**
   - Click the `Install...` button at the top right
   - Navigate to where you saved `__init__.py`
   - Select the file and click `Install Add-on`

4. **Enable the addon**
   - In the Add-ons list, search for "Grease Pencil to Rive"
   - Check the checkbox next to "Import-Export: Grease Pencil to Rive"
   - The addon is now active!

5. **Verify installation**
   - Go to `File` → `Export`
   - You should see "Rive (.lua)" in the export menu

## Method 2: Install as Blender Script

If you prefer to use it as a standalone script:

1. **Copy the script**
   - Copy the contents of `__init__.py`

2. **Open Blender's Scripting workspace**
   - In Blender, switch to the `Scripting` workspace (top menu bar)

3. **Create a new text file**
   - Click `New` in the Text Editor
   - Paste the copied script content

4. **Run the script**
   - Click `Run Script` or press `Alt+P`
   - The exporter will be available until you close Blender

## Troubleshooting

### "Module not found" error
- Make sure you're using Blender 3.0 or higher
- Try restarting Blender after installation

### Export menu doesn't show Rive option
- Verify the addon is enabled in Preferences → Add-ons
- Check the console for any error messages (`Window` → `Toggle System Console`)

### Export fails with no object selected
- Make sure you have a Grease Pencil object selected
- The object must have at least one stroke to export

## Uninstallation

1. Go to `Edit` → `Preferences` → `Add-ons`
2. Search for "Grease Pencil to Rive"
3. Click the `Remove` button
4. Restart Blender

## System Requirements

- **Blender**: Version 3.0 or higher
- **Operating System**: Windows, macOS, or Linux (any platform that runs Blender)
- **Python**: Bundled with Blender (no separate installation needed)

## Next Steps

After installation, check out:
- `README.md` for usage instructions
- `example_usage.py` for code examples

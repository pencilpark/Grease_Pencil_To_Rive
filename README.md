# Blender Grease Pencil to Rive

Export Blender Grease Pencil illustrations as Rive Node Scripts. Your 2D artwork renders natively in Rive with editable colors, smooth curves, and pixel-perfect fidelity.

## Features

- ✨ **Direct Export**: Export Grease Pencil objects directly from Blender
- 🎨 **Preserves Colors**: Material colors (stroke and fill) are maintained
- 📐 **Smooth Curves**: All stroke points and curves are preserved with full precision
- 🎭 **Layer Support**: Exports all visible layers with opacity settings
- 🎬 **Frame Data**: Maintains frame numbers for animation support
- 📝 **Luau Format**: Generates clean, readable Rive Node Scripts in Luau

## Installation

1. Download the `__init__.py` file from this repository
2. Open Blender (version 3.0 or higher)
3. Go to `Edit > Preferences > Add-ons`
4. Click `Install...` and select the downloaded `__init__.py` file
5. Enable the addon by checking the checkbox next to "Import-Export: Grease Pencil to Rive"

## Usage

1. Create or open a Grease Pencil object in Blender
2. Draw your illustration using the Grease Pencil tools
3. Select the Grease Pencil object
4. Go to `File > Export > Rive (.lua)`
5. Choose your export location and filename
6. Click `Export Rive`

The exported `.lua` file contains a Rive Node Script with all your stroke data, colors, and layer information.

## Export Options

- **Visible Layers Only**: When enabled, only exports layers that are currently visible (default: enabled)

## Exported Data Structure

The exporter generates a Luau table structure containing:

- **Materials**: Color information for strokes and fills
- **Layers**: All visible layers with their opacity settings
- **Frames**: Frame-by-frame data with frame numbers
- **Strokes**: Individual stroke paths with line width
- **Points**: Precise 3D coordinates for each point in a stroke

### Example Output

```lua
-- Rive Node Script generated from Blender Grease Pencil
-- Source: GPencil

local RiveNode = {}

-- Materials
RiveNode.materials = {
    [0] = {
        name = "Black",
        strokeColor = {0.000, 0.000, 0.000, 1.000},
        fillColor = {1.000, 1.000, 1.000, 0.000}
    },
}

-- Layers
RiveNode.layers = {
    {
        name = "Layer 1",
        opacity = 1.000,
        frames = {
            {
                frameNumber = 1,
                strokes = {
                    {
                        lineWidth = 10,
                        materialIndex = 0,
                        points = {
                            {-1.234567, 2.345678, 0.000000},
                            {1.234567, 2.345678, 0.000000},
                        }
                    },
                }
            },
        }
    },
}

-- Helper function to create Rive shapes from the data
function RiveNode:createShapes()
    -- Implementation...
end

return RiveNode
```

## Using in Rive

The exported Luau script can be imported into Rive and used as a Node Script to:

1. Programmatically create vector shapes
2. Apply materials and colors
3. Build animations from frame data
4. Customize rendering with full access to path data

## Requirements

- Blender 3.0 or higher
- A Grease Pencil object with at least one stroke

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

# Blender Grease Pencil to Rive

Export Blender Grease Pencil illustrations as Rive Node Scripts. Your 2D artwork renders natively in Rive with editable colors, smooth curves, and pixel-perfect fidelity.

![Pipeline](https://img.shields.io/badge/Blender-Grease_Pencil-orange) ![Target](https://img.shields.io/badge/Rive-Node_Script-blue) ![Language](https://img.shields.io/badge/Luau-Script-purple) ![License](https://img.shields.io/badge/license-MIT-green)

---

## What It Does

- **1:1 quality** — every point preserved, no decimation
- **Smooth curves** — Catmull-Rom to Cubic Bezier conversion for silky outlines
- **Editable colors** — material colors exposed in Rive's Property Group panel
- **Auto file splitting** — handles Rive's typecheck limits automatically
- **Two workflows** — standalone Blender script or AI-assisted via Claude Code + MCP

---

## Quick Start

### Option A: Standalone Script

1. Open your `.blend` file in Blender
2. Go to the **Scripting** tab
3. Open `blender_to_rive_gp.py`
4. Edit the **CONFIG** section at the top (model name, draw order, materials)
5. Run the script (**Alt+P**)
6. Copy all generated `.luau` files to your Rive project

### Option B: Claude Code + Blender MCP

1. Open your `.blend` in Blender with [Blender MCP](https://github.com/ahujasid/blender-mcp) running
2. Give Claude Code the `prompt.md` file as context
3. Claude analyzes your GP scene and generates everything automatically

---

## Configuration

Edit the `CONFIG` section at the top of `blender_to_rive_gp.py`:

```python
MODEL_NAME = "Bean"              # Used for filenames
OUTPUT_DIR = "/tmp/rive_export"  # Where to write .luau files

# Draw order: back to front (first = behind, last = in front)
DRAW_ORDER = [
    ("bean", "color"),       # object_name, layer_name
    ("bean", "strokes"),
    ("jar", "jar"),
    ("fingers", "strokes"),
]

# Materials: name -> index, color (RGB), and Rive property name
MATERIAL_MAP = {
    "skin": 1,
    "black_stroke": 2,
}
MATERIAL_COLORS = {
    "skin": (202, 181, 166),
    "black_stroke": (0, 0, 0),
}
MATERIAL_PROP_NAMES = {
    "skin": "colorSkin",
    "black_stroke": "colorBlackStroke",
}
```

### How to find these values

- **DRAW_ORDER**: In Blender, check your GP objects and their layer names. Bottom layer = drawn first (behind)
- **MATERIAL_MAP**: In Blender's material properties, list each GP material name. Skip effect materials (gradients, lights)
- **MATERIAL_COLORS**: Pick the RGB values from each material's fill or stroke color

---

## Output

The script generates:

```
output/
  Bean.luau              <- Main Node Script (entry point for Rive)
  BeanPartAData.luau     <- Stroke data part 1
  BeanPartBData.luau     <- Stroke data part 2
  ...                    <- More parts if needed (auto-split at ~7500 pts)
```

Import **all** `.luau` files into your Rive project. `Bean.luau` is the entry point.

---

## Rive Property Group

Once imported, these controls appear in Rive's Property Group panel:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `scale` | Number | 1 | Model scale |
| `offsetX` | Number | 0 | Horizontal position |
| `offsetY` | Number | 0 | Vertical position |
| `strokeScale` | Number | 1 | Global stroke thickness multiplier |
| `colorSkin` | Color | From Blender | Skin color |
| `colorBlackStroke` | Color | From Blender | Outline color |
| ... | Color | ... | One picker per material |

All colors are live-editable. Change a color in Rive and the illustration updates instantly.

---

## How It Works

```
Blender GP Scene
       |
  [Collect] strokes in draw order (back to front)
       |
  [Transform] 3D points to 2D (x = world.x, y = -world.z)
       |
  [Normalize] center + scale to ~400 units
       |
  [Split] into Part files (~7500 points max each)
       |
  [Generate] Node Script with Property Group + Bezier rendering
       |
  Rive .luau files
```

**Rendering details:**
- Fills (>200 points) use `lineTo` — already smooth at full resolution
- Stroke outlines (<200 points) use `cubicTo` with Catmull-Rom to Bezier conversion
- Fill paths are **closed**, stroke paths are **open** (prevents outline looping)

---

## File Reference

| File | What it is |
|------|------------|
| `blender_to_rive_gp.py` | Export script — run in Blender's Scripting tab |
| `prompt.md` | AI agent prompt for Claude Code + Blender MCP workflow |
| `CLAUDE.md` | Technical docs: lessons learned, pitfalls, code patterns |
| `README.md` | This file |

---

## Requirements

- **Blender 3.x+** with Grease Pencil objects
- **Rive** with Node Script / Luau support
- **Claude Code + Blender MCP** *(optional, for AI-assisted export)*

---

## Troubleshooting

| Problem | What to do |
|---------|------------|
| **Jagged outlines** | Should not happen — the script uses Catmull-Rom to Bezier. Check `SMOOTH_THRESHOLD` (default 200) |
| **Stroke outlines loop back** | Fill and stroke paths must be separate. The generated script handles this |
| **Eyes/details invisible** | Thickness formula issue. Should be `sw * strokeSc * 0.1`, NOT multiplied by scale |
| **Typecheck error in Rive** | A data file has too many points. Lower `MAX_POINTS_PER_FILE` (default 7500) |
| **Missing fills** | Some materials have `show_fill=True` but aren't cyclic. The script checks `show_fill` |
| **Colors not editable** | They should appear as color pickers in Rive's Property Group panel |
| **Wrong projection** | Coordinate transform should be `x = world.x`, `y = -world.z` (Blender Z-up) |
| **Script error in Blender** | Check object/layer names in `DRAW_ORDER` match your scene exactly |

---

## License

MIT — free for personal and commercial use.

---

## Credits

Pipeline developed by [Fred Berria](https://x.com/fredberria)

Rive: https://rive.app

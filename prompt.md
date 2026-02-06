# Blender Grease Pencil to Rive - AI Agent Prompt

> **For Claude Code with Blender MCP**: This prompt enables AI-assisted conversion of Blender Grease Pencil illustrations to Rive-compatible Luau Node Script code.

---

## ⚠️ STOP! Before You Start

**Read these 10 rules or face hours of debugging:**

1. **NO RDP/decimation on fills** - Fills MUST be 1:1 quality. RDP destroys fill shapes at ANY epsilon
2. **USE `c=index` format** - NOT RGB colors. Map materials to category indices 1-N
3. **Catmull-Rom → Cubic Bezier** - Use `cubicTo()` for strokes with < 200 points
4. **`lineTo` for dense fills** - Fills with > 200 points are already smooth
5. **SEPARATE fill/stroke paths** - Fill path is CLOSED, stroke path is OPEN (never closed)
6. **Thickness = `sw * strokeSc * 0.1`** - Do NOT multiply by scale. Min thickness = 0.3
7. **Coordinate transform**: `screen_x = world.x`, `screen_y = -world.z` (Blender Z-up)
8. **Split at ~7500 points** per Luau data file (Rive typecheck limit)
9. **Draw order from GP layers** - Back-to-front, respect Blender layer stacking
10. **Expose colors as `Input<Color>`** - For Rive Property Group editor control

---

## Your Task

Convert a Blender Grease Pencil illustration into functional Rive Node Script Luau code with:
- 1:1 quality point export (no decimation)
- Catmull-Rom → Cubic Bezier smooth stroke rendering
- Material-to-color category mapping
- Automatic file splitting (~7500 points per file)
- Colors exposed as `Input<Color>` in Property Group
- Correct draw order from GP layer stacking

---

## File Size Limits

| Parameter | Value | Notes |
|-----------|-------|-------|
| Max points/file | **~7500** | Rive Luau typecheck limit |
| Max file size | **~130 KB** | Per Luau script file |
| Normalization | **~400 units** | Center + scale to fit |

---

## Prerequisites

### Required
- **Blender MCP** (preferred) or run `blender_to_rive_gp.py` standalone in Blender

### Reference Files
- **CLAUDE.md** - Complete documentation (lessons learned, pitfalls, code examples)
- **blender_to_rive_gp.py** - Standalone export script (alternative to MCP)

---

## Export Pipeline (Step by Step)

### Step 1: Analyze the GP Scene

```python
import bpy

for obj in bpy.data.objects:
    if obj.type == 'GPENCIL':
        gp = obj.data
        print(f"\n=== {obj.name} ===")
        for layer in gp.layers:
            frame = layer.active_frame
            if frame:
                total_pts = sum(len(s.points) for s in frame.strokes)
                print(f"  Layer '{layer.info}': {len(frame.strokes)} strokes, {total_pts} pts")

        print(f"  Materials:")
        for i, mat in enumerate(gp.materials):
            mg = mat.grease_pencil
            print(f"    {i}: {mat.name} fill={mg.show_fill} stroke={mg.show_stroke}")
```

Report back: object names, layer names, stroke/point counts, material list.

### Step 2: Define Draw Order

Ask the user to confirm the layer stacking order. Default: inspect Blender layer order (bottom = behind).

```python
# Example draw order (back to front)
draw_order = [
    ("object_name", "layer_name"),
    # First = drawn first (behind), Last = drawn last (in front)
]
```

### Step 3: Map Materials

Create `material_map` dict: material name → category index (1-based).
Skip materials containing "light" (gradient/effect materials).

```python
material_map = {}
skip_materials = ["light_effect", "gradient"]  # Skip these

idx = 1
for mat in gp.materials:
    name = mat.name
    if any(skip in name.lower() for skip in skip_materials):
        continue
    material_map[name] = idx
    idx += 1
```

### Step 4: Extract Strokes (NO Decimation)

```python
all_strokes = []

for obj_name, layer_name in draw_order:
    obj = bpy.data.objects.get(obj_name)
    gp = obj.data
    world_matrix = obj.matrix_world

    # Find layer
    layer = next(l for l in gp.layers if l.info == layer_name)
    frame = layer.active_frame

    for stroke in frame.strokes:
        mat_idx = stroke.material_index
        mat_name = gp.materials[mat_idx].name
        mat_gp = gp.materials[mat_idx].grease_pencil

        # Skip effect materials
        if "light" in mat_name.lower():
            continue

        color_cat = material_map.get(mat_name, 1)
        is_fill = mat_gp.show_fill
        stroke_width = stroke.line_width if mat_gp.show_stroke else 0

        if not is_fill and stroke_width == 0:
            continue

        # Extract 2D points (Z-up → screen)
        pts_2d = []
        for pt in stroke.points:
            co = world_matrix @ pt.co
            pts_2d.append([co.x, -co.z])

        if len(pts_2d) < 2:
            continue

        all_strokes.append({
            "pts": pts_2d,
            "c": color_cat,
            "fill": is_fill,
            "sw": stroke_width,
        })
```

### Step 5: Normalize Coordinates

```python
all_x = [pt[0] for s in all_strokes for pt in s["pts"]]
all_y = [pt[1] for s in all_strokes for pt in s["pts"]]

cx = (min(all_x) + max(all_x)) / 2
cy = (min(all_y) + max(all_y)) / 2
span = max(max(all_x) - min(all_x), max(all_y) - min(all_y))
norm_scale = 400 / span

for s in all_strokes:
    for pt in s["pts"]:
        pt[0] = round((pt[0] - cx) * norm_scale, 2)
        pt[1] = round((pt[1] - cy) * norm_scale, 2)
```

### Step 6: Split into Parts and Write Files

```python
MAX_PTS = 7500
parts = []
current, count = [], 0

for s in all_strokes:
    n = len(s["pts"])
    if count + n > MAX_PTS and current:
        parts.append(current)
        current, count = [], 0
    current.append(s)
    count += n
if current:
    parts.append(current)

# Write each part
part_labels = "ABCDEFGHIJKLMNOP"
for i, part in enumerate(parts):
    label = part_labels[i]
    filename = f"ModelPart{label}Data.luau"
    # ... write strokes to file
```

### Step 7: Generate Node Script

Generate the main `Model.luau` with:
- `require()` for each Part file
- `export type` with `Input<Color>` for each material category
- `getColors(self)` function building color table from self properties
- `buildSmoothPath()` using Catmull-Rom → Bezier (cubicTo)
- `buildLinearPath()` using lineTo for dense fills
- `processStrokes()` with SEPARATE fill (closed) / stroke (open) paths
- Thickness = `sw * strokeSc * 0.1` (min 0.3)
- Default color values from Blender material colors (as `Color.rgba()`)

---

## Node Script Template

```luau
--!strict
local PartA = require("ModelPartAData")
-- ... more parts

type StrokeEntry = {
    pts: { { number } },
    c: number,
    fill: boolean,
    sw: number,
}

type DrawCommand = {
    path: Path,
    paint: Paint,
}

export type Model = {
    scale: Input<number>,
    offsetX: Input<number>,
    offsetY: Input<number>,
    strokeScale: Input<number>,
    -- Colors (one per material category)
    colorCategory1: Input<Color>,
    colorCategory2: Input<Color>,
    -- ...
    drawCommands: { DrawCommand },
    context: Context?,
}

local SMOOTH_THRESHOLD = 200

local function getColors(self: Model): { Color }
    return {
        self.colorCategory1,  -- 1
        self.colorCategory2,  -- 2
        -- ...
    }
end

local function buildSmoothPath(pts, sc, ox, oy, closePath): Path
    -- Catmull-Rom → Bezier: CP1 = P1 + (P2-P0)/6, CP2 = P2 - (P3-P1)/6
    -- Uses cubicTo() for each segment
end

local function buildLinearPath(pts, sc, ox, oy, closePath): Path
    -- Simple moveTo/lineTo for dense fills
end

local function processStrokes(self, strokes, sc, ox, oy, strokeSc, colors)
    for _, stroke in ipairs(strokes) do
        local pts = stroke.pts
        if #pts < 2 then continue end

        local color = colors[stroke.c] or colors[1]
        local useSmooth = #pts < SMOOTH_THRESHOLD

        -- Fill: CLOSED path
        if stroke.fill then
            local fillPath = if useSmooth
                then buildSmoothPath(pts, sc, ox, oy, true)
                else buildLinearPath(pts, sc, ox, oy, true)
            table.insert(self.drawCommands, {
                path = fillPath,
                paint = Paint.with({ style = "fill", color = color }),
            })
        end

        -- Stroke: OPEN path (never closed)
        if stroke.sw > 0 then
            local strokePath = if useSmooth
                then buildSmoothPath(pts, sc, ox, oy, false)
                else buildLinearPath(pts, sc, ox, oy, false)
            local thickness = math.max(stroke.sw * strokeSc * 0.1, 0.3)
            table.insert(self.drawCommands, {
                path = strokePath,
                paint = Paint.with({
                    style = "stroke", color = color,
                    thickness = thickness, cap = "round", join = "round",
                }),
            })
        end
    end
end

-- Lifecycle: init, advance (build paths), draw (render)
-- advance() calls processStrokes for each Part in draw order

return function(): Node<Model>
    return {
        scale = 1, offsetX = 0, offsetY = 0, strokeScale = 1,
        colorCategory1 = Color.rgba(R, G, B, 255),
        -- ... defaults from Blender
        drawCommands = {}, context = nil,
        init = init, advance = advance, draw = draw,
    }
end
```

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Angular/jagged outlines | `lineTo` instead of `cubicTo` | Use Catmull-Rom → Bezier for strokes < 200 pts |
| Stroke outlines loop closed | Shared path for fill + stroke | Build SEPARATE paths: fill=closed, stroke=open |
| Eyes invisible / gribouillis | Wrong thickness formula | `sw * strokeSc * 0.1`, not `sw * sc * strokeSc * 0.005` |
| Fills are angular/destroyed | RDP decimation on fills | NO decimation. Keep all points 1:1 |
| Typecheck error in Rive | >7500 points in one file | Split into multiple Part files |
| "Path modified between draws" | Modifying paths in draw() | Build paths in advance(), only render in draw() |
| Missing fills for freckles | Only checking `use_cyclic` | Check `mat_gp.show_fill` regardless |
| Colors not in Rive editor | Hardcoded color table | Use `Input<Color>` in export type |
| Wrong projection | Y-up confusion | Use `world.x` → screen X, `-world.z` → screen Y |

---

## Pre-Export Checklist

- [ ] Analyzed GP objects (names, layers, strokes, points, materials)
- [ ] Draw order defined and confirmed with user
- [ ] Materials mapped to category indices (skipped effects)
- [ ] NO RDP/decimation applied
- [ ] Coordinate transform: `x = world.x`, `y = -world.z`
- [ ] Normalized to ~400 units range
- [ ] Split at ~7500 points per file
- [ ] Node Script generated with:
  - [ ] Catmull-Rom → Bezier (`cubicTo`) for strokes < 200 pts
  - [ ] `lineTo` for dense fills > 200 pts
  - [ ] Separate closed/open paths for fill/stroke
  - [ ] Thickness = `sw * strokeSc * 0.1` (min 0.3)
  - [ ] Colors as `Input<Color>` with Blender defaults
  - [ ] Paths in `advance()`, rendering in `draw()`

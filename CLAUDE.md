# Blender Grease Pencil to Rive Export

> **Quick Start:** Run `blender_to_rive_gp.py` in Blender (or use Blender MCP) → Copy generated `.luau` files to Rive

## ⚠️ IMPORTANT: Read Before Exporting

1. **NO decimation on fills** - RDP destroys fill shapes even at low epsilon. Keep 1:1 points
2. **Use category index `c=1`** instead of RGB colors - Much smaller files
3. **Catmull-Rom → Cubic Bezier** for stroke outlines (`cubicTo()`) - Critical for smooth rendering
4. **lineTo for dense fills** (>200 points) - Already smooth, cubicTo would be wasteful
5. **Separate fill/stroke paths** - Fill path is closed, stroke path is OPEN (never closed)
6. **Thickness formula:** `stroke.sw * strokeSc * 0.1` - Do NOT multiply by scale
7. **Blender Z-up coordinate transform:** `screen_x = world.x`, `screen_y = -world.z`
8. **Split data files at ~7500 points max** per Luau file - Rive typecheck limit
9. **Draw order from GP layers** - Back-to-front layer stacking, respect object order
10. **Expose colors as `Input<Color>`** in Property Group for Rive editor control

## Project Structure

```
YOUR_MODEL/
├── Model.luau                # Main Node Script (rendering + Property Group)
├── ModelPartAData.luau       # Part A: ~7500 points max
├── ModelPartBData.luau       # Part B: ~7500 points max
├── ...PartNData.luau         # Additional parts if needed
├── blender_to_rive_gp.py     # Standalone export script
├── prompt.md                 # AI agent prompt for Claude Code
└── CLAUDE.md                 # This documentation
```

---

## Critical Lessons Learned

### 1. File Size Limits

- **Maximum ~7500 points** per Luau script file (Rive typecheck limit)
- **Maximum ~130 KB** per Luau file
- Using category index `c` instead of RGB colors reduces data size
- For a 29,000 point model: split into 5 parts of ~5,000-7,000 points each

### 2. Stroke Data Format

```luau
-- Each stroke entry in a Part data file
{
    pts = { {x1, y1}, {x2, y2}, ... },  -- 2D points (normalized)
    c = 1,                                -- Material category index
    fill = true,                          -- Has fill (closed polygon)
    sw = 10,                              -- Stroke width (0 = no outline)
}
```

### 3. DO NOT Decimate Fills

```python
# ❌ WRONG: RDP on everything — destroys fill shapes
if len(pts_2d) > 3:
    pts_2d = rdp(pts_2d, 0.005)  # Fills become angular garbage

# ✅ CORRECT: Keep fills at full resolution (1:1 quality)
# Only consider RDP for stroke-only entries (rare in GP)
# In practice: GP strokes almost always have fill=True, so NO RDP at all
```

**Why:** RDP removes points from polygons. Even at epsilon=0.001, large fills (1000+ points) lose critical shape detail. The cubic bezier smoothing only helps stroke outlines, not filled polygon edges which use `lineTo`.

### 4. Catmull-Rom → Cubic Bezier Conversion (CRITICAL)

**Problem:** Blender GP renders strokes using Catmull-Rom spline interpolation internally. Exporting raw points and connecting with `lineTo` produces angular/jagged outlines.

**Solution:** Convert to cubic Bezier curves using `cubicTo()`:

```
For each segment P1→P2, given neighbors P0 and P3:
  CP1 = P1 + (P2 - P0) / 6
  CP2 = P2 - (P3 - P1) / 6
```

```luau
-- Catmull-Rom → Bezier for strokes with < 200 points
for i = 1, n - 1 do
    local p0x = tx[math.max(1, i - 1)]
    local p0y = ty[math.max(1, i - 1)]
    local p1x, p1y = tx[i], ty[i]
    local p2x, p2y = tx[i + 1], ty[i + 1]
    local p3x = tx[math.min(n, i + 2)]
    local p3y = ty[math.min(n, i + 2)]

    local cp1x = p1x + (p2x - p0x) / 6
    local cp1y = p1y + (p2y - p0y) / 6
    local cp2x = p2x - (p3x - p1x) / 6
    local cp2y = p2y - (p3y - p1y) / 6

    path:cubicTo(
        Vector.xy(cp1x, cp1y),
        Vector.xy(cp2x, cp2y),
        Vector.xy(p2x, p2y)
    )
end
```

**Threshold:** Use `cubicTo` for strokes with < 200 points. Dense fills (>200 points) use `lineTo` — they're already smooth enough.

### 5. Separate Fill and Stroke Paths (CRITICAL)

**Problem:** A GP stroke can have BOTH `fill=true` AND `sw > 0`. If you build one path with `close()` and use it for both fill and stroke, the stroke outline loops back to start (closed).

**Solution:** Build two separate paths:

```luau
-- Fill: CLOSED path for polygon fill
if stroke.fill then
    local fillPath = buildPath(pts, sc, ox, oy, true)   -- closePath=true
    renderer:drawPath(fillPath, fillPaint)
end

-- Stroke: OPEN path for outline (never closed)
if stroke.sw > 0 then
    local strokePath = buildPath(pts, sc, ox, oy, false)  -- closePath=false
    renderer:drawPath(strokePath, strokePaint)
end
```

### 6. Stroke Thickness Formula

```luau
-- ❌ WRONG: Multiplying by scale makes thickness zoom-dependent
local thickness = stroke.sw * sc * strokeSc * 0.005  -- Eyes become invisible

-- ✅ CORRECT: Scale-independent thickness
local thickness = stroke.sw * strokeSc * 0.1
if thickness < 0.3 then
    thickness = 0.3  -- Minimum visible thickness
end
```

GP `line_width` is in screen pixels. The `0.1` factor converts to Rive units. `strokeScale` (exposed as `Input<number>`) lets the user tune globally from Rive.

### 7. Coordinate System (Blender Z-up → Rive 2D)

Blender Grease Pencil objects are 3D but drawn as 2D illustrations. The world matrix transforms points to world space, then we project to 2D:

```python
# In Blender export script
co_world = obj.matrix_world @ point.co
screen_x = co_world.x       # World X → Screen X
screen_y = -co_world.z      # World Z (negated) → Screen Y
# World Y is ignored (depth axis for 2D GP)
```

### 8. Material Mapping

```python
# Map GP material names to category indices (1-based)
material_map = {
    "black_stroke": 1,
    "hair_stroke": 2,
    "clothes_cyan": 3,
    "skin": 4,
    # ... etc
}

# Skip materials that are visual effects
if "light" in mat_name.lower():
    continue  # Skip light_effect, gradient fills, etc.
```

Each material's properties determine fill vs stroke behavior:

```python
mat_gp = material.grease_pencil
is_fill = mat_gp.show_fill        # Material has fill enabled
stroke_width = stroke.line_width if mat_gp.show_stroke else 0
```

### 9. Draw Order from GP Layers

GP layers stack back-to-front. Define the order explicitly:

```python
draw_order = [
    ("object_name", "layer_name"),  # First = drawn first (behind)
    ("bean", "color"),               # Base colors
    ("bean", "strokes"),             # Outlines on top
    ("bean", "details"),             # Small details
    ("jar", "jar"),                  # Separate object
    ("fingers", "color"),            # Foreground object
    ("fingers", "strokes"),          # Last = drawn last (in front)
]
```

### 10. Exposing Colors in Property Group

Colors are exposed as `Input<Color>` so they can be edited in the Rive editor:

```luau
export type Model = {
    -- Color palette (visible in Rive Property Group)
    colorSkin: Input<Color>,
    colorHair: Input<Color>,
    -- ... one per material category
}

-- Build lookup table from self properties
local function getColors(self: Model): { Color }
    return {
        self.colorBlackStroke,   -- 1
        self.colorHair,          -- 2
        -- ... matches category indices from export
    }
end

-- In Node return, set defaults from Blender material colors:
return function(): Node<Model>
    return {
        colorSkin = Color.rgba(202, 181, 166, 255),
        colorHair = Color.rgba(122, 121, 124, 255),
        -- ...
    }
end
```

---

## Export Workflow

### Step 1: Analyze GP Objects
```python
# List all GP objects, their layers, and frame stroke counts
for obj in bpy.data.objects:
    if obj.type == 'GPENCIL':
        for layer in obj.data.layers:
            frame = layer.active_frame
            print(f"{obj.name}/{layer.info}: {len(frame.strokes)} strokes")
```

### Step 2: Determine Draw Order
Inspect the layer stack in Blender. Bottom layers = drawn first (behind). Define `draw_order` list.

### Step 3: Map Materials
```python
# Enumerate GP materials, skip light_effect/gradient
for i, mat_slot in enumerate(gp_data.materials):
    mat_name = mat_slot.name
    mat_gp = mat_slot.grease_pencil
    print(f"  {i}: {mat_name} fill={mat_gp.show_fill} stroke={mat_gp.show_stroke}")
```

### Step 4: Extract Points (NO decimation)
```python
for stroke in frame.strokes:
    pts_2d = []
    for pt in stroke.points:
        co_world = obj.matrix_world @ pt.co
        pts_2d.append([co_world.x, -co_world.z])  # Z-up → 2D
```

### Step 5: Normalize Coordinates
```python
# Center and scale to ~400 units
cx = (min_x + max_x) / 2
cy = (min_y + max_y) / 2
span = max(max_x - min_x, max_y - min_y)
norm_scale = 400 / span
for pt in all_points:
    pt[0] = round((pt[0] - cx) * norm_scale, 2)
    pt[1] = round((pt[1] - cy) * norm_scale, 2)
```

### Step 6: Split into Part Files
```python
# Split strokes into parts of ~7500 points max
MAX_POINTS_PER_FILE = 7500
parts = []
current_part = []
current_count = 0

for stroke in all_strokes:
    n = len(stroke["pts"])
    if current_count + n > MAX_POINTS_PER_FILE and current_part:
        parts.append(current_part)
        current_part = []
        current_count = 0
    current_part.append(stroke)
    current_count += n

if current_part:
    parts.append(current_part)
```

### Step 7: Generate Luau Files
Write each part as `ModelPartXData.luau` and the main `Model.luau` Node Script.

---

## Common Pitfalls

| Issue | Cause | Solution |
|-------|-------|----------|
| Angular/jagged outlines | Using `lineTo` for strokes | Use Catmull-Rom → Cubic Bezier (`cubicTo`) |
| Stroke outlines loop closed | Same path for fill + stroke | Build separate paths: fill=closed, stroke=open |
| Eyes are gribouillis/invisible | Thickness formula wrong | Use `sw * strokeSc * 0.1`, remove scale dependency |
| Fill shapes are angular | RDP decimation on fills | NO decimation — keep 1:1 points for fills |
| Typecheck error in Rive | Too many points in one file | Split at ~7500 points per file |
| Missing fills | Only checking `use_cyclic` | Check `mat_gp.show_fill` regardless of cyclic |
| Colors don't show in Rive | Not using `Input<Color>` | Expose as `Input<Color>` in export type |
| Wrong coordinate mapping | Y-up vs Z-up confusion | `screen_x = world.x`, `screen_y = -world.z` |
| Some materials missing | Skipping non-stroke materials | Check both `show_fill` and `show_stroke` |
| Strokes have sw=0 but visible | Material has `show_stroke=False` | Set `sw=0` when `show_stroke` is false |

---

## Rive Luau Constraints

### Paths: advance() vs draw()
```luau
-- ✅ Build paths in advance(), only draw in draw()
function advance(self, seconds)
    self.drawCommands = {}
    -- Build all paths here
    table.insert(self.drawCommands, { path = p, paint = paint })
end

function draw(self, renderer)
    for _, cmd in ipairs(self.drawCommands) do
        renderer:drawPath(cmd.path, cmd.paint)
    end
end

-- ❌ NEVER modify paths in draw() — "Path was modified between draws" error
```

### Type Casting for Data Files
```luau
-- Data files are untyped — cast when accessing
processStrokes(self, (PartA :: any).strokes :: { StrokeEntry }, ...)
```

### Property Group (Input Types)
```luau
export type Model = {
    scale: Input<number>,           -- Number slider
    colorSkin: Input<Color>,        -- Color picker
    -- Internal state (not exposed to Rive UI)
    drawCommands: { DrawCommand },  -- No Input<> wrapper = internal
    context: Context?,
}
```

---

## Performance Notes

- **29,000 points** across 5 files renders smoothly
- Dense fills (>200 points) use `lineTo` — faster than `cubicTo`
- Sparse strokes (<200 points) use `cubicTo` — smooth curves
- Paths built once per frame in `advance()`, drawn in `draw()`
- Color table built once per frame from `self` properties
- No sorting needed — 2D draw order is deterministic from GP layer stacking

---

## Default Values

```luau
scale = 1,            -- Model scale
offsetX = 0,          -- Horizontal offset
offsetY = 0,          -- Vertical offset
strokeScale = 1,      -- Global stroke thickness multiplier
SMOOTH_THRESHOLD = 200 -- Points below this use cubicTo
```

---

## Quick Checklist (Before Export)

- [ ] GP objects and layers analyzed (stroke counts, materials)
- [ ] Draw order defined (back-to-front layer stacking)
- [ ] Materials mapped to category indices (skip light_effect)
- [ ] Using `c=index` format (NOT RGB)
- [ ] NO decimation on fills (1:1 quality)
- [ ] Coordinate transform: `screen_x = world.x`, `screen_y = -world.z`
- [ ] Normalized to ~400 units range
- [ ] Split at ~7500 points per file
- [ ] Node Script has:
  - [ ] Catmull-Rom → Bezier for strokes < 200 points
  - [ ] lineTo for dense fills > 200 points
  - [ ] Separate fill (closed) / stroke (open) paths
  - [ ] Thickness = `sw * strokeSc * 0.1` (min 0.3)
  - [ ] Colors exposed as `Input<Color>` in Property Group
  - [ ] Paths built in `advance()`, drawn in `draw()`

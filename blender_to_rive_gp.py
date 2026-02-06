"""
Blender Grease Pencil to Rive Luau Exporter
=============================================
Run this script inside Blender (Scripting tab) to export GP objects
as Rive-compatible Luau Node Script files.

Output:
  - ModelPartAData.luau, ModelPartBData.luau, ... (stroke data files)
  - Model.luau (main Node Script with rendering + Property Group)

Usage:
  1. Open your .blend file with Grease Pencil objects
  2. Edit the CONFIG section below (model name, draw order, materials, output dir)
  3. Run this script in Blender's Scripting tab
  4. Copy the generated .luau files to your Rive project
"""

import bpy
import os
import math

# =============================================================================
# CONFIG — Edit this section for your model
# =============================================================================

# Model name (used for filenames: Model.luau, ModelPartAData.luau, etc.)
MODEL_NAME = "Bean"

# Output directory (where .luau files will be written)
OUTPUT_DIR = "/tmp/rive_export"

# Draw order: (object_name, layer_name) — back to front
# First = drawn first (behind), Last = drawn last (in front)
DRAW_ORDER = [
    ("bean", "color"),
    ("bean", "strokes"),
    ("bean", "details"),
    ("jar", "jar"),
    ("jar", "details"),
    ("handle", "layer"),
    ("fingers", "color"),
    ("fingers", "strokes"),
]

# Material name → category index (1-based)
# Colors will be exposed as Input<Color> in the Rive Property Group
MATERIAL_MAP = {
    "black_stroke": 1,
    "hair_stroke": 2,
    "clothes_cyan": 3,
    "skin": 4,
    "white": 5,
    "clothes_cyan_light": 6,
    "freckles": 7,
    "clothes_shadow": 8,
    "wood_ligth": 9,
    "wood_dark": 10,
}

# Material name → (R, G, B) default color for Rive Property Group
MATERIAL_COLORS = {
    "black_stroke": (0, 0, 0),
    "hair_stroke": (122, 121, 124),
    "clothes_cyan": (71, 113, 115),
    "skin": (202, 181, 166),
    "white": (217, 217, 217),
    "clothes_cyan_light": (182, 239, 232),
    "freckles": (156, 138, 104),
    "clothes_shadow": (81, 95, 88),
    "wood_ligth": (79, 65, 52),
    "wood_dark": (55, 46, 37),
}

# Material name → camelCase property name for Rive
MATERIAL_PROP_NAMES = {
    "black_stroke": "colorBlackStroke",
    "hair_stroke": "colorHairStroke",
    "clothes_cyan": "colorClothesCyan",
    "skin": "colorSkin",
    "white": "colorWhite",
    "clothes_cyan_light": "colorClothesCyanLight",
    "freckles": "colorFreckles",
    "clothes_shadow": "colorClothesShadow",
    "wood_ligth": "colorWoodLight",
    "wood_dark": "colorWoodDark",
}

# Materials to skip (gradient effects, lights, etc.)
SKIP_MATERIALS = ["light_effect", "light"]

# Max points per data file (Rive typecheck limit)
MAX_POINTS_PER_FILE = 7500

# Normalization range (units)
NORM_RANGE = 400

# =============================================================================
# EXPORT LOGIC — No need to edit below this line
# =============================================================================


def collect_strokes():
    """Collect all GP strokes in draw order, no decimation."""
    all_strokes = []

    for obj_name, layer_name in DRAW_ORDER:
        obj = bpy.data.objects.get(obj_name)
        if not obj or obj.type != 'GPENCIL':
            print(f"  WARNING: Object '{obj_name}' not found or not GP")
            continue

        gp = obj.data
        world_matrix = obj.matrix_world

        # Find layer
        layer = None
        for l in gp.layers:
            if l.info == layer_name:
                layer = l
                break
        if not layer:
            print(f"  WARNING: Layer '{layer_name}' not found in '{obj_name}'")
            continue

        frame = layer.active_frame
        if not frame:
            print(f"  WARNING: No active frame for '{obj_name}/{layer_name}'")
            continue

        for stroke in frame.strokes:
            mat_idx = stroke.material_index
            if mat_idx >= len(gp.materials):
                continue

            mat_name = gp.materials[mat_idx].name
            mat_gp = gp.materials[mat_idx].grease_pencil

            # Skip effect materials
            if any(skip in mat_name.lower() for skip in SKIP_MATERIALS):
                continue

            color_cat = MATERIAL_MAP.get(mat_name, 1)

            is_fill = mat_gp.show_fill if mat_gp else False
            stroke_width = stroke.line_width if (mat_gp and mat_gp.show_stroke) else 0

            if not is_fill and stroke_width == 0:
                continue

            # Extract 2D points (Blender Z-up → screen)
            pts_2d = []
            for pt in stroke.points:
                co_world = world_matrix @ pt.co
                pts_2d.append([co_world.x, -co_world.z])

            if len(pts_2d) < 2:
                continue

            all_strokes.append({
                "pts": pts_2d,
                "c": color_cat,
                "fill": is_fill,
                "sw": stroke_width,
            })

    return all_strokes


def normalize_strokes(all_strokes):
    """Center and scale all points to NORM_RANGE units."""
    all_x = [pt[0] for s in all_strokes for pt in s["pts"]]
    all_y = [pt[1] for s in all_strokes for pt in s["pts"]]

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    span = max(max_x - min_x, max_y - min_y)
    norm_scale = NORM_RANGE / span

    for s in all_strokes:
        for pt in s["pts"]:
            pt[0] = round((pt[0] - cx) * norm_scale, 2)
            pt[1] = round((pt[1] - cy) * norm_scale, 2)

    print(f"  Normalized: center=({cx:.3f}, {cy:.3f}), scale={norm_scale:.3f}")


def split_into_parts(all_strokes):
    """Split strokes into parts of ~MAX_POINTS_PER_FILE points each."""
    parts = []
    current_part = []
    current_count = 0

    for s in all_strokes:
        n = len(s["pts"])
        if current_count + n > MAX_POINTS_PER_FILE and current_part:
            parts.append(current_part)
            current_part = []
            current_count = 0
        current_part.append(s)
        current_count += n

    if current_part:
        parts.append(current_part)

    return parts


def write_part_file(part_strokes, part_label, part_index, output_dir):
    """Write a single PartData.luau file."""
    total_pts = sum(len(s["pts"]) for s in part_strokes)
    filename = f"{MODEL_NAME}Part{part_label}Data.luau"
    filepath = os.path.join(output_dir, filename)

    lines = []
    lines.append("--!strict")
    lines.append(f"-- {filename}")
    lines.append(f"-- Auto-generated Grease Pencil export (1:1 quality)")
    lines.append(f"-- {len(part_strokes)} strokes, {total_pts} points")
    lines.append("")
    lines.append(f"local {MODEL_NAME}Part{part_label}Data = {{}}")
    lines.append("")
    lines.append(f"{MODEL_NAME}Part{part_label}Data.strokes = {{")

    for s in part_strokes:
        pts_str = ", ".join(f"{{{pt[0]},{pt[1]}}}" for pt in s["pts"])
        fill_str = "true" if s["fill"] else "false"
        lines.append(f"  {{pts={{{pts_str}}},c={s['c']},fill={fill_str},sw={s['sw']}}},")

    lines.append("}")
    lines.append("")
    lines.append(f"return {MODEL_NAME}Part{part_label}Data")
    lines.append("")

    content = "\n".join(lines)
    with open(filepath, "w") as f:
        f.write(content)

    print(f"  Written: {filename} ({len(content) / 1024:.1f} KB, {len(part_strokes)} strokes, {total_pts} pts)")
    return filename


def write_node_script(part_labels, output_dir):
    """Write the main Model.luau Node Script."""
    filepath = os.path.join(output_dir, f"{MODEL_NAME}.luau")

    # Build sorted material list by category index
    sorted_mats = sorted(MATERIAL_MAP.items(), key=lambda x: x[1])

    lines = []
    lines.append("--!strict")
    lines.append(f"-- {MODEL_NAME}.luau")
    lines.append("-- 2D Grease Pencil renderer for Rive")
    lines.append("-- Uses Catmull-Rom -> Cubic Bezier for smooth stroke outlines")
    lines.append("")

    # Requires
    for label in part_labels:
        lines.append(f'local Part{label} = require("{MODEL_NAME}Part{label}Data")')
    lines.append("")

    # Types
    lines.append("-- ============================================================================")
    lines.append("-- TYPES")
    lines.append("-- ============================================================================")
    lines.append("")
    lines.append("type StrokeEntry = {")
    lines.append("    pts: { { number } },")
    lines.append("    c: number,")
    lines.append("    fill: boolean,")
    lines.append("    sw: number,")
    lines.append("}")
    lines.append("")
    lines.append("type DrawCommand = {")
    lines.append("    path: Path,")
    lines.append("    paint: Paint,")
    lines.append("}")
    lines.append("")

    # Export type
    lines.append(f"export type {MODEL_NAME} = {{")
    lines.append("    -- Position & scale")
    lines.append("    scale: Input<number>,")
    lines.append("    offsetX: Input<number>,")
    lines.append("    offsetY: Input<number>,")
    lines.append("    -- Rendering")
    lines.append("    strokeScale: Input<number>,")
    lines.append("    -- Color palette (Property Group)")
    for mat_name, _ in sorted_mats:
        prop_name = MATERIAL_PROP_NAMES[mat_name]
        lines.append(f"    {prop_name}: Input<Color>,")
    lines.append("    -- Internal state")
    lines.append("    drawCommands: { DrawCommand },")
    lines.append("    context: Context?,")
    lines.append("}")
    lines.append("")

    # getColors function
    lines.append("-- ============================================================================")
    lines.append("-- COLOR PALETTE (built from Property Group inputs)")
    lines.append("-- ============================================================================")
    lines.append("")
    lines.append(f"local function getColors(self: {MODEL_NAME}): {{ Color }}")
    lines.append("    return {")
    for mat_name, cat_idx in sorted_mats:
        prop_name = MATERIAL_PROP_NAMES[mat_name]
        lines.append(f"        self.{prop_name},       -- {cat_idx}: {mat_name}")
    lines.append("    }")
    lines.append("end")
    lines.append("")

    # Catmull-Rom → Bezier conversion
    lines.append("-- ============================================================================")
    lines.append("-- CATMULL-ROM TO BEZIER CONVERSION")
    lines.append("-- ============================================================================")
    lines.append("-- Blender GP uses Catmull-Rom spline interpolation for stroke rendering.")
    lines.append("-- We convert to cubic Bezier for Rive's cubicTo() API.")
    lines.append("-- For each segment P1->P2, given neighbors P0 and P3:")
    lines.append("--   CP1 = P1 + (P2 - P0) / 6")
    lines.append("--   CP2 = P2 - (P3 - P1) / 6")
    lines.append("")
    lines.append("local SMOOTH_THRESHOLD = 200  -- strokes with < 200 points use cubic bezier")
    lines.append("")

    # buildSmoothPath
    lines.append("local function buildSmoothPath(")
    lines.append("    pts: { { number } },")
    lines.append("    sc: number,")
    lines.append("    ox: number,")
    lines.append("    oy: number,")
    lines.append("    closePath: boolean")
    lines.append("): Path")
    lines.append("    local p = Path.new()")
    lines.append("    local n = #pts")
    lines.append("")
    lines.append("    local tx: { number } = {}")
    lines.append("    local ty: { number } = {}")
    lines.append("    for i = 1, n do")
    lines.append("        tx[i] = pts[i][1] * sc + ox")
    lines.append("        ty[i] = pts[i][2] * sc + oy")
    lines.append("    end")
    lines.append("")
    lines.append("    p:moveTo(Vector.xy(tx[1], ty[1]))")
    lines.append("")
    lines.append("    if n == 2 then")
    lines.append("        p:lineTo(Vector.xy(tx[2], ty[2]))")
    lines.append("    elseif n >= 3 then")
    lines.append("        for i = 1, n - 1 do")
    lines.append("            local p0x: number = tx[math.max(1, i - 1)]")
    lines.append("            local p0y: number = ty[math.max(1, i - 1)]")
    lines.append("            local p1x: number = tx[i]")
    lines.append("            local p1y: number = ty[i]")
    lines.append("            local p2x: number = tx[i + 1]")
    lines.append("            local p2y: number = ty[i + 1]")
    lines.append("            local p3x: number = tx[math.min(n, i + 2)]")
    lines.append("            local p3y: number = ty[math.min(n, i + 2)]")
    lines.append("")
    lines.append("            local cp1x: number = p1x + (p2x - p0x) / 6")
    lines.append("            local cp1y: number = p1y + (p2y - p0y) / 6")
    lines.append("            local cp2x: number = p2x - (p3x - p1x) / 6")
    lines.append("            local cp2y: number = p2y - (p3y - p1y) / 6")
    lines.append("")
    lines.append("            p:cubicTo(")
    lines.append("                Vector.xy(cp1x, cp1y),")
    lines.append("                Vector.xy(cp2x, cp2y),")
    lines.append("                Vector.xy(p2x, p2y)")
    lines.append("            )")
    lines.append("        end")
    lines.append("    end")
    lines.append("")
    lines.append("    if closePath then")
    lines.append("        p:close()")
    lines.append("    end")
    lines.append("")
    lines.append("    return p")
    lines.append("end")
    lines.append("")

    # buildLinearPath
    lines.append("local function buildLinearPath(")
    lines.append("    pts: { { number } },")
    lines.append("    sc: number,")
    lines.append("    ox: number,")
    lines.append("    oy: number,")
    lines.append("    closePath: boolean")
    lines.append("): Path")
    lines.append("    local p = Path.new()")
    lines.append("    p:moveTo(Vector.xy(pts[1][1] * sc + ox, pts[1][2] * sc + oy))")
    lines.append("    for i = 2, #pts do")
    lines.append("        p:lineTo(Vector.xy(pts[i][1] * sc + ox, pts[i][2] * sc + oy))")
    lines.append("    end")
    lines.append("    if closePath then")
    lines.append("        p:close()")
    lines.append("    end")
    lines.append("    return p")
    lines.append("end")
    lines.append("")

    # processStrokes
    lines.append("-- ============================================================================")
    lines.append("-- STROKE PROCESSING")
    lines.append("-- ============================================================================")
    lines.append("")
    lines.append(f"local function processStrokes(")
    lines.append(f"    self: {MODEL_NAME},")
    lines.append("    strokes: { StrokeEntry },")
    lines.append("    sc: number,")
    lines.append("    ox: number,")
    lines.append("    oy: number,")
    lines.append("    strokeSc: number,")
    lines.append("    colors: { Color }")
    lines.append(")")
    lines.append("    for _, stroke in ipairs(strokes) do")
    lines.append("        local pts = stroke.pts")
    lines.append("        if #pts < 2 then")
    lines.append("            continue")
    lines.append("        end")
    lines.append("")
    lines.append("        local color = colors[stroke.c] or colors[1]")
    lines.append("        local useSmooth = #pts < SMOOTH_THRESHOLD")
    lines.append("")
    lines.append("        -- Fill: closed path")
    lines.append("        if stroke.fill then")
    lines.append("            local fillPath: Path")
    lines.append("            if useSmooth then")
    lines.append("                fillPath = buildSmoothPath(pts, sc, ox, oy, true)")
    lines.append("            else")
    lines.append("                fillPath = buildLinearPath(pts, sc, ox, oy, true)")
    lines.append("            end")
    lines.append("            local fillPaint = Paint.with({ style = \"fill\", color = color })")
    lines.append("            table.insert(self.drawCommands, { path = fillPath, paint = fillPaint })")
    lines.append("        end")
    lines.append("")
    lines.append("        -- Stroke outline: OPEN path (never closed)")
    lines.append("        if stroke.sw > 0 then")
    lines.append("            local strokePath: Path")
    lines.append("            if useSmooth then")
    lines.append("                strokePath = buildSmoothPath(pts, sc, ox, oy, false)")
    lines.append("            else")
    lines.append("                strokePath = buildLinearPath(pts, sc, ox, oy, false)")
    lines.append("            end")
    lines.append("            local thickness = stroke.sw * strokeSc * 0.1")
    lines.append("            if thickness < 0.3 then")
    lines.append("                thickness = 0.3")
    lines.append("            end")
    lines.append("            local strokePaint = Paint.with({")
    lines.append("                style = \"stroke\",")
    lines.append("                color = color,")
    lines.append("                thickness = thickness,")
    lines.append("                cap = \"round\",")
    lines.append("                join = \"round\",")
    lines.append("            })")
    lines.append("            table.insert(self.drawCommands, { path = strokePath, paint = strokePaint })")
    lines.append("        end")
    lines.append("    end")
    lines.append("end")
    lines.append("")

    # Lifecycle
    lines.append("-- ============================================================================")
    lines.append("-- LIFECYCLE")
    lines.append("-- ============================================================================")
    lines.append("")
    lines.append(f"local function init(self: {MODEL_NAME}, context: Context): boolean")
    lines.append("    self.drawCommands = {}")
    lines.append("    self.context = context")
    lines.append("    return true")
    lines.append("end")
    lines.append("")
    lines.append(f"local function advance(self: {MODEL_NAME}, seconds: number): boolean")
    lines.append("    self.drawCommands = {}")
    lines.append("")
    lines.append("    local sc = self.scale")
    lines.append("    local ox = self.offsetX")
    lines.append("    local oy = self.offsetY")
    lines.append("    local strokeSc = self.strokeScale")
    lines.append("    local colors = getColors(self)")
    lines.append("")
    lines.append("    -- Process all parts in draw order (back to front)")
    for label in part_labels:
        lines.append(f"    processStrokes(self, (Part{label} :: any).strokes :: {{ StrokeEntry }}, sc, ox, oy, strokeSc, colors)")
    lines.append("")
    lines.append("    return true")
    lines.append("end")
    lines.append("")
    lines.append(f"local function draw(self: {MODEL_NAME}, renderer: Renderer)")
    lines.append("    for _, cmd in ipairs(self.drawCommands) do")
    lines.append("        renderer:drawPath(cmd.path, cmd.paint)")
    lines.append("    end")
    lines.append("end")
    lines.append("")

    # Node export
    lines.append("-- ============================================================================")
    lines.append("-- NODE EXPORT")
    lines.append("-- ============================================================================")
    lines.append("")
    lines.append(f"return function(): Node<{MODEL_NAME}>")
    lines.append("    return {")
    lines.append("        -- Position & scale")
    lines.append("        scale = 1,")
    lines.append("        offsetX = 0,")
    lines.append("        offsetY = 0,")
    lines.append("        -- Rendering")
    lines.append("        strokeScale = 1,")
    lines.append("        -- Color palette")
    for mat_name, _ in sorted_mats:
        prop_name = MATERIAL_PROP_NAMES[mat_name]
        r, g, b = MATERIAL_COLORS[mat_name]
        lines.append(f"        {prop_name} = Color.rgba({r}, {g}, {b}, 255),")
    lines.append("        -- Internal state")
    lines.append("        drawCommands = {},")
    lines.append("        context = nil,")
    lines.append("        -- Lifecycle")
    lines.append("        init = init,")
    lines.append("        advance = advance,")
    lines.append("        draw = draw,")
    lines.append("    }")
    lines.append("end")
    lines.append("")

    content = "\n".join(lines)
    with open(filepath, "w") as f:
        f.write(content)

    print(f"  Written: {MODEL_NAME}.luau ({len(content) / 1024:.1f} KB)")


def main():
    print(f"\n{'='*60}")
    print(f"  Blender GP → Rive Exporter: {MODEL_NAME}")
    print(f"{'='*60}")

    # Ensure output dir exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: Collect strokes
    print("\n[1/4] Collecting strokes...")
    all_strokes = collect_strokes()
    total_pts = sum(len(s["pts"]) for s in all_strokes)
    print(f"  Collected: {len(all_strokes)} strokes, {total_pts} points")

    if not all_strokes:
        print("  ERROR: No strokes found. Check DRAW_ORDER and object/layer names.")
        return

    # Step 2: Normalize
    print("\n[2/4] Normalizing coordinates...")
    normalize_strokes(all_strokes)

    # Step 3: Split into parts
    print("\n[3/4] Splitting into part files...")
    parts = split_into_parts(all_strokes)
    print(f"  Split into {len(parts)} parts")

    part_labels = "ABCDEFGHIJKLMNOP"
    labels_used = []

    for i, part in enumerate(parts):
        label = part_labels[i]
        labels_used.append(label)
        write_part_file(part, label, i, OUTPUT_DIR)

    # Step 4: Generate Node Script
    print("\n[4/4] Generating Node Script...")
    write_node_script(labels_used, OUTPUT_DIR)

    # Summary
    print(f"\n{'='*60}")
    print(f"  Export complete!")
    print(f"  Files written to: {OUTPUT_DIR}")
    print(f"  {len(parts)} data files + 1 Node Script")
    print(f"  Total: {len(all_strokes)} strokes, {total_pts} points")
    print(f"{'='*60}")
    print(f"\n  Copy all .luau files to your Rive project.")
    print(f"  The Node Script '{MODEL_NAME}.luau' is the main entry point.")


if __name__ == "__main__":
    main()
else:
    # Running inside Blender scripting tab
    main()

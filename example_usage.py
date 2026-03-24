"""
Example usage of the Grease Pencil to Rive exporter
This script can be run in Blender's scripting environment
"""

import bpy

# Example 1: Create a simple Grease Pencil object with a stroke
def create_sample_grease_pencil():
    """Create a sample Grease Pencil object for testing"""
    
    # Create a new Grease Pencil object
    bpy.ops.object.gpencil_add(type='EMPTY')
    gp_obj = bpy.context.object
    gp_obj.name = "SampleDrawing"
    
    # Get the Grease Pencil data
    gp_data = gp_obj.data
    
    # Create a new layer
    layer = gp_data.layers.new('Layer1', set_active=True)
    
    # Create a new frame at frame 1
    frame = layer.frames.new(1)
    
    # Create a new stroke
    stroke = frame.strokes.new()
    stroke.line_width = 10
    
    # Add points to create a simple line
    stroke.points.add(count=4)
    stroke.points[0].co = (-1.0, 0.0, 0.0)
    stroke.points[1].co = (-0.5, 1.0, 0.0)
    stroke.points[2].co = (0.5, 1.0, 0.0)
    stroke.points[3].co = (1.0, 0.0, 0.0)
    
    # Set pressure for each point
    for point in stroke.points:
        point.pressure = 1.0
        point.strength = 1.0
    
    # Add a material
    mat = bpy.data.materials.new(name="BlackStroke")
    bpy.data.materials.create_gpencil_data(mat)
    gp_obj.data.materials.append(mat)
    
    # Set material color (for Blender 3.x)
    if mat.grease_pencil:
        mat.grease_pencil.color = (0.0, 0.0, 0.0, 1.0)  # Black
        mat.grease_pencil.fill_color = (1.0, 1.0, 1.0, 0.0)  # Transparent fill
    
    print(f"Created sample Grease Pencil object: {gp_obj.name}")
    return gp_obj


# Example 2: Export using the addon
def export_grease_pencil_to_rive(filepath):
    """Export the active Grease Pencil object to Rive format"""
    
    # Make sure we have a Grease Pencil object selected
    if not bpy.context.object or bpy.context.object.type != 'GPENCIL':
        print("Error: No Grease Pencil object selected")
        return
    
    # Call the export operator
    bpy.ops.export_scene.grease_pencil_to_rive(
        filepath=filepath,
        export_visible_only=True
    )
    
    print(f"Exported to: {filepath}")


# Example workflow
if __name__ == "__main__":
    # Step 1: Create a sample Grease Pencil object
    gp_obj = create_sample_grease_pencil()
    
    # Step 2: Make sure it's selected
    bpy.context.view_layer.objects.active = gp_obj
    
    # Step 3: Export to Rive format
    output_path = "/tmp/sample_export.lua"
    export_grease_pencil_to_rive(output_path)
    
    print("Example completed successfully!")

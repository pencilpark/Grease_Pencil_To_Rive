"""
Grease Pencil to Rive Exporter
Exports Blender Grease Pencil illustrations as Rive Node Scripts (Luau)
"""

bl_info = {
    "name": "Grease Pencil to Rive",
    "author": "Grease Pencil to Rive Contributors",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "File > Export > Rive (.lua)",
    "description": "Export Grease Pencil illustrations as Rive Node Scripts",
    "category": "Import-Export",
}

import bpy
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ExportHelper


class GreasePencilToRiveExporter:
    """Main exporter class that converts Grease Pencil data to Rive format"""
    
    def __init__(self, context, filepath, export_options):
        self.context = context
        self.filepath = filepath
        self.export_options = export_options
        
    def export(self):
        """Main export function"""
        gp_obj = self.context.object
        
        if not gp_obj or gp_obj.type != 'GPENCIL':
            return {'CANCELLED'}, "No Grease Pencil object selected"
        
        # Extract Grease Pencil data
        gp_data = self.extract_grease_pencil_data(gp_obj)
        
        # Convert to Rive Luau format
        rive_script = self.convert_to_rive_luau(gp_data)
        
        # Write to file
        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write(rive_script)
        
        return {'FINISHED'}, f"Successfully exported to {self.filepath}"
    
    def extract_grease_pencil_data(self, gp_obj):
        """Extract all relevant data from Grease Pencil object"""
        data = {
            'name': gp_obj.name,
            'layers': []
        }
        
        for layer in gp_obj.data.layers:
            # Skip hidden layers only if export_visible_only is enabled
            if self.export_options.get('export_visible_only', True) and layer.hide:
                continue
                
            layer_data = {
                'name': layer.info,
                'opacity': layer.opacity,
                'frames': []
            }
            
            for frame in layer.frames:
                frame_data = {
                    'frame_number': frame.frame_number,
                    'strokes': []
                }
                
                for stroke in frame.strokes:
                    stroke_data = {
                        'line_width': stroke.line_width,
                        'points': [],
                        'material_index': stroke.material_index,
                    }
                    
                    # Extract point coordinates
                    for point in stroke.points:
                        stroke_data['points'].append({
                            'x': point.co.x,
                            'y': point.co.y,
                            'z': point.co.z,
                            'pressure': point.pressure,
                            'strength': point.strength,
                        })
                    
                    frame_data['strokes'].append(stroke_data)
                
                layer_data['frames'].append(frame_data)
            
            data['layers'].append(layer_data)
        
        # Extract materials/colors
        data['materials'] = []
        if gp_obj.data.materials:
            for mat in gp_obj.data.materials:
                mat_data = {
                    'name': mat.name if mat else 'default',
                }
                # Get GP material settings if available
                if mat and mat.grease_pencil:
                    gp_mat = mat.grease_pencil
                    mat_data['stroke_color'] = list(gp_mat.color) if hasattr(gp_mat, 'color') else [0, 0, 0, 1]
                    mat_data['fill_color'] = list(gp_mat.fill_color) if hasattr(gp_mat, 'fill_color') else [1, 1, 1, 0]
                data['materials'].append(mat_data)
        
        return data
    
    def convert_to_rive_luau(self, gp_data):
        """Convert Grease Pencil data to Rive Luau node script format"""
        
        # Generate Luau script
        script = "-- Rive Node Script generated from Blender Grease Pencil\n"
        script += f"-- Source: {gp_data['name']}\n\n"
        
        script += "local RiveNode = {}\n\n"
        
        # Add materials (using 1-based indexing for Luau)
        script += "-- Materials (1-based indexing for Luau)\n"
        script += "RiveNode.materials = {\n"
        for i, mat in enumerate(gp_data['materials']):
            stroke_color = mat.get('stroke_color', [0, 0, 0, 1])
            fill_color = mat.get('fill_color', [1, 1, 1, 0])
            script += f"    [{i + 1}] = {{\n"
            script += f"        name = \"{mat['name']}\",\n"
            script += f"        strokeColor = {{{stroke_color[0]:.3f}, {stroke_color[1]:.3f}, {stroke_color[2]:.3f}, {stroke_color[3]:.3f}}},\n"
            script += f"        fillColor = {{{fill_color[0]:.3f}, {fill_color[1]:.3f}, {fill_color[2]:.3f}, {fill_color[3]:.3f}}}\n"
            script += "    },\n"
        script += "}\n\n"
        
        # Add layers
        script += "-- Layers\n"
        script += "RiveNode.layers = {\n"
        for layer in gp_data['layers']:
            script += f"    {{\n"
            script += f"        name = \"{layer['name']}\",\n"
            script += f"        opacity = {layer['opacity']:.3f},\n"
            script += f"        frames = {{\n"
            
            for frame in layer['frames']:
                script += f"            {{\n"
                script += f"                frameNumber = {frame['frame_number']},\n"
                script += f"                strokes = {{\n"
                
                for stroke in frame['strokes']:
                    script += f"                    {{\n"
                    script += f"                        lineWidth = {stroke['line_width']},\n"
                    script += f"                        materialIndex = {stroke['material_index'] + 1},\n"
                    script += f"                        points = {{\n"
                    
                    for point in stroke['points']:
                        script += f"                            {{{point['x']:.6f}, {point['y']:.6f}, {point['z']:.6f}}},\n"
                    
                    script += f"                        }}\n"
                    script += f"                    }},\n"
                
                script += f"                }}\n"
                script += f"            }},\n"
            
            script += f"        }}\n"
            script += f"    }},\n"
        script += "}\n\n"
        
        # Add helper function to render
        script += "-- Helper function to create Rive shapes from the data\n"
        script += "function RiveNode:createShapes()\n"
        script += "    local shapes = {}\n"
        script += "    for _, layer in ipairs(self.layers) do\n"
        script += "        for _, frame in ipairs(layer.frames) do\n"
        script += "            for _, stroke in ipairs(frame.strokes) do\n"
        script += "                local path = {}\n"
        script += "                for _, point in ipairs(stroke.points) do\n"
        script += "                    table.insert(path, {x = point[1], y = point[2]})\n"
        script += "                end\n"
        script += "                local material = self.materials[stroke.materialIndex] or self.materials[1]\n"
        script += "                table.insert(shapes, {\n"
        script += "                    path = path,\n"
        script += "                    lineWidth = stroke.lineWidth,\n"
        script += "                    strokeColor = material.strokeColor,\n"
        script += "                    fillColor = material.fillColor\n"
        script += "                })\n"
        script += "            end\n"
        script += "        end\n"
        script += "    end\n"
        script += "    return shapes\n"
        script += "end\n\n"
        
        script += "return RiveNode\n"
        
        return script


class EXPORT_OT_grease_pencil_to_rive(bpy.types.Operator, ExportHelper):
    """Export Grease Pencil to Rive Node Script"""
    bl_idname = "export_scene.grease_pencil_to_rive"
    bl_label = "Export Rive"
    bl_description = "Export Grease Pencil illustration as Rive Node Script (Luau)"
    
    filename_ext = ".lua"
    filter_glob: StringProperty(
        default="*.lua",
        options={'HIDDEN'},
    )
    
    export_visible_only: BoolProperty(
        name="Visible Layers Only",
        description="Export only visible layers",
        default=True,
    )
    
    def execute(self, context):
        export_options = {
            'export_visible_only': self.export_visible_only,
        }
        
        exporter = GreasePencilToRiveExporter(context, self.filepath, export_options)
        result, message = exporter.export()
        
        if result == {'FINISHED'}:
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)
        
        return result


def menu_func_export(self, context):
    """Add to File > Export menu"""
    self.layout.operator(EXPORT_OT_grease_pencil_to_rive.bl_idname, text="Rive (.lua)")


def register():
    """Register addon"""
    bpy.utils.register_class(EXPORT_OT_grease_pencil_to_rive)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    """Unregister addon"""
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.utils.unregister_class(EXPORT_OT_grease_pencil_to_rive)


if __name__ == "__main__":
    register()

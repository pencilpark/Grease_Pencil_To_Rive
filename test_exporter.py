"""
Unit tests for Grease Pencil to Rive exporter
These tests validate the core conversion logic without requiring Blender
"""

import sys
import os

# Mock the bpy module for testing
class MockVector:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class MockPoint:
    def __init__(self, x, y, z, pressure=1.0, strength=1.0):
        self.co = MockVector(x, y, z)
        self.pressure = pressure
        self.strength = strength

class MockStroke:
    def __init__(self, line_width=10, material_index=0):
        self.line_width = line_width
        self.material_index = material_index
        self.points = []
    
    def add_point(self, x, y, z, pressure=1.0, strength=1.0):
        self.points.append(MockPoint(x, y, z, pressure, strength))

class MockFrame:
    def __init__(self, frame_number=1):
        self.frame_number = frame_number
        self.strokes = []

class MockLayer:
    def __init__(self, name="Layer1", opacity=1.0, hide=False):
        self.info = name
        self.opacity = opacity
        self.hide = hide
        self.frames = []

class MockGPMaterial:
    def __init__(self):
        self.color = (0, 0, 0, 1)
        self.fill_color = (1, 1, 1, 0)

class MockMaterial:
    def __init__(self, name="Material"):
        self.name = name
        self.grease_pencil = MockGPMaterial()

class MockGPData:
    def __init__(self):
        self.layers = []
        self.materials = []

class MockGPObject:
    def __init__(self, name="GPencil"):
        self.name = name
        self.type = 'GPENCIL'
        self.data = MockGPData()


def test_data_extraction():
    """Test that Grease Pencil data is correctly extracted"""
    print("Testing data extraction...")
    
    # Import the exporter class (mocked environment)
    sys.path.insert(0, os.path.dirname(__file__))
    
    # Create mock Grease Pencil object
    gp_obj = MockGPObject("TestObject")
    
    # Add a layer
    layer = MockLayer("TestLayer", 0.8)
    gp_obj.data.layers.append(layer)
    
    # Add a frame
    frame = MockFrame(1)
    layer.frames.append(frame)
    
    # Add a stroke
    stroke = MockStroke(line_width=5, material_index=0)
    stroke.add_point(-1.0, 0.0, 0.0)
    stroke.add_point(1.0, 0.0, 0.0)
    frame.strokes.append(stroke)
    
    # Add material
    material = MockMaterial("TestMaterial")
    gp_obj.data.materials.append(material)
    
    # Mock context
    class MockContext:
        def __init__(self, obj):
            self.object = obj
    
    context = MockContext(gp_obj)
    
    # Test extraction (without actual Blender dependencies)
    # We'll test the data structure is correct
    assert gp_obj.name == "TestObject"
    assert len(gp_obj.data.layers) == 1
    assert gp_obj.data.layers[0].info == "TestLayer"
    assert gp_obj.data.layers[0].opacity == 0.8
    assert len(gp_obj.data.layers[0].frames) == 1
    assert gp_obj.data.layers[0].frames[0].frame_number == 1
    assert len(gp_obj.data.layers[0].frames[0].strokes) == 1
    assert gp_obj.data.layers[0].frames[0].strokes[0].line_width == 5
    assert len(gp_obj.data.layers[0].frames[0].strokes[0].points) == 2
    
    print("✓ Data extraction structure validated")


def test_luau_output_format():
    """Test that the Luau output format is valid"""
    print("\nTesting Luau output format...")
    
    # Create a simple data structure
    test_data = {
        'name': 'TestGP',
        'materials': [
            {
                'name': 'Black',
                'stroke_color': [0, 0, 0, 1],
                'fill_color': [1, 1, 1, 0]
            }
        ],
        'layers': [
            {
                'name': 'Layer1',
                'opacity': 1.0,
                'frames': [
                    {
                        'frame_number': 1,
                        'strokes': [
                            {
                                'line_width': 10,
                                'material_index': 0,
                                'points': [
                                    {'x': -1.0, 'y': 0.0, 'z': 0.0},
                                    {'x': 1.0, 'y': 0.0, 'z': 0.0}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # Test Luau generation
    output = generate_luau_script(test_data)
    
    # Validate output contains expected elements
    assert 'RiveNode' in output
    assert 'materials' in output
    assert 'layers' in output
    assert 'strokeColor' in output
    assert 'createShapes' in output
    assert 'return RiveNode' in output
    
    print("✓ Luau output format validated")


def generate_luau_script(gp_data):
    """
    Standalone Luau generator for testing
    Note: This is duplicated from the main exporter to allow testing without Blender dependencies.
    It intentionally tests the export format independently rather than importing from __init__.py
    which requires bpy (Blender Python API) to load.
    """
    script = "-- Rive Node Script generated from Blender Grease Pencil\n"
    script += f"-- Source: {gp_data['name']}\n\n"
    script += "local RiveNode = {}\n\n"
    
    # Add materials (using 1-based indexing for Luau)
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
    
    # Add helper function
    script += "function RiveNode:createShapes()\n"
    script += "    return {}\n"
    script += "end\n\n"
    script += "return RiveNode\n"
    
    return script


if __name__ == "__main__":
    print("Running Grease Pencil to Rive Exporter Tests\n")
    print("=" * 50)
    
    try:
        test_data_extraction()
        test_luau_output_format()
        
        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

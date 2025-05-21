# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import ezdxf
from ezdxf.math import Vec2

#%% Converting 3D poly to LW poly (the generated grains are somehow in 3D poly format)
def convert_3dpoly_to_lwpoly(input_path, output_path):
    # Load the DXF file
    doc = ezdxf.readfile(input_path)
    msp = doc.modelspace()
 
    # Create a new DXF document with a compatible version
    new_doc = ezdxf.new(dxfversion="R2010")
    new_msp = new_doc.modelspace()
 
    count = 0
    for entity in msp.query("POLYLINE"):
        if entity.is_3d_polyline:
            # Extract 2D points (flattening Z)
            points_2d = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
            # Auto-close if start and end match
            is_closed = points_2d[0] == points_2d[-1]
            new_poly = new_msp.add_lwpolyline(points_2d, close=is_closed)
            new_poly.dxf.layer = entity.dxf.layer
            count += 1
 
    if count == 0:
        print("⚠️ No 3D polylines found.")
    else:
        new_doc.saveas(output_path)
        print(f"✅ Converted {count} 3D polylines to LWPOLYLINE. Saved to: {output_path}")
 
# ✅ Example usage
convert_3dpoly_to_lwpoly(
    input_path=r"E:\\XXX.dxf",
    output_path=r"E:\\XXX_LW.dxf"
)
    
#%% Rescaling grains per direction

def get_centroid(points):
    """Compute centroid of a closed polygon (assuming it is simple and planar)."""
    x_list = [p[0] for p in points]
    y_list = [p[1] for p in points]
    n = len(points)
    area = 0.0
    cx = 0.0
    cy = 0.0
 
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
 
    area *= 0.5
    if area == 0:
        return (sum(x_list) / n, sum(y_list) / n)  # fallback: average of vertices
    cx /= (6.0 * area)
    cy /= (6.0 * area)
    return (cx, cy)
 
def rescale_polygon(points, center, scale_x, scale_y):
    """Rescale a list of (x, y) points around a center point."""
    cx, cy = center
    scaled_points = []
    for x, y in points:
        new_x = cx + (x - cx) * scale_x
        new_y = cy + (y - cy) * scale_y
        scaled_points.append((new_x, new_y))
    return scaled_points
 
def rescale_dxf(input_path, output_path, scale_x=1.0, scale_y=1.0):
    doc = ezdxf.readfile(input_path)
    msp = doc.modelspace()
    new_doc = ezdxf.new()
    new_msp = new_doc.modelspace()
 
    for entity in msp.query("LWPOLYLINE"):
        if not entity.closed:
            continue
 
        points = [(p[0], p[1]) for p in entity.get_points()]
        center = get_centroid(points)
        scaled_points = rescale_polygon(points, center, scale_x, scale_y)
 
        new_poly = new_msp.add_lwpolyline(scaled_points, close=True)
        new_poly.dxf.layer = entity.dxf.layer
 
    new_doc.saveas(output_path)
    print(f"Saved rescaled file to: {output_path}")
    
    
# Example usage (input,output, scale x, scale y)
rescale_dxf("E:\\XXX_LW.dxf", "E:\\XXX_rescale.dxf",scale_x = 2, scale_y = 0.5)
    
    
    
# -*- coding: utf-8 -*-
"""
DXF → tiled binary raster (multicore)

- No matplotlib
- No size limits
- True binary output
- Parallel tile rendering
"""

import ezdxf
import numpy as np
from PIL import Image, ImageDraw
from multiprocessing import Pool, cpu_count
import os


# -----------------------------
# DXF → polygons
# -----------------------------
def dxf_to_polygons(dxf_path):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    polygons = []

    for e in msp:
        if e.dxftype() == "LWPOLYLINE" and e.closed:
            pts = [(p[0], p[1]) for p in e.get_points()]
            if len(pts) >= 3:
                polygons.append(pts)

        elif e.dxftype() == "POLYLINE" and e.is_closed:
            pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
            if len(pts) >= 3:
                polygons.append(pts)

    return polygons


# -----------------------------
# Normalize to domain
# -----------------------------
def normalize_polygons(polygons, size_mm):
    all_x = [x for poly in polygons for x, _ in poly]
    all_y = [y for poly in polygons for _, y in poly]

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    width = max_x - min_x
    height = max_y - min_y

    scale_x = size_mm[0] / width
    scale_y = size_mm[1] / height
    scale = min(scale_x, scale_y)

    normalized = []
    for poly in polygons:
        new_poly = [
            ((x - min_x) * scale, (y - min_y) * scale)
            for x, y in poly
        ]
        normalized.append(new_poly)

    return normalized


# -----------------------------
# Tile rendering
# -----------------------------
def render_tile(args):
    tile_x, tile_y, tile_w, tile_h, polygons_px, tile_size = args

    img = Image.new("1", (tile_w, tile_h), 0)
    draw = ImageDraw.Draw(img)

    x0 = tile_x * tile_size
    y0 = tile_y * tile_size

    for poly in polygons_px:
        shifted = [(x - x0, y - y0) for x, y in poly]
        draw.polygon(shifted, fill=1)

    return (tile_x, tile_y, img)


# -----------------------------
# Main tiling pipeline
# -----------------------------
def rasterize_tiled(polygons, size_mm, dpi, tile_size=4096, out_path="output.png"):
    # mm → pixels
    px_per_mm = dpi / 25.4
    width_px = int(size_mm[0] * px_per_mm)
    height_px = int(size_mm[1] * px_per_mm)

    print(f"Final image size: {width_px} x {height_px}")

    # convert polygons to pixel coords
    polygons_px = []
    for poly in polygons:
        poly_px = [(x * px_per_mm, y * px_per_mm) for x, y in poly]
        polygons_px.append(poly_px)

    tiles_x = (width_px + tile_size - 1) // tile_size
    tiles_y = (height_px + tile_size - 1) // tile_size

    print(f"Tiling: {tiles_x} x {tiles_y} tiles")

    # prepare jobs
    jobs = []
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            w = min(tile_size, width_px - tx * tile_size)
            h = min(tile_size, height_px - ty * tile_size)
            jobs.append((tx, ty, w, h, polygons_px, tile_size))

    # multiprocessing
    with Pool(cpu_count()) as pool:
        results = pool.map(render_tile, jobs)

    # assemble final image
    final = Image.new("1", (width_px, height_px), 0)

    for tx, ty, tile_img in results:
        final.paste(tile_img, (tx * tile_size, ty * tile_size))

    final.save(out_path)
    print("Saved:", out_path)


# -----------------------------
# MAIN
# -----------------------------
def main():
    dxf_path = 'Original\\DXF\\File.dxf'
    output_path = 'Generated\\Image\\File.png'

    dpi = 25400
    size_mm = (70, 60)

    polygons = dxf_to_polygons(dxf_path)
    polygons = normalize_polygons(polygons, size_mm)

    rasterize_tiled(
        polygons,
        size_mm=size_mm,
        dpi=dpi,
        tile_size=4096,   # safe tile size (<65536)
        out_path=output_path
    )


if __name__ == "__main__":
    main()
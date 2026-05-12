#v1.0 by Tang 20260512
# install ezdxf first

import math
from collections import Counter
import ezdxf
from ezdxf import path


# ---------------- USER SETTINGS ----------------

DXF_FILE = "Your//Files.dxf"

# Options:
#   "closed" = count only closed shapes
#   "all"    = count all supported curve/shape entities
MODE = "closed"

# Include shapes inside AutoCAD blocks?
INCLUDE_BLOCKS = True

# Tolerance for deciding whether an open polyline is visually closed
CLOSE_TOL = 1e-6

# Curve flattening tolerance for length approximation
# Smaller = more accurate but slower
FLATTEN_TOL = 0.01

# Ignore these layers if needed, for example ["Outline", "Frame"]
IGNORE_LAYERS = ["Outline"]

# -----------------------------------------------


SUPPORTED_TYPES = {
    "LINE",
    "ARC",
    "CIRCLE",
    "ELLIPSE",
    "SPLINE",
    "LWPOLYLINE",
    "POLYLINE",
}


def dist(p1, p2):
    return math.dist((p1[0], p1[1], p1[2]), (p2[0], p2[1], p2[2]))


def path_length(entity, flatten_tol=0.01):
    """
    Approximate entity length by converting to a path and flattening curves.
    Works for lines, arcs, circles, ellipses, splines, polylines, etc.
    """
    try:
        p = path.make_path(entity)
        pts = list(p.flattening(distance=flatten_tol))
    except Exception:
        return 0.0

    if len(pts) < 2:
        return 0.0

    return sum(dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def endpoints_close(entity, tol=1e-6):
    """
    Detect whether an entity is visually closed by comparing start and end points.
    Useful for polylines whose DXF closed flag is not set.
    """
    try:
        p = path.make_path(entity)
        pts = list(p.flattening(distance=tol))
    except Exception:
        return False

    if len(pts) < 2:
        return False

    return dist(pts[0], pts[-1]) <= tol


def is_closed_shape(entity, tol=1e-6):
    dxftype = entity.dxftype()

    if dxftype == "CIRCLE":
        return True

    if dxftype == "LWPOLYLINE":
        return bool(entity.closed) or endpoints_close(entity, tol)

    if dxftype == "POLYLINE":
        return bool(entity.is_closed) or endpoints_close(entity, tol)

    if dxftype == "SPLINE":
        return bool(getattr(entity, "closed", False)) or endpoints_close(entity, tol)

    if dxftype == "ELLIPSE":
        return endpoints_close(entity, tol)

    # LINE and ARC are normally open
    return endpoints_close(entity, tol)


def iter_entities(layout, include_blocks=True):
    """
    Iterate through modelspace entities.
    If INCLUDE_BLOCKS is True, INSERT block contents are expanded.
    """
    for entity in layout:
        if entity.dxftype() == "INSERT" and include_blocks:
            try:
                for virtual_entity in entity.virtual_entities():
                    yield virtual_entity
            except Exception:
                pass
        else:
            yield entity


def analyze_dxf(
    dxf_file,
    mode="closed",
    include_blocks=True,
    close_tol=1e-6,
    flatten_tol=0.01,
    ignore_layers=None,
):
    if ignore_layers is None:
        ignore_layers = []

    doc = ezdxf.readfile(dxf_file)
    msp = doc.modelspace()

    count = 0
    total_length = 0.0
    type_counter = Counter()
    skipped_counter = Counter()

    for entity in iter_entities(msp, include_blocks=include_blocks):
        dxftype = entity.dxftype()

        layer = getattr(entity.dxf, "layer", "")
        if layer in ignore_layers:
            skipped_counter[f"ignored layer: {layer}"] += 1
            continue

        if dxftype not in SUPPORTED_TYPES:
            skipped_counter[dxftype] += 1
            continue

        closed = is_closed_shape(entity, tol=close_tol)

        if mode == "closed" and not closed:
            skipped_counter[f"open {dxftype}"] += 1
            continue

        count += 1
        type_counter[dxftype] += 1
        total_length += path_length(entity, flatten_tol=flatten_tol)

    return count, total_length, type_counter, skipped_counter


if __name__ == "__main__":
    count, total_length, type_counter, skipped_counter = analyze_dxf(
        DXF_FILE,
        mode=MODE,
        include_blocks=INCLUDE_BLOCKS,
        close_tol=CLOSE_TOL,
        flatten_tol=FLATTEN_TOL,
        ignore_layers=IGNORE_LAYERS,
    )

    if MODE == "closed":
        print("Mode: closed shapes only")
        print(f"Number of closed grains: {count}")
        print(f"Total closed-grain perimeter: {total_length}")
    else:
        print("Mode: all supported shapes")
        print(f"Number of supported shapes: {count}")
        print(f"Total curve/perimeter length: {total_length}")

    print("\nCounted entity types:")
    for k, v in type_counter.items():
        print(f"  {k}: {v}")

    print("\nSkipped / not counted:")
    for k, v in skipped_counter.items():
        print(f"  {k}: {v}")
"""Sanity checks on the built model: every print file watertight, nothing overlapping the body,
arch-to-arch distance at counter level.  Run from the repo root after smiley.py:
    PYTHONPATH=. .venv/bin/python tools/check.py
"""
import glob

import manifold3d as mf
import numpy as np
import trimesh

import smiley as s


def load(f):
    t = trimesh.load(f)
    return t, mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32),
                                  tri_verts=np.asarray(t.faces, np.uint32)))


for f in sorted(glob.glob("print/smiley_*.stl")):
    t, _ = load(f)
    print(f"{f.split('/')[-1]:28s} watertight {t.is_watertight}  size {np.round(t.extents, 1)}")
_, body = load("out/smiley_body.stl")
for k in ["fixtures", "soap", "brush", "sponge"]:
    _, ph = load(f"out/smiley_phantom_{k}.stl")
    print(f"{k:9s} overlap with body {round((body ^ ph).volume(), 2)} mm3")
_, div = load("out/smiley_divider.stl")
print(f"T insert  overlap with body {round((body ^ div).volume(), 2)} mm3")
pts = np.vstack([np.array(p) for p in body.slice(0.5).to_polygons()])
band = pts[np.abs(pts[:, 1] - s.L["fix_y"]) < 0.5]
print("arches at the fixture line: x", band[:, 0].min().round(1), "..", band[:, 0].max().round(1))

"""Drain check: the 4 mm of air above the sloped tower floor, minus the body, split into connected pieces.
Every probe (corners of both halves and both T pockets) must land in the piece that reaches the bowl,
and the trace below shows that water's path through the tunnel into the bowl.
Run from the repo root after smiley.py:  PYTHONPATH=. .venv/bin/python tools/flow.py [film_mm]
"""
import sys; sys.path.insert(0, '.')
import trimesh, numpy as np, manifold3d as mf, smiley as s
L, P = s.L, s.P
t = trimesh.load('out/smiley_body.stl')
body = mf.Manifold(mf.Mesh(t.vertices.astype(np.float32), t.faces.astype(np.uint32)))
w, Tx, Ty0, Ty1 = P['wall'], L['Tx'], L['Ty0'], L['Ty1']
# sloped "floor + film" solid built as two halves (abs(x) slope)
def half(xa, xb, dz):
    import cadquery as cq
    z0 = L['z_out'] - 6
    bot = [cq.Vector(xa, Ty0 - 20, z0), cq.Vector(xb, Ty0 - 20, z0), cq.Vector(xb, Ty1 + 5, z0), cq.Vector(xa, Ty1 + 5, z0)]
    top = [cq.Vector(v.x, v.y, s.tray_floor_z(P, L, v.x, v.y) + dz) for v in bot]
    return s.to_manifold(cq.Workplane().add(cq.Solid.makeLoft([cq.Wire.makePolygon(bot, close=True), cq.Wire.makePolygon(top, close=True)], ruled=True)))
film = half(-Tx - 5, 0, FILM := float(sys.argv[1]) if len(sys.argv) > 1 else 4.0) + half(0, Tx + 5, FILM)
air = film - body
pieces = air.decompose()
print('film', FILM, 'mm, pieces:', len(pieces))
xb0, xd = L['xb0'], L['xd']
probes = {'mid-left back': (-5.4, Ty1 - w - 4), 'mid-right back': (5.4, Ty1 - w - 4),
          'left pocket back': (-Tx + w + 1.5, Ty1 - w - 4), 'right pocket back': (Tx - w - 1.5, Ty1 - w - 4),
          'left pocket front': (-Tx + w + 1.5, L['fix_y'] + L['fix_rc'] + w + 3), 'right pocket front': (Tx - w - 1.5, L['fix_y'] + L['fix_rc'] + w + 3), 'front-left center': (-20, Ty0 + w + 3), 'front-right center': (20, Ty0 + w + 3),
          'bowl (trough)': (0, L['Ty0'] - 30)}
for i, pc in enumerate(sorted(pieces, key=lambda m: -m.volume())):
    bb = pc.bounding_box()
    hits = []
    for name, (x, y) in probes.items():
        z = s.tray_floor_z(P, L, x, y) + 1.0 if 'bowl' not in name else None
        for zz in ([z] if z is not None else np.arange(L['z_out'] - 6, L['z_out'] + 4, 0.5)):
            if (pc ^ mf.Manifold.cube((0.4, 0.4, 0.4), True).translate((x, y, zz))).volume() > 1e-4:
                hits.append(name); break
    if pc.volume() > 5 or hits:
        print(f'  piece {i}: vol {pc.volume():.0f} mm3, y {bb[1]:.0f}..{bb[4]:.0f}, contains: {hits}')
pc = sorted(pieces, key=lambda m: -m.volume())[1]
for y in np.arange(Ty0 + 4, Ty0 - 24, -4):
    sl = pc ^ mf.Manifold.cube((60, 4, 60), True).translate((0, y - 2, L['z_out']))
    bb = sl.bounding_box() if sl.volume() > 0 else None
    print(f'  y {y:6.1f}: water vol {sl.volume():7.1f}', '' if bb is None else f'x {bb[0]:.1f}..{bb[3]:.1f} z {bb[2]:.1f}..{bb[5]:.1f}')

"""Sink organizer with a shared sloped drain pan that empties through a little
figure sitting in an armchair built into the front wall, legs dangling over
the edge, "peeing" into the sink.

Layout (top view, sink side at the bottom):
    back row :  [ soap pad          ][ brush slot     ]
    front row:  [ sponge, on edge   ][ figure in chair]

Coordinates: X = left/right, Y = front(0) -> back, Z = up. Units: mm.
Run:  .venv/bin/python organizer.py   -> writes out/*.stl
"""
import math
import os

import cadquery as cq
import manifold3d as mf
import numpy as np
import trimesh

# ---------------------------------------------------------------- parameters
P = dict(
    # things we hold
    sponge_l=110, sponge_h=70, sponge_t=30,  # sponge stands on its long edge: l along X, t front/back
    soap_l=82, soap_w=45,             # EKOLN base (oval) - placeholder, measure!
    brush_slot_l=70, brush_slot_w=28, brush_slot_h=60,  # inner size of the upright-brush slot

    # body
    wall=3.0,
    shelf=3.0,                        # ledge inside the pan the inserts rest on
    clearance=2.0,                    # margin around the sponge rack, soap ring and brush slot
    corner_r=8.0,
    floor_low=20.0,                   # floor height at the drain (= plinth height)
    slope_x_deg=2.0,                  # floor fall toward the drain, sideways
    slope_y_deg=3.0,                  # floor fall toward the drain, front/back
    rim_above_inserts=10.0,           # how far walls rise above the insert tops

    # inserts
    insert_t=3.0, insert_gap=0.4, rib_h=4.0, rib_w=2.0, slot_w=3.0,
    sponge_gap=2.0,                   # play on each side of the sponge in its rack
    rack_h=35.0, rack_t=2.4,          # height / thickness of the sponge rack walls

    # drain / figure (figure sits in the front row, right of the sponge)
    figure_x=None,                    # None = centered in its cell
    notch_w=27.0,                     # gap in the front wall the thighs pass through
    armrest_w=9.0, armrest_h=15.0,    # chair arms beside him (height above the seat)
    backrest_h=30.0, water_gap=6.0,   # backrest top above seat; opening under it for water
    groove_w=7.0, groove_drop=1.5,
    spout_len=12.0, spout_od=7.5, spout_id=4.5, spout_tilt_deg=15.0,
    drip_ring_from_tip=2.5,           # groove around the spout so creeping drops fall off there
    drip_groove=(4.0, 2.5, 2.0),      # underside groove: distance from front edge, width, depth
)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane().box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl(p0, p1, r):
    v = cq.Vector(*p1) - cq.Vector(*p0)
    return cq.Workplane().add(cq.Solid.makeCylinder(r, v.Length, cq.Vector(*p0), v.normalized()))


def sphere(c, r):
    # tilt each sphere's axis a little differently so seams of touching spheres never coincide
    # (coincident seams make OpenCascade booleans silently drop solids)
    k = c[0] * 0.37 + c[1] * 0.71 + c[2] * 1.13 + r
    axis = cq.Vector(0.3 * math.sin(k), 0.3 * math.cos(k), 1)
    return cq.Workplane().add(cq.Solid.makeSphere(r, cq.Vector(*c), axis, angleDegrees1=-90))


def capsule(p0, p1, r):
    return cyl(p0, p1, r).union(sphere(p0, r)).union(sphere(p1, r))


# Organic shapes (the figure) are built as meshes with manifold3d: OpenCascade booleans on
# dozens of overlapping spheres silently drop solids.
SEG = 40


def m_sphere(c, r):
    return mf.Manifold.sphere(r, SEG).translate(tuple(c))


def m_capsule(p0, p1, r):
    return mf.Manifold.batch_hull([m_sphere(p0, r), m_sphere(p1, r)])


def m_union(parts):
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add)


def to_manifold(wp, tol=0.05):
    """CadQuery solid -> manifold3d mesh."""
    vs, ts = wp.val().tessellate(tol, 0.2)
    tm = trimesh.Trimesh(np.array([v.toTuple() for v in vs]), np.array(ts), process=True)
    tm.merge_vertices()
    m = mf.Manifold(mf.Mesh(vert_properties=tm.vertices.astype(np.float32), tri_verts=tm.faces.astype(np.uint32)))
    assert m.status() == mf.Error.NoError, m.status()
    return m


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts))


# ------------------------------------------------------------------ layout
def layout(p):
    c, w = p["clearance"], p["wall"]
    L = {}
    # cell sizes
    Ws = p["sponge_l"] + 2 * p["sponge_gap"] + 2 * p["rack_t"] + 2 * c   # sponge cell width
    Wf = p["notch_w"] + 2 * p["armrest_w"] + 8                           # figure cell width
    Wsoap = p["soap_l"] + 4 + 2 * c
    Wbrush = p["brush_slot_l"] + 5 + 2 * c
    Df = max(p["sponge_t"] + 2 * p["sponge_gap"] + 2 * p["rack_t"] + 2 * c, 30.0)  # front row depth
    Db = max(p["soap_w"] + 4 + 2 * c, p["brush_slot_w"] + 5 + 2 * c)              # back row depth
    inner_l = max(Ws + Wf, Wsoap + Wbrush)
    L["Lx"], L["D"] = inner_l + 2 * w, Df + Db + 2 * w
    L["Ws"], L["Wf"], L["Wsoap"], L["Df"], L["Db"] = Ws, Wf, Wsoap, Df, Db
    L["y_row"] = w + Df                                # boundary between front and back rows
    # cells as (x0, x1, y0, y1)
    L["sponge"] = (w, w + Ws, w, L["y_row"])
    L["fig"] = (w + Ws, L["Lx"] - w, w, L["y_row"])
    L["soap"] = (w, w + Wsoap, L["y_row"], L["D"] - w)
    L["brush"] = (w + Wsoap, L["Lx"] - w, L["y_row"], L["D"] - w)
    L["x_out"] = p["figure_x"] if p["figure_x"] is not None else (L["fig"][0] + L["fig"][1]) / 2
    L["yt"] = w + 11.0                                 # figure torso axis
    L["y_sump"] = L["yt"] + 10.5 + 3.0                 # drain inlet, just behind his back
    sx, sy = math.tan(math.radians(p["slope_x_deg"])), math.tan(math.radians(p["slope_y_deg"]))
    L["sx"], L["sy"] = sx, sy
    # lower (drain) cavity, inset by the shelf
    L["cx0"], L["cx1"] = w + p["shelf"], L["Lx"] - w - p["shelf"]
    L["cy0"], L["cy1"] = w + p["shelf"], L["D"] - w - p["shelf"]
    fmax = max(floor_z(p, L, x, y) for x in (L["cx0"], L["cx1"]) for y in (L["cy0"], L["cy1"]))
    L["shelf_z"] = math.ceil(fmax) + 2.0
    L["insert_top"] = L["shelf_z"] + p["insert_t"]
    L["top"] = L["insert_top"] + p["rim_above_inserts"]
    L["seat"] = p["floor_low"] + 2.0                   # notch bottom / where his thighs rest
    L["arm_z"] = L["seat"] + p["armrest_h"]
    return L


def floor_z(p, L, x, y):
    """Floor falls toward the sump at (x_out, y_sump) from every side."""
    return p["floor_low"] + L["sy"] * abs(y - L["y_sump"]) + L["sx"] * abs(x - L["x_out"])


# -------------------------------------------------------------------- body
def on_head(c, r, nx, ny, nz, inset=0.0):
    """Point on the head sphere (center c, radius r) along direction n, pushed in by inset."""
    k = math.sqrt(nx * nx + ny * ny + nz * nz)
    return (c[0] + (r - inset) * nx / k, c[1] + (r - inset) * ny / k, c[2] + (r - inset) * nz / k)


def figure(p, L):
    """Cartoon Manneken Pis, sitting: chibi proportions, curly hair, chubby belly. Returns a Manifold."""
    x, s, yt = L["x_out"], L["seat"], L["yt"]
    foot_z = 4.0                      # foot capsule axis; feet are trimmed flat on the counter (z=0)
    add, sub = [], []
    # body: round belly + smaller chest, pear shaped
    add += [m_sphere((x, yt - 1, s + 9), 11.5), m_capsule((x, yt, s + 12), (x, yt, s + 20), 9.0)]
    sub += [m_sphere((x, yt - 12.6, s + 9), 1.3)]                                  # belly button
    # head, big (chibi), face toward -Y
    hc, hr = (x, yt - 1.5, s + 38.0), 15.0
    add += [m_sphere(hc, hr)]
    # 45deg cone under the head so the chin grows out of the chest without supports
    zt45 = hc[2] - hr * math.sqrt(0.5)
    add += [mf.Manifold.cylinder(8.0, hr * math.sqrt(0.5) - 8.0, hr * math.sqrt(0.5), SEG)
            .translate((hc[0], hc[1], zt45 - 8.0))]
    for e in (-1, 1):
        eye = on_head(hc, hr, 0.36 * e, -0.93, 0.08, -0.6)
        sub += [mf.Manifold.sphere(2.2, SEG).scale((1, 1, 1.4)).translate(eye)]      # eyes: tall recessed ovals
        add += [m_sphere(on_head(hc, hr, 0.55 * e, -0.80, -0.28, 2.2), 3.4),         # cheeks
                m_sphere(on_head(hc, hr, 1.0 * e, 0.05, 0.0, 1.0), 3.8)]             # ears
    add += [m_sphere(on_head(hc, hr, 0, -1, -0.12, 0.6), 1.9)]                       # button nose
    for i in range(21):                                                              # smile groove
        a = math.radians(-50 + i * 5)
        sub += [m_sphere(on_head(hc, hr, 0.30 * math.sin(a), -0.92, -0.36 - 0.12 * math.cos(a), -0.3), 1.05)]
    # curly hair: little balls over the crown and back of the head
    gold, N = math.pi * (3 - math.sqrt(5)), 90
    for i in range(N):
        nz = 1 - 2 * (i + 0.5) / N
        rr = math.sqrt(1 - nz * nz)
        nx, ny = rr * math.cos(gold * i), rr * math.sin(gold * i)
        if nz > 0.42 or (ny > 0.15 and nz > -0.35) or (abs(nx) > 0.8 and nz > 0.15 and ny > -0.3):
            add += [m_sphere(on_head(hc, hr, nx, ny, nz, 0.6), 3.1)]
    # chubby limbs
    for e in (-1, 1):
        kx = x + 8.5 * e
        ankle = (kx + 1.5 * e, -4, foot_z + 1.0)
        add += [m_capsule((x + 6 * e, yt - 2, s + 5.5), (kx, -2, s + 5.5), 5.6),   # thigh
                m_capsule((kx, -2, s + 5.5), ankle, 5.0),                            # shin
                m_capsule(ankle, (kx + 1.5 * e, -10, foot_z), 4.6)]                  # foot
        ax = x + e * (p["notch_w"] / 2 + p["armrest_w"] / 2)
        elbow, hand = (ax, yt + 5, L["arm_z"] + 1.8), (ax, 1.5, L["arm_z"] + 1.8)   # sunk into the armrest
        add += [m_capsule((x + 8 * e, yt, s + 19), elbow, 3.8),                      # upper arm
                m_capsule(elbow, hand, 3.8), m_sphere(hand, 4.6)]                    # forearm on the armrest
    f = m_union(add) - m_union(sub)
    return f.trim_by_plane((0, 0, 1), 0.0)                                           # flat feet on the bed


def body(p, L):
    w, Lx, D, x = p["wall"], L["Lx"], L["D"], L["x_out"]
    b = box(0, Lx, 0, D, 0, L["top"]).edges("|Z").fillet(p["corner_r"])
    # upper pocket where the inserts drop in
    b = b.cut(box(w, Lx - w, w, D - w, L["shelf_z"], L["top"] + 1).edges("|Z").fillet(p["corner_r"] - w))
    # lower drain cavity
    b = b.cut(box(L["cx0"], L["cx1"], L["cy0"], L["cy1"], p["floor_low"] - 1, L["shelf_z"] + 0.01))
    # sloped floor: four planar wedges falling toward the sump
    z0 = p["floor_low"] - 1
    for xa, xb in ((L["cx0"], x), (x, L["cx1"])):
        for ya, yb in ((L["cy0"], L["y_sump"]), (L["y_sump"], L["cy1"])):
            bot = [cq.Vector(xa, ya, z0), cq.Vector(xb, ya, z0), cq.Vector(xb, yb, z0), cq.Vector(xa, yb, z0)]
            top = [cq.Vector(v.x, v.y, floor_z(p, L, v.x, v.y)) for v in bot]
            wedge = cq.Solid.makeLoft([cq.Wire.makePolygon(bot, close=True),
                                       cq.Wire.makePolygon(top, close=True)], ruled=True)
            b = b.union(cq.Workplane().add(wedge))
    # posts under insert edges that have no wall shelf below them
    yr, sp, br = L["y_row"], L["sponge"], L["brush"]
    posts = [(px, yr) for px in (sp[0] + 12, (sp[0] + sp[1]) / 2, sp[1] - 4, br[1] - 12)]
    posts += [(sp[1], (sp[2] + sp[3]) / 2), (br[0], (br[2] + br[3]) / 2)]
    for px, py in posts:
        b = b.union(cyl((px, py, z0), (px, py, L["shelf_z"]), 3.0))

    xi, xo = p["notch_w"] / 2, p["notch_w"] / 2 + p["armrest_w"]
    b = b.cut(box(x - xi, x + xi, -1, L["cy0"] + 0.01, L["seat"], L["top"] + 1))
    # armchair: front wall drops to armrest height beside him, armrests run back past his elbows,
    # backrest bridges between two posts with an opening underneath so water reaches the sump
    yt, az = L["yt"], L["arm_z"]
    bt = L["seat"] + p["backrest_h"]
    b = b.cut(box(x - xo, x + xo, -1, L["cy0"] + 0.01, az, L["top"] + 1))
    for e in (-1, 1):
        xa, xb = sorted((x + e * xi, x + e * xo))
        arm = box(xa, xb, -3, yt + 9, z0, az).edges("|Z").fillet(2.5).edges(">Z").fillet(2.5)
        b = b.union(arm)
        pa, pb = sorted((x + e * (xo - 4.5), x + e * xo))
        b = b.union(box(pa, pb, yt + 12, yt + 16, z0, bt))
    back = box(x - xo, x + xo, yt + 12, yt + 16, p["floor_low"] + p["water_gap"], bt)
    b = b.union(back.edges("|Y and >Z").fillet(6))
    fig = figure(p, L)

    # spout: tube out of the front face between his knees, tilted down, gusset under it
    t = math.radians(p["spout_tilt_deg"])
    zb = p["floor_low"] - p["groove_drop"]
    ro, ri = p["spout_od"] / 2, p["spout_id"] / 2
    s0 = (x, 2.0, zb + ri - 0.3)                 # bore sits 0.3 below the groove: no tangent faces
    d = (0, -math.cos(t), -math.sin(t))
    s1 = tuple(s0[i] + d[i] * (p["spout_len"] + 2) for i in range(3))
    spout = cyl(s0, s1, ro)
    gus = (cq.Workplane("YZ").workplane(offset=x - 1.2)
           .polyline([(0.5, s0[2] - ro + 0.8), (s1[1] + 4, s1[2] - ro + 0.8), (0.5, s0[2] - ro + 0.8 - 1.25 * (0.5 - s1[1] - 4))])
           .close().extrude(2.4))
    spout = spout.union(gus)
    pr = tuple(s1[i] - d[i] * p["drip_ring_from_tip"] for i in range(3))
    ring = cyl(tuple(pr[i] - d[i] * 0.6 for i in range(3)), tuple(pr[i] + d[i] * 0.6 for i in range(3)), ro + 1)
    spout = spout.cut(ring.cut(cyl(tuple(pr[i] - d[i] for i in range(3)), tuple(pr[i] + d[i] for i in range(3)), ro - 0.9)))
    # drip groove under the front edge: water running down the front face drops off here
    gy, gw, gh = p["drip_groove"]
    b = b.cut(box(-1, Lx + 1, gy, gy + gw, -1, gh))

    # drain path: sump behind his back -> tunnel under him -> spout
    g = (cq.Workplane("YZ").workplane(offset=x - p["groove_w"] / 2)
         .polyline([(L["y_sump"] + 3, p["floor_low"]), (1.0, zb),
                    (1.0, p["floor_low"] + 4), (L["y_sump"] + 3, p["floor_low"] + 4)])
         .close().extrude(p["groove_w"]))
    bore = cyl((s0[0], s0[1] + 3, s0[2]), tuple(s1[i] + d[i] * 1 for i in range(3)), ri)
    b = b.cut(g).cut(bore)
    fig = (fig + to_manifold(spout)) - to_manifold(b) - to_manifold(g) - to_manifold(bore)
    fig = m_union([c for c in fig.decompose() if c.volume() > 1.0])      # drop zero-volume slivers
    return b, fig


# ----------------------------------------------------------------- inserts
def slotted_plate(p, L, cell, slots_along="y"):
    """Plate filling a cell, with drain slots. Returns plate and its inner bounds + top z."""
    g = p["insert_gap"]
    x0, x1, y0, y1 = cell[0] + g, cell[1] - g, cell[2] + g, cell[3] - g
    z0 = L["shelf_z"]
    pl = box(x0, x1, y0, y1, z0, z0 + p["insert_t"]).edges("|Z").fillet(2)
    pitch = p["slot_w"] + p["rib_w"] + 2
    if slots_along == "y":                         # slots run front-back, repeat along X
        n = int((x1 - x0 - 8) // pitch)
        s = x0 + (x1 - x0 - (n - 1) * pitch) / 2
        for i in range(n):
            c = s + i * pitch
            pl = pl.cut(box(c - p["slot_w"] / 2, c + p["slot_w"] / 2, y0 + 4, y1 - 4, z0 - 1, z0 + 10))
    else:                                          # slots run left-right, repeat along Y
        n = int((y1 - y0 - 8) // pitch)
        s = y0 + (y1 - y0 - (n - 1) * pitch) / 2
        for i in range(n):
            c = s + i * pitch
            pl = pl.cut(box(x0 + 4, x1 - 4, c - p["slot_w"] / 2, c + p["slot_w"] / 2, z0 - 1, z0 + 10))
    return pl, (x0, x1, y0, y1, z0 + p["insert_t"])


def windowed_wall(x0, x1, y0, y1, z0, z1, along_x):
    """A thin wall with vertical drain/air windows."""
    wall = box(x0, x1, y0, y1, z0, z1)
    length = (x1 - x0) if along_x else (y1 - y0)
    pitch, ww = 10.0, 4.0
    n = int((length - 10) // pitch)
    s = (x0 if along_x else y0) + (length - (n - 1) * pitch) / 2
    for i in range(n):
        c = s + i * pitch
        if along_x:
            wall = wall.cut(box(c - ww / 2, c + ww / 2, y0 - 1, y1 + 1, z0 + 4, z1 - 5))
        else:
            wall = wall.cut(box(x0 - 1, x1 + 1, c - ww / 2, c + ww / 2, z0 + 4, z1 - 5))
    return wall


def sponge_insert(p, L):
    """Grate with two windowed walls that hold the sponge upright on its long edge."""
    pl, (x0, x1, y0, y1, zt) = slotted_plate(p, L, L["sponge"], slots_along="x")
    cy = (y0 + y1) / 2
    half = p["sponge_t"] / 2 + p["sponge_gap"]
    xa, xb = (x0 + x1) / 2 - p["sponge_l"] / 2 - p["sponge_gap"], (x0 + x1) / 2 + p["sponge_l"] / 2 + p["sponge_gap"]
    for ya, yb in ((cy - half - p["rack_t"], cy - half), (cy + half, cy + half + p["rack_t"])):
        pl = pl.union(windowed_wall(xa - p["rack_t"], xb + p["rack_t"], ya, yb, zt - 0.5, zt + p["rack_h"], True))
    for xa2, xb2 in ((xa - p["rack_t"], xa), (xb, xb + p["rack_t"])):      # short end walls
        pl = pl.union(box(xa2, xb2, cy - half, cy + half, zt - 0.5, zt + p["rack_h"] * 0.6))
    # low ribs the sponge edge sits on, so its bottom can drain
    for k in (-1, 0, 1):
        pl = pl.union(box(xa, xb, cy + k * half * 0.6 - p["rib_w"] / 2, cy + k * half * 0.6 + p["rib_w"] / 2,
                          zt - 0.5, zt + 2.5))
    return pl


def soap_insert(p, L):
    pl, (x0, x1, y0, y1, zt) = slotted_plate(p, L, L["soap"])
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    a, b2 = p["soap_l"] / 2 + 1, p["soap_w"] / 2 + 1
    ring = (cq.Workplane().workplane(offset=zt - 0.5).center(cx, cy).ellipse(a + 2, b2 + 2).extrude(6.5)
            .cut(cq.Workplane().workplane(offset=zt - 1).center(cx, cy).ellipse(a, b2).extrude(10)))
    return pl.union(ring)


def brush_insert(p, L):
    """Rectangular slot for brushes standing upright, open slotted floor."""
    pl, (x0, x1, y0, y1, zt) = slotted_plate(p, L, L["brush"])
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    il, iw, t = p["brush_slot_l"], p["brush_slot_w"], 2.4
    outer = box(cx - il / 2 - t, cx + il / 2 + t, cy - iw / 2 - t, cy + iw / 2 + t, zt - 0.5, zt + p["brush_slot_h"])
    outer = outer.edges("|Z").fillet(5)
    inner = box(cx - il / 2, cx + il / 2, cy - iw / 2, cy + iw / 2, zt, zt + p["brush_slot_h"] + 1).edges("|Z").fillet(3)
    slot = outer.cut(inner)
    for along_x, rng in ((True, (cy - iw / 2 - t - 1, cy + iw / 2 + t + 1)),):   # drain windows at the base
        for i in range(-2, 3):
            px = cx + i * 14
            slot = slot.cut(box(px - 3, px + 3, rng[0], rng[1], zt + 2, zt + 8))
    return pl.union(slot)


# --------------------------------------------------- phantom contents (render only)
def phantoms(p, L):
    sp, so, br = L["sponge"], L["soap"], L["brush"]
    zt = L["insert_top"] + 2.5
    cx, cy = (sp[0] + sp[1]) / 2, (sp[2] + sp[3]) / 2
    sponge = box(cx - p["sponge_l"] / 2, cx + p["sponge_l"] / 2, cy - p["sponge_t"] / 2, cy + p["sponge_t"] / 2,
                 zt, zt + p["sponge_h"]).edges().fillet(4)
    cx, cy = (so[0] + so[1]) / 2, (so[2] + so[3]) / 2
    soap = (cq.Workplane().workplane(offset=L["insert_top"]).center(cx, cy)
            .ellipse(p["soap_l"] / 2, p["soap_w"] / 2).extrude(150).edges(">Z").fillet(10)
            .union(cq.Workplane().workplane(offset=L["insert_top"] + 150).center(cx, cy).circle(6).extrude(20)))
    cx, cy = (br[0] + br[1]) / 2, (br[2] + br[3]) / 2
    brush = None
    for dx in (-18, 18):                           # two dish brushes, handles down, heads up
        b1 = (cq.Workplane().workplane(offset=L["insert_top"] + 1).center(cx + dx, cy).circle(7).extrude(130)
              .union(cq.Workplane().workplane(offset=L["insert_top"] + 131).center(cx + dx, cy).circle(13).extrude(40)))
        brush = b1 if brush is None else brush.union(b1)
    return dict(sponge=sponge, soap=soap, brush=brush)


L = layout(P)

if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    b, fig = body(P, L)
    parts = dict(body=b, figure=fig, sponge_insert=sponge_insert(P, L),
                 soap_insert=soap_insert(P, L), brush_insert=brush_insert(P, L))
    for k, v in {**parts, **{"phantom_" + k: v for k, v in phantoms(P, L).items()}}.items():
        if isinstance(v, mf.Manifold):
            to_trimesh(v).export(f"out/{k}.stl")
        else:
            cq.exporters.export(v, f"out/{k}.stl", tolerance=0.05, angularTolerance=0.15)
        print("wrote", k)
    # print-ready files: base + figure keep their shared coordinates (load them together as one
    # two-part object); inserts are dropped onto the bed
    os.makedirs("print", exist_ok=True)
    to_trimesh(to_manifold(b)).export("print/1_base.stl")
    to_trimesh(fig).export("print/2_figure.stl")
    for name, part in (("3_sponge_rack", parts["sponge_insert"]), ("4_soap_pad", parts["soap_insert"]),
                       ("5_brush_slot", parts["brush_insert"])):
        cq.exporters.export(part.translate((0, 0, -L["shelf_z"])), f"print/{name}.stl",
                            tolerance=0.05, angularTolerance=0.15)
    # test piece: the figure's corner of the base with capped cut walls, to check drip + sink fit
    x0, y1, t = L["x_out"] - 35, L["y_row"], 2.4
    outer = to_manifold(box(0, L["Lx"], 0, L["D"], 0, L["top"]).edges("|Z").fillet(P["corner_r"]))
    clip = to_manifold(box(x0, L["Lx"] + 1, -1, y1, -1, L["top"] + 1))
    caps = to_manifold(box(x0, x0 + t, 0, y1, 0, L["top"]).union(box(x0, L["Lx"], y1 - t, y1, 0, L["top"])))
    to_trimesh((to_manifold(b) ^ clip) + (caps ^ outer)).export("print/test_corner_base.stl")
    print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in L.items()})

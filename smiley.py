"""Smiley sink organizer (after the Etsy "peeing sponge holder").

Front: a D-shaped smiley bowl holding the sponge on its long edge, leaning back as if relaxing,
propped up on hands placed behind it. Legs (separate, clip in) rest on the counter and bend down
over the edge into the sink, ending in dome feet (separate, push on). A straight spout (separate,
push in) angles down between the legs. Back: a tower split by a fixed middle wall into two halves
(soap dispenser in one), with a loose T insert that splits either half front/back. Arches in its sides
wrap the disposal button and the dishwasher air gap. The tower drains forward into the bowl; the bowl
drains into the spout.

Coordinates: X = left/right (0 = center), Y = front(0) -> back, Z = up, counter top at Z = 0,
counter edge at Y = L["edge_y"] (the front of the base on the counter). Units: mm.
Run:  .venv/bin/python smiley.py   -> writes print/smiley_*.stl (print poses) and out/smiley_*.stl (assembled)
"""
import math
import os

import cadquery as cq
import manifold3d as mf

from organizer import SEG, box, cyl, m_capsule, m_sphere, m_union, to_manifold, to_trimesh

P = dict(
    # contents
    sponge_l=82.6, sponge_h=110, sponge_t=30, sponge_gap=2.0,   # standing up: 3.25" across, 110 tall
    soap_l=80, soap_w=58,                 # EKOLN base, measured (widest in the middle, rounded ends)
    soap_collar_h=30.0,                   # wall around the bottom of the soap dispenser
    soap_rotated=True,                    # long axis front-to-back: narrower stand, deeper tower
    side_extra=5.0,                       # sides reach this far past the fixture centers: the arches wrap a bit more
    tower_inner_h=101.6,                  # 4" deep inside, from the highest rib top to the rim
    divider_t=2.4, divider_fit=0.3, divider_bar=6.0,   # loose T insert: splits either half front/back, ears rest on the rims

    # site: counter depth sink edge -> wall, and two 2" fixtures (disposal button, dishwasher air gap), 110 mm apart surface to surface (measured); arches set 2 mm wider each side after the test print
    counter_depth=152.4, fixture_d=50.8, fixture_from_wall=101.6, fixture_spacing=164.8, fixture_clear=2.0,

    # smiley bowl (front view is a "D": flat top, superellipse bottom)
    wall=2.4, front_wall=4.0,             # front is thicker so the smile can be a 2 mm groove
    bowl_side_room=5.3,                   # extra half-width beyond the sponge's half-width
    bowl_curve_depth=56.0,                # inner depth of the D from rim to bottom
    bowl_curve_n=3.0,                     # 2 = half-ellipse, higher = flatter bottom
    pedestal_recess=10.0,                 # base is undercut at 45deg this far behind the face
    pedestal_flare=9.0,                   # how far the domed base bulges out at the counter
    bowl_bottom_z=18.0,                   # outer bottom of the bowl above the counter
    lean_deg=10.0,                        # the whole smiley leans back (a shear, floor stays level)

    # back tray
    tray_drop=2.0,                        # tray floor at the outlet sits this far above the bowl floor
    slope_x_deg=2.5, slope_y_deg=2.0,     # tray floor falls toward the center and the front (gentle: keeps the bottle low)

    # face
    eye_r=6.0, eye_proud=4.0, eye_dx=19.0, eye_dz=22.0,           # dz: below the rim
    smile_r=13.0, smile_w=3.4, smile_depth=2.0, smile_dz=27.0, smile_span=(205, 335),

    # hands: placed behind, propping him up
    hand_y=11.0, hand_dx=9.0, elbow_dx=5.0,   # hands: beside the hips, in the free strip along the sink edge
    platform_h=6.0,                       # base slab: full width, front on the counter edge line,
                                          # arches cut around the fixtures lock it in place

    # drain + spout (separate straight tube, angled down between the legs)
    groove_w=5.0, spout_od=8.0, spout_id=4.5, spout_out=12.0, spout_in=10.0, spout_angle_deg=25.0,
    fit=0.15,                             # clearance per side for sockets

    # legs: thighs rest on the counter, bend down at the edge; separate, click in
    leg_x=20.0, thigh_r=6.0, shin_r=5.5, peg_r=4.0, peg_len=12.0, bump=0.35,
    # feet: separate domes with flat soles, push onto a peg at the bottom of the shin
    foot_r=13.0, foot_h=11.0, foot_sole_z=-42.0, foot_forward=3.0, foot_peg_r=3.0, foot_peg_len=8.0,
)


# ------------------------------------------------------------------ layout
def d_curve_z(x, A, B, n, z_top):
    u = min(abs(x) / A, 1.0)
    return z_top - B * (1 - u ** n) ** (1 / n)


def d_slope(x, A, B, n):
    u = x / A
    return B * (1 - u ** n) ** (1 / n - 1) * u ** (n - 1) / A


def layout(p):
    L = {}
    w = p["wall"]
    L["Ai"] = p["sponge_l"] / 2 + p["bowl_side_room"]
    L["Bi"] = p["bowl_curve_depth"]
    L["A"], L["B"] = L["Ai"] + w, L["Bi"] + w
    L["Dw"] = p["sponge_t"] + 2 * p["sponge_gap"] + p["front_wall"] + w
    L["zb"] = p["bowl_bottom_z"]
    L["z_rim"] = L["zb"] + L["B"]
    L["z_ib"] = L["zb"] + w                               # inner bottom of the bowl
    L["k"] = math.tan(math.radians(p["lean_deg"]))        # lean: y += k * (z - zb)
    # x where the outer curve reaches 45deg: the pedestal must reach at least this far
    lo, hi = 0.0, L["A"] * 0.9999
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if d_slope(mid, L["A"], L["B"], p["bowl_curve_n"]) < 1 else (lo, mid)
    L["x45"] = lo
    L["z45"] = d_curve_z(lo, L["A"], L["B"], p["bowl_curve_n"], L["z_rim"])
    # tray starts behind the leaning bowl's back at rim height
    L["soap_x"], L["soap_y"] = (p["soap_w"], p["soap_l"]) if p["soap_rotated"] else (p["soap_l"], p["soap_w"])
    # wide enough for the contents and for the hands on the platforms
    L["edge_y"] = lean(L, p["pedestal_recess"], 0.0)
    L["wall_y"] = L["edge_y"] + p["counter_depth"]
    L["fix_y"] = L["wall_y"] - p["fixture_from_wall"]
    L["fix_x"] = p["fixture_spacing"] / 2
    L["fix_rc"] = p["fixture_d"] / 2 + p["fixture_clear"]                # arch radius
    # one width for the whole stand: a little past the fixture centers, so the arches wrap them and lock it in
    L["Tx"] = L["fix_x"] + p["side_extra"]
    # tower starts right at the leaning bowl's back at rim height (the sponge just leans on it)
    L["Ty0"] = L["Dw"] - w + L["k"] * (L["z_rim"] - L["zb"])
    # the bottle sits at the back of its half: far enough back that its rounded front clears the arch by 1 mm
    a, b, x0 = L["soap_x"] / 2, L["soap_y"] / 2, -(w / 2 + 2 + 0.8 + L["soap_x"] / 2)
    rc = L["fix_rc"] + w
    yb = L["Ty0"] + w + 1 + b
    while min(math.hypot(x0 + a * math.cos(t / 100) + L["fix_x"], yb + b * math.sin(t / 100) - L["fix_y"])
              for t in range(629)) < rc + 1.0:
        yb += 0.25
    L["soap_cy"] = yb
    L["Ty1"] = yb + b + 1 + w
    L["z_out"] = L["z_ib"] + p["tray_drop"]
    L["sx"], L["sy"] = (math.tan(math.radians(p[k])) for k in ("slope_x_deg", "slope_y_deg"))
    # the reference line = the sink edge: front of the base where it sits on the counter.
    # Platform fronts sit on it and the knees bend at it; the face leans out over the sink.
    # two equal halves either side of the fixed middle wall (bottle fits either); xb0 only places the phantoms.
    L["xd"] = -w / 2
    L["xb0"] = -(w / 2 + 2 + L["soap_x"] + 0.8)                            # left edge of the bottle's room, clear of the rails
    return L


def lean(L, y, z):
    return y + L["k"] * (z - L["zb"])


def shear(m, L):
    """Lean a manifold back: y += k * (z - zb). Linear, so the bowl floor stays level."""
    k = L["k"]
    return m.transform([[1, 0, 0, 0], [0, 1, k, -k * L["zb"]], [0, 0, 1, 0]])


def d_prism(A, B, n, z_top, y0, y1, extra_top=0.0, N=120):
    """The D shape (flat top at z_top, superellipse bottom) extruded from y0 to y1."""
    pts = [(-A + 2 * A * i / N, d_curve_z(-A + 2 * A * i / N, A, B, n, z_top)) for i in range(N + 1)]
    if extra_top > 0:
        pts += [(A, z_top + extra_top), (-A, z_top + extra_top)]
    solid = cq.Workplane("XZ").polyline(pts).close().extrude(-(y1 - y0))
    bb = solid.val().BoundingBox()
    return solid.translate((0, y0 - bb.ymin, 0))


def y_face(p, L, x, z):
    """Front surface of the (leaning) base at (x, z): 45deg undercut below the face, then the recess."""
    zc = d_curve_z(x, L["A"], L["B"], p["bowl_curve_n"], L["z_rim"])
    return lean(L, min(max(zc - z, 0.0), p["pedestal_recess"]), z)


def tray_floor_z(p, L, x, y):
    return L["z_out"] + L["sx"] * abs(x) + L["sy"] * (y - L["Ty0"] - p["wall"])


def flat_trim(m, sgn, x_flat):
    """Keep the side of x_flat away from sgn (sgn points at the flat face)."""
    return m.trim_by_plane((-sgn, 0, 0), -sgn * x_flat)


# ------------------------------------------------------------------ build
def build(p, L):
    w, n, Dw, zr, zib = p["wall"], p["bowl_curve_n"], L["Dw"], L["z_rim"], L["z_ib"]
    fit = p["fit"]

    # --- smiley bowl + domed, undercut base (built upright, then leaned back)
    bowl = d_prism(L["A"], L["B"], n, zr, 0, Dw)
    x45, z45, fl = L["x45"], L["z45"], p["pedestal_flare"]
    side = [(x45 + fl * math.sin(math.pi / 2 * k / 12), z45 * (1 - k / 12)) for k in range(13)]
    prof = [(x, z) for x, z in side] + [(-x, z) for x, z in reversed(side)]
    ped = cq.Workplane("XZ").polyline(prof).close().extrude(-(Dw + 60))       # runs back into the tower: no gap under the lean
    ped = ped.translate((0, -ped.val().BoundingBox().ymin, 0))
    rec, xw, N = p["pedestal_recess"], x45 + fl + 2, 60

    def under(y, dz):
        pts = [cq.Vector(-xw + 2 * xw * i / N, y, d_curve_z(-xw + 2 * xw * i / N, L["A"], L["B"], n, zr) - dz)
               for i in range(N + 1)]
        return cq.Wire.makePolygon(pts + [cq.Vector(xw, y, -1 - dz), cq.Vector(-xw, y, -1 - dz)], close=True)
    undercut = cq.Workplane().add(cq.Solid.makeLoft([under(-0.01, 0), under(rec, rec)], ruled=True))
    cavity = to_manifold(d_prism(L["Ai"], L["Bi"], n, zr, p["front_wall"], Dw - w, extra_top=5))
    # the base runs back under the lean but must stop inside the tray's front wall, never inside the
    # tray. That limit is a vertical plane AFTER leaning, i.e. a tilted plane here, before the lean.
    k_ang = math.degrees(math.atan(L["k"]))
    clip = (box(-300, 300, -500, 0, -300, 300).rotate((0, 0, 0), (1, 0, 0), k_ang)
            .translate((0, L["Ty0"] + w / 2, L["zb"])))
    bowl_m = to_manifold(bowl.union(ped.cut(undercut).intersect(clip)))   # exact CAD union, then mesh

    # face, on the upright front (y = 0) before leaning
    zs = zr - p["smile_dz"]
    a0, a1 = (math.radians(v) for v in p["smile_span"])
    pts = [(p["smile_r"] * math.cos(a0 + (a1 - a0) * i / 24), zs + p["smile_r"] * math.sin(a0 + (a1 - a0) * i / 24))
           for i in range(25)]
    dots = [mf.Manifold.cylinder(p["smile_depth"] + 1, p["smile_w"] / 2, p["smile_w"] / 2, SEG)
            .rotate((-90, 0, 0)).translate((x, -1, z)) for x, z in pts]
    smile = m_union([mf.Manifold.batch_hull([dots[i], dots[i + 1]]) for i in range(len(dots) - 1)])
    smile = smile.trim_by_plane((0, -1, 0), -p["smile_depth"])
    bowl_m = bowl_m - cavity
    dots_in = [mf.Manifold.cylinder(p["smile_depth"] - 0.1, p["smile_w"] / 2 - fit, p["smile_w"] / 2 - fit, SEG)
               .rotate((-90, 0, 0)).translate((x, 0, z)) for x, z in pts]
    smile_inlay = m_union([mf.Manifold.batch_hull([dots_in[i], dots_in[i + 1]]) for i in range(len(dots_in) - 1)])
    bowl_m = bowl_m - smile
    ze = zr - p["eye_dz"]
    # eyes and smile are printed apart (any filament) and glued in: the eyes sit 1 mm deep in pockets
    yec = p["eye_r"] - p["eye_proud"]
    eyes = m_union([m_sphere((e * p["eye_dx"], yec, ze), p["eye_r"]) for e in (-1, 1)])
    eyes = eyes.trim_by_plane((0, -1, 0), -1.0)
    rp = math.sqrt(p["eye_r"] ** 2 - (1.0 - yec) ** 2) + fit
    bowl_m = bowl_m - m_union([mf.Manifold.cylinder(2.0, rp, rp, SEG).rotate((-90, 0, 0)).translate((e * p["eye_dx"], -1.0, ze))
                               for e in (-1, 1)])

    eyes_flat, smile_flat = eyes, smile_inlay                              # upright copies for the print files
    bowl_m, smile_inlay, eyes, cavity = (shear(m, L) for m in (bowl_m, smile_inlay, eyes, cavity))
    bowl_m = bowl_m.trim_by_plane((0, 0, 1), 0.0)          # the lean pushes the base below z=0 a hair

    # --- back tower, full width minus the arches: bottle well, brush well, a pocket behind
    # each fixture; floors slope to the front center, ribs everywhere keep things out of the runoff,
    # everything drains into the bowl
    Tx, Ty0, Ty1, xb0, xd = L["Tx"], L["Ty0"], L["Ty1"], L["xb0"], L["xd"]
    z0 = L["z_out"] - 3
    ty = (Ty0 + Ty1) / 2
    z_top = tray_floor_z(p, L, Tx - w, Ty1 - w) + 2.5 + p["tower_inner_h"]  # one height for the whole tower
    xr0 = -xb0                                                             # right pocket wall mirrors the left one

    def arches(r, z_lo=-1.0, h=300.0):
        return m_union([mf.Manifold.cylinder(h, r, r, SEG * 2).translate((e * L["fix_x"], L["fix_y"], z_lo)) for e in (-1, 1)])
    tray = box(-Tx, Tx, Ty0, Ty1, 0, z_top).edges("|Z and >Y").fillet(6)
    for xa, xb in ((-Tx + w, 0), (0, Tx - w)):
        bot = [cq.Vector(xa, Ty0 + w, z0), cq.Vector(xb, Ty0 + w, z0), cq.Vector(xb, Ty1 - w, z0), cq.Vector(xa, Ty1 - w, z0)]
        top = [cq.Vector(v.x, v.y, tray_floor_z(p, L, v.x, v.y)) for v in bot]
        floor = cq.Workplane().add(cq.Solid.makeLoft(
            [cq.Wire.makePolygon(bot, close=True), cq.Wire.makePolygon(top, close=True)], ruled=True))
        if xa == -Tx + w:
            floors = floor
        else:
            floors = floors.union(floor)
    inner = to_manifold(box(-Tx + w, Tx - w, Ty0 + w, Ty1 - w, z0, z_top + 1)) - arches(L["fix_rc"] + w)
    sections = [inner ^ to_manifold(box(-Tx, 0, Ty0, Ty1, z0, z_top + 2)),                           # left half
                inner ^ to_manifold(box(0, Tx, Ty0, Ty1, z0, z_top + 2))]                            # right half
    wells = m_union(sections)
    floors = to_manifold(floors) ^ inner
    ribs = []
    for sec in sections:                                                   # level ribs, 2.5 mm over the floor's
        bx = sec.bounding_box()                                            # high corner, in 4 mm-gap pieces
        x0, y0, x1, y1 = bx[0], bx[1], bx[3], bx[4]
        top = max(tray_floor_z(p, L, x, y) for x in (x0, x1) for y in (y0, y1)) + 2.5
        nx = int((x1 - x0 - 6) // 8.5) + 1
        nseg = max(2, round((y1 - y0 - 6) / 14))
        seg = (y1 - y0 - 6 - 4 * (nseg - 1)) / nseg
        cx = (x0 + x1) / 2
        for i in range(nx):
            rx = cx + (i - (nx - 1) / 2) * 8.5
            for j in range(nseg):
                ya = y0 + 3 + j * (seg + 4)
                ribs.append(to_manifold(box(rx - 1, rx + 1, ya, ya + seg, z0, top)) ^ sec)
    # fixed middle wall: left and right halves. Pointed windows along its foot let water cross and leave
    # nothing to scrub in the corner; the 45 deg roofs print without supports.
    rib_top = max(tray_floor_z(p, L, x, y) for x in (-Tx + w, Tx - w) for y in (Ty0 + w, Ty1 - w)) + 2.5
    mid = box(-w / 2, w / 2, Ty0 + w / 2, Ty1 - w / 2, z0, z_top)
    win_w, post = 12.0, 5.0
    nwin = int((Ty1 - Ty0 - 2 * w - post) // (win_w + post))
    y_w0 = ty - (nwin * win_w + (nwin - 1) * post) / 2
    for i in range(nwin):
        ya = y_w0 + i * (win_w + post)
        prof = [(ya, z0 - 1), (ya + win_w, z0 - 1), (ya + win_w, rib_top + 1),
                (ya + win_w / 2, rib_top + 1 + win_w / 2), (ya, rib_top + 1)]
        mid = mid.cut(cq.Workplane("YZ").workplane(offset=-w).polyline(prof).close().extrude(2 * w))
    mid = to_manifold(mid) ^ to_manifold(box(-w, w, Ty0 + w / 2, Ty1 - w / 2, z0, z_top))
    # loose T insert: drops into either half at mid-depth and splits it front/back. Rails on both faces of the
    # middle wall and on both side walls; the ears rest on the middle wall's rim and the side wall's rim.
    # Water runs under it; lift it out to clean.
    g = p["divider_t"] / 2 + p["divider_fit"]
    rails = [to_manifold(box(*sorted((xa, xb)), *sorted((ty + e * g, ty + e * (g + 2))), rib_top, z_top))
             for xa, xb in ((w / 2 - 0.5, w / 2 + 2), (Tx - w + 0.5, Tx - w - 2),
                            (-w / 2 + 0.5, -w / 2 - 2), (-Tx + w - 0.5, -Tx + w + 2))
             for e in (-1, 1)]
    hb, ht = p["divider_bar"] / 2, p["divider_t"] / 2
    xd0, xd1 = w / 2 + p["divider_fit"], Tx - w - p["divider_fit"]
    divider = box(xd0, xd1, ty - ht, ty + ht, rib_top + 0.5, z_top + 2.5)
    for xa, xb in ((-w / 2 + 0.3, w / 2 + 8), (Tx - w - 8, Tx - 0.5)):     # ears over the middle and side rims
        divider = divider.union(box(xa, xb, ty - hb, ty + hb, z_top, z_top + 2.5).edges("|X").fillet(1))
    divider = to_manifold(divider)                                          # shown in the right half; turn it
    tower = (to_manifold(tray) - wells + floors + m_union(ribs) + m_union(rails) + mid) - arches(L["fix_rc"])   # round for the left

    # base slab: full width, arches around the fixtures; kept out of the way in front of the smiley's base
    ph = p["platform_h"]
    slab = box(-Tx, Tx, L["edge_y"], Ty1, 0, ph).edges("|Z").fillet(6)
    xs = L["x45"] + p["pedestal_flare"] - 0.5
    slab = to_manifold(slab.cut(box(-xs, xs, L["edge_y"] - 1, L["edge_y"] + 3, -1, ph + 1))) - arches(L["fix_rc"])
    # fill the wedge between the leaning bowl's back and the tray's front wall
    fill = shear(to_manifold(d_prism(L["A"] - 0.3, L["B"] - 0.3, n, zr - 0.3, Dw - w / 2, Dw + 60)), L) ^ to_manifold(
        box(-L["A"], L["A"], 0, Ty0 + w / 2, 0, zr))                      # kept inside the outlines: no coincident faces

    body = bowl_m + tower + fill + slab

    # --- arms: shoulders on the leaning sides, hands on the pads beside the hips
    A, yc, hy = L["A"], Dw / 2, L["edge_y"] + p["hand_y"]
    limbs = []
    for e in (-1, 1):
        zsh, zel = zr - 14, zr - 32
        sh = (e * (A - 3), lean(L, yc, zsh), zsh)
        el = (e * (A + p["elbow_dx"]), lean(L, yc, zel), zel)
        wr = (e * (A + p["hand_dx"] - 3), hy + 2, ph + 6.0)
        limbs += [m_capsule(sh, el, 6.0), m_capsule(el, wr, 5.5), m_sphere(el, 6.3)]
        hc = (e * (A + p["hand_dx"]), hy, ph + 3.6)
        limbs += [mf.Manifold.sphere(8.0, SEG).scale((1.2, 1.0, 0.55)).translate(hc)]
        for ang in (-24, -8, 8, 24):                                       # fingers point outward
            r = math.radians(ang)
            dx, dy = e * math.cos(r), math.sin(r)
            limbs += [m_capsule((hc[0], hc[1], ph + 2.0), (hc[0] + 9 * dx, hc[1] + 9 * dy, ph + 2.0), 2.4)]
        limbs += [m_capsule((hc[0] - e * 3, hc[1] - 3, ph + 2.2), (hc[0] - e * 4, hc[1] - 8, ph + 2.2), 2.6)]   # thumb forward
    body = body + m_union(limbs).trim_by_plane((0, 0, 1), 0.0)
    body = body - cavity                                                   # nothing pokes into the sponge space

    # --- drain: V trough along the bowl bottom -> drop hole -> chamber -> angled spout socket
    gw, ro, ri = p["groove_w"], p["spout_od"] / 2, p["spout_id"] / 2
    ang = math.radians(p["spout_angle_deg"])
    d = (0, -math.cos(ang), -math.sin(ang))                               # spout direction, out and down
    zgf = zib - 2.0
    zE = zgf - 3.0                                                        # deep end of the spout
    z_mouth = zE + d[2] * p["spout_in"]
    yE = y_face(p, L, 0, z_mouth) - d[1] * p["spout_in"] + 1.0
    E = (0, yE, zE)
    at = lambda t: tuple(E[i] + d[i] * t for i in range(3))
    yf, yb = lean(L, p["front_wall"], zib) - 0.5, lean(L, Dw - w, zib) + 1
    trough = (cq.Workplane("YZ").workplane(offset=-gw / 2)
              .polyline([(yb, zib - 0.5), (yE, zgf), (yf, zib - 0.5), (yf, zib + 4), (yb, zib + 4)])
              .close().extrude(gw))
    drop = cyl((0, yE, zgf + 0.5), (0, yE, zE), ri)
    chamber = cyl(at(-3.0), at(0.5), ri)
    socket = cyl(at(-0.3), at(p["spout_in"] + 8), ro + fit)
    y_in_lo = lean(L, Dw - w, L["z_out"]) - 1
    inlet = box(-10, 10, y_in_lo, Ty0 + w + 1, L["z_out"] - 0.5, L["z_out"] + 8)
    for c in (trough, drop, chamber, socket, inlet):
        body = body - to_manifold(c)

    # --- legs: thigh on the counter, knee just past the edge, shin straight down; D-peg clicks in
    tr, sr, pr, pl = p["thigh_r"], p["shin_r"], p["peg_r"], p["peg_len"]
    yk = L["edge_y"] - sr - 0.5                                            # shin clears the counter edge
    foot_top = p["foot_sole_z"] + p["foot_h"] - 1.0
    legs, feet = [], []
    for e in (-1, 1):
        xc, sgn = e * p["leg_x"], -e                                       # sgn points at the inner (flat) side
        hz = tr                                                            # thigh rests on the counter
        yl = y_face(p, L, xc, hz)
        x_flat = xc + sgn * (sr - 1.5)
        pc = x_flat - sgn * (pr - 1.0)                                     # peg gets a 1 mm flat too
        knee = (xc, yk, sr)                                                # thigh tapers to the shin at the knee,
        leg = m_union([mf.Manifold.batch_hull([m_sphere((xc, yl + 2, hz), tr), m_sphere(knee, sr)]),  # bottom stays on the counter
                       mf.Manifold.cylinder(sr - foot_top, sr, sr, SEG).translate((xc, yk, foot_top)),
                       mf.Manifold.cylinder(pl + 1, pr, pr, SEG).rotate((-90, 0, 0)).translate((pc, yl, hz))])
        bump_c = [(pc, yl + pl - 3, hz + kk * (pr - 1.2 + p["bump"])) for kk in (-1, 1)]
        leg = leg + m_union([m_sphere(c, 1.2) for c in bump_c])
        leg = leg - to_manifold(box(pc - pr - 1, pc + pr + 1, yl + pl - 8, yl + pl + 2, hz - 0.6, hz + 0.6))
        # foot peg (down into the foot)
        fpr, fpl = p["foot_peg_r"], p["foot_peg_len"]
        fpc = x_flat - sgn * (fpr - 1.0)
        leg = leg + mf.Manifold.cylinder(fpl + 1, fpr, fpr, SEG).translate((fpc, yk, foot_top - fpl))
        leg = flat_trim(leg, sgn, x_flat)
        # socket in the base
        sock = mf.Manifold.cylinder(pl + 4, pr + fit, pr + fit, SEG).rotate((-90, 0, 0)).translate((pc, yl - 3, hz))
        sock = flat_trim(sock, sgn, x_flat + sgn * fit) + m_union([m_sphere(c, 1.4) for c in bump_c])
        body = body - sock
        # foot: dome with a flat sole and a D-socket for the shin peg
        fc = (xc, yk - p["foot_forward"], p["foot_sole_z"])
        foot = (mf.Manifold.sphere(p["foot_r"], SEG * 2).scale((1, 1.1, p["foot_h"] / p["foot_r"]))
                .translate(fc).trim_by_plane((0, 0, 1), p["foot_sole_z"]))
        fsock = flat_trim(mf.Manifold.cylinder(fpl + 3, fpr + fit, fpr + fit, SEG)
                          .translate((fpc, yk, foot_top - fpl - 0.4)), sgn, x_flat + sgn * fit)
        foot = foot - fsock
        foot = foot.trim_by_plane((0, -1, 0), -(L["edge_y"] - 0.5))           # flat heel: nothing behind the counter edge
        legs.append((leg, sgn))
        feet.append(foot)

    body = m_union([c for c in body.decompose() if c.volume() > 1.0]).trim_by_plane((0, 0, 1), 0.0)
    legs = [(flat_trim(leg - body, sgn, x_flat_of(p, sgn)) - feet[i], sgn) for i, (leg, sgn) in enumerate(legs)]
    spout = (mf.Manifold.cylinder(p["spout_in"] + p["spout_out"], ro, ro, SEG)
             - mf.Manifold.cylinder(p["spout_in"] + p["spout_out"] + 2, ri, ri, SEG).translate((0, 0, -1)))
    spout_assy = spout.rotate((90 + p["spout_angle_deg"], 0, 0)).translate(E)
    return dict(body=body, eyes=eyes, smile_inlay=smile_inlay, eyes_flat=eyes_flat, smile_flat=smile_flat,
                divider=divider, legs=legs, feet=feet,
                spout=spout_assy, spout_print=spout)


def x_flat_of(p, sgn):
    xc = -sgn * p["leg_x"]
    return xc + sgn * (p["shin_r"] - 1.5)


def phantoms(p, L):
    """Sponge / dispenser / brushes / counter for renders only."""
    w, Dw, n = p["wall"], L["Dw"], p["bowl_curve_n"]
    hx = p["sponge_l"] / 2
    z_rest = d_curve_z(hx, L["Ai"], L["Bi"], n, L["z_rim"])
    yc = (p["front_wall"] + Dw - w) / 2
    # stands a bit more upright than the bowl: front face on the bowl's front rim, top resting on the tower wall
    k, t = L["k"], p["sponge_t"]
    y_rim = p["front_wall"] + k * (L["z_rim"] - L["zb"]) + 0.3                  # inner front at the rim
    k2 = min(k, (L["Ty0"] - 0.5 - t - y_rim) / (z_rest + p["sponge_h"] - L["z_rim"]))
    y_f = y_rim - k2 * (L["z_rim"] - z_rest)                                     # front face at the bottom
    sponge = to_manifold(box(-hx, hx, 0, t, z_rest, z_rest + p["sponge_h"]).edges().fillet(4)).transform(
        [[1, 0, 0, 0], [0, 1, k2, y_f - k2 * z_rest], [0, 0, 1, 0]])
    Tx, ty, xd = L["Tx"], (L["Ty0"] + L["Ty1"]) / 2, L["xd"]
    sx0 = L["xb0"] + L["soap_x"] / 2                                       # beside the middle wall
    y0, y1 = L["Ty0"] + w, L["Ty1"] - w
    zt = max(tray_floor_z(p, L, x, y) for x in (-Tx + w, Tx - w) for y in (y0, y1)) + 2.6   # on the ribs
    soap = (cq.Workplane().workplane(offset=zt).center(sx0, L["soap_cy"]).ellipse(L["soap_x"] / 2, L["soap_y"] / 2)
            .extrude(150).edges(">Z").fillet(8)
            .union(cq.Workplane().workplane(offset=zt + 150).center(sx0, L["soap_cy"]).circle(6).extrude(20)))
    bx0 = -sx0
    brush = None
    for dy in (-20, 20):
        zf = zt
        b1 = (cq.Workplane().workplane(offset=zf).center(bx0, ty + dy).circle(7).extrude(130)
              .union(cq.Workplane().workplane(offset=zf + 130).center(bx0, ty + dy).circle(13).extrude(40)))
        brush = b1 if brush is None else brush.union(b1)
    counter = (box(-160, 160, L["edge_y"], L["wall_y"], -30, 0)
               .union(box(-160, 160, L["wall_y"], L["wall_y"] + 12, -30, 160)))      # counter + backsplash wall
    fr = p["fixture_d"] / 2
    fixtures = None
    for e, h in ((-1, 40), (1, 70)):                                       # heights unknown: shown 40 / 70
        f1 = (cq.Workplane().center(e * L["fix_x"], L["fix_y"]).circle(fr).extrude(h).edges(">Z").fillet(fr * 0.6))
        fixtures = f1 if fixtures is None else fixtures.union(f1)
    return dict(sponge=sponge, soap=to_manifold(soap), brush=to_manifold(brush), counter=to_manifold(counter),
                fixtures=to_manifold(fixtures))


def base_test(body, rim=8.0, h=2.0):
    """Thin frame of the exact footprint: lay it on the counter to check the arches before the big print.
    The front edge goes on the sink edge; the arrow points at the sink."""
    fp = body.slice(0.3).simplify(0.05)
    ring = (fp - fp.offset(-rim, mf.JoinType.Round)).simplify(0.05)       # no near-duplicate points
    b = fp.bounds()                                                        # (xmin, ymin, xmax, ymax)
    cx, y0 = (b[0] + b[2]) / 2, b[1]
    arrow = mf.CrossSection([[(cx - 10, y0 + rim + 14), (cx + 10, y0 + rim + 14), (cx, y0 + rim - 0.5)]])
    return mf.Manifold.extrude(ring + arrow, h)


def print_pose_leg(m, sgn):
    """Lay a leg on its flat inner face."""
    m = m.rotate((0, 90 * sgn, 0))
    bb = m.bounding_box()
    return m.translate((-(bb[0] + bb[3]) / 2, -(bb[1] + bb[4]) / 2, -bb[2]))


def print_pose_flat(m, rx):
    """Rotate about x, then sit on the bed, centered."""
    m = m.rotate((rx, 0, 0))
    bb = m.bounding_box()
    return m.translate((-(bb[0] + bb[3]) / 2, -(bb[1] + bb[4]) / 2, -bb[2]))


def print_pose_foot(m):
    bb = m.bounding_box()
    return m.translate((-(bb[0] + bb[3]) / 2, -(bb[1] + bb[4]) / 2, -bb[2]))


L = layout(P)

if __name__ == "__main__":
    os.makedirs("print", exist_ok=True)
    os.makedirs("out", exist_ok=True)
    for f in os.listdir("print"):
        if f.startswith("smiley_"):
            os.remove(os.path.join("print", f))
    r = build(P, L)
    (leg_l, sl), (leg_r, sr_) = r["legs"]
    assy = dict(smiley_body=r["body"], smiley_eyes=r["eyes"], smiley_smile_inlay=r["smile_inlay"],
                smiley_leg_l=leg_l, smiley_leg_r=leg_r, smiley_foot_l=r["feet"][0], smiley_foot_r=r["feet"][1],
                smiley_spout=r["spout"], smiley_divider=r["divider"])
    for name, m in assy.items():
        to_trimesh(m).export(f"out/{name}.stl")
    printable = dict(smiley_body=r["body"], smiley_eyes=print_pose_flat(r["eyes_flat"], -90),
                     smiley_smile=print_pose_flat(r["smile_flat"], 90),
                     smiley_divider=print_pose_flat(r["divider"], 180),
                     smiley_leg_left=print_pose_leg(leg_l, sl), smiley_leg_right=print_pose_leg(leg_r, sr_),
                     smiley_foot_left=print_pose_foot(r["feet"][0]), smiley_foot_right=print_pose_foot(r["feet"][1]),
                     smiley_spout=r["spout_print"],
                     smiley_base_test=base_test(r["body"]))
    for name, m in printable.items():
        to_trimesh(m).export(f"print/{name}.stl")
    for k, v in phantoms(P, L).items():
        to_trimesh(v).export(f"out/smiley_phantom_{k}.stl")
    print({k: round(v, 1) for k, v in L.items()})

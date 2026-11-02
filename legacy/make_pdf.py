"""Concept sheet: renders + layout + numbers -> sink_buddy_concept.pdf"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

from organizer import L, P

TEAL = colors.HexColor("#2f8f93")
INK = colors.HexColor("#1d2a2b")
MUTED = colors.HexColor("#5d6f70")
LINE = colors.HexColor("#d7e1e1")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Title"], alignment=0, fontSize=22, leading=26, textColor=INK, spaceAfter=4)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13, textColor=TEAL, spaceBefore=10, spaceAfter=6)
BODY = ParagraphStyle("b", parent=ss["BodyText"], fontSize=10, leading=14, textColor=INK)
SMALL = ParagraphStyle("s", parent=BODY, fontSize=8.5, leading=11, textColor=MUTED)
BUL = ParagraphStyle("bul", parent=BODY, leftIndent=12, bulletIndent=2)


def img(path, width):
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(path).getSize()
    return Image(path, width=width, height=width * h / w)


def crop(path, out):
    """Trim white margins off a render."""
    from PIL import Image as PI, ImageChops
    im = PI.open(path).convert("RGB")
    bg = PI.new("RGB", im.size, (255, 255, 255))
    box = ImageChops.difference(im, bg).getbbox()
    if box:
        pad = 20
        box = (max(box[0] - pad, 0), max(box[1] - pad, 0), min(box[2] + pad, im.width), min(box[3] + pad, im.height))
        im = im.crop(box)
    im.save(out)
    return out


def layout_diagram(width):
    """Top view of the four cells, to scale."""
    s = width / (L["Lx"] + 30)
    d = Drawing(width, (L["D"] + 30) * s)
    ox, oy = 10 * s, 18 * s

    def R(x0, x1, y0, y1, fill, label, sub):
        d.add(Rect(ox + x0 * s, oy + y0 * s, (x1 - x0) * s, (y1 - y0) * s, fillColor=fill, strokeColor=INK, strokeWidth=0.6))
        cx, cy = ox + (x0 + x1) / 2 * s, oy + (y0 + y1) / 2 * s
        d.add(String(cx, cy + 2, label, fontSize=9, textAnchor="middle", fillColor=INK, fontName="Helvetica-Bold"))
        d.add(String(cx, cy - 9, sub, fontSize=7.5, textAnchor="middle", fillColor=MUTED))

    d.add(Rect(ox, oy, L["Lx"] * s, L["D"] * s, rx=8 * s, ry=8 * s, fillColor=colors.HexColor("#cfe6e7"), strokeColor=TEAL, strokeWidth=1.2))
    sp, fg, so, br = L["sponge"], L["fig"], L["soap"], L["brush"]
    R(*sp, colors.HexColor("#fbf1c4"), "Sponge rack", f"{P['sponge_l']} x {P['sponge_t']}, on edge")
    R(*fg, colors.HexColor("#fde0bd"), "Figure + chair", "drain spout")
    R(*so, colors.white, "Soap (EKOLN)", f"{P['soap_l']} x {P['soap_w']} oval")
    R(*br, colors.white, "Brush slot", f"{P['brush_slot_l']} x {P['brush_slot_w']}")
    # sump + spout marker
    x = ox + L["x_out"] * s
    d.add(Line(x, oy + L["y_sump"] * s, x, oy - 8 * s, strokeColor=colors.HexColor("#2a7fd4"), strokeWidth=1.5))
    d.add(String(x + 4, oy - 12 * s, "water out", fontSize=7.5, fillColor=colors.HexColor("#2a7fd4")))
    # dimensions
    d.add(String(ox + L["Lx"] * s / 2, oy + L["D"] * s + 5, f"{L['Lx']:.0f} mm", fontSize=8.5, textAnchor="middle", fillColor=INK))
    d.add(String(ox + L["Lx"] * s + 4, oy + L["D"] * s / 2, f"{L['D']:.0f} mm", fontSize=8.5, fillColor=INK))
    d.add(String(ox, oy - 12 * s, "sink side", fontSize=7.5, fillColor=MUTED))
    return d


def table(rows, col_w):
    t = Table(rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
        ("FONT", (1, 0), (1, -1), "Courier", 9.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def build(out="sink_buddy_concept.pdf"):
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title="Sink Buddy - concept v4")
    W = A4[0] - 36 * mm
    r = {k: crop(f"renders/{k}.png", f"renders/_crop_{k}.png")
         for k in ("1_loaded", "2_empty", "3_drain_pan", "4_figure", "5_figure_side", "6_chair")}
    st = []

    # page 1
    st += [Paragraph("Sink Buddy", H1),
           Paragraph("Concept v4 &middot; 3D-printed sink organizer for a soap dispenser, brushes and a sponge, "
                     "with a self-draining pan that empties through a little figure into the sink.", SMALL),
           Spacer(1, 8), img(r["1_loaded"], W * 0.78), Spacer(1, 6),
           Paragraph("Layout (top view, to scale)", H2), layout_diagram(W * 0.8)]
    st.append(PageBreak())

    # page 2: how it works
    st += [Paragraph("How it works", H2)]
    for t in [
        "<b>One shared drain pan.</b> All four stations sit over one pan. Its floor slopes "
        f"{P['slope_y_deg']:g}&deg; front/back and {P['slope_x_deg']:g}&deg; sideways toward a single sump behind the figure.",
        "<b>Out through the figure.</b> A short tunnel runs from the sump under the figure's seat to a "
        f"&Oslash;{P['spout_id']:g} mm spout between his knees, tilted {P['spout_tilt_deg']:g}&deg; down so water drips into the sink "
        "instead of running back down the front.",
        "<b>Armchair.</b> The figure sits in a chair built into the front wall: armrests on both sides with his forearms on them, "
        f"and a backrest bridged over a {P['water_gap']:g} mm gap so water flows underneath to the sump.",
        "<b>Lift-out inserts.</b> The sponge rack, soap pad and brush slot are separate drop-in parts resting on an inner shelf "
        "and posts. Lift them out to rinse the whole pan; there are no hidden channels apart from the short tunnel under the figure.",
        "<b>Only the legs stick out.</b> His shins, feet and the spout reach about 15 mm past the front edge; everything else "
        "is inside the footprint.",
    ]:
        st.append(Paragraph(t, BUL, bulletText="•"))
        st.append(Spacer(1, 3))
    st += [Spacer(1, 6),
           Table([[img(r["2_empty"], W / 2 - 4), img(r["3_drain_pan"], W / 2 - 4)],
                  [Paragraph("Inserts only", SMALL), Paragraph("Drain pan with inserts removed (posts hold the inserts)", SMALL)]],
                 colWidths=[W / 2, W / 2]),
           Spacer(1, 6),
           Table([[img(r["6_chair"], W / 2 - 4), img(r["4_figure"], W / 2 - 4)],
                  [Paragraph("Armchair close-up", SMALL), Paragraph("Figure and spout", SMALL)]],
                 colWidths=[W / 2, W / 2])]
    st.append(PageBreak())

    # page 3: numbers + open questions
    st += [Paragraph("Current numbers", H2),
           Paragraph("All values are parameters in organizer.py; most are placeholders until measured.", SMALL), Spacer(1, 4),
           table([
               ["Overall footprint", f"{L['Lx']:.0f} x {L['D']:.0f} mm"],
               ["Overall height (walls / backrest)", f"{L['top']:.0f} / {L['seat'] + P['backrest_h']:.0f} mm"],
               ["Past the front edge (feet + spout)", "~15 mm"],
               ["Sponge, standing on edge", f"{P['sponge_l']} x {P['sponge_h']} x {P['sponge_t']} mm"],
               ["Soap base (EKOLN, guessed oval)", f"{P['soap_l']} x {P['soap_w']} mm"],
               ["Brush slot, inner", f"{P['brush_slot_l']} x {P['brush_slot_w']}, {P['brush_slot_h']} tall"],
               ["Floor at drain / insert shelf", f"{P['floor_low']:g} / {L['shelf_z']:g} mm"],
               ["Floor slope front-back / sideways", f"{P['slope_y_deg']:g} / {P['slope_x_deg']:g} deg"],
               ["Armrest height above seat", f"{P['armrest_h']:g} mm"],
               ["Spout bore / tilt", f"{P['spout_id']:g} mm / {P['spout_tilt_deg']:g} deg"],
               ["Figure height", "~60 mm"],
           ], [W * 0.62, W * 0.38]),
           Paragraph("Parts to print", H2),
           table([
               ["Base (pan, chair, posts)", "1 part"],
               ["Figure (separate color)", "1 part"],
               ["Sponge rack / soap pad / brush slot", "3 inserts"],
           ], [W * 0.62, W * 0.38]),
           Paragraph("Material: PETG (holds up to water and dish soap better than PLA).", SMALL),
           Paragraph("Open questions", H2)]
    for q in ["Figure: bigger? A specific character or style?",
              "Figure on the right front corner, or swap with the sponge?",
              "Will the spout reach the sink from where it sits on the counter?",
              "Real measurements: sponge, EKOLN base, number and thickness of brush handles.",
              "Brush slot as one rectangle, or a row of round holes?"]:
        st.append(Paragraph(q, BUL, bulletText="•"))
    st += [Spacer(1, 10), img(r["5_figure_side"], W * 0.45),
           Paragraph("Side view: figure's legs and spout over the front edge", SMALL)]

    doc.build(st)
    print("wrote", out)


if __name__ == "__main__":
    build()

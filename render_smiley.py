"""Previews of the smiley organizer -> renders/smiley_*.png"""
import render as r

r.COLORS.update(smiley_body=(0.62, 0.64, 0.66), smiley_eyes=(0.12, 0.12, 0.13), smiley_smile_inlay=(0.12, 0.12, 0.13),
                smiley_leg_l=(0.62, 0.64, 0.66), smiley_leg_r=(0.62, 0.64, 0.66), smiley_foot_l=(0.62, 0.64, 0.66), smiley_foot_r=(0.62, 0.64, 0.66), smiley_spout=(0.62, 0.64, 0.66), smiley_divider=(0.72, 0.58, 0.40),
                smiley_phantom_sponge=(0.96, 0.82, 0.26), smiley_phantom_soap=(0.3, 0.3, 0.32),
                smiley_phantom_brush=(0.75, 0.22, 0.17), smiley_phantom_counter=(0.45, 0.42, 0.40),
                smiley_phantom_fixtures=(0.80, 0.80, 0.78))
parts = ["smiley_body", "smiley_divider", "smiley_eyes", "smiley_smile_inlay", "smiley_leg_l", "smiley_leg_r", "smiley_foot_l", "smiley_foot_r", "smiley_spout"]
ph = ["smiley_phantom_sponge", "smiley_phantom_soap", "smiley_phantom_brush"]
ctr = ["smiley_phantom_counter", "smiley_phantom_fixtures"]
r.render(parts + ph + ctr, "smiley_1_loaded", (-200, -420, 300), (0, 50, 50), 0.95)
r.render(parts + ["smiley_phantom_sponge"] + ctr, "smiley_3_front_sponge", (60, -330, 90), (0, 20, 30), 1.15)
r.render(parts + ctr, "smiley_6_legs", (90, -190, 10), (0, -5, -5), 1.3)
r.render(parts + ctr, "smiley_5_side", (420, -20, 10), (0, 20, 15), 1.1)
r.render(parts + ["smiley_phantom_fixtures"], "smiley_4_top", (0, 20, 560), (0, 75, 20), 1.0)
r.render(parts, "smiley_2_front", (0, -400, 60), (0, 40, 20), 1.15)

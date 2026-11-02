"""Copy the print files into package/ and zip them.

Run after smiley.py:  .venv/bin/python package.py
  -> package/smiley_*.stl (next to the hand-written package/README.txt)
  -> sink_buddy_print.zip (every part + README), sink_buddy_base_test.zip (fit test + README)
"""
import glob
import os
import shutil
import zipfile

PARTS = ["smiley_body", "smiley_divider", "smiley_leg_left", "smiley_leg_right", "smiley_foot_left",
         "smiley_foot_right", "smiley_spout", "smiley_eyes", "smiley_smile", "smiley_base_test"]

if __name__ == "__main__":
    for f in glob.glob("package/*.stl"):
        os.remove(f)
    for name in PARTS:
        shutil.copy(f"print/{name}.stl", f"package/{name}.stl")
    for zname, names in (("sink_buddy_print.zip", PARTS), ("sink_buddy_base_test.zip", ["smiley_base_test"])):
        with zipfile.ZipFile(zname, "w", zipfile.ZIP_DEFLATED) as z:
            z.write("package/README.txt", "README.txt")
            for name in names:
                z.write(f"package/{name}.stl", f"{name}.stl")
        print(zname, os.path.getsize(zname) // 1024, "KB")

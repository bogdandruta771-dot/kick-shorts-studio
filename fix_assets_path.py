from pathlib import Path

p = Path("H:/kick project/core/motion_explainer/tradeit_assets.py")
txt = p.read_text(encoding="utf-8")

old_str = 'ASSETS_DIR = Path(__file__).parent.parent / "assets"'
new_str = 'ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"'

if old_str in txt:
    txt = txt.replace(old_str, new_str)
    p.write_text(txt, encoding="utf-8")
    print("SUCCESS: ASSETS_DIR updated")
else:
    print("ERROR: old_str not found")

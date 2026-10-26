#!/usr/bin/env python3
"""Let the gallery wrapper own horizontal swipes instead of competing with PageView."""
from pathlib import Path

path = Path("lib/main.dart")
text = path.read_text(encoding="utf-8")

gallery = text.find("class _GalleryTabState extends State<GalleryTab>")
if gallery < 0 or "onHorizontalDragEnd" not in text[gallery:]:
    raise SystemExit("Expected the gallery-level horizontal drag handler.")

old = """            child: PageView(
              controller: _galleryPageController,
"""
new = """            child: PageView(
              physics: const NeverScrollableScrollPhysics(),
              controller: _galleryPageController,
"""
count = text.count(old)
if count == 1:
    text = text.replace(old, new, 1)
    print("applied: prevent PageView from competing with gallery swipe handler")
elif new in text:
    print("already applied: PageView scroll physics")
else:
    raise SystemExit(f"Could not find the gallery PageView: matches={count}")

path.write_text(text, encoding="utf-8")

#!/usr/bin/env python3
"""Restore native PageView swipes and test both gallery directions."""
from pathlib import Path

source = Path("lib/main.dart")
text = source.read_text(encoding="utf-8")

# Keep PageView as the only horizontal gesture recognizer.
wrapper_start = "    return GestureDetector(\n      behavior: HitTestBehavior.opaque,\n      onHorizontalDragStart:"
start = text.find(wrapper_start)
if start >= 0:
    safe_area = "      child: SafeArea(\n        child: Column("
    anchor = text.find(safe_area, start)
    if anchor < 0:
        raise SystemExit("Could not find the gallery SafeArea inside the gesture wrapper.")
    text = text[:start] + "    return SafeArea(\n      child: Column(" + text[anchor + len(safe_area):]
    old_end = "        ],\n      ),\n    ),\n    );\n  }\n\n  Widget _buildGalleryPage("
    new_end = "        ],\n      ),\n    );\n  }\n\n  Widget _buildGalleryPage("
    if text.count(old_end) != 1:
        raise SystemExit(f"Could not restore gallery widget closing: matches={text.count(old_end)}")
    text = text.replace(old_end, new_end, 1)
    print("fixed: removed competing gallery-level horizontal gesture handler")
elif "onHorizontalDragStart:" not in text:
    print("already fixed: native PageView handles gallery swipes")
else:
    raise SystemExit("Found a gesture wrapper but could not identify its safe start.")

never_scroll = """            child: PageView(
              physics: const NeverScrollableScrollPhysics(),
              controller: _galleryPageController,
"""
scrollable = """            child: PageView(
              controller: _galleryPageController,
"""
if text.count(never_scroll) == 1:
    text = text.replace(never_scroll, scrollable, 1)
    print("fixed: restored native horizontal PageView scrolling")
elif "NeverScrollableScrollPhysics" not in text:
    print("already fixed: PageView is scrollable")
else:
    raise SystemExit("Could not safely restore PageView horizontal scrolling.")

text = text.replace("  double _manualSwipeDistance = 0;\n", "")
source.write_text(text, encoding="utf-8")

test_path = Path("test/widget_test.dart")
test_text = test_path.read_text(encoding="utf-8")
old_drag = """    await tester.drag(
      find.textContaining('swipe right for photos'),
      const Offset(700, 0),
    );
"""
new_drag = """    await tester.drag(find.byType(PageView), const Offset(700, 0));
"""
if test_text.count(old_drag) == 1:
    test_path.write_text(test_text.replace(old_drag, new_drag, 1), encoding="utf-8")
    print("fixed: reverse-swipe test now starts on the actual gallery PageView")
elif new_drag in test_text:
    print("already fixed: reverse-swipe regression test")
else:
    raise SystemExit("Could not safely update the reverse-swipe widget test.")

print("Gallery swipe correction complete.")

#!/usr/bin/env python3
"""Avoid pumpAndSettle hanging while GalleryTab has an indeterminate loader."""
from pathlib import Path

path = Path("test/widget_test.dart")
text = path.read_text(encoding="utf-8")

old = """    await tester.pumpWidget(MaterialApp(home: GalleryTab(onOpenCamera: () {})));
    await tester.pumpAndSettle();
    expect(find.textContaining('swipe left for videos'), findsOneWidget);
    await tester.drag(find.byType(PageView), const Offset(-350, 0));
    await tester.pumpAndSettle();
"""
new = """    await tester.pumpWidget(
      MaterialApp(home: GalleryTab(onOpenCamera: () {})),
    );
    await tester.pump();
    expect(find.textContaining('swipe left for videos'), findsOneWidget);
    await tester.drag(find.byType(PageView), const Offset(-350, 0));
    await tester.pump(const Duration(milliseconds: 800));
"""
if text.count(old) == 1:
    text = text.replace(old, new, 1)
    print("fixed: gallery swipe test uses finite frame pumps")
elif new in text:
    print("already fixed: gallery swipe test uses finite frame pumps")
else:
    raise SystemExit(
        f"Could not safely update gallery test timing: matches={text.count(old)}"
    )

path.write_text(text, encoding="utf-8")

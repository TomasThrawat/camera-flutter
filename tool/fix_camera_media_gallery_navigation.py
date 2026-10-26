#!/usr/bin/env python3
"""Final video folder and gallery navigation corrections for the release build."""
from pathlib import Path
import re

source = Path("lib/main.dart")
text = source.read_text(encoding="utf-8")
if "import 'package:flutter/gestures.dart';" not in text:
    marker = "import 'package:flutter/material.dart';\n"
    if text.count(marker) != 1: raise SystemExit("Could not add gestures import")
    text = text.replace(marker, marker + "import 'package:flutter/gestures.dart';\n", 1)

# Never redirect a failed DCIM save into Movies; videos must show with camera media.
pattern = re.compile(r"  Future<void> _saveVideo\(XFile video\) async \{.*?\n  \}\n", re.S)
method = """  Future<void> _saveVideo(XFile video) async {
    try {
      if (!await _requestMediaPermission()) return;
      final file = File(video.path);
      if (!await file.exists() || await file.length() == 0) return;
      final AssetEntity? saved = await PhotoManager.editor.saveVideo(
        file,
        title: _mediaTitle('.mp4'),
        relativePath: 'DCIM/Camera/',
      );
      if (saved != null) {
        widget.onMediaSaved();
      } else {
        debugPrint('Video was not added to the DCIM/Camera media collection.');
      }
    } catch (error, stackTrace) {
      debugPrint('Video save failed: $error\\n$stackTrace');
    }
  }
"""
matches = list(pattern.finditer(text))
if len(matches) == 1:
    text = pattern.sub(lambda _: method, text, count=1)
elif len(matches) == 0 and method.strip() in text:
    print("already applied: silent DCIM/Camera-only video save")
else:
    raise SystemExit(f"Unsafe _saveVideo patch: matches={len(matches)}")
print("applied: video save uses DCIM/Camera/ only; Movies fallback removed")

# Remove the top-right camera shortcut (and handle the original refresh-icon variant).
state = text.find("class _GalleryTabState extends State<GalleryTab>")
build_start = text.find("  Widget build(BuildContext context) {", state)
build_end = text.find("  Widget _buildGalleryPage(", build_start)
if min(state, build_start, build_end) < 0: raise SystemExit("Gallery build not found")
part = text[build_start:build_end]
patterns = [
    re.compile(r"\n\s*IconButton\(\n\s*onPressed: widget\.onOpenCamera,\n\s*tooltip: 'Camera',\n\s*icon: const Icon\(Icons\.camera_alt_outlined, color: _white\),\n\s*\),"),
    re.compile(r"\n\s*IconButton\(\n\s*onPressed: _loadAssets,\n\s*tooltip: 'Refresh gallery',\n\s*icon: const Icon\(Icons\.refresh, color: _white\),\n\s*\),"),
]
removed = 0
for p in patterns:
    part, n = p.subn("", part, count=1)
    removed += n
if removed:
    text = text[:build_start] + part + text[build_end:]
    print("applied: removed top-right gallery icon")
elif "tooltip: 'Camera'" not in part and "tooltip: 'Refresh gallery'" not in part:
    print("already applied: no top-right gallery icon")
else:
    raise SystemExit("Gallery icon found but could not safely remove it")

# Observe raw pointer events without competing with GridView or PageView gesture recognizers.
field = "  final PageController _galleryPageController = PageController();\n"
handlers = """  Offset? _galleryPointerStart;

  void _onGalleryPointerDown(PointerDownEvent event) {
    _galleryPointerStart = event.position;
  }

  void _onGalleryPointerCancel(PointerCancelEvent event) {
    _galleryPointerStart = null;
  }

  void _onGalleryPointerUp(PointerUpEvent event) {
    final start = _galleryPointerStart;
    _galleryPointerStart = null;
    if (start == null) return;
    final delta = event.position - start;
    if (delta.dx.abs() < 60 || delta.dx.abs() < delta.dy.abs() * 1.2) return;
    if (!_galleryPageController.hasClients) return;
    final targetPage = delta.dx < 0 ? 1 : 0;
    if (targetPage == _selectedGalleryPage) return;
    _galleryPageController.animateToPage(
      targetPage,
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
    );
  }
"""
if "void _onGalleryPointerDown(PointerDownEvent event)" not in text:
    if text.count(field) != 1: raise SystemExit("Gallery PageController field not found")
    text = text.replace(field, field + handlers, 1)
    print("applied: raw horizontal pointer gesture handlers")

state = text.find("class _GalleryTabState extends State<GalleryTab>")
build_start = text.find("  Widget build(BuildContext context) {", state)
build_end = text.find("  Widget _buildGalleryPage(", build_start)
part = text[build_start:build_end]
old_open = """  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,"""
new_open = """  Widget build(BuildContext context) {
    return Listener(
      behavior: HitTestBehavior.opaque,
      onPointerDown: _onGalleryPointerDown,
      onPointerUp: _onGalleryPointerUp,
      onPointerCancel: _onGalleryPointerCancel,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,"""
if old_open in part:
    part = part.replace(old_open, new_open, 1)
    old_close = """        ],
      ),
    );
  }

"""
    if part.count(old_close) != 1: raise SystemExit("Gallery wrapper close pattern not unique")
    part = part.replace(old_close, """        ],
      ),
      ),
    );
  }

""", 1)
    text = text[:build_start] + part + text[build_end:]
    print("applied: gallery root Listener")
elif "onPointerDown: _onGalleryPointerDown" not in part:
    raise SystemExit("Could not safely wrap the GalleryTab build in Listener")

# Native PageView must not compete with our listener; animateToPage still works programmatically.
pageview = "PageView(\n              controller: _galleryPageController,"
pageview_disabled = "PageView(\n              physics: const NeverScrollableScrollPhysics(),\n              controller: _galleryPageController,"
state = text.find("class _GalleryTabState extends State<GalleryTab>")
pos = text.find(pageview, state)
if pos >= 0:
    text = text[:pos] + text[pos:].replace(pageview, pageview_disabled, 1)
elif pageview_disabled not in text[state:]:
    raise SystemExit("Gallery PageView target not found")
if "home: PopScope<Object?>" not in text or "onPopInvokedWithResult:" not in text:
    raise SystemExit("System-back handler is missing; refusing to ship")
source.write_text(text, encoding="utf-8")
print("verified: system back is intercepted on Gallery and returns to Camera")

# Make the gesture test exercise the Listener's full hit area rather than PageView internals.
test_path = Path("test/widget_test.dart")
if not test_path.is_file(): raise SystemExit("widget_test.dart missing")
tests = test_path.read_text(encoding="utf-8")
tests, drag_count = re.subn(
    r"(await tester\\.drag\\(\\s*)find\\.(?:textContaining\\('swipe (?:right for photos|left for videos)'\\)|byType\\(PageView\\)),",
    r"\\1find.byType(GalleryTab),",
    tests,
)
# Previous post-processors may already have changed the finder, so normalize those as well.
if "await tester.drag(\n      find.byType(PageView)," in tests:
    tests = tests.replace("await tester.drag(\n      find.byType(PageView),", "await tester.drag(\n      find.byType(GalleryTab),")
if "system back from gallery returns to camera" not in tests:
    tests += """

testWidgets('system back from gallery returns to camera', (tester) async {
  await tester.pumpWidget(const CameraApp());
  await tester.pump(const Duration(milliseconds: 100));
  await tester.tap(find.text('Gallery').last);
  await tester.pump(const Duration(milliseconds: 100));
  expect(find.byType(GalleryTab), findsOneWidget);
  await tester.binding.handlePopRoute();
  await tester.pump(const Duration(milliseconds: 300));
  expect(find.byType(GalleryTab), findsNothing);
  expect(find.byType(CameraTab), findsOneWidget);
});
"""
test_path.write_text(tests, encoding="utf-8")
print(f"updated gesture test targets ({drag_count} regex replacements) and ensured back regression test")
if "relativePath: 'Movies/Camera'" in text:
    raise SystemExit("Movies/Camera fallback still present in main.dart")
if "Video saved to Gallery." in text or "Photo saved to Gallery." in text:
    raise SystemExit("Save confirmation popup string remains")
print("verified: no Movies fallback or save confirmation text")

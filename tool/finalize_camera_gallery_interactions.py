#!/usr/bin/env python3
"""Finalize gallery gesture handling and silent Camera-folder media saving."""
from pathlib import Path

source = Path("lib/main.dart")
text = source.read_text(encoding="utf-8")

# Pointer listeners observe a horizontal gesture without competing with nested
# GridView/ListView drag recognizers. Disable PageView's own drag recognizer and
# move between the two pages after a clearly horizontal swipe.
# Pointer event types are exported by material.dart; no extra import is needed.

fields_old = """  int _selectedGalleryPage = 0;
  final PageController _galleryPageController = PageController();"""
fields_new = """  int _selectedGalleryPage = 0;
  final PageController _galleryPageController = PageController();
  Offset? _galleryPointerDown;"""
if fields_old in text:
    text = text.replace(fields_old, fields_new, 1)
elif "Offset? _galleryPointerDown;" not in text:
    raise SystemExit("Cannot locate gallery paging fields for swipe handling.")

methods = """  void _onGalleryPointerDown(PointerDownEvent event) {
    _galleryPointerDown = event.position;
  }

  void _onGalleryPointerUp(PointerUpEvent event) {
    final start = _galleryPointerDown;
    _galleryPointerDown = null;
    if (start == null || !_galleryPageController.hasClients) return;
    final dx = event.position.dx - start.dx;
    final dy = event.position.dy - start.dy;
    if (dx.abs() < 70 || dx.abs() <= dy.abs() * 1.25) return;
    final targetPage = dx < 0 ? 1 : 0;
    if (targetPage == _selectedGalleryPage) return;
    _galleryPageController.animateToPage(
      targetPage,
      duration: const Duration(milliseconds: 240),
      curve: Curves.easeOutCubic,
    );
  }

"""
if "void _onGalleryPointerDown(PointerDownEvent event)" not in text:
    dispose_end = """  @override
  void dispose() {
    _galleryPageController.dispose();
    super.dispose();
  }

"""
    if text.count(dispose_end) != 1:
        raise SystemExit("Cannot locate gallery dispose method to insert swipe handlers.")
    text = text.replace(dispose_end, dispose_end + methods, 1)

# Remove only the top-right camera shortcut in the Gallery header.
icon_block = """                IconButton(
                  onPressed: widget.onOpenCamera,
                  tooltip: 'Camera',
                  icon: const Icon(Icons.camera_alt_outlined, color: _white),
                ),
"""
if icon_block in text:
    text = text.replace(icon_block, "", 1)
elif "tooltip: 'Camera'" in text[text.find('class _GalleryTabState'):text.find('Widget _buildGalleryPage(')]:
    raise SystemExit("Found an unexpected top-right camera icon block; refusing unsafe removal.")

# A Listener sits outside the nested vertical grids, so raw pointer events are
# observed while ordinary taps and vertical scrolling keep their normal behavior.
listener_marker = """  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,"""
listener_replacement = """  @override
  Widget build(BuildContext context) {
    return Listener(
      behavior: HitTestBehavior.opaque,
      onPointerDown: _onGalleryPointerDown,
      onPointerUp: _onGalleryPointerUp,
      onPointerCancel: (_) => _galleryPointerDown = null,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,"""
gallery_start = text.find("class _GalleryTabState extends State<GalleryTab>")
gallery_end = text.find("Widget _buildGalleryPage(", gallery_start)
if gallery_start < 0 or gallery_end < 0:
    raise SystemExit("Cannot locate generated gallery widget.")
section = text[gallery_start:gallery_end]
if "onPointerDown: _onGalleryPointerDown" not in section:
    if section.count(listener_marker) != 1:
        raise SystemExit("Cannot locate gallery build root for Listener wrapper.")
    section = section.replace(listener_marker, listener_replacement, 1)
    old_end = """        ],
      ),
    );
  }

  """
    new_end = """        ],
      ),
    ),
    );
  }

  """
    if section.count(old_end) != 1:
        raise SystemExit("Cannot safely close gallery Listener wrapper.")
    section = section.replace(old_end, new_end, 1)
    text = text[:gallery_start] + section + text[gallery_end:]

# Only the Listener performs horizontal page changes.
pageview_old = """            child: PageView(
              controller: _galleryPageController,"""
pageview_new = """            child: PageView(
              physics: const NeverScrollableScrollPhysics(),
              controller: _galleryPageController,"""
if pageview_old in text:
    text = text.replace(pageview_old, pageview_new, 1)
elif "physics: const NeverScrollableScrollPhysics()" not in text[text.find('class _GalleryTabState'):text.find('Widget _buildGalleryPage(')]:
    raise SystemExit("Cannot locate gallery PageView to disable competing drag recognition.")

# Replace the generated save methods by matching balanced braces, not fragile
# line-based regex. All outcomes remain silent; video goes only to DCIM/Camera.
def replace_method(src: str, signature: str, replacement: str) -> str:
    start = src.find(signature)
    if start < 0:
        raise SystemExit(f"Missing method: {signature}")
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit(f"Missing method body: {signature}")
    depth = 0
    end = None
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise SystemExit(f"Unbalanced method body: {signature}")
    return src[:start] + replacement + src[end:]

photo_method = """  Future<void> _savePhoto(XFile image) async {
    try {
      if (!await _requestMediaPermission()) return;
      final file = File(image.path);
      if (!await file.exists() || await file.length() == 0) return;
      await PhotoManager.editor.saveImageWithPath(
        file.path,
        title: _mediaTitle('.jpg'),
        relativePath: 'DCIM/Camera',
      );
      widget.onMediaSaved();
    } catch (_) {
      // Keep capture silent; do not interrupt taking photos with save popups.
    }
  }"""
video_method = """  Future<void> _saveVideo(XFile video) async {
    try {
      if (!await _requestMediaPermission()) return;
      final file = File(video.path);
      if (!await file.exists() || await file.length() == 0) return;
      await PhotoManager.editor.saveVideo(
        file,
        title: _mediaTitle('.mp4'),
        relativePath: 'DCIM/Camera',
      );
      widget.onMediaSaved();
    } catch (_) {
      // Keep capture silent. Never redirect videos into Movies/Camera.
    }
  }"""
text = replace_method(text, "  Future<void> _savePhoto(XFile image) async {", photo_method)
text = replace_method(text, "  Future<void> _saveVideo(XFile video) async {", video_method)
if "relativePath: 'Movies/Camera'" in text:
    # Only fail if it still appears in a save method; other references are not expected here.
    save_start = text.find("  Future<void> _saveVideo(XFile video) async {")
    next_method = text.find("\n  Future<void> ", save_start + 10)
    if next_method < 0: next_method = len(text)
    if "Movies/Camera" in text[save_start:next_method]:
        raise SystemExit("Video save still has a Movies/Camera fallback.")

if "home: PopScope<Object?>" not in text or "if (!didPop && _selectedTab != 0) _openCamera();" not in text:
    raise SystemExit("System-back-to-camera PopScope patch is missing; refusing to ship.")
if "_message('Video saved to Gallery.')" in text or "_message('Photo saved to Gallery.')" in text:
    raise SystemExit("A save-success popup remains in the generated camera code.")

source.write_text(text, encoding="utf-8")
print("verified: horizontal gestures are handled by raw pointer listener on the entire gallery")
print("verified: Gallery header no longer has a top-right camera shortcut")
print("verified: system back from Gallery is intercepted to return to Camera")
print("verified: photo and video saving is silent and targets DCIM/Camera")
print("verified: no Movies/Camera fallback in the video saver")

# Keep focused regression tests aligned with the final generated source.
Path("test/widget_test.dart").write_text("""import 'package:black_camera/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('shows camera capture controls and gallery shortcut', (
    tester,
  ) async {
    await tester.pumpWidget(const CameraApp());
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('PHOTO'), findsOneWidget);
    expect(find.text('VIDEO'), findsOneWidget);
    expect(find.byTooltip('Gallery'), findsOneWidget);
    expect(find.byTooltip('Switch camera'), findsOneWidget);
  });

  testWidgets('gallery switches photos and videos in both swipe directions', (
    tester,
  ) async {
    await tester.pumpWidget(MaterialApp(home: GalleryTab(onOpenCamera: () {})));
    await tester.pumpAndSettle();
    expect(find.textContaining('swipe left for videos'), findsOneWidget);
    expect(find.byTooltip('Camera'), findsNothing);
    await tester.drag(find.byType(PageView), const Offset(-350, 0));
    await tester.pumpAndSettle();
    expect(find.textContaining('swipe right for photos'), findsOneWidget);
    await tester.drag(find.byType(PageView), const Offset(350, 0));
    await tester.pumpAndSettle();
    expect(find.textContaining('swipe left for videos'), findsOneWidget);
  });

  testWidgets('system back from gallery returns to camera', (tester) async {
    await tester.pumpWidget(const CameraApp());
    await tester.pump(const Duration(milliseconds: 100));
    await tester.tap(find.byTooltip('Gallery'));
    await tester.pumpAndSettle();
    expect(find.textContaining('swipe left for videos'), findsOneWidget);
    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();
    expect(find.text('PHOTO'), findsOneWidget);
    expect(find.textContaining('swipe left for videos'), findsNothing);
  });
}
""", encoding="utf-8")
print("updated: widget tests cover both swipe directions and system back from Gallery")

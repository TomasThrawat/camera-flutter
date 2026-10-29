#!/usr/bin/env python3
"""Restore native gallery swipes and apply final camera interaction fixes."""
from pathlib import Path
import re

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
    test_text = test_text.replace(old_drag, new_drag, 1)
    print("fixed: reverse-swipe test starts on the actual gallery PageView")
elif new_drag in test_text:
    print("already fixed: reverse-swipe regression test")
else:
    raise SystemExit("Could not safely update the reverse-swipe widget test.")

# A system back gesture while in Gallery must switch to Camera, not exit.
if "system back from Gallery returns to Camera" not in test_text:
    test_case = """testWidgets('system back from Gallery returns to Camera', (tester) async {
  await tester.pumpWidget(const CameraApp());
  await tester.pump(const Duration(milliseconds: 100));

  final galleryShortcut = find.byTooltip('Gallery');
  expect(galleryShortcut, findsOneWidget);
  await tester.tap(galleryShortcut);
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 150));

  expect(find.textContaining('swipe left for videos'), findsOneWidget);
  expect(find.byTooltip('Gallery'), findsNothing);

  await tester.binding.handlePopRoute();
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 100));

  expect(find.byTooltip('Gallery'), findsOneWidget);
  expect(find.textContaining('swipe left for videos'), findsNothing);
});"""
    main_end = test_text.rfind("\n}")
    if main_end < 0:
        raise SystemExit("Could not find main() closing brace for the system-back regression test.")
    test_text = test_text[:main_end] + "\n\n" + test_case + test_text[main_end:]
    print("added: system-back navigation regression test")
test_path.write_text(test_text, encoding="utf-8")

# Apply changes after all earlier generated-code patchers to avoid regressions.
text = source.read_text(encoding="utf-8")

# Remove the top-right Gallery refresh icon; back is handled by the phone gesture.
refresh = """                IconButton(
                  onPressed: _loadAssets,
                  tooltip: 'Refresh gallery',
                  icon: const Icon(Icons.refresh, color: _white),
                ),
"""
if refresh in text:
    if text.count(refresh) != 1:
        raise SystemExit("Found multiple Gallery refresh icons; refusing an unsafe replacement.")
    text = text.replace(refresh, "", 1)
    print("removed: Gallery refresh icon")
elif "tooltip: 'Refresh gallery'" not in text:
    print("already fixed: Gallery refresh icon absent")
else:
    raise SystemExit("Could not safely identify the Gallery refresh icon.")

# Remove the actual top-right Camera shortcut; rely on the phone's system-back gesture.
camera_shortcut = """                IconButton(
                  onPressed: widget.onOpenCamera,
                  tooltip: 'Camera',
                  icon: const Icon(Icons.camera_alt_outlined, color: _white),
                ),
"""
if camera_shortcut in text:
    if text.count(camera_shortcut) != 1:
        raise SystemExit("Found multiple Gallery camera shortcuts; refusing an unsafe replacement.")
    text = text.replace(camera_shortcut, "", 1)
    print("removed: top-right Gallery camera shortcut")
elif "onPressed: widget.onOpenCamera" not in text:
    print("already fixed: top-right Gallery camera shortcut absent")
else:
    raise SystemExit("Could not safely identify the top-right Gallery camera shortcut.")

if "canPop: _selectedTab == 0" not in text or "onPopInvokedWithResult: (didPop, result)" not in text:
    raise SystemExit("The Gallery system-back PopScope is missing; refusing to build without it.")
print("verified: system back from Gallery returns to Camera")

photo_method = """  Future<void> _savePhoto(XFile image) async {
    try {
      if (!await _requestMediaPermission()) return;
      await PhotoManager.editor.saveImageWithPath(
        image.path,
        title: _mediaTitle('.jpg'),
        relativePath: 'DCIM/Camera',
      );
      widget.onMediaSaved();
    } catch (_) {
      // Capture remains silent; never show a save-status popup.
    }
  }"""
text, photo_count = re.subn(
    r"^  Future<void> _savePhoto\(XFile image\) async \{.*?^  \}",
    photo_method,
    text,
    count=1,
    flags=re.MULTILINE | re.DOTALL,
)
if photo_count != 1:
    raise SystemExit(f"Could not safely replace silent photo save method: matches={photo_count}")

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
      // Capture remains silent; never redirect videos to a different folder.
    }
  }"""
text, video_count = re.subn(
    r"^  Future<void> _saveVideo\(XFile video\) async \{.*?^  \}",
    video_method,
    text,
    count=1,
    flags=re.MULTILINE | re.DOTALL,
)
if video_count != 1:
    raise SystemExit(f"Could not safely replace silent video save method: matches={video_count}")
if "Movies/Camera" in text or "Movies/Camera" in video_method:
    raise SystemExit("Video-save method still contains an unwanted Movies destination.")
print("fixed: save photos/videos silently under DCIM, with a DCIM-only video fallback")

# Reduce pinch sensitivity and ease native camera zoom over frame-paced steps.
zoom_methods = """  void _onZoomUpdate(ScaleUpdateDetails details) {
    final controller = _controller;
    if (details.pointerCount < 2 ||
        _maxZoom <= _minZoom ||
        controller == null ||
        !controller.value.isInitialized) {
      return;
    }
    _requestedZoom =
        (_zoomAtScaleStart * details.scale).clamp(_minZoom, _maxZoom).toDouble();
    _scheduleZoomUpdate();
  }

  // Coalesce high-frequency pointer events but never serialize platform Futures.
  // CameraX supersedes older pending zoom requests, so the latest target can
  // follow the user's fingers without walking through stale intermediate steps.
  void _scheduleZoomUpdate() {
    if (_zoomUpdateTimer?.isActive ?? false) return;
    _zoomUpdateTimer = Timer(const Duration(milliseconds: 16), () {
      _zoomUpdateTimer = null;
      _dispatchLatestZoom();
    });
  }

  void _onZoomEnd(ScaleEndDetails details) {
    _zoomUpdateTimer?.cancel();
    _zoomUpdateTimer = null;
    _dispatchLatestZoom();
  }

  void _dispatchLatestZoom() {
    final controller = _controller;
    if (!mounted ||
        controller == null ||
        !controller.value.isInitialized) {
      return;
    }
    final target = _requestedZoom.clamp(_minZoom, _maxZoom).toDouble();
    if ((target - _zoomLevel).abs() < 0.005) return;
    // Track the newest requested target rather than waiting for each Future.
    _zoomLevel = target;
    unawaited(_applyZoomCommand(controller, target));
  }

  Future<void> _applyZoomCommand(
    CameraController controller,
    double target,
  ) async {
    try {
      await controller.setZoomLevel(target);
    } catch (_) {
      // Superseded CameraX zoom requests may be cancelled by a newer target.
    }
  }

  Future<void> _applyVideoSettings({"""
text, zoom_count = re.subn(
    r"^  void _onZoomUpdate\(ScaleUpdateDetails details\) \{.*?^  Future<void> _applyVideoSettings\(\{",
    zoom_methods,
    text,
    count=1,
    flags=re.MULTILINE | re.DOTALL,
)
if zoom_count != 1:
    raise SystemExit(f"Could not safely replace camera zoom handlers: matches={zoom_count}")
# Start any new pinch from the latest target so rapid consecutive gestures stay continuous.
zoom_start_old = """  void _onZoomStart(ScaleStartDetails details) {
    _zoomAtScaleStart = _zoomLevel;
  }"""
zoom_start_new = """  void _onZoomStart(ScaleStartDetails details) {
    _zoomAtScaleStart = _requestedZoom;
  }"""
zoom_start_clamped = """  void _onZoomStart(ScaleStartDetails details) {
    // Start at the latest requested zoom, including any update still in flight.
    _zoomAtScaleStart = _requestedZoom.clamp(_minZoom, _maxZoom).toDouble();
  }"""
zoom_start_current = """  void _onZoomStart(ScaleStartDetails details) {
    _zoomUpdateTimer?.cancel();
    _zoomUpdateTimer = null;
    _zoomAtScaleStart = _requestedZoom.clamp(_minZoom, _maxZoom).toDouble();
  }"""
if zoom_start_old in text:
    text = text.replace(zoom_start_old, zoom_start_current, 1)
elif any(pattern in text for pattern in (zoom_start_new, zoom_start_clamped, zoom_start_current)):
    print("already fixed: zoom gesture starts from latest target and clears stale timer")
else:
    raise SystemExit("Could not safely adjust zoom gesture start.")
print("fixed: latest-target pinch zoom without serialized platform updates")

source.write_text(text, encoding="utf-8")
print("Camera final interaction patch complete.")

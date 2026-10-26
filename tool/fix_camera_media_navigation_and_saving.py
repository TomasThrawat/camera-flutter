#!/usr/bin/env python3
"""Finalize camera media paths, quiet capture UX, and gallery navigation."""
from pathlib import Path

source = Path("lib/main.dart")
text = source.read_text(encoding="utf-8")


def replace_region(start_marker: str, end_marker: str, replacement: str, label: str) -> None:
    global text
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker)) if start >= 0 else -1
    if start < 0 or end < 0:
        if replacement in text:
            print(f"already applied: {label}")
            return
        raise SystemExit(f"Could not safely locate {label}: start={start}, end={end}")
    text = text[:start] + replacement + text[end:]
    print(f"applied: {label}")


photo = """  Future<void> _savePhoto(XFile image) async {
    try {
      if (!await _requestMediaPermission()) return;
      final file = File(image.path);
      if (!await file.exists() || await file.length() == 0) return;
      await PhotoManager.editor.saveImageWithPath(
        image.path,
        title: _mediaTitle('.jpg'),
        relativePath: 'DCIM/Camera/',
      );
      widget.onMediaSaved();
    } catch (_) {
      // Capture stays silent; do not show save-status notifications.
    }
  }

"""
replace_region("  Future<void> _savePhoto(XFile image) async {", "  Future<void> _saveVideo(XFile video) async {", photo, "silent photo save to DCIM/Camera")

video = """  Future<void> _saveVideo(XFile video) async {
    try {
      if (!await _requestMediaPermission()) return;
      final file = File(video.path);
      if (!await file.exists() || await file.length() == 0) return;

      final title = _mediaTitle('.mp4');
      AssetEntity? saved;
      try {
        saved = await PhotoManager.editor.saveVideo(
          file,
          title: title,
          relativePath: 'DCIM/Camera/',
        );
      } catch (_) {
        // Retry the same camera folder using the plugin's non-trailing-slash form.
      }
      if (saved == null) {
        try {
          saved = await PhotoManager.editor.saveVideo(
            file,
            title: title,
            relativePath: 'DCIM/Camera',
          );
        } catch (_) {
          return;
        }
      }
      if (saved != null) widget.onMediaSaved();
    } catch (_) {
      // Capture stays silent; never fall back to Movies or show a save popup.
    }
  }

"""
replace_region("  Future<void> _saveVideo(XFile video) async {", "  void _message(String value) {", video, "silent video save only to DCIM/Camera")

# Remove the camera shortcut from the gallery header; the phone's back gesture
# is handled by the app-level PopScope to return to Camera.
header_camera = """                IconButton(
                  onPressed: widget.onOpenCamera,
                  tooltip: 'Camera',
                  icon: const Icon(Icons.camera_alt_outlined, color: _white),
                ),
"""
if header_camera in text:
    text = text.replace(header_camera, "", 1)
    print("applied: removed top-right gallery camera icon")
elif "tooltip: 'Camera'," not in text:
    print("already applied: gallery camera icon removed")
else:
    raise SystemExit("Could not safely identify the top-right gallery camera icon")

refresh = """                IconButton(
                  onPressed: _loadAssets,
                  tooltip: 'Refresh gallery',
                  icon: const Icon(Icons.refresh, color: _white),
                ),
"""
if refresh in text:
    text = text.replace(refresh, "", 1)
    print("applied: removed top-right refresh icon")

# Make the intended horizontal two-page gallery explicit and make sure no
# competing gallery-level horizontal drag recognizer captures the gesture.
old_page_view = """            child: PageView(
              controller: _galleryPageController,
"""
new_page_view = """            child: PageView(
              scrollDirection: Axis.horizontal,
              physics: const PageScrollPhysics(parent: ClampingScrollPhysics()),
              controller: _galleryPageController,
"""
if old_page_view in text:
    text = text.replace(old_page_view, new_page_view, 1)
    print("applied: explicit horizontal gallery paging")
elif "physics: const PageScrollPhysics(parent: ClampingScrollPhysics())," in text:
    print("already applied: explicit horizontal gallery paging")
else:
    raise SystemExit("Could not locate the generated gallery PageView")

gallery_start = text.find("class _GalleryTabState extends State<GalleryTab>")
gallery_end = text.find("  Widget _permissionMessage()", gallery_start)
if gallery_start < 0 or gallery_end < 0:
    raise SystemExit("Could not validate GalleryTab gesture hierarchy")
gallery = text[gallery_start:gallery_end]
if "onHorizontalDragStart:" in gallery or "onHorizontalDragUpdate:" in gallery or "onHorizontalDragEnd:" in gallery:
    raise SystemExit("A competing horizontal drag handler remains around GalleryTab")

# The existing final navigation patch must intercept system back on the Gallery
# tab. Fail the build rather than silently shipping an app that exits.
if "home: PopScope<Object?>(" not in text or "if (!didPop && _selectedTab != 0) _openCamera();" not in text:
    raise SystemExit("System back must be intercepted to return from Gallery to Camera")

source.write_text(text, encoding="utf-8")

# Add a runtime widget regression for Android's system-back route, without using
# an emulator. The swipe test is supplied by the previous CI patch and exercises
# PageView in both directions.
test_path = Path("test/widget_test.dart")
test = test_path.read_text(encoding="utf-8")
test_name = "system back from gallery returns to camera instead of exiting"
if test_name not in test:
    marker = "\n}"
    index = test.rfind(marker)
    if index < 0:
        raise SystemExit("Could not append gallery back-navigation regression test")
    extra = """

  testWidgets('system back from gallery returns to camera instead of exiting', (
    tester,
  ) async {
    await tester.pumpWidget(const CameraApp());
    await tester.pump(const Duration(milliseconds: 100));
    await tester.tap(find.byTooltip('Gallery'));
    await tester.pump(const Duration(milliseconds: 100));
    await tester.binding.handlePopRoute();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('PHOTO'), findsOneWidget);
    expect(find.textContaining('swipe left for videos'), findsNothing);
    expect(find.byTooltip('Camera'), findsOneWidget);
  });
"""
    test = test[:index] + extra + test[index:]
    test_path.write_text(test, encoding="utf-8")
    print("applied: system-back navigation regression test")
else:
    print("already applied: system-back navigation regression test")

print("Final camera navigation and video path patch complete.")

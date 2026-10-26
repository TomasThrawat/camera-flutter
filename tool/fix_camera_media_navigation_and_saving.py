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

# Native PageView gestures passed widget tests but were not reliable on the
# user's physical phone. Observe raw pointer events around the entire gallery;
# this does not compete in Flutter's gesture arena with vertical GridView scroll.
gallery_state_marker = "class _GalleryTabState extends State<GalleryTab>"
gallery_state = text.find(gallery_state_marker)
if gallery_state < 0:
    raise SystemExit("Could not find GalleryTab state to wire raw swipe input")
state_old = """  int _selectedGalleryPage = 0;
  final PageController _galleryPageController = PageController();
"""
state_new = """  int _selectedGalleryPage = 0;
  Offset? _galleryPointerStart;
  final PageController _galleryPageController = PageController();
"""
if state_old in text[gallery_state:]:
    text = text.replace(state_old, state_new, 1)
elif state_new in text[gallery_state:]:
    print("already applied: gallery pointer state")
else:
    raise SystemExit("Could not safely add gallery pointer start state")

init_old = """  @override
  void initState() {
    super.initState();
    _loadAssets();
  }
"""
handler = """  void _handleGalleryPointerUp(PointerUpEvent event) {
    final start = _galleryPointerStart;
    _galleryPointerStart = null;
    if (start == null) return;
    final delta = event.position - start;
    if (delta.dx.abs() < 70 || delta.dx.abs() < delta.dy.abs() * 1.2) return;
    if (!_galleryPageController.hasClients) return;
    final targetPage = delta.dx < 0 ? 1 : 0;
    if (targetPage == _selectedGalleryPage) return;
    unawaited(
      _galleryPageController.animateToPage(
        targetPage,
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _loadAssets();
  }
"""
init_pos = text.find(init_old, gallery_state)
if init_pos >= 0:
    text = text[:init_pos] + handler + text[init_pos + len(init_old):]
elif "void _handleGalleryPointerUp(PointerUpEvent event)" in text[gallery_state:]:
    print("already applied: raw pointer swipe handler")
else:
    raise SystemExit("Could not insert gallery pointer swipe handler")

root_old = """    return SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
"""
root_new = """    return Listener(
      behavior: HitTestBehavior.opaque,
      onPointerDown: (event) => _galleryPointerStart = event.position,
      onPointerCancel: (_) => _galleryPointerStart = null,
      onPointerUp: _handleGalleryPointerUp,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
"""
root_pos = text.find(root_old, gallery_state)
if root_pos >= 0:
    text = text[:root_pos] + root_new + text[root_pos + len(root_old):]
elif "onPointerUp: _handleGalleryPointerUp," in text[gallery_state:]:
    print("already applied: raw pointer listener over gallery")
else:
    raise SystemExit("Could not wrap GalleryTab in a raw pointer Listener")

close_old = """        ],
      ),
    );
  }

  Widget _buildGalleryPage("""
close_new = """        ],
      ),
    ),
    );
  }

  Widget _buildGalleryPage("""
close_pos = text.find(close_old, gallery_state)
if close_pos >= 0:
    text = text[:close_pos] + close_new + text[close_pos + len(close_old):]
elif "Widget _buildGalleryPage(" in text[gallery_state:] and "    ),\n    );\n  }\n\n  Widget _buildGalleryPage(" in text[gallery_state:]:
    print("already applied: Listener closes around entire gallery")
else:
    raise SystemExit("Could not safely close the raw pointer Listener")

# Keep the gesture logic in Listener alone; PageView is animated programmatically.
page_old = """            child: PageView(
              controller: _galleryPageController,
"""
page_new = """            child: PageView(
              physics: const NeverScrollableScrollPhysics(),
              controller: _galleryPageController,
"""
if page_old in text[gallery_state:]:
    text = text[:gallery_state] + text[gallery_state:].replace(page_old, page_new, 1)
elif "physics: const NeverScrollableScrollPhysics(),\n              controller: _galleryPageController," in text[gallery_state:]:
    print("already applied: PageView uses Listener-controlled movement")
else:
    raise SystemExit("Could not disable competing native PageView swipe recognizer")

gallery_end = text.find("  Widget _permissionMessage()", gallery_state)
if gallery_end < 0:
    raise SystemExit("Could not validate GalleryTab gesture hierarchy")
gallery = text[gallery_state:gallery_end]
if "onHorizontalDragStart:" in gallery or "onHorizontalDragUpdate:" in gallery or "onHorizontalDragEnd:" in gallery:
    raise SystemExit("A competing horizontal drag recognizer remains around GalleryTab")

# The existing final navigation patch must intercept system back on the Gallery tab.
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

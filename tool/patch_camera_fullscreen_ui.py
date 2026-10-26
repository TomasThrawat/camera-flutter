#!/usr/bin/env python3
"""Make the camera preview full-screen and simplify camera/gallery navigation."""
from pathlib import Path
import re

source = Path("lib/main.dart")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if text.count(old) == 1:
        text = text.replace(old, new, 1)
        print(f"applied: {label}")
    elif new in text:
        print(f"already applied: {label}")
    else:
        raise SystemExit(
            f"Could not safely apply {label}: expected one match, found {text.count(old)}."
        )


# Remove the two permanent Camera/Gallery destinations below the shutter.
nav_pattern = (
    r"(?ms)^        bottomNavigationBar: SafeArea\(.*?^        \),\n"
    r"(?=      \),\n    \);\n  }\n\})"
)
text, nav_count = re.subn(nav_pattern, "", text, count=1)
if nav_count:
    print("applied: remove bottom Camera/Gallery navigation icons")
elif "bottomNavigationBar:" not in text:
    print("already applied: bottom Camera/Gallery navigation icons removed")
else:
    raise SystemExit("Could not safely remove the bottom navigation bar.")

# This private widget is only used by the removed bottom navigation bar.
nav_class = text.find("\nclass _NavigationItem extends StatelessWidget")
if nav_class >= 0:
    camera_class = text.find("\nclass CameraTab extends StatefulWidget", nav_class)
    if camera_class < 0:
        raise SystemExit("Could not locate CameraTab after the navigation widget.")
    text = text[:nav_class] + text[camera_class:]
    print("applied: remove unused bottom navigation widget")
elif "class _NavigationItem extends StatelessWidget" not in text:
    print("already applied: unused bottom navigation widget removed")

# The gallery remains accessible next to the shutter; add a route back to camera
# on the Gallery page because the permanent bottom navigation is gone.
gallery_title = """                const Expanded(
                  child: Text(
                    'Gallery',
                    style: TextStyle(
                      color: _white,
                      fontSize: 25,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
"""
gallery_title_with_camera = gallery_title + """                IconButton(
                  onPressed: widget.onOpenCamera,
                  tooltip: 'Camera',
                  icon: const Icon(Icons.camera_alt_outlined, color: _white),
                ),
"""
replace_once(
    gallery_title,
    gallery_title_with_camera,
    "add camera shortcut to Gallery header",
)

# Replace the old vertical Column layout with a layered camera scene. The camera
# preview fills the entire available area; all controls are drawn above it.
build_start_marker = """  @override
  Widget build(BuildContext context) {
    final controller = _controller;
"""
build_end_marker = "\n  Widget _cameraPlaceholder()"
camera_state = text.find("class _CameraTabState extends State<CameraTab>")
if camera_state < 0:
    raise SystemExit("Could not locate the camera state class.")

if "// FULLSCREEN_CAPTURE_UI_PATCH_APPLIED" not in text:
    build_start = text.find(build_start_marker, camera_state)
    build_end = text.find(build_end_marker, build_start)
    if build_start < 0 or build_end < 0:
        raise SystemExit("Could not locate the camera build method boundaries.")

    new_build = r"""  // FULLSCREEN_CAPTURE_UI_PATCH_APPLIED
  @override
  Widget build(BuildContext context) {
    final controller = _controller;
    final videoQuality =
        _videoResolution == VideoResolution.p1080 ? '1080p' : '720p';

    return Stack(
      fit: StackFit.expand,
      children: [
        if (controller != null &&
            controller.value.isInitialized &&
            _error == null)
          GestureDetector(
            onScaleStart: _onZoomStart,
            onScaleUpdate: _onZoomUpdate,
            child: ClipRect(child: CameraPreview(controller)),
          )
        else
          Positioned.fill(child: _cameraPlaceholder()),

        Positioned(
          top: 0,
          left: 0,
          right: 0,
          child: SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 4, 12, 0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  if (_recording)
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 7,
                          height: 7,
                          decoration: const BoxDecoration(
                            color: _white,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 7),
                        Text(
                          _recordTime,
                          style: const TextStyle(
                            color: _white,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    )
                  else if (_mode == CaptureMode.video)
                    GestureDetector(
                      onTap: _showVideoSettings,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 11,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0x66000000),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: const Color(0x55FFFFFF),
                          ),
                        ),
                        child: Text(
                          '$videoQuality · $_videoFps FPS',
                          style: const TextStyle(
                            color: _white,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    )
                  else
                    const SizedBox(width: 40),
                  IconButton(
                    onPressed: _toggleTorch,
                    tooltip: 'Flashlight',
                    icon: Icon(
                      _torchEnabled ? Icons.flash_on : Icons.flash_off,
                      color: _white,
                    ),
                    style: IconButton.styleFrom(
                      backgroundColor: const Color(0x66000000),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),

        if (_busy)
          Positioned(
            top: 64,
            right: 22,
            child: const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: _white,
              ),
            ),
          ),

        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          child: SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(28, 0, 28, 12),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _ModeLabel(
                        label: 'PHOTO',
                        selected: _mode == CaptureMode.photo,
                        onTap: () => _changeMode(CaptureMode.photo),
                      ),
                      const SizedBox(width: 30),
                      _ModeLabel(
                        label: 'VIDEO',
                        selected: _mode == CaptureMode.video,
                        onTap: () => _changeMode(CaptureMode.video),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _RoundControl(
                        icon: Icons.photo_library_outlined,
                        label: 'Gallery',
                        onTap: _recording ? null : widget.onOpenGallery,
                      ),
                      Semantics(
                        label: _recording ? 'Stop video recording' : 'Capture',
                        button: true,
                        child: GestureDetector(
                          onTap: _busy ? null : _shutterPressed,
                          child: Container(
                            width: 76,
                            height: 76,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              border: Border.all(color: _white, width: 3),
                            ),
                            padding: const EdgeInsets.all(7),
                            child: Center(
                              child: AnimatedContainer(
                                duration: const Duration(milliseconds: 120),
                                width: _recording ? 24 : 56,
                                height: _recording ? 24 : 56,
                                decoration: BoxDecoration(
                                  color: _white,
                                  shape: _recording
                                      ? BoxShape.rectangle
                                      : BoxShape.circle,
                                  borderRadius: _recording
                                      ? BorderRadius.circular(5)
                                      : null,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                      _RoundControl(
                        icon: Icons.flip_camera_android_outlined,
                        label: 'Switch camera',
                        onTap: _switchCamera,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
"""
    text = text[:build_start] + new_build + text[build_end:]
    print("applied: full-screen camera preview behind overlay controls")
else:
    print("already applied: full-screen camera preview behind overlay controls")

source.write_text(text, encoding="utf-8")

test_path = Path("test/widget_test.dart")
test = test_path.read_text(encoding="utf-8")
old_test = """void main() {
  testWidgets('shows only Camera and Gallery as primary destinations', (
    tester,
  ) async {
    await tester.pumpWidget(const CameraApp());
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Camera'), findsOneWidget);
    expect(find.text('Gallery'), findsOneWidget);
  });
}
"""
new_test = """void main() {
  testWidgets('shows full-screen capture controls and gallery shortcut', (
    tester,
  ) async {
    await tester.pumpWidget(const CameraApp());
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('PHOTO'), findsOneWidget);
    expect(find.text('VIDEO'), findsOneWidget);
    expect(find.byTooltip('Gallery'), findsOneWidget);
    expect(find.byTooltip('Switch camera'), findsOneWidget);
    expect(find.text('Camera'), findsNothing);
  });
}
"""
if old_test in test:
    test_path.write_text(test.replace(old_test, new_test, 1), encoding="utf-8")
    print("applied: update widget test for the full-screen controls")
elif new_test in test:
    print("already applied: widget test reflects full-screen controls")
else:
    raise SystemExit("Could not safely update the old bottom-navigation widget test.")

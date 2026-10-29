#!/usr/bin/env python3
"""Apply touch focus, swipeable media gallery, and direct video setting controls."""
from pathlib import Path

p = Path("lib/main.dart")
s = p.read_text(encoding="utf-8")


def sub_once(old, new, label):
    global s
    if s.count(old) == 1:
        s = s.replace(old, new, 1)
        print("applied: " + label)
    elif new in s:
        print("already applied: " + label)
    else:
        raise SystemExit(f"Unsafe patch for {label}; matches={s.count(old)}")


a = s.find("  Future<void> _showVideoSettings() async {")
b = s.find("  Future<void> _applyVideoSettings({", a)
if a >= 0 and b > a:
    s = s[:a] + s[b:]
    print("applied: remove popup video settings")
elif a < 0:
    print("already applied: popup video settings removed")
else:
    raise SystemExit("Could not find popup method end.")

sub_once(
"""  Future<void> _applyVideoSettings({
    required VideoResolution resolution,
    required int fps,
  }) async {""",
"""  Future<void> _applyVideoSettings({
    required VideoResolution resolution,
    required int fps,
    bool prioritizeFps = false,
  }) async {""",
"allow frame-rate priority",
)
sub_once(
"""    final candidates = <({VideoResolution resolution, int fps})>[
      (resolution: resolution, fps: fps),
      if (fps == 60) (resolution: resolution, fps: 30),
      if (fps == 60 && resolution != VideoResolution.p720)
        (resolution: VideoResolution.p720, fps: 60),
      (resolution: VideoResolution.p720, fps: 30),
      (resolution: previousResolution, fps: previousFps),
    ];""",
"""    final candidates = <({VideoResolution resolution, int fps})>[
      (resolution: resolution, fps: fps),
      if (prioritizeFps && fps == 60 && resolution != VideoResolution.p720)
        (resolution: VideoResolution.p720, fps: 60),
      if (fps == 60) (resolution: resolution, fps: 30),
      if (!prioritizeFps && fps == 60 && resolution != VideoResolution.p720)
        (resolution: VideoResolution.p720, fps: 60),
      (resolution: VideoResolution.p720, fps: 30),
      (resolution: previousResolution, fps: previousFps),
    ];""",
"keep the requested setting on camera fallback",
)

old_ui = """                  else if (_mode == CaptureMode.video)
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
"""
new_ui = """                  else if (_mode == CaptureMode.video)
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _InlineSettingChip(
                          label: videoQuality,
                          onTap: _recording || _busy || _loading
                              ? null
                              : () => unawaited(
                                  _applyVideoSettings(
                                    resolution:
                                        _videoResolution == VideoResolution.p1080
                                        ? VideoResolution.p720
                                        : VideoResolution.p1080,
                                    fps: _videoFps,
                                  ),
                                ),
                        ),
                        const SizedBox(width: 6),
                        _InlineSettingChip(
                          label: '$_videoFps FPS',
                          onTap: _recording || _busy || _loading
                              ? null
                              : () => unawaited(
                                  _applyVideoSettings(
                                    resolution: _videoResolution,
                                    fps: _videoFps == 30 ? 60 : 30,
                                    prioritizeFps: true,
                                  ),
                                ),
                        ),
                      ],
                    )
                  else
                    const SizedBox(width: 40),
"""
sub_once(old_ui, new_ui, "direct tap resolution and FPS")

chip = """class _InlineSettingChip extends StatelessWidget {
  const _InlineSettingChip({required this.label, required this.onTap});
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    label: label,
    child: GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0x99000000),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: onTap == null
                ? const Color(0x55777777)
                : const Color(0x77FFFFFF),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: onTap == null ? _muted : _white,
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    ),
  );
}

class GalleryTab extends StatefulWidget {
"""
if "class _InlineSettingChip extends StatelessWidget" not in s:
    sub_once("class GalleryTab extends StatefulWidget {\n", chip, "inline setting chip widget")

marker = "  // FULLSCREEN_CAPTURE_UI_PATCH_APPLIED"
start = s.find(marker)
old_open = """          GestureDetector(
            onScaleStart: _onZoomStart,
            onScaleUpdate: _onZoomUpdate,
            child: ClipRect("""
if start < 0:
    raise SystemExit("Fullscreen camera build marker was not found.")
if old_open in s[start:]:
    s = s.replace(old_open, """          LayoutBuilder(
            builder: (context, constraints) => GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTapDown: (details) => unawaited(
                _focusAt(details.localPosition, constraints.biggest),
              ),
              onScaleStart: _onZoomStart,
              onScaleUpdate: _onZoomUpdate,
              onScaleEnd: _onZoomEnd,
              child: ClipRect(""", 1)
    close = """          )
        else
          Positioned.fill(child: _cameraPlaceholder()),"""
    if s.count(close) != 1:
        raise SystemExit("Could not safely close focus LayoutBuilder.")
    s = s.replace(close, """            ),
          )
        else
          Positioned.fill(child: _cameraPlaceholder()),""", 1)
    print("applied: tap focus with pinch zoom")
elif "_focusAt(details.localPosition, constraints.biggest)" in s:
    print("already applied: tap focus with pinch zoom")
else:
    raise SystemExit("Could not safely apply tap focus.")

focus = """
  Future<void> _focusAt(Offset position, Size previewSize) async {
    final controller = _controller;
    if (controller == null ||
        !controller.value.isInitialized ||
        previewSize.width <= 0 ||
        previewSize.height <= 0) {
      return;
    }

    // Match the BoxFit.cover crop used by the full-screen preview so the
    // selected camera point corresponds to the visible pixel under the tap.
    final orientation = MediaQuery.orientationOf(context);
    final contentAspectRatio = orientation == Orientation.portrait
        ? 1 / controller.value.aspectRatio
        : controller.value.aspectRatio;
    final viewportAspectRatio = previewSize.width / previewSize.height;
    var x = position.dx / previewSize.width;
    var y = position.dy / previewSize.height;

    if (viewportAspectRatio < contentAspectRatio) {
      final visibleFraction = viewportAspectRatio / contentAspectRatio;
      x = (1 - visibleFraction) / 2 + x * visibleFraction;
    } else if (viewportAspectRatio > contentAspectRatio) {
      final visibleFraction = contentAspectRatio / viewportAspectRatio;
      y = (1 - visibleFraction) / 2 + y * visibleFraction;
    }

    final point = Offset(
      x.clamp(0.0, 1.0).toDouble(),
      y.clamp(0.0, 1.0).toDouble(),
    );
    try {
      await controller.setFocusPoint(point);
    } catch (_) {
      // Touch focus is optional on some devices.
    }
    try {
      await controller.setExposurePoint(point);
    } catch (_) {
      // Exposure-point metering may not be supported by every camera.
    }
  }
"""
if "Future<void> _focusAt(Offset position, Size previewSize)" not in s:
    sub_once("\n  Widget _cameraPlaceholder()", focus + "\n  Widget _cameraPlaceholder()", "focus/exposure point mapping")
else:
    # Replace the earlier basic implementation, which didn't account for BoxFit.cover cropping.
    start_focus = s.find("  Future<void> _focusAt(Offset position, Size previewSize) async {")
    end_focus = s.find("\n  Widget _cameraPlaceholder()", start_focus)
    if start_focus < 0 or end_focus < 0:
        raise SystemExit("Could not replace existing focus-point mapper.")
    s = s[:start_focus] + focus + s[end_focus:]
    print("updated: focus point mapping accounts for full-screen crop")

sub_once(
"""  String? _error;
  List<AssetEntity> _assets = [];

  @override
  void initState() {
    super.initState();
    _loadAssets();
  }

""",
"""  String? _error;
  List<AssetEntity> _imageAssets = [];
  List<AssetEntity> _videoAssets = [];
  int _selectedGalleryPage = 0;
  final PageController _galleryPageController = PageController();

  @override
  void initState() {
    super.initState();
    _loadAssets();
  }

  @override
  void dispose() {
    _galleryPageController.dispose();
    super.dispose();
  }

""",
"separate photos and videos in gallery",
)

ls = s.find("  Future<void> _loadAssets() async {")
le = s.find("\n  Future<void> _openAsset(AssetEntity asset) async {", ls)
if ls < 0 or le < 0:
    raise SystemExit("Could not locate gallery loader.")
loader = """  Future<void> _loadAssets() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final permission = await PhotoManager.requestPermissionExtend();
      if (!(permission.isAuth || permission.hasAccess)) {
        if (mounted) {
          setState(() {
            _hasPermission = false;
            _imageAssets = [];
            _videoAssets = [];
          });
        }
        return;
      }
      Future<List<AssetEntity>> loadType(RequestType type) async {
        final paths = await PhotoManager.getAssetPathList(
          type: type,
          onlyAll: true,
        );
        if (paths.isEmpty) return <AssetEntity>[];
        final assets = await paths.first.getAssetListPaged(page: 0, size: 200);
        assets.sort((a, b) => b.createDateTime.compareTo(a.createDateTime));
        return assets;
      }
      final results = await Future.wait([
        loadType(RequestType.image),
        loadType(RequestType.video),
      ]);
      if (mounted) {
        setState(() {
          _hasPermission = true;
          _imageAssets = results[0];
          _videoAssets = results[1];
        });
      }
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not load media from this device.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }
"""
s = s[:ls] + loader + s[le:]
print("applied: load images and videos independently")

gclass = s.find("class _GalleryTabState extends State<GalleryTab>")
gstart = s.find("""  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,""", gclass)
gend = s.find("\n  Widget _permissionMessage()", gstart)
if gstart < 0 or gend < 0:
    raise SystemExit("Could not locate gallery build method.")
gallery = """  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 14, 12, 16),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Gallery',
                        style: TextStyle(
                          color: _white,
                          fontSize: 25,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        _selectedGalleryPage == 0
                            ? 'Photos · swipe left for videos'
                            : 'Videos · swipe right for photos',
                        style: const TextStyle(color: _muted, fontSize: 12),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: widget.onOpenCamera,
                  tooltip: 'Camera',
                  icon: const Icon(Icons.camera_alt_outlined, color: _white),
                ),
              ],
            ),
          ),
          Expanded(
            child: PageView(
              controller: _galleryPageController,
              onPageChanged: (page) => setState(() => _selectedGalleryPage = page),
              children: [
                _buildGalleryPage(
                  _imageAssets,
                  emptyMessage: 'Photos you take will appear here.',
                  emptyIcon: Icons.photo_outlined,
                ),
                _buildGalleryPage(
                  _videoAssets,
                  emptyMessage: 'Videos you record will appear here.',
                  emptyIcon: Icons.video_library_outlined,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGalleryPage(
    List<AssetEntity> assets, {
    required String emptyMessage,
    required IconData emptyIcon,
  }) {
    return RefreshIndicator(
      onRefresh: _loadAssets,
      color: _white,
      backgroundColor: _surface,
      child: _loading
          ? ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: const [
                SizedBox(
                  height: 260,
                  child: Center(
                    child: CircularProgressIndicator(color: _white, strokeWidth: 2),
                  ),
                ),
              ],
            )
          : !_hasPermission
          ? ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: [SizedBox(height: 280, child: _permissionMessage())],
            )
          : _error != null
          ? ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: [
                SizedBox(height: 280, child: _emptyMessage(_error!, Icons.error_outline)),
              ],
            )
          : assets.isEmpty
          ? ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: [SizedBox(height: 280, child: _emptyMessage(emptyMessage, emptyIcon))],
            )
          : GridView.builder(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(3, 0, 3, 8),
              itemCount: assets.length,
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3,
                crossAxisSpacing: 3,
                mainAxisSpacing: 3,
              ),
              itemBuilder: (context, index) {
                final asset = assets[index];
                return _GalleryTile(asset: asset, onTap: () => _openAsset(asset));
              },
            ),
    );
  }
"""
s = s[:gstart] + gallery + s[gend:]
p.write_text(s, encoding="utf-8")

Path("test/widget_test.dart").write_text(
"""import 'package:black_camera/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
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

  testWidgets('gallery switches between photos and videos with a swipe', (
    tester,
  ) async {
    await tester.pumpWidget(MaterialApp(home: GalleryTab(onOpenCamera: () {})));
    await tester.pumpAndSettle();
    expect(find.textContaining('swipe left for videos'), findsOneWidget);
    await tester.drag(find.byType(PageView), const Offset(-350, 0));
    await tester.pumpAndSettle();
    expect(find.textContaining('swipe right for photos'), findsOneWidget);
  });
}
""", encoding="utf-8")
print("updated: widget tests")

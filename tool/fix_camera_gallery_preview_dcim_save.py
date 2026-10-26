#!/usr/bin/env python3
"""Apply final gallery navigation and public camera-folder save behavior."""
from pathlib import Path
import re

source = Path("lib/main.dart")
text = source.read_text(encoding="utf-8")

def replace_method(signature: str, replacement: str, label: str) -> None:
    global text
    pattern = re.compile(r"  " + re.escape(signature) + r".*?\n  }\n", re.S)
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        if replacement.strip() in text:
            print(f"already fixed: {label}")
            return
        raise SystemExit(f"Could not safely locate {label}: matches={len(matches)}")
    text = text[:matches[0].start()] + replacement + text[matches[0].end():]
    print(f"fixed: {label}")

replace_method(
    "Future<void> _savePhoto(XFile image) async {",
    """  Future<void> _savePhoto(XFile image) async {
    try {
      if (!await _requestMediaPermission()) return;
      final file = File(image.path);
      if (!await file.exists() || await file.length() == 0) return;
      final saved = await PhotoManager.editor.saveImageWithPath(
        image.path,
        title: _mediaTitle('.jpg'),
        relativePath: 'DCIM/Camera/',
      );
      if (saved != null) widget.onMediaSaved();
    } catch (_) {
      // Capturing should remain quiet; do not show save-status popups.
    }
  }
""",
    "silent photo save to DCIM/Camera/",
)
replace_method(
    "Future<void> _saveVideo(XFile video) async {",
    """  Future<void> _saveVideo(XFile video) async {
    try {
      if (!await _requestMediaPermission()) return;
      final file = File(video.path);
      if (!await file.exists() || await file.length() == 0) return;
      final saved = await PhotoManager.editor.saveVideo(
        file,
        title: _mediaTitle('.mp4'),
        relativePath: 'DCIM/Camera/',
      );
      if (saved != null) widget.onMediaSaved();
    } catch (_) {
      // No fallback to Movies and no save-status popup.
    }
  }
""",
    "silent video save only to DCIM/Camera/",
)

refresh = """                IconButton(
                  onPressed: _loadAssets,
                  tooltip: 'Refresh gallery',
                  icon: const Icon(Icons.refresh, color: _white),
                ),
"""
if text.count(refresh) == 1:
    text = text.replace(refresh, "", 1)
    print("fixed: removed the gallery header refresh icon")
elif "tooltip: 'Refresh gallery'" in text:
    raise SystemExit("Could not safely remove the gallery header icon")
else:
    print("already fixed: no gallery header refresh icon")

replace_method(
    "Future<void> _openAsset(AssetEntity asset) async {",
    """  Future<void> _openAsset(AssetEntity asset) async {
    final currentAssets = asset.type == AssetType.video ? _videoAssets : _imageAssets;
    final index = currentAssets.indexOf(asset);
    if (!mounted || index < 0) return;
    final assets = List<AssetEntity>.unmodifiable(currentAssets);
    final files = List<Future<File?>>.unmodifiable(
      assets.map((item) => item.file),
    );
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => _GalleryAssetViewer(
          assets: assets,
          files: files,
          initialIndex: index,
        ),
      ),
    );
  }
""",
    "open a swipeable preview across all gallery assets",
)

if "class _GalleryAssetViewer extends StatefulWidget" not in text:
    anchor = "class _AssetPreview extends StatefulWidget {"
    if text.count(anchor) != 1:
        raise SystemExit("Could not safely find the asset preview class insertion point")
    viewer = """class _GalleryAssetViewer extends StatefulWidget {
  const _GalleryAssetViewer({
    required this.assets,
    required this.files,
    required this.initialIndex,
  });

  final List<AssetEntity> assets;
  final List<Future<File?>> files;
  final int initialIndex;

  @override
  State<_GalleryAssetViewer> createState() => _GalleryAssetViewerState();
}

class MediaPreviewPager extends StatefulWidget {
  const MediaPreviewPager({
    required this.itemCount,
    required this.initialIndex,
    required this.itemBuilder,
  });

  final int itemCount;
  final int initialIndex;
  final IndexedWidgetBuilder itemBuilder;

  @override
  State<MediaPreviewPager> createState() => _MediaPreviewPagerState();
}

class _MediaPreviewPagerState extends State<MediaPreviewPager> {
  late final PageController _controller;

  @override
  void initState() {
    super.initState();
    _controller = PageController(initialPage: widget.initialIndex);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => PageView.builder(
    key: const ValueKey<String>('media-preview-pager'),
    controller: _controller,
    itemCount: widget.itemCount,
    itemBuilder: widget.itemBuilder,
  );
}

class _GalleryAssetViewerState extends State<_GalleryAssetViewer> {
  @override
  Widget build(BuildContext context) {
    return MediaPreviewPager(
      itemCount: widget.assets.length,
      initialIndex: widget.initialIndex,
      itemBuilder: (context, index) {
        final asset = widget.assets[index];
        return FutureBuilder<File?>(
          future: widget.files[index],
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Scaffold(
                backgroundColor: _black,
                body: Center(
                  child: CircularProgressIndicator(
                    color: _white,
                    strokeWidth: 2,
                  ),
                ),
              );
            }
            final file = snapshot.data;
            if (snapshot.hasError || file == null) {
              return const Scaffold(
                backgroundColor: _black,
                body: Center(
                  child: Text(
                    'Could not open this media.',
                    style: TextStyle(color: _muted),
                  ),
                ),
              );
            }
            return KeyedSubtree(
              key: ValueKey<String>(asset.id),
              child: _AssetPreview(asset: asset, file: file),
            );
          },
        );
      },
    );
  }
}

"""
    text = text.replace(anchor, viewer + anchor, 1)
    print("fixed: added native PageView media preview for left/right swipes")
else:
    print("already fixed: swipeable gallery media preview exists")

# The earlier CI patch wraps the home screen in PopScope so the system back
# gesture returns from the Gallery tab to Camera rather than closing the app.
if "canPop: _selectedTab == 0" not in text or "onPopInvokedWithResult:" not in text:
    raise SystemExit("Gallery-to-camera system back handling is missing; refusing to build")
print("verified: system back from Gallery returns to Camera")

if "relativePath: 'Movies/Camera'" in text or "relativePath: 'Movies/Camera/'" in text:
    raise SystemExit("Unexpected Movies/Camera fallback remains in the final save methods")
if "relativePath: 'DCIM/Camera/'" not in text or "class _GalleryAssetViewer extends StatefulWidget" not in text:
    raise SystemExit("Final save destination or swipe viewer verification failed")
source.write_text(text, encoding="utf-8")
# Regression-test the exact pager widget used inside each opened photo/video.
test_marker = "swiping inside the opened media viewer changes the displayed item"
test_path = Path("test/widget_test.dart")
test_text = test_path.read_text(encoding="utf-8")
if test_marker not in test_text:
    case = """  testWidgets('swiping inside the opened media viewer changes the displayed item', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MediaPreviewPager(
            itemCount: 3,
            initialIndex: 1,
            itemBuilder: (context, index) => Center(child: Text('media-$index')),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('media-1'), findsOneWidget);

    final pager = find.byKey(const ValueKey<String>('media-preview-pager'));
    await tester.drag(pager, const Offset(-500, 0));
    await tester.pumpAndSettle();
    expect(find.text('media-2'), findsOneWidget);

    await tester.drag(pager, const Offset(500, 0));
    await tester.pumpAndSettle();
    expect(find.text('media-1'), findsOneWidget);
  });
"""
    insert_at = test_text.rfind("\n}")
    if insert_at < 0:
        raise SystemExit("Could not find main() closing brace in generated widget test.")
    test_text = test_text[:insert_at] + "\n\n" + case + test_text[insert_at:]
    test_path.write_text(test_text, encoding="utf-8")
    print("added: in-viewer left/right swipe regression test")
else:
    print("already present: in-viewer swipe regression test")

print("final gallery and media-save patch complete")

#!/usr/bin/env python3
# Final camera-app fixes applied after the generated gallery/navigation patches.
from pathlib import Path
import re

main_path = Path("lib/main.dart")
text = main_path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count == 1:
        text = text.replace(old, new, 1)
        print(f"applied: {label}")
    elif count == 0 and new in text:
        print(f"already applied: {label}")
    else:
        raise SystemExit(f"Cannot safely apply {label}: found {count} original matches.")


# MethodChannel is used only for the Android MediaStore writer.
if "import 'package:flutter/services.dart';" not in text:
    replace_once(
        "import 'package:flutter/material.dart';\n",
        "import 'package:flutter/material.dart';\nimport 'package:flutter/services.dart';\n",
        "Flutter services import",
    )
if "const MethodChannel _cameraMediaStore" not in text:
    replace_once(
        "const Color _muted = Color(0xFF8C8C8C);",
        "const Color _muted = Color(0xFF8C8C8C);\n\n"
        "const MethodChannel _cameraMediaStore =\n"
        "    MethodChannel('black_camera/media_store');",
        "native media-store channel",
    )

# Silent saves: photos keep their existing PhotoManager path; Android videos
# are inserted into DCIM/Camera through MediaStore and never fall back to Movies.
photo_start = text.find("  Future<void> _savePhoto(XFile image) async {")
message_start = text.find("  void _message(String value) {", photo_start)
if photo_start < 0 or message_start < 0:
    raise SystemExit("Cannot locate capture save methods in lib/main.dart.")
save_methods = """  Future<void> _savePhoto(XFile image) async {
    try {
      if (!await _requestMediaPermission()) return;
      await PhotoManager.editor.saveImageWithPath(
        image.path,
        title: _mediaTitle('.jpg'),
      );
      widget.onMediaSaved();
    } catch (_) {
      // Capture remains silent; no save-status popup.
    }
  }

  Future<void> _saveVideo(XFile video) async {
    try {
      if (!await _requestMediaPermission()) return;
      final source = File(video.path);
      if (!await source.exists() || await source.length() == 0) return;
      final title = _mediaTitle('.mp4');
      if (Platform.isAndroid) {
        final saved = await _cameraMediaStore.invokeMethod<String>(
          'saveVideoToDcimCamera',
          <String, Object>{'sourcePath': source.path, 'displayName': title},
        );
        if (saved == null || saved.isEmpty) return;
      } else {
        final saved = await PhotoManager.editor.saveVideo(
          source,
          title: title,
        );
        if (saved == null) return;
      }
      widget.onMediaSaved();
    } catch (_) {
      // Capture remains silent; no save-status popup.
    }
  }

"""
text = text[:photo_start] + save_methods + text[message_start:]
print("applied: silent photo/video saving; Android videos use DCIM/Camera only")

# System Back / Android edge-back: Gallery returns to Camera instead of exiting.
if "home: PopScope<Object?>(" not in text:
    home_start = text.find("      home: Scaffold(")
    if home_start < 0:
        raise SystemExit("Could not find the app home Scaffold for PopScope.")
    text = text[:home_start] + text[home_start:].replace(
        "      home: Scaffold(",
        "      home: PopScope<Object?>(\n"
        "        canPop: _selectedTab == 0,\n"
        "        onPopInvokedWithResult: (didPop, result) {\n"
        "          if (!didPop && _selectedTab != 0) _openCamera();\n"
        "        },\n"
        "        child: Scaffold(",
        1,
    )
    material_end = text.find("\n    );\n  }\n}", home_start)
    scaffold_close = text.rfind("\n      ),", home_start, material_end)
    if material_end < 0 or scaffold_close < 0:
        raise SystemExit("Could not safely close the new PopScope wrapper.")
    close_end = scaffold_close + len("\n      ),")
    text = text[:close_end] + "\n      )," + text[close_end:]
    print("applied: system Back from Gallery returns to Camera")
else:
    if "_selectedTab != 0) _openCamera();" not in text:
        raise SystemExit("PopScope exists but does not route Back to Camera.")
    print("already applied: system Back navigation")

# The gallery header should not have a top-right Camera or Refresh icon.
gallery_start = text.find("class _GalleryTabState extends State<GalleryTab>")
if gallery_start < 0:
    raise SystemExit("Generated GalleryTab state was not found.")
page_method = text.find("  Widget _buildGalleryPage(", gallery_start)
if page_method < 0:
    raise SystemExit("Generated gallery page builder was not found.")
gallery_segment = text[gallery_start:page_method]
icon_patterns = [
    re.compile(
        r"IconButton\(\s*onPressed:\s*widget\.onOpenCamera,\s*"
        r"tooltip:\s*'Camera',\s*icon:\s*const Icon\("
        r"Icons\.camera_alt_outlined,\s*color:\s*_white\),\s*\),"
    ),
    re.compile(
        r"IconButton\(\s*onPressed:\s*_loadAssets,\s*"
        r"tooltip:\s*'Refresh gallery',\s*icon:\s*const Icon\("
        r"Icons\.refresh,\s*color:\s*_white\),\s*\),"
    ),
]
removed = 0
for pattern in icon_patterns:
    gallery_segment, count = pattern.subn("", gallery_segment, count=1)
    removed += count
if removed:
    text = text[:gallery_start] + gallery_segment + text[page_method:]
    print("applied: removed top-right gallery icon")
else:
    print("already applied: no top-right Camera/Refresh icon")

# Use one explicit full-gallery horizontal gesture handler. Disable the
# PageView's competing recognizer while retaining animated page changes.
gallery_start = text.find("class _GalleryTabState extends State<GalleryTab>")
page_method = text.find("  Widget _buildGalleryPage(", gallery_start)
build_start = text.find("  Widget build(BuildContext context) {", gallery_start)
if min(gallery_start, page_method, build_start) < 0 or page_method < build_start:
    raise SystemExit("Could not locate GalleryTab build/page methods.")
gallery_build = text[build_start:page_method]

if "_manualSwipeDistance" not in text:
    replace_once(
        "final PageController _galleryPageController = PageController();",
        "final PageController _galleryPageController = PageController();\n"
        "  double _manualSwipeDistance = 0;",
        "gallery swipe state",
    )
    # Refresh the offsets after the insertion.
    gallery_start = text.find("class _GalleryTabState extends State<GalleryTab>")
    page_method = text.find("  Widget _buildGalleryPage(", gallery_start)
    build_start = text.find("  Widget build(BuildContext context) {", gallery_start)
    gallery_build = text[build_start:page_method]

if "onHorizontalDragEnd:" not in gallery_build:
    old_open = "    return SafeArea(\n      child: Column("
    if gallery_build.count(old_open) != 1:
        raise SystemExit("Could not safely add the gallery-wide swipe handler.")
    new_open = """    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onHorizontalDragStart: (_) => _manualSwipeDistance = 0,
      onHorizontalDragUpdate: (details) =>
          _manualSwipeDistance += details.delta.dx,
      onHorizontalDragEnd: (_) {
        final distance = _manualSwipeDistance;
        _manualSwipeDistance = 0;
        if (distance.abs() < 50 || !_galleryPageController.hasClients) return;
        final target = distance < 0 ? 1 : 0;
        if (target == _selectedGalleryPage) return;
        unawaited(
          _galleryPageController.animateToPage(
            target,
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeOutCubic,
          ),
        );
      },
      child: SafeArea(
        child: Column("""
    gallery_build = gallery_build.replace(old_open, new_open, 1)
    old_end = "\n    );\n  }\n\n"
    if not gallery_build.endswith(old_end):
        raise SystemExit("Could not safely close the gallery-wide swipe handler.")
    gallery_build = gallery_build[:-len(old_end)] + "\n    ),\n    );\n  }\n\n"
    text = text[:build_start] + gallery_build + text[page_method:]
    print("applied: horizontal swipe works across the entire Gallery screen")
else:
    print("already applied: gallery-wide horizontal swipe handler")

gallery_start = text.find("class _GalleryTabState extends State<GalleryTab>")
page_method = text.find("  Widget _buildGalleryPage(", gallery_start)
gallery_segment = text[gallery_start:page_method]
pageview_old = "            child: PageView(\n              controller: _galleryPageController,"
pageview_new = (
    "            child: PageView(\n"
    "              physics: const NeverScrollableScrollPhysics(),\n"
    "              controller: _galleryPageController,"
)
if pageview_old in gallery_segment:
    gallery_segment = gallery_segment.replace(pageview_old, pageview_new, 1)
    text = text[:gallery_start] + gallery_segment + text[page_method:]
    print("applied: PageView uses controller-driven swipe animation")
elif "physics: const NeverScrollableScrollPhysics()," in gallery_segment:
    print("already applied: PageView gesture arbitration")
else:
    raise SystemExit("Could not locate the gallery PageView controller.")

# Dispose PageController to avoid leaking its animation resources.
gallery_start = text.find("class _GalleryTabState extends State<GalleryTab>")
page_method = text.find("  Widget _buildGalleryPage(", gallery_start)
gallery_segment = text[gallery_start:page_method]
if "_galleryPageController.dispose()" not in gallery_segment:
    init_anchor = """  @override
  void initState() {
    super.initState();
    _loadAssets();
  }
"""
    if gallery_segment.count(init_anchor) != 1:
        raise SystemExit("Could not insert GalleryTab controller disposal.")
    dispose_block = init_anchor + """
  @override
  void dispose() {
    _galleryPageController.dispose();
    super.dispose();
  }
"""
    gallery_segment = gallery_segment.replace(init_anchor, dispose_block, 1)
    text = text[:gallery_start] + gallery_segment + text[page_method:]
    print("applied: dispose gallery PageController")

main_path.write_text(text, encoding="utf-8")

# Make the regression test swipe on the header, which proves the gesture works
# across the whole gallery, not only when a drag starts inside PageView.
test_path = Path("test/widget_test.dart")
if test_path.exists():
    test_text = test_path.read_text(encoding="utf-8")

    def replace_page_drag(match: re.Match) -> str:
        dx = int(match.group(1))
        if dx < 0:
            return (
                "await tester.drag(find.textContaining('swipe left for videos'), "
                "const Offset(-350, 0));"
            )
        return (
            "await tester.drag(find.textContaining('swipe right for photos'), "
            "const Offset(350, 0));"
        )

    test_text, changed = re.subn(
        r"await tester\.drag\(find\.byType\(PageView\), const Offset\((-?\d+), 0\)\);",
        replace_page_drag,
        test_text,
    )
    # Handle the old multi-line reverse-swipe test if a prior script left it.
    old_reverse = """await tester.drag(
      find.textContaining('swipe right for photos'),
      const Offset(700, 0),
    );"""
    if old_reverse in test_text:
        test_text = test_text.replace(
            old_reverse,
            "await tester.drag(find.textContaining('swipe right for photos'), "
            "const Offset(350, 0));",
            1,
        )
        changed += 1
    if changed:
        test_path.write_text(test_text, encoding="utf-8")
        print("applied: swipe regression test targets both visible gallery labels")
    elif (
        "find.textContaining('swipe left for videos')" not in test_text
        or "find.textContaining('swipe right for photos')" not in test_text
    ):
        raise SystemExit("Gallery swipe regression test could not be updated.")
    else:
        print("already applied: swipe regression test")
else:
    raise SystemExit("test/widget_test.dart not found.")

# Patch generated Android MainActivity with a scoped-storage-safe MediaStore
# writer. This is the authoritative save path for Android 10+.
kotlin_root = Path("android/app/src/main/kotlin")
activities = list(kotlin_root.rglob("MainActivity.kt")) if kotlin_root.exists() else []
if len(activities) != 1:
    raise SystemExit(f"Expected one generated MainActivity.kt, found {len(activities)}.")
activity_path = activities[0]
activity_text = activity_path.read_text(encoding="utf-8")
package_match = re.search(r"^package\s+([\w.]+)\s*$", activity_text, re.MULTILINE)
if not package_match:
    raise SystemExit("Could not determine the package name from MainActivity.kt.")
package_name = package_match.group(1)

kotlin_source = f"""package {package_name}

import android.content.ContentValues
import android.media.MediaScannerConnection
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileInputStream
import java.io.IOException

class MainActivity : FlutterActivity() {{
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {{
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "black_camera/media_store"
        ).setMethodCallHandler {{ call, result ->
            if (call.method != "saveVideoToDcimCamera") {{
                result.notImplemented()
                return@setMethodCallHandler
            }}
            val sourcePath = call.argument<String>("sourcePath")
            val displayName = call.argument<String>("displayName")
            if (sourcePath.isNullOrBlank() || displayName.isNullOrBlank()) {{
                result.error("invalid_arguments", "Missing video path or name.", null)
                return@setMethodCallHandler
            }}
            val source = File(sourcePath)
            if (!source.isFile || source.length() <= 0L) {{
                result.error("invalid_video", "The recorded video file is empty.", null)
                return@setMethodCallHandler
            }}
            try {{
                val uri = saveVideoToDcimCamera(source, displayName)
                result.success(uri.toString())
            }} catch (error: Exception) {{
                result.error(
                    "video_save_failed",
                    error.message ?: "Could not save the video to DCIM/Camera.",
                    null
                )
            }}
        }}
    }}

    @Suppress("DEPRECATION")
    private fun saveVideoToDcimCamera(source: File, displayName: String): Uri {{
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {{
            val values = ContentValues().apply {{
                put(MediaStore.MediaColumns.DISPLAY_NAME, displayName)
                put(MediaStore.MediaColumns.MIME_TYPE, "video/mp4")
                put(MediaStore.MediaColumns.RELATIVE_PATH, "DCIM/Camera")
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            }}
            val uri = contentResolver.insert(
                MediaStore.Video.Media.EXTERNAL_CONTENT_URI,
                values
            ) ?: throw IOException("Could not create a DCIM/Camera media entry.")
            try {{
                val output = contentResolver.openOutputStream(uri, "w")
                    ?: throw IOException("Could not open the DCIM/Camera media entry.")
                output.use {{ outputStream ->
                    FileInputStream(source).use {{ inputStream ->
                        inputStream.copyTo(outputStream)
                    }}
                }}
                val published = ContentValues().apply {{
                    put(MediaStore.MediaColumns.IS_PENDING, 0)
                }}
                if (contentResolver.update(uri, published, null, null) <= 0) {{
                    throw IOException("Could not publish the saved camera video.")
                }}
                return uri
            }} catch (error: Exception) {{
                contentResolver.delete(uri, null, null)
                throw error
            }}
        }}

        val cameraDirectory = File(
            Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DCIM),
            "Camera"
        )
        if (!cameraDirectory.exists() && !cameraDirectory.mkdirs()) {{
            throw IOException("Could not create DCIM/Camera.")
        }}
        val destination = File(cameraDirectory, displayName)
        source.copyTo(destination, overwrite = false)
        MediaScannerConnection.scanFile(
            this,
            arrayOf(destination.absolutePath),
            arrayOf("video/mp4"),
            null
        )
        return Uri.fromFile(destination)
    }}
}}
"""
if activity_text != kotlin_source:
    activity_path.write_text(kotlin_source, encoding="utf-8")
    print("applied: Android MediaStore saves recorded videos to DCIM/Camera")
else:
    print("already applied: Android MediaStore writer")

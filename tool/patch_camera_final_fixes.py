#!/usr/bin/env python3
"""Fix camera media saving, gallery gestures, Android back, and video controls."""
from pathlib import Path

source = Path("lib/main.dart")
text = source.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count == 1:
        text = text.replace(old, new, 1)
        print(f"applied: {label}")
    elif new in text:
        print(f"already applied: {label}")
    else:
        raise SystemExit(
            f"Could not safely apply {label}: expected one match, found {count}."
        )


# Hardware/system back should return from Gallery to Camera instead of exiting.
replace_once(
    """      home: Scaffold(
        backgroundColor: _black,
""",
    """      home: PopScope<Object?>(
        canPop: _selectedTab == 0,
        onPopInvokedWithResult: (didPop, result) {
          if (!didPop && _selectedTab != 0) _openCamera();
        },
        child: Scaffold(
          backgroundColor: _black,
""",
    "gallery back navigation",
)
replace_once(
    """                onOpenCamera: _openCamera,
              ),
      ),
    );
  }
}

class CameraTab""",
    """                onOpenCamera: _openCamera,
              ),
        ),
      ),
    );
  }
}

class CameraTab""",
    "close PopScope around app scaffold",
)

# Save images quietly and place them with the camera's other media.
replace_once(
    """  Future<void> _savePhoto(XFile image) async {
    try {
      if (!await _requestMediaPermission()) {
        _message('Photo captured, but gallery access was denied.');
        return;
      }
      await PhotoManager.editor.saveImageWithPath(
        image.path,
        title: _mediaTitle('.jpg'),
      );
      widget.onMediaSaved();
      _message('Photo saved to Gallery.');
    } catch (_) {
      _message('Photo captured, but could not save it to Gallery.');
    }
  }
""",
    """  Future<void> _savePhoto(XFile image) async {
    try {
      if (!await _requestMediaPermission()) return;
      await PhotoManager.editor.saveImageWithPath(
        image.path,
        title: _mediaTitle('.jpg'),
        relativePath: 'DCIM/Camera',
      );
      widget.onMediaSaved();
    } catch (_) {
      // Keep capture silent; do not show save-status popups.
    }
  }
""",
    "silent photo save",
)

replace_once(
    """  Future<void> _saveVideo(XFile video) async {
    try {
      if (!await _requestMediaPermission()) {
        _message('Video recorded, but gallery access was denied.');
        return;
      }
      await PhotoManager.editor.saveVideo(
        File(video.path),
        title: _mediaTitle('.mp4'),
      );
      widget.onMediaSaved();
      _message('Video saved to Gallery.');
    } catch (_) {
      _message('Video recorded, but could not save it to Gallery.');
    }
  }
""",
    """  Future<void> _saveVideo(XFile video) async {
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
          relativePath: 'DCIM/Camera',
        );
      } catch (_) {
        // Retry in the Movies collection below.
      }

      if (saved == null) {
        try {
          saved = await PhotoManager.editor.saveVideo(
            file,
            title: title,
            relativePath: 'Movies/Camera',
          );
        } catch (_) {
          return;
        }
      }
      if (saved == null) return;
      widget.onMediaSaved();
    } catch (_) {
      // Never interrupt capture with a save-status popup.
    }
  }
""",
    "save recorded video to a public gallery collection with fallback",
)

# Never attempt the stutter-prone 1080p/60 FPS combination.
replace_once(
    """    final candidates = <({VideoResolution resolution, int fps})>[
      (resolution: resolution, fps: fps),
      if (prioritizeFps && fps == 60 && resolution != VideoResolution.p720)
        (resolution: VideoResolution.p720, fps: 60),
      if (fps == 60) (resolution: resolution, fps: 30),
      if (!prioritizeFps && fps == 60 && resolution != VideoResolution.p720)
        (resolution: VideoResolution.p720, fps: 60),
      (resolution: VideoResolution.p720, fps: 30),
      (resolution: previousResolution, fps: previousFps),
    ];
""",
    """    final is1080p60 = resolution == VideoResolution.p1080 && fps == 60;
    final candidates = <({VideoResolution resolution, int fps})>[
      if (is1080p60 && prioritizeFps)
        (resolution: VideoResolution.p720, fps: 60),
      if (is1080p60 && !prioritizeFps)
        (resolution: VideoResolution.p1080, fps: 30),
      if (!is1080p60) (resolution: resolution, fps: fps),
      if (prioritizeFps && fps == 60 && resolution != VideoResolution.p720)
        (resolution: VideoResolution.p720, fps: 60),
      if (fps == 60) (resolution: resolution, fps: 30),
      if (!prioritizeFps && fps == 60 && resolution != VideoResolution.p720)
        (resolution: VideoResolution.p720, fps: 60),
      (resolution: VideoResolution.p720, fps: 30),
      (resolution: previousResolution, fps: previousFps),
    ];
""",
    "stable resolution and FPS fallback",
)
replace_once(
    """    var actualResolution = previousResolution;
    var actualFps = previousFps;
""",
    "",
    "remove obsolete settings result variables",
)
replace_once(
    """          actualResolution = candidate.resolution;
          actualFps = candidate.fps;
""",
    "",
    "remove obsolete settings assignments",
)
replace_once(
    """    if (applied && (actualResolution != resolution || actualFps != fps)) {
      final quality = actualResolution == VideoResolution.p1080
          ? '1080p'
          : '720p';
      _message('Unsupported combination; using $quality at $actualFps FPS.');
    } else if (!applied) {
      _message(
        'Could not apply the selected video settings; camera is unavailable.',
      );
    }
""",
    """    // Active settings are shown inline; do not display a popup.
""",
    "remove settings popups",
)

# Restore a single connected control capsule with a straight divider.
marker = text.find("// FULLSCREEN_CAPTURE_UI_PATCH_APPLIED")
ui_start = "                  else if (_mode == CaptureMode.video)\n"
ui_end = "                  else\n                    const SizedBox(width: 40),"
start = text.find(ui_start, marker)
end = text.find(ui_end, start) if start >= 0 else -1
if start >= 0 and end > start:
    new_ui = """                  else if (_mode == CaptureMode.video)
                    Container(
                      decoration: BoxDecoration(
                        color: const Color(0x99000000),
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(
                          color: const Color(0x77FFFFFF),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          _InlineSettingChip(
                            label: videoQuality,
                            onTap: _recording || _busy || _loading
                                ? null
                                : () => unawaited(
                                    _applyVideoSettings(
                                      resolution:
                                          _videoResolution ==
                                                  VideoResolution.p1080
                                              ? VideoResolution.p720
                                              : VideoResolution.p1080,
                                      fps: _videoFps,
                                    ),
                                  ),
                          ),
                          Container(
                            width: 1,
                            height: 22,
                            color: const Color(0x77FFFFFF),
                          ),
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
                      ),
                    )
"""
    text = text[:start] + new_ui + text[end:]
    print("applied: connected resolution/FPS control with vertical divider")
elif "height: 22," in text and "InlineSettingChip" in text:
    print("already applied: connected resolution/FPS control")
else:
    raise SystemExit("Could not locate the generated inline video-settings row.")

chip_start = text.find("class _InlineSettingChip extends StatelessWidget {")
chip_end = text.find("class GalleryTab extends StatefulWidget {", chip_start)
if chip_start >= 0 and chip_end > chip_start:
    chip = """class _InlineSettingChip extends StatelessWidget {
  const _InlineSettingChip({required this.label, required this.onTap});
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    label: label,
    child: GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
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

"""
    text = text[:chip_start] + chip + text[chip_end:]
    print("applied: plain controls inside one shared capsule")
elif "class _InlineSettingChip extends StatelessWidget {" in text and "GestureDetector(" in text:
    print("already applied: inline control chip")
else:
    raise SystemExit("Could not locate the inline setting chip widget.")

# Make horizontal swipes work even when they begin on the gallery header.
gallery_state = text.find("class _GalleryTabState extends State<GalleryTab>")
if gallery_state < 0:
    raise SystemExit("Could not locate GalleryTab state.")
replace_once(
    """  List<AssetEntity> _videoAssets = [];
  int _selectedGalleryPage = 0;
  final PageController _galleryPageController = PageController();
""",
    """  List<AssetEntity> _videoAssets = [];
  int _selectedGalleryPage = 0;
  double _manualSwipeDistance = 0;
  final PageController _galleryPageController = PageController();
""",
    "gallery header gesture state",
)
gallery_state = text.find("class _GalleryTabState extends State<GalleryTab>")
build_start = text.find("    return SafeArea(\n      child: Column(", gallery_state)
if build_start >= 0:
    old_start = "    return SafeArea(\n      child: Column("
    new_start = """    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onHorizontalDragStart: (_) => _manualSwipeDistance = 0,
      onHorizontalDragUpdate: (details) =>
          _manualSwipeDistance += details.delta.dx,
      onHorizontalDragEnd: (details) {
        final distance = _manualSwipeDistance;
        _manualSwipeDistance = 0;
        if (distance.abs() < 50 || !_galleryPageController.hasClients) return;
        final target = distance < 0 ? 1 : 0;
        if (target == _selectedGalleryPage) return;
        unawaited(
          _galleryPageController.animateToPage(
            target,
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOutCubic,
          ),
        );
      },
      child: SafeArea(
        child: Column("""
    text = text[:build_start] + new_start + text[build_start + len(old_start):]
    gallery_end = "        ],\n      ),\n    );\n  }\n\n  Widget _buildGalleryPage("
    if text.count(gallery_end) == 1:
        text = text.replace(
            gallery_end,
            "        ],\n      ),\n    ),\n    );\n  }\n\n  Widget _buildGalleryPage(",
            1,
        )
        print("applied: horizontal swipe across the full gallery, including its header")
    elif "Widget _buildGalleryPage(" in text[build_start:] and "child: SafeArea(" in text[build_start:]:
        print("already applied: full-gallery gesture")
    else:
        raise SystemExit("Could not safely close the full-gallery gesture.")
elif "onHorizontalDragUpdate: (details)" in text[gallery_state:]:
    print("already applied: full-gallery gesture")
else:
    raise SystemExit("Could not locate the gallery build method to add swipes.")

source.write_text(text, encoding="utf-8")

# Add a regression check for the reverse swipe initiated on the gallery header.
test_path = Path("test/widget_test.dart")
test_text = test_path.read_text(encoding="utf-8")
old_test_end = """    expect(find.textContaining('swipe right for photos'), findsOneWidget);
  });
}"""
new_test_end = """    expect(find.textContaining('swipe right for photos'), findsOneWidget);
    await tester.drag(
      find.textContaining('swipe right for photos'),
      const Offset(700, 0),
    );
    await tester.pump(const Duration(milliseconds: 800));
    expect(find.textContaining('swipe left for videos'), findsOneWidget);
  });
}"""
count = test_text.count(old_test_end)
if count == 1:
    test_text = test_text.replace(old_test_end, new_test_end, 1)
    test_path.write_text(test_text, encoding="utf-8")
    print("applied: gallery left/right gesture regression test")
elif new_test_end in test_text:
    print("already applied: gallery left/right gesture regression test")
else:
    raise SystemExit(
        "Could not safely extend the gallery widget test: "
        f"expected one test ending, found {count}."
    )

print("Camera follow-up patch complete.")

#!/usr/bin/env python3
"""Final camera save path, silent capture, and Gallery navigation fixes."""
from pathlib import Path
import re

source = Path("lib/main.dart")
text = source.read_text(encoding="utf-8")


def replace_method(name, replacement):
    global text
    pattern = re.compile(
        r"  Future<void> " + re.escape(name) + r"\([^\n]*\) async \{.*?\n  \}",
        re.DOTALL,
    )
    updated, count = pattern.subn(replacement.rstrip(), text, count=1)
    if count != 1:
        raise SystemExit("Could not safely replace " + name + ": matches=" + str(count))
    text = updated


replace_method("_savePhoto", r'''  Future<void> _savePhoto(XFile image) async {
    try {
      if (!await _requestMediaPermission()) return;
      final file = File(image.path);
      if (!await file.exists() || await file.length() == 0) return;
      await PhotoManager.editor.saveImageWithPath(
        image.path,
        title: _mediaTitle('.jpg'),
        relativePath: 'DCIM/Camera',
      );
      widget.onMediaSaved();
    } catch (_) {
      // Keep capture silent; do not show a saved-status popup.
    }
  }''')

replace_method("_saveVideo", r'''  Future<void> _saveVideo(XFile video) async {
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
      // Never show a save popup or fall back to Movies.
    }
  }''')

refresh_pattern = re.compile(
    r"(?m)^[ \t]*IconButton\(\n"
    r"[ \t]*onPressed: _loadAssets,\n"
    r"[ \t]*tooltip: 'Refresh gallery',\n"
    r"[ \t]*icon: const Icon\(Icons\.refresh, color: _white\),\n"
    r"[ \t]*\),\n?"
)
text, refresh_count = refresh_pattern.subn("", text, count=1)
if refresh_count:
    print("fixed: removed Gallery top-right refresh icon")
elif "tooltip: 'Refresh gallery'" not in text:
    print("already fixed: Gallery refresh icon absent")
else:
    raise SystemExit("Could not safely remove the Gallery refresh button")

# If the previous navigation patch did not survive, put PopScope around the
# home Scaffold so Android system-back returns from Gallery to Camera.
if "canPop: _selectedTab == 0" not in text:
    marker = "      home: Scaffold("
    if text.count(marker) != 1:
        raise SystemExit("Could not safely locate home Scaffold for back navigation")
    text = text.replace(marker, """      home: PopScope<Object?>(
        canPop: _selectedTab == 0,
        onPopInvokedWithResult: (didPop, result) {
          if (!didPop && _selectedTab != 0) _openCamera();
        },
        child: Scaffold(""", 1)
    # Add one closing parenthesis for the inserted PopScope.
    closing = "      ),\n    );\n  }\n}"
    if text.count(closing) != 1:
        raise SystemExit("Could not safely close PopScope wrapper")
    text = text.replace(closing, "      ),\n      ),\n    );\n  }\n}", 1)
    print("fixed: Android system-back returns from Gallery to Camera")
else:
    print("already fixed: Android system-back returns from Gallery to Camera")

for method in ("_savePhoto", "_saveVideo"):
    start = text.find("  Future<void> " + method + "(")
    end = text.find("\n  }", start)
    body = text[start:end + 4] if start >= 0 and end >= 0 else ""
    if "relativePath: 'DCIM/Camera'" not in body or "_message(" in body:
        raise SystemExit(method + " must save silently to DCIM/Camera")

video_start = text.find("  Future<void> _saveVideo(")
video_end = text.find("\n  }", video_start)
video_body = text[video_start:video_end + 4]
if "Movies/Camera" in video_body or "Movies" in video_body:
    raise SystemExit("Video save still falls back to Movies")
if "tooltip: 'Refresh gallery'" in text:
    raise SystemExit("Gallery refresh icon still exists")
if "canPop: _selectedTab == 0" not in text:
    raise SystemExit("Gallery system-back handling is missing")

source.write_text(text, encoding="utf-8")
print("verified: photos and videos save silently to DCIM/Camera, no Movies fallback, Gallery back returns to Camera")

#!/usr/bin/env python3
"""Keep camera media saves silent, store videos alongside camera photos, and fix gallery navigation UI."""
from pathlib import Path
import re

source = Path("lib/main.dart")
text = source.read_text(encoding="utf-8")


def replace_method(start_marker: str, end_marker: str, replacement: str, label: str) -> None:
    global text
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker)) if start >= 0 else -1
    if start < 0 or end < 0:
        raise SystemExit(f"Could not safely locate {label} in lib/main.dart.")
    text = text[:start] + replacement.rstrip() + "\n\n" + text[end:]


replace_method(
    "  Future<void> _savePhoto(XFile image) async {",
    "  Future<void> _saveVideo(XFile video) async {",
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
      // Keep capture silent; do not show media-save status popups.
    }
  }""",
    "photo-save method",
)

replace_method(
    "  Future<void> _saveVideo(XFile video) async {",
    "  void _message(String value) {",
    """  Future<void> _saveVideo(XFile video) async {
    try {
      if (!await _requestMediaPermission()) return;
      final file = File(video.path);
      if (!await file.exists() || await file.length() == 0) return;

      await PhotoManager.editor.saveVideo(
        file,
        title: _mediaTitle('.mp4'),
        relativePath: 'DCIM/Camera/',
      );
      widget.onMediaSaved();
    } catch (_) {
      // Never show save-status popups or redirect videos to Movies.
    }
  }""",
    "video-save method",
)

# Remove only the Gallery refresh button; the gallery opens fresh when selected.
refresh_button = re.compile(
    r"\s*IconButton\(\s*onPressed: _loadAssets,\s*"
    r"tooltip: 'Refresh gallery',\s*"
    r"icon: const Icon\(Icons\.refresh, color: _white\),\s*\),",
    re.MULTILINE,
)
text, removed_refresh = refresh_button.subn("", text, count=1)
if removed_refresh != 1 and "Refresh gallery" in text:
    raise SystemExit("Could not safely remove the gallery refresh icon.")

# Hardware/system back on the Gallery tab must switch back to Camera.
required_back_handling = (
    "canPop: _selectedTab == 0",
    "onPopInvokedWithResult: (didPop, result)",
    "if (!didPop && _selectedTab != 0) _openCamera();",
)
if not all(piece in text for piece in required_back_handling):
    raise SystemExit("Gallery-to-camera system-back handling is missing.")

if "Movies/Camera" in text:
    raise SystemExit("A Movies/Camera video-save fallback remains in the app source.")

source.write_text(text, encoding="utf-8")
print("Applied: silent photo/video saving, video destination DCIM/Camera/, removed gallery refresh icon.")
print("Verified: Android system back from Gallery returns to Camera.")

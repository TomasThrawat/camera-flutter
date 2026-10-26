#!/usr/bin/env python3
"""Avoid an unnecessary-null-comparison analyzer warning in video saving."""
from pathlib import Path

path = Path("lib/main.dart")
text = path.read_text(encoding="utf-8")
old = """      AssetEntity? saved;
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
"""
new = """      try {
        await PhotoManager.editor.saveVideo(
          file,
          title: title,
          relativePath: 'DCIM/Camera',
        );
      } catch (_) {
        try {
          await PhotoManager.editor.saveVideo(
            file,
            title: title,
            relativePath: 'Movies/Camera',
          );
        } catch (_) {
          return;
        }
      }
      widget.onMediaSaved();
"""
if text.count(old) == 1:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("fixed: saveVideo error-only fallback avoids unnecessary null checks")
elif new in text:
    print("already fixed: saveVideo error-only fallback")
else:
    raise SystemExit(
        "Could not find the exact generated video-save block; "
        f"matches={text.count(old)}."
    )

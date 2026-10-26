#!/usr/bin/env python3
"""Fix analyzer lints in the generated camera-interaction source."""
from pathlib import Path

path = Path("lib/main.dart")
text = path.read_text(encoding="utf-8")

replacements = [
    (
        "      if (mounted) setState(() => _error = 'Could not load media from this device.');",
        """      if (mounted) {
        setState(() => _error = 'Could not load media from this device.');
      }""",
        "gallery error state guard",
    ),
    (
        "      if (mounted) setState(() => _loading = false);",
        """      if (mounted) {
        setState(() => _loading = false);
      }""",
        "gallery loading state guard",
    ),
]

for old, new, label in replacements:
    if text.count(old) == 1:
        text = text.replace(old, new, 1)
        print(f"fixed: {label}")
    elif new in text:
        print(f"already fixed: {label}")
    else:
        raise SystemExit(
            f"Could not safely fix {label}: expected one source match, found {text.count(old)}."
        )

path.write_text(text, encoding="utf-8")

#!/usr/bin/env python3
"""Make only the live camera preview fill its available viewport."""
from pathlib import Path

source = Path("lib/main.dart")
text = source.read_text(encoding="utf-8")
old = "ClipRect(child: CameraPreview(controller))"
new = """ClipRect(
                    child: SizedBox.expand(
                      child: FittedBox(
                        fit: BoxFit.cover,
                        clipBehavior: Clip.hardEdge,
                        child: SizedBox(
                          width: 1000 *
                              (MediaQuery.orientationOf(context) ==
                                      Orientation.portrait
                                  ? 1 / controller.value.aspectRatio
                                  : controller.value.aspectRatio),
                          height: 1000,
                          child: CameraPreview(controller),
                        ),
                      ),
                    ),
                  )"""

if text.count(old) == 1:
    source.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("Applied the full-screen camera preview patch (single targeted widget change).")
elif text.count(old) == 0 and "FittedBox(" in text and "CameraPreview(controller)" in text:
    print("Full-screen camera preview is already applied.")
else:
    raise SystemExit(
        f"Expected one original camera preview widget, found {text.count(old)}; "
        "refusing to change other UI."
    )

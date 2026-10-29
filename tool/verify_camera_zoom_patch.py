#!/usr/bin/env python3
"""Guard against CI patchers regressing continuous pinch-to-zoom handling."""
from pathlib import Path
import sys

source = Path("lib/main.dart").read_text(encoding="utf-8")
errors = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

zoom_start = source.find("  void _onZoomStart(ScaleStartDetails details) {")
zoom_end = source.find("  Future<void> _applyVideoSettings(", zoom_start)
zoom_block = source[zoom_start:zoom_end] if zoom_start >= 0 and zoom_end > zoom_start else ""
require(bool(zoom_block), "pinch zoom handlers are missing")
require("_scheduleZoomUpdate();" in zoom_block, "pinch updates must be scheduled/coalesced")
require("Timer(const Duration(milliseconds: 16)" in zoom_block, "zoom updates must be paced at approximately one frame")
require("void _onZoomEnd(ScaleEndDetails details)" in zoom_block, "pinch end handler is missing")
require("_dispatchLatestZoom();" in zoom_block, "last requested zoom must be applied at gesture end")
require("unawaited(_applyZoomCommand(controller, target));" in zoom_block, "new zoom targets must not wait for prior platform calls")
require("Future<void> _applyZoomCommand(" in zoom_block, "direct zoom command handler is missing")
require("onScaleEnd: _onZoomEnd" in source, "ScaleEnd callback is not wired to the preview gesture")
require("_zoomUpdateInFlight" not in source, "serialized in-flight zoom lock regressed")
require("await Future<void>.delayed(const Duration(milliseconds: 16))" not in source, "step-by-step zoom interpolation regressed")
if errors:
    print("PINCH ZOOM REGRESSION CHECK FAILED:")
    for error in errors:
        print(" - " + error)
    sys.exit(1)
print("Pinch zoom regression check passed: frame-paced targets, non-serialized platform calls, end flush, and gesture wiring are present.")

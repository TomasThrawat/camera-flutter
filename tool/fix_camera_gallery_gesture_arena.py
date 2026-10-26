from pathlib import Path

p = Path("lib/main.dart")
s = p.read_text(encoding="utf-8")
old = """return Listener(
      behavior: HitTestBehavior.opaque,
      onPointerDown: (_) => _manualSwipeDistance = 0,
      onPointerMove: (event) => _manualSwipeDistance += event.delta.dx,
      onPointerCancel: (_) => _manualSwipeDistance = 0,
      onPointerUp: (_) {
        final distance = _manualSwipeDistance;
        _manualSwipeDistance = 0;
        if (distance.abs() < 50 || !_galleryPageController.hasClients) return;
        final target = distance < 0 ? 1 : 0;
        if (target == _selectedGalleryPage) return;
        unawaited(_galleryPageController.animateToPage(target,
          duration: const Duration(milliseconds: 200), curve: Curves.easeOutCubic));
      },
      child: SafeArea(
"""
new = """return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onHorizontalDragStart: (_) => _manualSwipeDistance = 0,
      onHorizontalDragUpdate: (details) =>
          _manualSwipeDistance += details.delta.dx,
      onHorizontalDragCancel: () => _manualSwipeDistance = 0,
      onHorizontalDragEnd: (_) {
        final distance = _manualSwipeDistance;
        _manualSwipeDistance = 0;
        if (distance.abs() < 50 || !_galleryPageController.hasClients) return;
        final target = distance < 0 ? 1 : 0;
        if (target == _selectedGalleryPage) return;
        unawaited(_galleryPageController.animateToPage(
          target,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOutCubic,
        ));
      },
      child: SafeArea(
"""
if s.count(old) != 1:
    raise SystemExit(f"wrapper match count: {s.count(old)}")
s = s.replace(old, new, 1)
old = """            child: PageView(
              controller: _galleryPageController,
"""
new = """            child: PageView(
              physics: const NeverScrollableScrollPhysics(),
              controller: _galleryPageController,
"""
if s.count(old) != 1:
    raise SystemExit(f"PageView match count: {s.count(old)}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("Gallery drag is handled by the parent; PageView no longer competes.")

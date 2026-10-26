from pathlib import Path
p=Path("lib/main.dart")
s=p.read_text()
old="""return GestureDetector(
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
"""
new="""return Listener(
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
if s.count(old)!=1: raise SystemExit(f"expected one gesture wrapper, got {s.count(old)}")
p.write_text(s.replace(old,new,1))
print("gallery swipe listener updated")

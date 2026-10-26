#!/usr/bin/env python3
"""Apply camera controls and gallery refresh to the checked-out Flutter source."""
from pathlib import Path

path = Path("lib/main.dart")
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if text.count(old) == 1:
        text = text.replace(old, new, 1)
        print(f"applied: {label}")
    elif new in text:
        print(f"already applied: {label}")
    else:
        raise SystemExit(
            f"Could not safely apply {label}: expected one source match, "
            f"found {text.count(old)}."
        )


replace_once(
    "enum CaptureMode { photo, video }\n",
    "enum CaptureMode { photo, video }\n\nenum VideoResolution { p720, p1080 }\n",
    "video resolution choices",
)

replace_once(
    """  bool _torchEnabled = false;
  String? _error;
  int _recordSeconds = 0;
  Timer? _recordTimer;
""",
    """  bool _torchEnabled = false;
  String? _error;
  int _recordSeconds = 0;
  Timer? _recordTimer;
  VideoResolution _videoResolution = VideoResolution.p1080;
  int _videoFps = 30;
  double _minZoom = 1;
  double _maxZoom = 1;
  double _zoomLevel = 1;
  double _zoomAtScaleStart = 1;
  double _requestedZoom = 1;
  bool _zoomUpdateInFlight = false;
""",
    "camera settings and zoom state",
)

replace_once(
    """    final controller = CameraController(
      _cameras[index],
      ResolutionPreset.high,
      enableAudio: true,
    );
    _controller = controller;
    await controller.initialize();
    if (!mounted) {
      await controller.dispose();
      return;
    }
    setState(() => _error = null);
""",
    """    final controller = CameraController(
      _cameras[index],
      _mode == CaptureMode.video
          ? (_videoResolution == VideoResolution.p1080
              ? ResolutionPreset.veryHigh
              : ResolutionPreset.high)
          : ResolutionPreset.high,
      enableAudio: true,
      fps: _mode == CaptureMode.video ? _videoFps : null,
    );
    _controller = controller;
    try {
      await controller.initialize();
    } catch (_) {
      if (identical(_controller, controller)) _controller = null;
      try {
        await controller.dispose();
      } catch (_) {}
      rethrow;
    }
    if (!mounted) {
      await controller.dispose();
      return;
    }
    try {
      _minZoom = await controller.getMinZoomLevel();
      _maxZoom = await controller.getMaxZoomLevel();
    } catch (_) {
      _minZoom = 1;
      _maxZoom = 1;
    }
    _zoomLevel = _zoomLevel.clamp(_minZoom, _maxZoom).toDouble();
    _requestedZoom = _zoomLevel;
    try {
      await controller.setZoomLevel(_zoomLevel);
    } catch (_) {}
    if (mounted) setState(() => _error = null);
""",
    "configurable camera initialization",
)

replace_once(
    """  void _changeMode(CaptureMode mode) {
    if (_recording || _busy) return;
    setState(() => _mode = mode);
  }
""",
    """  void _changeMode(CaptureMode mode) {
    if (_recording || _busy || _loading || mode == _mode) return;
    setState(() {
      _mode = mode;
      _loading = true;
      _error = null;
    });
    unawaited(_reconfigureForMode());
  }

  Future<void> _reconfigureForMode() async {
    try {
      await _configureCamera(_cameraIndex);
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not change camera mode.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }
""",
    "camera mode reconfiguration",
)

replace_once(
    "  Future<void> _switchCamera() async {\n",
    """  void _onZoomStart(ScaleStartDetails details) {
    _zoomAtScaleStart = _zoomLevel;
  }

  void _onZoomUpdate(ScaleUpdateDetails details) {
    final controller = _controller;
    if (details.pointerCount < 2 ||
        _maxZoom <= _minZoom ||
        controller == null ||
        !controller.value.isInitialized) {
      return;
    }
    _requestedZoom =
        (_zoomAtScaleStart * details.scale).clamp(_minZoom, _maxZoom).toDouble();
    unawaited(_applyZoom());
  }

  Future<void> _applyZoom() async {
    final controller = _controller;
    if (_zoomUpdateInFlight ||
        controller == null ||
        !controller.value.isInitialized) {
      return;
    }
    _zoomUpdateInFlight = true;
    try {
      while (mounted && identical(_controller, controller)) {
        final target = _requestedZoom;
        await controller.setZoomLevel(target);
        _zoomLevel = target;
        if ((_requestedZoom - target).abs() < 0.01) break;
      }
    } catch (_) {
      // Zoom is optional; leave the camera working if a device rejects it.
    } finally {
      _zoomUpdateInFlight = false;
      if (mounted && (_requestedZoom - _zoomLevel).abs() >= 0.01) {
        unawaited(_applyZoom());
      }
    }
  }

  Future<void> _showVideoSettings() async {
    if (_recording || _busy || _loading) return;
    var selectedResolution = _videoResolution;
    var selectedFps = _videoFps;
    final settings = await showModalBottomSheet<
      ({VideoResolution resolution, int fps})
    >(
      context: context,
      backgroundColor: _surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (sheetContext) => StatefulBuilder(
        builder: (context, setSheetState) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 22, 20, 18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Video settings',
                  style: TextStyle(
                    color: _white,
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 20),
                const Text('Resolution', style: TextStyle(color: _muted)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 10,
                  children: [
                    ChoiceChip(
                      label: const Text('720p'),
                      selected: selectedResolution == VideoResolution.p720,
                      selectedColor: _white,
                      backgroundColor: _black,
                      side: const BorderSide(color: Color(0xFF444444)),
                      labelStyle: TextStyle(
                        color: selectedResolution == VideoResolution.p720
                            ? _black
                            : _white,
                      ),
                      onSelected: (_) => setSheetState(
                        () => selectedResolution = VideoResolution.p720,
                      ),
                    ),
                    ChoiceChip(
                      label: const Text('1080p'),
                      selected: selectedResolution == VideoResolution.p1080,
                      selectedColor: _white,
                      backgroundColor: _black,
                      side: const BorderSide(color: Color(0xFF444444)),
                      labelStyle: TextStyle(
                        color: selectedResolution == VideoResolution.p1080
                            ? _black
                            : _white,
                      ),
                      onSelected: (_) => setSheetState(
                        () => selectedResolution = VideoResolution.p1080,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const Text('Frame rate', style: TextStyle(color: _muted)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 10,
                  children: [
                    ChoiceChip(
                      label: const Text('30 FPS'),
                      selected: selectedFps == 30,
                      selectedColor: _white,
                      backgroundColor: _black,
                      side: const BorderSide(color: Color(0xFF444444)),
                      labelStyle: TextStyle(
                        color: selectedFps == 30 ? _black : _white,
                      ),
                      onSelected: (_) => setSheetState(() => selectedFps = 30),
                    ),
                    ChoiceChip(
                      label: const Text('60 FPS'),
                      selected: selectedFps == 60,
                      selectedColor: _white,
                      backgroundColor: _black,
                      side: const BorderSide(color: Color(0xFF444444)),
                      labelStyle: TextStyle(
                        color: selectedFps == 60 ? _black : _white,
                      ),
                      onSelected: (_) => setSheetState(() => selectedFps = 60),
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor: _white,
                      foregroundColor: _black,
                    ),
                    onPressed: () => Navigator.of(sheetContext).pop((
                      resolution: selectedResolution,
                      fps: selectedFps,
                    )),
                    child: const Text('Apply'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    if (settings == null || !mounted) return;
    await _applyVideoSettings(
      resolution: settings.resolution,
      fps: settings.fps,
    );
  }

  Future<void> _applyVideoSettings({
    required VideoResolution resolution,
    required int fps,
  }) async {
    if (_recording || _busy || _cameras.isEmpty) return;
    final previousResolution = _videoResolution;
    final previousFps = _videoFps;
    if (resolution == previousResolution && fps == previousFps) return;

    setState(() {
      _loading = true;
      _error = null;
      _torchEnabled = false;
    });
    final candidates = <({VideoResolution resolution, int fps})>[
      (resolution: resolution, fps: fps),
      if (fps == 60) (resolution: resolution, fps: 30),
      if (fps == 60 && resolution != VideoResolution.p720)
        (resolution: VideoResolution.p720, fps: 60),
      (resolution: VideoResolution.p720, fps: 30),
      (resolution: previousResolution, fps: previousFps),
    ];
    final tried = <String>{};
    var applied = false;
    var actualResolution = previousResolution;
    var actualFps = previousFps;
    try {
      for (final candidate in candidates) {
        final key = '${candidate.resolution.name}:${candidate.fps}';
        if (!tried.add(key)) continue;
        if (mounted) {
          setState(() {
            _videoResolution = candidate.resolution;
            _videoFps = candidate.fps;
            _error = null;
          });
        }
        try {
          await _configureCamera(_cameraIndex);
          applied = true;
          actualResolution = candidate.resolution;
          actualFps = candidate.fps;
          break;
        } catch (_) {
          // Try a supported fallback if this camera cannot use the selection.
        }
      }
      if (!applied && mounted) {
        setState(() {
          _videoResolution = previousResolution;
          _videoFps = previousFps;
          _error = 'Camera could not be reconfigured.';
        });
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
    if (applied && (actualResolution != resolution || actualFps != fps)) {
      final quality = actualResolution == VideoResolution.p1080
          ? '1080p'
          : '720p';
      _message('Unsupported combination; using $quality at $actualFps FPS.');
    } else if (!applied) {
      _message(
        'Could not apply the selected video settings; camera is unavailable.',
      );
    }
  }

  Future<void> _switchCamera() async {
""",
    "pinch zoom and video settings controls",
)

replace_once(
    "                  ClipRect(child: CameraPreview(controller))",
    """                  GestureDetector(
                    onScaleStart: _onZoomStart,
                    onScaleUpdate: _onZoomUpdate,
                    child: ClipRect(child: CameraPreview(controller)),
                  )""",
    "pinch-to-zoom gesture",
)

replace_once(
    """                      else
                        const SizedBox(width: 40),
                      IconButton(
""",
    """                      else if (_mode == CaptureMode.video)
                        GestureDetector(
                          onTap: _showVideoSettings,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 11,
                              vertical: 8,
                            ),
                            decoration: BoxDecoration(
                              color: const Color(0x66000000),
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(
                                color: const Color(0x55FFFFFF),
                              ),
                            ),
                            child: Text(
                              '${_videoResolution == VideoResolution.p1080 ? '1080p' : '720p'} · $_videoFps FPS',
                              style: const TextStyle(
                                color: _white,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        )
                      else
                        const SizedBox(width: 40),
                      IconButton(
""",
    "quick video settings indicator",
)

replace_once(
    """              children: [
                _RoundControl(
                  icon: Icons.photo_library_outlined,
                  label: 'Gallery',
                  onTap: _recording ? null : widget.onOpenGallery,
                ),
                Semantics(
""",
    """              children: [
                const SizedBox(width: 52),
                Semantics(
""",
    "remove duplicate gallery shortcut",
)

replace_once(
    """                            shape: _recording || _mode == CaptureMode.video
                                ? BoxShape.rectangle
                                : BoxShape.circle,
""",
    """                            shape: _recording
                                ? BoxShape.rectangle
                                : BoxShape.circle,
""",
    "round the shutter outside active recording",
)

replace_once(
    """                IconButton(
                  onPressed: _loadAssets,
                  tooltip: 'Refresh gallery',
                  icon: const Icon(Icons.refresh, color: _white),
                ),
""",
    "",
    "remove separate gallery refresh button",
)

old_gallery = """          Expanded(
            child: _loading
                ? const Center(
                    child: CircularProgressIndicator(
                      color: _white,
                      strokeWidth: 2,
                    ),
                  )
                : !_hasPermission
                ? _permissionMessage()
                : _error != null
                ? _emptyMessage(_error!, Icons.error_outline)
                : _assets.isEmpty
                ? _emptyMessage(
                    'Photos and videos you take will appear here.',
                    Icons.photo_library_outlined,
                  )
                : GridView.builder(
                    padding: const EdgeInsets.fromLTRB(3, 0, 3, 8),
                    itemCount: _assets.length,
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 3,
                          crossAxisSpacing: 3,
                          mainAxisSpacing: 3,
                        ),
                    itemBuilder: (context, index) {
                      final asset = _assets[index];
                      return _GalleryTile(
                        asset: asset,
                        onTap: () => _openAsset(asset),
                      );
                    },
                  ),
          ),
"""
new_gallery = """          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadAssets,
              color: _white,
              backgroundColor: _surface,
              child: _loading
                  ? ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      children: const [
                        SizedBox(
                          height: 260,
                          child: Center(
                            child: CircularProgressIndicator(
                              color: _white,
                              strokeWidth: 2,
                            ),
                          ),
                        ),
                      ],
                    )
                  : !_hasPermission
                  ? ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      children: [
                        SizedBox(height: 280, child: _permissionMessage()),
                      ],
                    )
                  : _error != null
                  ? ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      children: [
                        SizedBox(
                          height: 280,
                          child: _emptyMessage(_error!, Icons.error_outline),
                        ),
                      ],
                    )
                  : _assets.isEmpty
                  ? ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      children: [
                        SizedBox(
                          height: 280,
                          child: _emptyMessage(
                            'Photos and videos you take will appear here.',
                            Icons.photo_library_outlined,
                          ),
                        ),
                      ],
                    )
                  : GridView.builder(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(3, 0, 3, 8),
                      itemCount: _assets.length,
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: 3,
                            crossAxisSpacing: 3,
                            mainAxisSpacing: 3,
                          ),
                      itemBuilder: (context, index) {
                        final asset = _assets[index];
                        return _GalleryTile(
                          asset: asset,
                          onTap: () => _openAsset(asset),
                        );
                      },
                    ),
            ),
          ),
"""
replace_once(old_gallery, new_gallery, "pull-to-refresh gallery list")

path.write_text(text, encoding="utf-8")
print("Camera feature patch complete.")

import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:photo_manager/photo_manager.dart';
import 'package:video_player/video_player.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const CameraApp());
}

enum CaptureMode { photo, video }

const Color _black = Color(0xFF000000);
const Color _white = Color(0xFFFFFFFF);
const Color _surface = Color(0xFF151515);
const Color _muted = Color(0xFF8C8C8C);

class CameraApp extends StatefulWidget {
  const CameraApp({super.key});

  @override
  State<CameraApp> createState() => _CameraAppState();
}

class _CameraAppState extends State<CameraApp> {
  int _selectedTab = 0;
  int _galleryRevision = 0;
  bool _recording = false;

  void _openGallery() {
    if (_recording) return;
    setState(() => _selectedTab = 1);
  }

  void _openCamera() => setState(() => _selectedTab = 0);

  void _mediaSaved() => setState(() => _galleryRevision++);

  void _recordingChanged(bool value) => setState(() => _recording = value);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Camera',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: _black,
        colorScheme: const ColorScheme.dark(
          primary: _white,
          onPrimary: _black,
          surface: _black,
          onSurface: _white,
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: _black,
          foregroundColor: _white,
          elevation: 0,
          centerTitle: false,
        ),
        snackBarTheme: const SnackBarThemeData(
          backgroundColor: Color(0xFF242424),
          contentTextStyle: TextStyle(color: _white),
          behavior: SnackBarBehavior.floating,
        ),
        useMaterial3: true,
      ),
      home: Scaffold(
        backgroundColor: _black,
        body: _selectedTab == 0
            ? CameraTab(
                onOpenGallery: _openGallery,
                onMediaSaved: _mediaSaved,
                onRecordingChanged: _recordingChanged,
              )
            : GalleryTab(
                key: ValueKey<int>(_galleryRevision),
                onOpenCamera: _openCamera,
              ),
        bottomNavigationBar: SafeArea(
          top: false,
          child: Container(
            height: 62,
            decoration: const BoxDecoration(
              color: _black,
              border: Border(top: BorderSide(color: Color(0xFF202020))),
            ),
            child: Row(
              children: [
                Expanded(
                  child: _NavigationItem(
                    icon: Icons.camera_alt_outlined,
                    label: 'Camera',
                    selected: _selectedTab == 0,
                    onTap: _openCamera,
                  ),
                ),
                Expanded(
                  child: _NavigationItem(
                    icon: Icons.photo_library_outlined,
                    label: 'Gallery',
                    selected: _selectedTab == 1,
                    onTap: _openGallery,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _NavigationItem extends StatelessWidget {
  const _NavigationItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected ? _white : _muted;
    return InkWell(
      onTap: onTap,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 23, color: color),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 10,
              fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
        ],
      ),
    );
  }
}

class CameraTab extends StatefulWidget {
  const CameraTab({
    super.key,
    required this.onOpenGallery,
    required this.onMediaSaved,
    required this.onRecordingChanged,
  });

  final VoidCallback onOpenGallery;
  final VoidCallback onMediaSaved;
  final ValueChanged<bool> onRecordingChanged;

  @override
  State<CameraTab> createState() => _CameraTabState();
}

class _CameraTabState extends State<CameraTab> with WidgetsBindingObserver {
  CameraController? _controller;
  List<CameraDescription> _cameras = [];
  int _cameraIndex = 0;
  CaptureMode _mode = CaptureMode.photo;
  bool _loading = true;
  bool _busy = false;
  bool _recording = false;
  bool _torchEnabled = false;
  String? _error;
  int _recordSeconds = 0;
  Timer? _recordTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeCamera();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _recordTimer?.cancel();
    final controller = _controller;
    _controller = null;
    if (controller != null) unawaited(controller.dispose());
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.paused ||
        state == AppLifecycleState.detached) {
      final controller = _controller;
      _controller = null;
      if (controller != null) unawaited(controller.dispose());
      return;
    }
    if (state == AppLifecycleState.resumed &&
        _cameras.isNotEmpty &&
        _controller == null &&
        !_recording) {
      unawaited(_resumeCamera());
    }
  }

  Future<void> _initializeCamera() async {
    try {
      final cameras = await availableCameras();
      if (!mounted) return;
      if (cameras.isEmpty) {
        throw CameraException('no_camera', 'No camera was found on this device.');
      }
      _cameras = cameras;
      final backIndex = cameras.indexWhere(
        (item) => item.lensDirection == CameraLensDirection.back,
      );
      _cameraIndex = backIndex >= 0 ? backIndex : 0;
      await _configureCamera(_cameraIndex);
    } catch (error) {
      if (mounted) {
        setState(() => _error = 'Camera is unavailable. Check camera permission.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _resumeCamera() async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await _configureCamera(_cameraIndex);
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not reopen the camera.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _configureCamera(int index) async {
    final previous = _controller;
    _controller = null;
    if (previous != null) await previous.dispose();

    final controller = CameraController(
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
  }

  Future<void> _switchCamera() async {
    if (_cameras.length < 2 || _busy || _recording) return;
    final nextIndex = (_cameraIndex + 1) % _cameras.length;
    setState(() {
      _cameraIndex = nextIndex;
      _loading = true;
      _error = null;
    });
    try {
      await _configureCamera(nextIndex);
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not switch camera.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _toggleTorch() async {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized || _busy) return;
    final enable = !_torchEnabled;
    try {
      await controller.setFlashMode(enable ? FlashMode.torch : FlashMode.off);
      if (mounted) setState(() => _torchEnabled = enable);
    } catch (_) {
      _message('Flash is not available on this camera.');
    }
  }

  void _changeMode(CaptureMode mode) {
    if (_recording || _busy) return;
    setState(() => _mode = mode);
  }

  Future<void> _shutterPressed() async {
    final controller = _controller;
    if (_busy || controller == null || !controller.value.isInitialized) return;

    setState(() => _busy = true);
    try {
      if (_mode == CaptureMode.photo) {
        final image = await controller.takePicture();
        await _savePhoto(image);
      } else if (!_recording) {
        await controller.startVideoRecording();
        _recordTimer?.cancel();
        if (mounted) {
          setState(() {
            _recording = true;
            _recordSeconds = 0;
          });
          widget.onRecordingChanged(true);
        }
        _recordTimer = Timer.periodic(const Duration(seconds: 1), (_) {
          if (mounted) setState(() => _recordSeconds++);
        });
      } else {
        final video = await controller.stopVideoRecording();
        _recordTimer?.cancel();
        if (mounted) {
          setState(() {
            _recording = false;
            _recordSeconds = 0;
          });
          widget.onRecordingChanged(false);
        }
        await _saveVideo(video);
      }
    } catch (error) {
      _message('Camera action failed. Check camera and microphone permission.');
      if (_recording && !(controller.value.isRecordingVideo)) {
        _recordTimer?.cancel();
        if (mounted) {
          setState(() {
            _recording = false;
            _recordSeconds = 0;
          });
          widget.onRecordingChanged(false);
        }
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<bool> _requestMediaPermission() async {
    final permission = await PhotoManager.requestPermissionExtend();
    return permission.isAuth || permission.hasAccess;
  }

  String _mediaTitle(String extension) {
    final stamp = DateTime.now().millisecondsSinceEpoch.toString();
    return 'Camera_' + stamp + extension;
  }

  Future<void> _savePhoto(XFile image) async {
    try {
      if (!await _requestMediaPermission()) {
        _message('Photo captured, but gallery access was denied.');
        return;
      }
      final saved = await PhotoManager.editor.saveImageWithPath(
        image.path,
        title: _mediaTitle('.jpg'),
      );
      if (saved == null) {
        _message('Photo captured, but could not save it to Gallery.');
        return;
      }
      widget.onMediaSaved();
      _message('Photo saved to Gallery.');
    } catch (_) {
      _message('Photo captured, but could not save it to Gallery.');
    }
  }

  Future<void> _saveVideo(XFile video) async {
    try {
      if (!await _requestMediaPermission()) {
        _message('Video recorded, but gallery access was denied.');
        return;
      }
      final saved = await PhotoManager.editor.saveVideo(
        File(video.path),
        title: _mediaTitle('.mp4'),
      );
      if (saved == null) {
        _message('Video recorded, but could not save it to Gallery.');
        return;
      }
      widget.onMediaSaved();
      _message('Video saved to Gallery.');
    } catch (_) {
      _message('Video recorded, but could not save it to Gallery.');
    }
  }

  void _message(String value) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(value)));
  }

  String get _recordTime {
    final minutes = (_recordSeconds ~/ 60).toString().padLeft(2, '0');
    final seconds = (_recordSeconds % 60).toString().padLeft(2, '0');
    return minutes + ':' + seconds;
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;
    return SafeArea(
      child: Column(
        children: [
          Expanded(
            child: Stack(
              fit: StackFit.expand,
              children: [
                if (controller != null &&
                    controller.value.isInitialized &&
                    _error == null)
                  ClipRect(child: CameraPreview(controller))
                else
                  _cameraPlaceholder(),
                Positioned(
                  top: 4,
                  left: 12,
                  right: 12,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      if (_recording)
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 7,
                              height: 7,
                              decoration: const BoxDecoration(
                                color: _white,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 7),
                            Text(
                              _recordTime,
                              style: const TextStyle(
                                color: _white,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        )
                      else
                        const SizedBox(width: 40),
                      IconButton(
                        onPressed: _toggleTorch,
                        tooltip: 'Flashlight',
                        icon: Icon(
                          _torchEnabled ? Icons.flash_on : Icons.flash_off,
                          color: _white,
                        ),
                        style: IconButton.styleFrom(
                          backgroundColor: const Color(0x66000000),
                        ),
                      ),
                    ],
                  ),
                ),
                if (_busy)
                  const Positioned(
                    top: 56,
                    right: 20,
                    child: SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: _white,
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _ModeLabel(
                label: 'PHOTO',
                selected: _mode == CaptureMode.photo,
                onTap: () => _changeMode(CaptureMode.photo),
              ),
              const SizedBox(width: 30),
              _ModeLabel(
                label: 'VIDEO',
                selected: _mode == CaptureMode.video,
                onTap: () => _changeMode(CaptureMode.video),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 28),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _RoundControl(
                  icon: Icons.photo_library_outlined,
                  label: 'Gallery',
                  onTap: _recording ? null : widget.onOpenGallery,
                ),
                Semantics(
                  label: _recording ? 'Stop video recording' : 'Capture',
                  button: true,
                  child: GestureDetector(
                    onTap: _busy ? null : _shutterPressed,
                    child: Container(
                      width: 76,
                      height: 76,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(color: _white, width: 3),
                      ),
                      padding: const EdgeInsets.all(7),
                      child: Center(
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 120),
                          width: _recording ? 24 : 56,
                          height: _recording ? 24 : 56,
                          decoration: BoxDecoration(
                            color: _white,
                            shape: _recording || _mode == CaptureMode.video
                                ? BoxShape.rectangle
                                : BoxShape.circle,
                            borderRadius: _recording || _mode == CaptureMode.video
                                ? BorderRadius.circular(5)
                                : null,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                _RoundControl(
                  icon: Icons.flip_camera_android_outlined,
                  label: 'Switch camera',
                  onTap: _switchCamera,
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
        ],
      ),
    );
  }

  Widget _cameraPlaceholder() {
    return Container(
      color: _black,
      width: double.infinity,
      child: Center(
        child: _loading
            ? const CircularProgressIndicator(color: _white, strokeWidth: 2)
            : Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.camera_alt_outlined, size: 42, color: _muted),
                  const SizedBox(height: 16),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 36),
                    child: Text(
                      _error ?? 'Camera is unavailable.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: _muted, fontSize: 13),
                    ),
                  ),
                  const SizedBox(height: 18),
                  OutlinedButton(
                    onPressed: _initializeCamera,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: _white,
                      side: const BorderSide(color: Color(0xFF555555)),
                    ),
                    child: const Text('Try again'),
                  ),
                ],
              ),
      ),
    );
  }
}

class _ModeLabel extends StatelessWidget {
  const _ModeLabel({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: TextStyle(
                color: selected ? _white : _muted,
                fontSize: 11,
                letterSpacing: 1.4,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
            const SizedBox(height: 8),
            AnimatedContainer(
              duration: const Duration(milliseconds: 140),
              width: selected ? 34 : 0,
              height: 2,
              decoration: BoxDecoration(
                color: _white,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RoundControl extends StatelessWidget {
  const _RoundControl({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return IconButton(
      onPressed: onTap,
      tooltip: label,
      icon: Icon(icon, color: onTap == null ? _muted : _white, size: 25),
      style: IconButton.styleFrom(
        backgroundColor: _surface,
        minimumSize: const Size(48, 48),
        maximumSize: const Size(48, 48),
      ),
    );
  }
}

class GalleryTab extends StatefulWidget {
  const GalleryTab({
    super.key,
    required this.onOpenCamera,
  });

  final VoidCallback onOpenCamera;

  @override
  State<GalleryTab> createState() => _GalleryTabState();
}

class _GalleryTabState extends State<GalleryTab> {
  bool _loading = true;
  bool _hasPermission = true;
  String? _error;
  List<AssetEntity> _assets = [];

  @override
  void initState() {
    super.initState();
    _loadAssets();
  }

  Future<void> _loadAssets() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final permission = await PhotoManager.requestPermissionExtend();
      if (!(permission.isAuth || permission.hasAccess)) {
        if (mounted) {
          setState(() {
            _hasPermission = false;
            _assets = [];
          });
        }
        return;
      }
      final paths = await PhotoManager.getAssetPathList(
        type: RequestType.common,
        onlyAll: true,
      );
      final assets = paths.isEmpty
          ? <AssetEntity>[]
          : await paths.first.getAssetListPaged(page: 0, size: 200);
      assets.sort((a, b) => b.createDateTime.compareTo(a.createDateTime));
      if (mounted) {
        setState(() {
          _hasPermission = true;
          _assets = assets;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not load media from this device.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openAsset(AssetEntity asset) async {
    final file = await asset.file;
    if (!mounted || file == null) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => _AssetPreview(asset: asset, file: file),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 14, 12, 16),
            child: Row(
              children: [
                const Expanded(
                  child: Text(
                    'Gallery',
                    style: TextStyle(
                      color: _white,
                      fontSize: 25,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: _loadAssets,
                  tooltip: 'Refresh gallery',
                  icon: const Icon(Icons.refresh, color: _white),
                ),
              ],
            ),
          ),
          Expanded(
            child: _loading
                ? const Center(
                    child: CircularProgressIndicator(color: _white, strokeWidth: 2),
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
        ],
      ),
    );
  }

  Widget _permissionMessage() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.photo_library_outlined, color: _muted, size: 38),
            const SizedBox(height: 16),
            const Text(
              'Allow media access to view your Gallery.',
              textAlign: TextAlign.center,
              style: TextStyle(color: _muted, fontSize: 13),
            ),
            const SizedBox(height: 14),
            OutlinedButton(
              onPressed: PhotoManager.openSetting,
              child: const Text('Open settings'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _emptyMessage(String message, IconData icon) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: _muted, size: 40),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: _muted, fontSize: 13),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: widget.onOpenCamera,
              icon: const Icon(Icons.camera_alt_outlined, size: 18),
              label: const Text('Open camera'),
            ),
          ],
        ),
      ),
    );
  }
}

class _GalleryTile extends StatelessWidget {
  const _GalleryTile({required this.asset, required this.onTap});

  final AssetEntity asset;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Stack(
        fit: StackFit.expand,
        children: [
          FutureBuilder<Uint8List?>(
            future: asset.thumbnailDataWithSize(const ThumbnailSize(320, 320)),
            builder: (context, snapshot) {
              final bytes = snapshot.data;
              if (bytes == null) {
                return Container(color: const Color(0xFF181818));
              }
              return Image.memory(bytes, fit: BoxFit.cover, gaplessPlayback: true);
            },
          ),
          if (asset.type == AssetType.video)
            const Positioned(
              right: 6,
              bottom: 6,
              child: Icon(Icons.play_circle_fill, size: 22, color: _white),
            ),
        ],
      ),
    );
  }
}

class _AssetPreview extends StatefulWidget {
  const _AssetPreview({required this.asset, required this.file});

  final AssetEntity asset;
  final File file;

  @override
  State<_AssetPreview> createState() => _AssetPreviewState();
}

class _AssetPreviewState extends State<_AssetPreview> {
  VideoPlayerController? _videoController;
  Future<void>? _videoInitialization;

  @override
  void initState() {
    super.initState();
    if (widget.asset.type == AssetType.video) {
      final controller = VideoPlayerController.file(widget.file);
      _videoController = controller;
      _videoInitialization = controller.initialize();
    }
  }

  @override
  void dispose() {
    _videoController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isVideo = widget.asset.type == AssetType.video;
    return Scaffold(
      backgroundColor: _black,
      appBar: AppBar(
        backgroundColor: _black,
        leading: IconButton(
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.arrow_back, color: _white),
        ),
        title: Text(
          isVideo ? 'Video' : 'Photo',
          style: const TextStyle(color: _white, fontSize: 16),
        ),
      ),
      body: Center(
        child: isVideo ? _videoBody() : Image.file(widget.file, fit: BoxFit.contain),
      ),
    );
  }

  Widget _videoBody() {
    final controller = _videoController;
    if (controller == null) return const SizedBox.shrink();
    return FutureBuilder<void>(
      future: _videoInitialization,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done ||
            !controller.value.isInitialized) {
          return const CircularProgressIndicator(color: _white, strokeWidth: 2);
        }
        return GestureDetector(
          onTap: () {
            setState(() {
              if (controller.value.isPlaying) {
                controller.pause();
              } else {
                controller.play();
              }
            });
          },
          child: Stack(
            alignment: Alignment.center,
            children: [
              AspectRatio(
                aspectRatio: controller.value.aspectRatio,
                child: VideoPlayer(controller),
              ),
              if (!controller.value.isPlaying)
                const Icon(Icons.play_circle_outline, color: _white, size: 64),
            ],
          ),
        );
      },
    );
  }
}

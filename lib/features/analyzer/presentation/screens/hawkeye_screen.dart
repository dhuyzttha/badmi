import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/constants/bwf_dimensions.dart';
import '../../../../core/math/homography_matrix.dart';
import '../../../../core/math/kalman_filter.dart';
import '../../domain/models/court_model.dart';
import '../../domain/models/player_model.dart';
import '../../domain/models/shuttlecock_model.dart';
import '../../domain/models/rally_stats.dart';
import '../../data/services/xiaomi_safe_file_picker.dart';
import '../widgets/hawkeye_painter.dart';
import '../widgets/mini_court_widget.dart';
import '../widgets/stats_hud_widget.dart';
import '../widgets/control_panel_widget.dart';

class HawkEyeScreen extends StatefulWidget {
  const HawkEyeScreen({Key? key}) : super(key: key);

  @override
  State<HawkEyeScreen> createState() => _HawkEyeScreenState();
}

class _HawkEyeScreenState extends State<HawkEyeScreen> {
  VideoPlayerController? _videoController;
  bool _isLoading = false;
  String? _videoPath;

  // Domain state
  late CourtModel _court;
  late List<PlayerModel> _players;
  late ShuttlecockModel _shuttlecock;
  late RallyStats _rallyStats;
  double _sensitivity = 0.8;

  // Math engines
  late ShuttlecockKalmanFilter _kalmanFilter;

  @override
  void initState() {
    super.initState();
    _court = CourtModel.initial(CourtMode.singles);
    _initPlayers();
    _shuttlecock = ShuttlecockModel();
    _rallyStats = RallyStats();
    _kalmanFilter = ShuttlecockKalmanFilter();

    // Recompute initial homography
    _court = _court.copyWithCorners(_court.corners);
  }

  void _initPlayers() {
    _players = [
      PlayerModel(
        id: 1,
        name: "Momota",
        side: "top",
        bbox: const Rect.fromLTWH(210, 370, 70, 100),
        footPx: const Offset(245, 470),
        footBwf: const Offset(2.4, 2.5),
        totalDistanceMeters: 18.2,
        rallyDistanceMeters: 4.8,
      ),
      PlayerModel(
        id: 2,
        name: "Axelsen",
        side: "bottom",
        bbox: const Rect.fromLTWH(290, 540, 95, 130),
        footPx: const Offset(337, 670),
        footBwf: const Offset(3.1, 10.7),
        totalDistanceMeters: 12.2,
        rallyDistanceMeters: 3.5,
      ),
    ];
  }

  @override
  void dispose() {
    _videoController?.dispose();
    super.dispose();
  }

  Future<void> _handlePickVideo() async {
    setState(() => _isLoading = true);
    try {
      final path = await XiaomiSafeFilePicker.pickVideo();
      if (path != null) {
        _videoPath = path;
        await _initializeVideo(File(path));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi tải video: $e'), backgroundColor: HawkEyeTheme.neonRed),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _initializeVideo(File file) async {
    await _videoController?.dispose();
    _videoController = VideoPlayerController.file(file);
    await _videoController!.initialize();
    _videoController!.setLooping(true);
    _videoController!.addListener(_onVideoTick);
    await _videoController!.play();
    setState(() {});
  }

  void _onVideoTick() {
    if (_videoController == null || !_videoController!.value.isInitialized) return;

    final pos = _videoController!.value.position;
    final total = _videoController!.value.duration;

    // Synchronize telemetry with video time
    final double t = pos.inMilliseconds / 1000.0;
    
    // Smooth mathematical trajectory projection
    final double courtW = _court.corners[1].dx - _court.corners[0].dx;
    final double courtH = _court.corners[2].dy - _court.corners[0].dy;
    final double simX = _court.corners[0].dx + (courtW * 0.5) + (courtW * 0.3) * math.sin(t * 2.0);
    final double simY = _court.corners[0].dy + (courtH * 0.5) + (courtH * 0.4) * math.cos(t * 1.5);

    final Offset simPx = Offset(simX, simY);
    _kalmanFilter.predict();
    final Offset smoothedPx = _kalmanFilter.update(simPx);

    final Offset bwfPos = _court.homography?.transform(smoothedPx) ?? const Offset(2.6, 6.7);
    final double simSpeed = (120.0 + 80.0 * (math.sin(t * 2.5)).abs()).clamp(30.0, 340.0);

    final List<TrajectoryPoint> updatedTrail = List.from(_shuttlecock.trajectory);
    updatedTrail.add(TrajectoryPoint(
      frame: (t * 30).toInt(),
      px: smoothedPx,
      bwf: bwfPos,
      speedKmh: simSpeed,
    ));
    if (updatedTrail.length > 25) updatedTrail.removeAt(0);

    setState(() {
      _shuttlecock = _shuttlecock.copyWith(
        currentPx: smoothedPx,
        currentBwf: bwfPos,
        currentSpeedKmh: simSpeed,
        maxSpeedKmh: simSpeed > _shuttlecock.maxSpeedKmh ? simSpeed : _shuttlecock.maxSpeedKmh,
        trajectory: updatedTrail,
        isTracking: true,
      );

      _rallyStats = _rallyStats.copyWith(
        durationSeconds: t,
        shotCount: (t * 1.8).toInt(),
        state: RallyState.inPlay,
      );
    });
  }

  void _onModeChanged(CourtMode mode) {
    setState(() {
      _court = CourtModel(
        mode: mode,
        corners: _court.corners,
      ).copyWithCorners(_court.corners);
    });
  }

  void _onSensitivityChanged(double val) {
    setState(() => _sensitivity = val);
  }

  void _togglePlayPause() {
    if (_videoController == null) return;
    if (_videoController!.value.isPlaying) {
      _videoController!.pause();
    } else {
      _videoController!.play();
    }
    setState(() {});
  }

  void _stepFrame(int frames) {
    if (_videoController == null) return;
    final currentMs = _videoController!.value.position.inMilliseconds;
    final stepMs = (frames * (1000 / 30)).toInt();
    final target = Duration(milliseconds: (currentMs + stepMs).clamp(0, _videoController!.value.duration.inMilliseconds));
    _videoController!.seekTo(target);
  }

  @override
  Widget build(BuildContext context) {
    final Size videoSize = _videoController != null && _videoController!.value.isInitialized
        ? _videoController!.value.size
        : const Size(576, 1024);

    return Scaffold(
      backgroundColor: HawkEyeTheme.background,
      body: SafeArea(
        child: Column(
          children: [
            // Top HUD
            StatsHudWidget(stats: _rallyStats, shuttlecock: _shuttlecock),

            // Video & Hawk-Eye AR Layer
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  // Video Stream or Placeholder
                  if (_videoController != null && _videoController!.value.isInitialized)
                    Center(
                      child: AspectRatio(
                        aspectRatio: _videoController!.value.aspectRatio,
                        child: VideoPlayer(_videoController!),
                      ),
                    )
                  else
                    Container(
                      color: Colors.black,
                      child: Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.sports_tennis, size: 64, color: HawkEyeTheme.neonGreen),
                            const SizedBox(height: 12),
                            const Text(
                              'HỆ THỐNG PHÂN TÍCH HAWK-EYE CẦU LÔNG',
                              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                            ),
                            const SizedBox(height: 6),
                            const Text(
                              'Bấm "Chọn Video" để bắt đầu phân tích tự động',
                              style: TextStyle(color: HawkEyeTheme.textSecondary, fontSize: 12),
                            ),
                            const SizedBox(height: 16),
                            ElevatedButton.icon(
                              onPressed: _handlePickVideo,
                              icon: const Icon(Icons.folder_open),
                              label: const Text('Tải Video Lên'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: HawkEyeTheme.neonGreen,
                                foregroundColor: Colors.black,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                  // Hawk-Eye Canvas AR Overlay
                  Positioned.fill(
                    child: CustomPaint(
                      painter: HawkEyePainter(
                        court: _court,
                        players: _players,
                        shuttlecock: _shuttlecock,
                        rallyStats: _rallyStats,
                        originalVideoSize: videoSize,
                      ),
                    ),
                  ),

                  // Floating 2D Mini-Court Map (Top-Right)
                  Positioned(
                    top: 12,
                    right: 12,
                    child: MiniCourtWidget(
                      court: _court,
                      players: _players,
                      shuttlecock: _shuttlecock,
                    ),
                  ),

                  if (_isLoading)
                    Container(
                      color: Colors.black54,
                      child: const Center(
                        child: CircularProgressIndicator(color: HawkEyeTheme.neonGreen),
                      ),
                    ),
                ],
              ),
            ),

            // Bottom Controls & Sliders
            ControlPanelWidget(
              currentMode: _court.mode,
              onModeChanged: _onModeChanged,
              sensitivity: _sensitivity,
              onSensitivityChanged: _onSensitivityChanged,
              isPlaying: _videoController?.value.isPlaying ?? false,
              onPlayPauseToggle: _togglePlayPause,
              onStepForward: () => _stepFrame(1),
              onStepBackward: () => _stepFrame(-1),
              currentPosition: _videoController?.value.position ?? Duration.zero,
              totalDuration: _videoController?.value.duration ?? Duration.zero,
              onSeek: (pos) => _videoController?.seekTo(pos),
              onPickVideo: _handlePickVideo,
              players: _players,
            ),
          ],
        ),
      ),
    );
  }
}

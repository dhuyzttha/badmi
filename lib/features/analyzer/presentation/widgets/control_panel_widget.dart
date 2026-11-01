import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/utils/debouncer.dart';
import '../../domain/models/court_model.dart';
import '../../domain/models/player_model.dart';

class ControlPanelWidget extends StatefulWidget {
  final CourtMode currentMode;
  final ValueChanged<CourtMode> onModeChanged;
  final double sensitivity;
  final ValueChanged<double> onSensitivityChanged;
  final bool isPlaying;
  final VoidCallback onPlayPauseToggle;
  final VoidCallback onStepForward;
  final VoidCallback onStepBackward;
  final Duration currentPosition;
  final Duration totalDuration;
  final ValueChanged<Duration> onSeek;
  final VoidCallback onPickVideo;
  final List<PlayerModel> players;

  const ControlPanelWidget({
    Key? key,
    required this.currentMode,
    required this.onModeChanged,
    required this.sensitivity,
    required this.onSensitivityChanged,
    required this.isPlaying,
    required this.onPlayPauseToggle,
    required this.onStepForward,
    required this.onStepBackward,
    required this.currentPosition,
    required this.totalDuration,
    required this.onSeek,
    required this.onPickVideo,
    required this.players,
  }) : super(key: key);

  @override
  State<ControlPanelWidget> createState() => _ControlPanelWidgetState();
}

class _ControlPanelWidgetState extends State<ControlPanelWidget> {
  late final Throttler _sliderThrottler;
  double? _draggingValue;

  @override
  void initState() {
    super.initState();
    _sliderThrottler = Throttler(interval: const Duration(milliseconds: 32)); // ~30-60 fps cap
  }

  @override
  void dispose() {
    _sliderThrottler.dispose();
    super.dispose();
  }

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    final millis = (d.inMilliseconds.remainder(1000) ~/ 100).toString();
    return '$minutes:$seconds.$millis';
  }

  @override
  Widget build(BuildContext context) {
    final double maxSec = widget.totalDuration.inMilliseconds > 0
        ? widget.totalDuration.inMilliseconds.toDouble()
        : 1.0;
    final double currentSec = (_draggingValue ?? widget.currentPosition.inMilliseconds.toDouble())
        .clamp(0.0, maxSec);

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
      decoration: const BoxDecoration(
        color: HawkEyeTheme.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
        boxShadow: [
          BoxShadow(color: Colors.black45, blurRadius: 10, offset: Offset(0, -3)),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 1. Time Slider with 60/120Hz Throttler
          Row(
            children: [
              Text(
                _formatDuration(widget.currentPosition),
                style: const TextStyle(color: HawkEyeTheme.textSecondary, fontSize: 11, fontFamily: 'monospace'),
              ),
              Expanded(
                child: Slider(
                  value: currentSec,
                  min: 0.0,
                  max: maxSec,
                  onChanged: (val) {
                    setState(() => _draggingValue = val);
                    _sliderThrottler.run(() {
                      widget.onSeek(Duration(milliseconds: val.toInt()));
                    });
                  },
                  onChangeEnd: (val) {
                    setState(() => _draggingValue = null);
                    widget.onSeek(Duration(milliseconds: val.toInt()));
                  },
                ),
              ),
              Text(
                _formatDuration(widget.totalDuration),
                style: const TextStyle(color: HawkEyeTheme.textSecondary, fontSize: 11, fontFamily: 'monospace'),
              ),
            ],
          ),

          // 2. Playback Action Buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              IconButton(
                icon: const Icon(Icons.skip_previous, color: Colors.white70),
                onPressed: widget.onStepBackward,
                tooltip: 'Lùi 1 khung hình',
              ),
              IconButton(
                iconSize: 42,
                icon: Icon(
                  widget.isPlaying ? Icons.pause_circle_filled : Icons.play_circle_filled,
                  color: HawkEyeTheme.neonGreen,
                ),
                onPressed: widget.onPlayPauseToggle,
                tooltip: widget.isPlaying ? 'Tạm dừng' : 'Phát tiếp',
              ),
              IconButton(
                icon: const Icon(Icons.skip_next, color: Colors.white70),
                onPressed: widget.onStepForward,
                tooltip: 'Tới 1 khung hình',
              ),
              ElevatedButton.icon(
                onPressed: widget.onPickVideo,
                icon: const Icon(Icons.video_library, size: 16),
                label: const Text('Chọn Video'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: HawkEyeTheme.surfaceElevated,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),

          // 3. Mode Toggle (Singles / Doubles) & Sensitivity Slider
          Row(
            children: [
              // Singles / Doubles Selector
              SegmentedButton<CourtMode>(
                segments: const [
                  ButtonSegment(value: CourtMode.singles, label: Text('Đánh Đơn', style: TextStyle(fontSize: 11))),
                  ButtonSegment(value: CourtMode.doubles, label: Text('Đánh Đôi', style: TextStyle(fontSize: 11))),
                ],
                selected: {widget.currentMode},
                onSelectionChanged: (set) => widget.onModeChanged(set.first),
                style: ButtonStyle(
                  visualDensity: VisualDensity.compact,
                  backgroundColor: MaterialStateProperty.resolveWith((states) {
                    if (states.contains(MaterialState.selected)) {
                      return HawkEyeTheme.neonGreen.withOpacity(0.2);
                    }
                    return HawkEyeTheme.surfaceElevated;
                  }),
                  foregroundColor: MaterialStateProperty.resolveWith((states) {
                    if (states.contains(MaterialState.selected)) {
                      return HawkEyeTheme.neonGreen;
                    }
                    return Colors.white70;
                  }),
                ),
              ),
              const SizedBox(width: 12),
              // Sensitivity Slider
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Độ nhạy bóng (Motion Blur):', style: TextStyle(color: HawkEyeTheme.textSecondary, fontSize: 10)),
                        Text('${(widget.sensitivity * 100).toInt()}%', style: const TextStyle(color: HawkEyeTheme.neonAmber, fontSize: 10, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    Slider(
                      value: widget.sensitivity,
                      min: 0.1,
                      max: 1.0,
                      divisions: 9,
                      activeColor: HawkEyeTheme.neonAmber,
                      onChanged: widget.onSensitivityChanged,
                    ),
                  ],
                ),
              ),
            ],
          ),

          // 4. Player Distances Badge Bar
          if (widget.players.length >= 2) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: HawkEyeTheme.surfaceElevated,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: HawkEyeTheme.neonAmber.withOpacity(0.4)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(widget.players[0].name, style: const TextStyle(color: HawkEyeTheme.neonAmber, fontSize: 11, fontWeight: FontWeight.bold)),
                        Text('${widget.players[0].totalDistanceMeters.toStringAsFixed(1)} m', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: HawkEyeTheme.surfaceElevated,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: HawkEyeTheme.neonBlue.withOpacity(0.4)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(widget.players[1].name, style: const TextStyle(color: HawkEyeTheme.neonBlue, fontSize: 11, fontWeight: FontWeight.bold)),
                        Text('${widget.players[1].totalDistanceMeters.toStringAsFixed(1)} m', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

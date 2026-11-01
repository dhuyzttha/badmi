import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../domain/models/rally_stats.dart';
import '../../domain/models/shuttlecock_model.dart';

class StatsHudWidget extends StatelessWidget {
  final RallyStats stats;
  final ShuttlecockModel shuttlecock;

  const StatsHudWidget({
    Key? key,
    required this.stats,
    required this.shuttlecock,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    Color statusColor;
    String statusText;
    switch (stats.state) {
      case RallyState.inPlay:
        statusColor = HawkEyeTheme.neonGreen;
        statusText = "IN PLAY";
        break;
      case RallyState.pointAwarded:
        statusColor = HawkEyeTheme.neonRed;
        statusText = "POINT";
        break;
      case RallyState.serve:
        statusColor = HawkEyeTheme.neonBlue;
        statusText = "SERVICE";
        break;
      case RallyState.paused:
        statusColor = HawkEyeTheme.neonAmber;
        statusText = "PAUSED";
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xE60D1117),
        border: Border(
          bottom: BorderSide(color: HawkEyeTheme.neonGreen.withOpacity(0.5), width: 1.5),
        ),
      ),
      child: Row(
        children: [
          // Left: Brand & Status
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Row(
                children: [
                  Icon(Icons.radar, color: HawkEyeTheme.neonGreen, size: 16),
                  SizedBox(width: 4),
                  Text(
                    'HAWK-EYE PRO AI',
                    style: TextStyle(
                      color: HawkEyeTheme.neonGreen,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.0,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 3),
              Row(
                children: [
                  Container(
                    width: 7,
                    height: 7,
                    decoration: BoxDecoration(shape: BoxShape.circle, color: statusColor),
                  ),
                  const SizedBox(width: 5),
                  Text(
                    statusText,
                    style: TextStyle(
                      color: statusColor,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    'SHOTS: ${stats.shotCount.toString().padLeft(2, '0')}',
                    style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    '${stats.durationSeconds.toStringAsFixed(1)}s',
                    style: const TextStyle(color: HawkEyeTheme.textSecondary, fontSize: 10),
                  ),
                ],
              ),
            ],
          ),
          const Spacer(),
          // Center: Speed Readout
          Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text(
                    shuttlecock.currentSpeedKmh.toStringAsFixed(0),
                    style: const TextStyle(
                      color: HawkEyeTheme.neonAmber,
                      fontSize: 22,
                      fontWeight: FontWeight.w900,
                      fontFamily: 'monospace',
                    ),
                  ),
                  const SizedBox(width: 2),
                  const Text(
                    'KM/H',
                    style: TextStyle(color: HawkEyeTheme.textSecondary, fontSize: 9, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              Text(
                'MAX: ${shuttlecock.maxSpeedKmh.toStringAsFixed(0)} KM/H',
                style: const TextStyle(color: HawkEyeTheme.textMuted, fontSize: 9),
              ),
            ],
          ),
          const SizedBox(width: 12),
          // Right: In/Out Decision Badge
          if (stats.refereeDecision != "PLAY ON")
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: stats.refereeDecision == "IN"
                    ? HawkEyeTheme.neonGreen.withOpacity(0.2)
                    : HawkEyeTheme.neonRed.withOpacity(0.2),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(
                  color: stats.refereeDecision == "IN" ? HawkEyeTheme.neonGreen : HawkEyeTheme.neonRed,
                  width: 1.2,
                ),
              ),
              child: Text(
                stats.refereeDecision,
                style: TextStyle(
                  color: stats.refereeDecision == "IN" ? HawkEyeTheme.neonGreen : HawkEyeTheme.neonRed,
                  fontSize: 12,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

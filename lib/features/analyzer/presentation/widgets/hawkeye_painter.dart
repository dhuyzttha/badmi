import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../domain/models/court_model.dart';
import '../../domain/models/player_model.dart';
import '../../domain/models/shuttlecock_model.dart';
import '../../domain/models/rally_stats.dart';

class HawkEyePainter extends CustomPainter {
  final CourtModel court;
  final List<PlayerModel> players;
  final ShuttlecockModel shuttlecock;
  final RallyStats rallyStats;
  final Size originalVideoSize;

  HawkEyePainter({
    required this.court,
    required this.players,
    required this.shuttlecock,
    required this.rallyStats,
    required this.originalVideoSize,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (originalVideoSize.width <= 0 || originalVideoSize.height <= 0) return;

    final double scaleX = size.width / originalVideoSize.width;
    final double scaleY = size.height / originalVideoSize.height;

    canvas.save();
    canvas.scale(scaleX, scaleY);

    // 1. Draw Court Boundary Polygon
    if (court.corners.length == 4) {
      final Path courtPath = Path();
      courtPath.moveTo(court.corners[0].dx, court.corners[0].dy);
      for (int i = 1; i < 4; i++) {
        courtPath.lineTo(court.corners[i].dx, court.corners[i].dy);
      }
      courtPath.close();

      // Semi-transparent glowing border
      final Paint courtGlow = Paint()
        ..color = HawkEyeTheme.neonGreen.withOpacity(0.4)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 4.0;
      canvas.drawPath(courtPath, courtGlow);

      final Paint courtLine = Paint()
        ..color = HawkEyeTheme.neonGreen
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0;
      canvas.drawPath(courtPath, courtLine);

      // Corner points
      final Paint cornerPaint = Paint()..color = HawkEyeTheme.neonAmber;
      for (final pt in court.corners) {
        canvas.drawCircle(pt, 5.0, cornerPaint);
      }
    }

    // 2. Draw Players
    for (final player in players) {
      if (player.bbox != null) {
        final Color pColor = player.id == 1 ? HawkEyeTheme.neonAmber : HawkEyeTheme.neonBlue;

        // Bounding box
        final Paint boxPaint = Paint()
          ..color = pColor
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.0;
        canvas.drawRect(player.bbox!, boxPaint);

        // Player Tag Badge
        final textSpan = TextSpan(
          text: '${player.name} | ${player.rallyDistanceMeters.toStringAsFixed(1)}m',
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.bold,
          ),
        );
        final textPainter = TextPainter(
          text: textSpan,
          textDirection: TextDirection.ltr,
        )..layout();

        final double badgeX = player.bbox!.left;
        final double badgeY = (player.bbox!.top - 20).clamp(10.0, originalVideoSize.height - 30);

        final Rect badgeRect = Rect.fromLTWH(badgeX, badgeY, textPainter.width + 10, 18);
        canvas.drawRect(badgeRect, Paint()..color = const Color(0xCC111827));
        canvas.drawRect(badgeRect, Paint()..color = pColor..style = PaintingStyle.stroke..strokeWidth = 1.0);
        textPainter.paint(canvas, Offset(badgeX + 5, badgeY + 2));

        // Foot anchor
        if (player.footPx != null) {
          canvas.drawOval(
            Rect.fromCenter(center: player.footPx!, width: 24, height: 10),
            Paint()..color = pColor..style = PaintingStyle.stroke..strokeWidth = 2.0,
          );
        }
      }
    }

    // 3. Draw Shuttlecock Glowing Trajectory Ribbon
    if (shuttlecock.trajectory.length > 1) {
      for (int i = 1; i < shuttlecock.trajectory.length; i++) {
        final pt1 = shuttlecock.trajectory[i - 1].px;
        final pt2 = shuttlecock.trajectory[i].px;
        final speed = shuttlecock.trajectory[i].speedKmh;

        Color trailColor;
        if (speed < 90) {
          trailColor = HawkEyeTheme.neonGreen;
        } else if (speed < 180) {
          trailColor = HawkEyeTheme.neonAmber;
        } else {
          trailColor = HawkEyeTheme.neonRed;
        }

        final double thickness = (2.0 + 3.0 * (i / shuttlecock.trajectory.length)).clamp(1.5, 6.0);
        final Paint trailPaint = Paint()
          ..color = trailColor.withOpacity(0.85)
          ..strokeWidth = thickness
          ..strokeCap = StrokeCap.round;

        canvas.drawLine(pt1, pt2, trailPaint);
      }
    }

    // 4. Draw Current Shuttlecock Marker & Callout
    if (shuttlecock.currentPx != null) {
      final Offset sPos = shuttlecock.currentPx!;
      
      // Target Reticle
      canvas.drawCircle(sPos, 6.0, Paint()..color = HawkEyeTheme.neonAmber);
      canvas.drawCircle(sPos, 12.0, Paint()..color = HawkEyeTheme.neonAmber.withOpacity(0.5)..style = PaintingStyle.stroke..strokeWidth = 2.0);

      // Speedometer pin
      final String spdText = '${shuttlecock.currentSpeedKmh.toStringAsFixed(0)} km/h';
      final textSpan = TextSpan(
        text: spdText,
        style: const TextStyle(
          color: HawkEyeTheme.neonAmber,
          fontSize: 11,
          fontWeight: FontWeight.bold,
        ),
      );
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      )..layout();

      final double calloutX = (sPos.dx + 14).clamp(10.0, originalVideoSize.width - 80);
      final double calloutY = (sPos.dy - 16).clamp(20.0, originalVideoSize.height - 30);
      final Rect calloutRect = Rect.fromLTWH(calloutX - 4, calloutY - 2, textPainter.width + 8, 16);
      
      canvas.drawRect(calloutRect, Paint()..color = Colors.black.withOpacity(0.85));
      canvas.drawRect(calloutRect, Paint()..color = HawkEyeTheme.neonAmber..style = PaintingStyle.stroke..strokeWidth = 1.0);
      textPainter.paint(canvas, Offset(calloutX, calloutY));
    }

    // 5. Draw Landing Spot if detected
    if (rallyStats.landingSpotPx != null) {
      final isOut = rallyStats.refereeDecision == "OUT";
      final impactColor = isOut ? HawkEyeTheme.neonRed : HawkEyeTheme.neonGreen;
      
      canvas.drawCircle(rallyStats.landingSpotPx!, 16.0, Paint()..color = impactColor.withOpacity(0.3));
      canvas.drawCircle(rallyStats.landingSpotPx!, 16.0, Paint()..color = impactColor..style = PaintingStyle.stroke..strokeWidth = 2.0);
      canvas.drawCircle(rallyStats.landingSpotPx!, 4.0, Paint()..color = impactColor);
    }

    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant HawkEyePainter oldDelegate) => true;
}

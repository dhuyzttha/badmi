import 'package:flutter/material.dart';
import '../../../../core/constants/bwf_dimensions.dart';
import '../../../../core/theme/app_theme.dart';
import '../../domain/models/court_model.dart';
import '../../domain/models/player_model.dart';
import '../../domain/models/shuttlecock_model.dart';

class MiniCourtWidget extends StatelessWidget {
  final CourtModel court;
  final List<PlayerModel> players;
  final ShuttlecockModel shuttlecock;
  final double width;
  final double height;

  const MiniCourtWidget({
    Key? key,
    required this.court,
    required this.players,
    required this.shuttlecock,
    this.width = 110,
    this.height = 220,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: const Color(0xE6111827),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: HawkEyeTheme.surfaceElevated, width: 1.5),
        boxShadow: const [
          BoxShadow(color: Colors.black54, blurRadius: 8, offset: Offset(0, 4)),
        ],
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(vertical: 4),
            width: double.infinity,
            alignment: Alignment.center,
            decoration: const BoxDecoration(
              color: Color(0xFF1E2631),
              borderRadius: BorderRadius.vertical(top: Radius.circular(7)),
            ),
            child: const Text(
              '2D MINI-COURT',
              style: TextStyle(
                color: HawkEyeTheme.neonGreen,
                fontSize: 9,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.5,
              ),
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(6.0),
              child: CustomPaint(
                size: Size.infinite,
                painter: _MiniCourtPainter(
                  court: court,
                  players: players,
                  shuttlecock: shuttlecock,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniCourtPainter extends CustomPainter {
  final CourtModel court;
  final List<PlayerModel> players;
  final ShuttlecockModel shuttlecock;

  _MiniCourtPainter({
    required this.court,
    required this.players,
    required this.shuttlecock,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final double courtW = court.width;
    final double courtL = court.length;

    // Background court surface
    final Rect courtRect = Offset.zero & size;
    final Paint surfacePaint = Paint()..color = const Color(0xFF1B6A3E); // Badminton Mat Green
    canvas.drawRect(courtRect, surfacePaint);

    // Boundary border
    final Paint linePaint = Paint()
      ..color = Colors.white
      ..strokeWidth = 1.2
      ..style = PaintingStyle.stroke;
    canvas.drawRect(courtRect, linePaint);

    final double scaleX = size.width / courtW;
    final double scaleY = size.height / courtL;

    // Net line (center)
    final double netY = BwfDimensions.netPosition * scaleY;
    final Paint netPaint = Paint()
      ..color = Colors.white
      ..strokeWidth = 2.0;
    canvas.drawLine(Offset(0, netY), Offset(size.width, netY), netPaint);

    // Short service lines (1.98m from net)
    final double sslFarY = BwfDimensions.shortServiceLineFar * scaleY;
    final double sslNearY = BwfDimensions.shortServiceLineNear * scaleY;
    canvas.drawLine(Offset(0, sslFarY), Offset(size.width, sslFarY), linePaint);
    canvas.drawLine(Offset(0, sslNearY), Offset(size.width, sslNearY), linePaint);

    // Center dividing lines
    final double midX = size.width / 2.0;
    canvas.drawLine(Offset(midX, 0), Offset(midX, sslFarY), linePaint);
    canvas.drawLine(Offset(midX, sslNearY), Offset(midX, size.height), linePaint);

    // Tramlines if doubles mode
    if (court.mode == CourtMode.doubles) {
      final double tramlineX = BwfDimensions.tramlineWidth * scaleX;
      canvas.drawLine(Offset(tramlineX, 0), Offset(tramlineX, size.height), linePaint);
      canvas.drawLine(Offset(size.width - tramlineX, 0), Offset(size.width - tramlineX, size.height), linePaint);
    }

    // Draw Players on 2D Court
    for (final p in players) {
      if (p.footBwf != null) {
        final double px = (p.footBwf!.dx * scaleX).clamp(0.0, size.width);
        final double py = (p.footBwf!.dy * scaleY).clamp(0.0, size.height);
        final Color dotColor = p.id == 1 ? HawkEyeTheme.neonAmber : HawkEyeTheme.neonBlue;

        // Player dot
        canvas.drawCircle(Offset(px, py), 4.5, Paint()..color = dotColor);
        canvas.drawCircle(Offset(px, py), 6.0, Paint()..color = Colors.white..style = PaintingStyle.stroke..strokeWidth = 1.0);
      }
    }

    // Draw Shuttlecock on 2D Court
    if (shuttlecock.currentBwf != null) {
      final double sx = (shuttlecock.currentBwf!.dx * scaleX).clamp(0.0, size.width);
      final double sy = (shuttlecock.currentBwf!.dy * scaleY).clamp(0.0, size.height);

      canvas.drawCircle(Offset(sx, sy), 3.5, Paint()..color = Colors.yellowAccent);
      canvas.drawCircle(Offset(sx, sy), 5.5, Paint()..color = Colors.white.withOpacity(0.8)..style = PaintingStyle.stroke..strokeWidth = 1.0);
    }
  }

  @override
  bool shouldRepaint(covariant _MiniCourtPainter oldDelegate) => true;
}

import 'dart:ui';

enum RallyState { serve, inPlay, pointAwarded, paused }

class RallyStats {
  final RallyState state;
  final int shotCount;
  final double durationSeconds;
  final String refereeDecision; // "IN", "OUT", "FAULT", "PLAY ON"
  final Offset? landingSpotBwf;
  final Offset? landingSpotPx;

  RallyStats({
    this.state = RallyState.inPlay,
    this.shotCount = 0,
    this.durationSeconds = 0.0,
    this.refereeDecision = "PLAY ON",
    this.landingSpotBwf,
    this.landingSpotPx,
  });

  RallyStats copyWith({
    RallyState? state,
    int? shotCount,
    double? durationSeconds,
    String? refereeDecision,
    Offset? landingSpotBwf,
    Offset? landingSpotPx,
  }) {
    return RallyStats(
      state: state ?? this.state,
      shotCount: shotCount ?? this.shotCount,
      durationSeconds: durationSeconds ?? this.durationSeconds,
      refereeDecision: refereeDecision ?? this.refereeDecision,
      landingSpotBwf: landingSpotBwf ?? this.landingSpotBwf,
      landingSpotPx: landingSpotPx ?? this.landingSpotPx,
    );
  }
}

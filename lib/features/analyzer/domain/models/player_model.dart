import 'dart:ui';

class PlayerModel {
  final int id;
  final String name;
  final String side; // "top" or "bottom"
  final Rect? bbox;
  final Offset? footPx;
  final Offset? footBwf; // in meters (X: 0..5.18, Y: 0..13.40)
  final double totalDistanceMeters;
  final double rallyDistanceMeters;
  final List<Offset> historyBwf;

  PlayerModel({
    required this.id,
    required this.name,
    required this.side,
    this.bbox,
    this.footPx,
    this.footBwf,
    this.totalDistanceMeters = 0.0,
    this.rallyDistanceMeters = 0.0,
    this.historyBwf = const [],
  });

  PlayerModel copyWith({
    Rect? bbox,
    Offset? footPx,
    Offset? footBwf,
    double? totalDistanceMeters,
    double? rallyDistanceMeters,
    List<Offset>? historyBwf,
  }) {
    return PlayerModel(
      id: id,
      name: name,
      side: side,
      bbox: bbox ?? this.bbox,
      footPx: footPx ?? this.footPx,
      footBwf: footBwf ?? this.footBwf,
      totalDistanceMeters: totalDistanceMeters ?? this.totalDistanceMeters,
      rallyDistanceMeters: rallyDistanceMeters ?? this.rallyDistanceMeters,
      historyBwf: historyBwf ?? this.historyBwf,
    );
  }
}

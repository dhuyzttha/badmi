import 'dart:ui';
import '../../../../core/constants/bwf_dimensions.dart';
import '../../../../core/math/homography_matrix.dart';

enum CourtMode { singles, doubles }

class CourtModel {
  final CourtMode mode;
  final List<Offset> corners; // [Top-Left, Top-Right, Bottom-Right, Bottom-Left]
  final HomographyMatrix? homography;
  final HomographyMatrix? inverseHomography;

  CourtModel({
    required this.mode,
    required this.corners,
    this.homography,
    this.inverseHomography,
  });

  double get width => mode == CourtMode.singles ? BwfDimensions.widthSingles : BwfDimensions.widthDoubles;
  double get length => BwfDimensions.length;

  factory CourtModel.initial(CourtMode mode) {
    return CourtModel(
      mode: mode,
      corners: const [
        Offset(145, 430),
        Offset(432, 430),
        Offset(560, 765),
        Offset(16, 765),
      ],
    );
  }

  CourtModel copyWithCorners(List<Offset> newCorners) {
    // Recompute homography matrix to standard BWF coordinates
    List<Offset> worldPoints = [
      const Offset(0.0, 0.0),
      Offset(width, 0.0),
      Offset(width, length),
      Offset(0.0, length),
    ];

    HomographyMatrix? h = HomographyMatrix.compute(newCorners, worldPoints);
    HomographyMatrix? hInv = h?.inverse();

    return CourtModel(
      mode: mode,
      corners: newCorners,
      homography: h,
      inverseHomography: hInv,
    );
  }
}

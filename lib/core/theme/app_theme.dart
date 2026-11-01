import 'package:flutter/material.dart';

class HawkEyeTheme {
  static const Color background = Color(0xFF0A0E14);
  static const Color surface = Color(0xFF151B23);
  static const Color surfaceElevated = Color(0xFF1E2631);
  
  static const Color neonGreen = Color(0xFF00FF9D);
  static const Color neonBlue = Color(0xFF00C8FF);
  static const Color neonAmber = Color(0xFFFFC400);
  static const Color neonRed = Color(0xFFFF3366);

  static const Color textPrimary = Color(0xFFF0F6FC);
  static const Color textSecondary = Color(0xFF8B949E);
  static const Color textMuted = Color(0xFF6E7681);

  static ThemeData get darkTheme {
    return ThemeData.dark().copyWith(
      scaffoldBackgroundColor: background,
      primaryColor: neonGreen,
      cardColor: surface,
      colorScheme: const ColorScheme.dark(
        primary: neonGreen,
        secondary: neonBlue,
        surface: surface,
        error: neonRed,
      ),
      sliderTheme: const SliderThemeData(
        activeTrackColor: neonGreen,
        inactiveTrackColor: surfaceElevated,
        thumbColor: neonGreen,
        overlayColor: Color(0x3300FF9D),
        trackHeight: 3.0,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: background,
        elevation: 0,
        centerTitle: false,
      ),
    );
  }
}

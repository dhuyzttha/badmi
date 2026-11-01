import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'core/theme/app_theme.dart';
import 'features/analyzer/presentation/screens/hawkeye_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Lock to portrait or allow landscape orientation
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
    DeviceOrientation.landscapeLeft,
    DeviceOrientation.landscapeRight,
  ]);

  // Immersive edge-to-edge UI
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: HawkEyeTheme.background,
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  runApp(const BadmintonHawkEyeApp());
}

class BadmintonHawkEyeApp extends StatelessWidget {
  const BadmintonHawkEyeApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Badminton Hawk-Eye Pro',
      debugShowCheckedModeBanner: false,
      theme: HawkEyeTheme.darkTheme,
      home: const HawkEyeScreen(),
    );
  }
}

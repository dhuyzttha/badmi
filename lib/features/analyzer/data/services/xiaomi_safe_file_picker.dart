import 'dart:io';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';

/// Specialized Safe File Picker engineered for Xiaomi MIUI & HyperOS.
/// Bypasses manufacturer-specific Scoped Storage and intent permission denials
/// by streaming content into application-specific cacheDir.
class XiaomiSafeFilePicker {
  static const MethodChannel _channel = MethodChannel('com.hawkeye.badminton/file_picker');

  /// Requests appropriate video permission based on Android SDK level
  static Future<bool> requestStoragePermissions() async {
    if (!Platform.isAndroid) return true;

    // Check Android 13+ (API 33+) granular media permission
    final videoStatus = await Permission.videos.status;
    if (videoStatus.isGranted) return true;

    if (await Permission.videos.request().isGranted) {
      return true;
    }

    // Fallback for Android 10-12
    final storageStatus = await Permission.storage.status;
    if (storageStatus.isGranted) return true;

    return await Permission.storage.request().isGranted;
  }

  /// Launches Native ActivityResultContracts.PickVisualMedia or SAF,
  /// streams content safely to context.cacheDir, and returns the absolute POSIX path.
  static Future<String?> pickVideo() async {
    try {
      await requestStoragePermissions();

      final String? cachedFilePath = await _channel.invokeMethod<String>('pickVideoSafe');
      if (cachedFilePath != null && File(cachedFilePath).existsSync()) {
        return cachedFilePath;
      }
      return null;
    } on PlatformException catch (e) {
      // ignore: avoid_print
      print('Safe file picker failed: ${e.message}');
      return null;
    } catch (e) {
      // ignore: avoid_print
      print('Generic file picker error: $e');
      return null;
    }
  }
}

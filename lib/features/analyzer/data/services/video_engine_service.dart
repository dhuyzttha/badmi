import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../../domain/models/court_model.dart';
import '../../domain/models/player_model.dart';
import '../../domain/models/shuttlecock_model.dart';
import '../../domain/models/rally_stats.dart';

class VideoEngineService {
  String serverUrl;

  VideoEngineService({this.serverUrl = "http://10.0.2.2:8000"}); // Default Android Emulator host IP

  /// Uploads video to Computer Vision engine and retrieves processed analysis
  Future<Map<String, dynamic>?> uploadAndAnalyze({
    required File videoFile,
    required CourtMode mode,
    required String player1,
    required String player2,
    double sensitivity = 0.8,
  }) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$serverUrl/api/analyze_video'),
      );

      request.fields['mode'] = mode == CourtMode.singles ? 'singles' : 'doubles';
      request.fields['player1'] = player1;
      request.fields['player2'] = player2;
      request.fields['sensitivity'] = sensitivity.toString();

      request.files.add(await http.MultipartFile.fromPath('file', videoFile.path));

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        // ignore: avoid_print
        print('Server analysis failed with status: ${response.statusCode}');
        return null;
      }
    } catch (e) {
      // ignore: avoid_print
      print('Network exception connecting to CV engine: $e');
      return null;
    }
  }
}

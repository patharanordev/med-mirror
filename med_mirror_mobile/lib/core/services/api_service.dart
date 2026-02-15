import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:image/image.dart'
    as img; // For lightweight processing if needed
import '../../features/chat/models/message.dart';

class ApiService {
  final String segmentationBaseUrl;
  final String agentBaseUrl;
  final http.Client? _client;

  ApiService(
      {required this.segmentationBaseUrl,
      required this.agentBaseUrl,
      http.Client? client})
      : _client = client;

  // --- 1. Segmentation ---
  Future<Map<String, dynamic>> segmentImage(List<int> imageBytes) async {
    try {
      var request = http.MultipartRequest(
          'POST', Uri.parse('$segmentationBaseUrl/segment'));
      request.files.add(
        http.MultipartFile.fromBytes('file', imageBytes, filename: 'frame.jpg'),
      );

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Segmentation failed: ${response.statusCode}');
      }
    } catch (e) {
      print('Segmentation Error: $e');
      rethrow;
    }
  }

  // --- 2. Chat Agent ---
  // Returns a Stream of dynamic (String for text, Map for interrupt)
  Stream<dynamic> sendChat(String text, List<Message> history,
      {required String threadId,
      String? context,
      String? imageUrl,
      String? runId}) async* {
    final client = _client ?? http.Client();
    try {
      final payload = {
        'message': text,
        'history': history.map((m) => m.toJson()).toList(),
        'context': context,
        'image_url': imageUrl,
        if (runId != null) 'run_id': runId,
      };

      print("DEBUG: Sending Payload: $payload");

      // We will assume we talk directly to Agent Service on port 8001
      final directUri = Uri.parse('$agentBaseUrl/chat/$threadId');

      final req = http.Request('POST', directUri);
      req.headers['Content-Type'] = 'application/json';
      req.body = jsonEncode(payload);

      print("DEBUG: Sending chat request to $directUri");
      final response = await client.send(req);
      print("DEBUG: Response headers: ${response.headers}");

      if (response.statusCode != 200) {
        throw Exception('Chat API Error: ${response.statusCode}');
      }

      // Stream handling with buffering
      final stream = response.stream.transform(utf8.decoder);
      String buffer = '';

      await for (final chunk in stream) {
        buffer += chunk;

        // Split by simple newline to handle various SSE formats (e.g. data: ...\n)
        // We keep the last part in buffer if it doesn't end with a newline
        while (buffer.contains('\n')) {
          final splitIndex = buffer.indexOf('\n');
          final line = buffer.substring(0, splitIndex).trim();
          buffer = buffer.substring(splitIndex + 1);

          if (line.startsWith("data: ")) {
            final dataStr = line.substring(6).trim(); // Remove "data: "
            if (dataStr == "[DONE]") return; // End of stream

            if (dataStr.isEmpty) continue;

            print("DEBUG: Line: $dataStr");

            try {
              final json = jsonDecode(dataStr);
              final type = json['type'];
              final content = json['content'];

              print("DEBUG: Type: $type, Content Type: ${content.runtimeType}");

              if (type == 'debug') {
                continue;
              }

              if (type == 'text') {
                if (content is String) {
                  yield content;
                }
              } else if (type == 'interrupt') {
                if (content is Map) {
                  print("DEBUG: Yielding Interrupt Map");
                  yield {
                    'type': 'interrupt',
                    'question': content['question'] ?? "",
                    'run_id': content['run_id']
                  };
                } else if (content is String) {
                  yield content;
                } else {
                  print(
                      "DEBUG: Content is NOT Map or String: ${content.runtimeType} -> $content");
                }
              }
              // Ignore 'task', 'profile_update', 'tool', 'debug' for now
            } catch (e) {
              print("DEBUG: Parse Error: $e");
            }
          }
        }
      }
    } catch (e) {
      print('Chat Error: $e');
      rethrow;
    } finally {
      client.close();
    }
  }

  // --- 3. Speech to Text ---
  Future<String?> transcribeAudio(String filePath) async {
    try {
      var request = http.MultipartRequest(
          'POST', Uri.parse('$agentBaseUrl/stt')); // Direct agent STT

      // Web Support: If path starts with 'blob:', fetch it first
      if (filePath.startsWith('blob:')) {
        final blobResponse = await http.get(Uri.parse(filePath));
        if (blobResponse.statusCode == 200) {
          request.files.add(http.MultipartFile.fromBytes(
              'file', blobResponse.bodyBytes,
              filename: 'voice.m4a' // or .wav or .webm depending on encoder
              ));
        } else {
          print("Failed to fetch blob: ${blobResponse.statusCode}");
          return null;
        }
      } else {
        // Mobile/Desktop: Use file path
        request.files.add(await http.MultipartFile.fromPath('file', filePath));
      }

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['text'];
      }
    } catch (e) {
      print('STT Error: $e');
    }
    return null;
  }

  Future<String?> transcribeAudioBytes(List<int> audioBytes) async {
    try {
      final url = Uri.parse('$agentBaseUrl/stt');
      print("STT: Sending to $url (${audioBytes.length} bytes)");

      var request = http.MultipartRequest('POST', url);
      request.files.add(http.MultipartFile.fromBytes('file', audioBytes,
          filename: 'voice.wav'));

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      print("STT: Status ${response.statusCode}");

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        print("STT: Body ${response.body}");
        return data['text'];
      } else {
        print("STT: Failed Body ${response.body}");
      }
    } catch (e) {
      print('STT Bytes Error: $e');
    }
    return null;
  }
}

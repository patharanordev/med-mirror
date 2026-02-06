import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:image/image.dart' as img; // For lightweight processing if needed
import '../models/message.dart';

class ApiService {
  final String segmentationBaseUrl;
  final String agentBaseUrl;

  ApiService({required this.segmentationBaseUrl, required this.agentBaseUrl});

  // --- 1. Segmentation ---
  Future<Map<String, dynamic>> segmentImage(List<int> imageBytes) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$segmentationBaseUrl/segment'));
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
  // Returns a Stream of text chunks (simulating the streaming response)
  Stream<String> sendChat(String text, List<Message> history, {String? context, String? imageUrl}) async* {
    try {
      final payload = {
        'message': text,
        'history': history.map((m) => m.toJson()).toList(),
        'context': context,
        'image_url': imageUrl,
      };

      final client = http.Client();
      final request = http.Request('POST', Uri.parse('$agentBaseUrl/api/proxy/chat')); // Using proxy path or direct agent? 
      // NOTE: The web client uses /api/proxy which forwards to agent:8001. 
      // If we talk directly to agent:8001, the path is likely /chat or similar.
      // Checking web client: fetch(`${API_AGENT}/chat`) -> proxy -> http://med_mirror_agent:8001/chat
      // So path is likely /chat
      
      // We will assume we talk directly to Agent Service on port 8001
      final directUri = Uri.parse('$agentBaseUrl/chat'); 
      
      final req = http.Request('POST', directUri);
      req.headers['Content-Type'] = 'application/json';
      req.body = jsonEncode(payload);

      final response = await client.send(req);

      if (response.statusCode != 200) {
        throw Exception('Chat API Error: ${response.statusCode}');
      }

      // Stream handling
      final stream = response.stream.transform(utf8.decoder);
      
      // Simple SSE parser logic
      await for (final chunk in stream) {
        // This is a naive parser for the SSE format "data: {...}"
        // In a real app, use a robust SSE client. 
        // For this demo, we'll yield raw text chunks if they contain content.
        
        final lines = chunk.split('\n\n');
        for (final line in lines) {
           if (line.trim().startsWith("data: ")) {
             final dataStr = line.replaceAll("data: ", "").trim();
             if (dataStr == "[DONE]") break;
             try {
               final json = jsonDecode(dataStr);
               if (json['content'] != null) {
                 yield json['content'];
               }
             } catch (_) {}
           }
        }
      }
      client.close();
    } catch (e) {
      print('Chat Error: $e');
      rethrow;
    }
  }

  // --- 3. Speech to Text ---
  Future<String?> transcribeAudio(String filePath) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$agentBaseUrl/stt')); // Direct agent STT
      request.files.add(await http.MultipartFile.fromPath('file', filePath));

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
}

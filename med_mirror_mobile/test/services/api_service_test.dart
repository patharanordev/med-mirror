import 'package:flutter_test/flutter_test.dart';
import 'package:med_mirror_mobile/core/services/api_service.dart';
import 'package:med_mirror_mobile/features/chat/models/message.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';

void main() {
  group('ApiService Tests', () {
    test('sendChat parses split SSE chunks correctly', () async {
      // Create a specific stream with split chunks to test parsing logic
      final stream = Stream<List<int>>.fromIterable([
        utf8.encode('data: {"content": "He"}\n'),
        utf8.encode('data: {"cont'), // Split chunk 1
        utf8.encode('ent": "llo"}\n'), // Split chunk 2
        utf8.encode('data: [DONE]\n'),
      ]);

      final mockClient = MockStreamingClient(stream);

      final api = ApiService(
          segmentationBaseUrl: 'http://test',
          agentBaseUrl: 'http://test',
          client: mockClient);

      final messages = [Message(role: 'user', content: 'Hi')];
      // sendChat uses the client.send() internally
      final outputStream = api.sendChat('Hi', messages, threadId: 't1');

      final output = await outputStream.toList();

      expect(output.join(), equals('Hello'));
    });
  });
}

class MockStreamingClient extends http.BaseClient {
  final Stream<List<int>> stream;
  MockStreamingClient(this.stream);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    return http.StreamedResponse(stream, 200);
  }
}

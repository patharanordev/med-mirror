import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:med_mirror_mobile/core/services/api_service.dart';
import 'package:med_mirror_mobile/features/chat/models/message.dart';

void main() {
  test('ApiService parses interrupt correctly', () async {
    const mockResponse = 'data: {"type": "text", "content": "Hello"}\n\n'
        'data: {"type": "interrupt", "content": {"question": "Check?", "run_id": "123"}}\n\n'
        'data: [DONE]\n\n';

    final client = MockClient((request) async {
      return http.Response(mockResponse, 200);
    });

    final api = ApiService(
        segmentationBaseUrl: 'http://mock',
        agentBaseUrl: 'http://mock',
        client: client);

    final stream = api.sendChat('hi', [], threadId: 't1');
    final events = await stream.toList();

    print("DEBUG: Received events: $events");
    expect(events.length, 2);
    expect(events[0], "Hello");
    expect(events[1], isA<Map>());
    expect(events[1]['question'], "Check?");
    expect(events[1]['run_id'], "123");

    print("Test Passed: Events received: $events");
  });
}

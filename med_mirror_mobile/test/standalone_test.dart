import 'dart:convert';
import 'dart:async';

void main() async {
  final stream = Stream<String>.fromIterable([
    'data: {"type": "text", "content": "Hello"}\n\n',
    'data: {"type": "interrupt", "content": {"question": "Check?", "run_id": "123"}}\n\n',
    'data: [DONE]\n\n'
  ]);

  final parser = StreamParser();
  final events = await parser.parse(stream).toList();

  print("Events: $events");

  if (events.length != 2) throw "Wrong length";
  if (events[0] != "Hello") throw "Wrong text";

  final interrupt = events[1];
  if (interrupt is! Map) throw "Interrupt not a Map";
  if (interrupt['question'] != "Check?") throw "Wrong question";
  if (interrupt['run_id'] != "123") throw "Wrong run_id";

  print("SUCCESS: Logic Verified");
}

class StreamParser {
  Stream<dynamic> parse(Stream<String> input) async* {
    String buffer = '';
    await for (final chunk in input) {
      buffer += chunk;
      while (buffer.contains('\n')) {
        final splitIndex = buffer.indexOf('\n');
        final line = buffer.substring(0, splitIndex).trim();
        buffer = buffer.substring(splitIndex + 1);

        if (line.startsWith("data: ")) {
          final dataStr = line.substring(6).trim();
          if (dataStr == "[DONE]") return;
          if (dataStr.isEmpty) continue;

          try {
            final json = jsonDecode(dataStr);
            final type = json['type'];
            final content = json['content'];

            if (type == 'text') {
              if (content is String) yield content;
            } else if (type == 'interrupt') {
              if (content is Map) {
                yield {
                  'type': 'interrupt',
                  'question': content['question'] ?? "",
                  'run_id': content['run_id']
                };
              } else if (content is String) {
                yield content;
              }
            }
          } catch (e) {
            print("Error: $e");
          }
        }
      }
    }
  }
}

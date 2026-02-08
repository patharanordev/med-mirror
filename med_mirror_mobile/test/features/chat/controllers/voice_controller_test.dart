import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:vad/vad.dart';
import 'package:med_mirror_mobile/features/chat/controllers/voice_controller.dart';
import 'package:med_mirror_mobile/core/services/api_service.dart';

class MockApiService extends Mock implements ApiService {}

class MockVadHandler extends Mock implements VadHandler {}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late VoiceController voiceController;
  late MockApiService mockApiService;
  late MockVadHandler mockVadHandler;

  // StreamControllers to simulate VAD events
  late StreamController<void> speechStartController;
  late StreamController<List<double>> speechEndController;
  late StreamController<String> errorController;

  setUp(() {
    mockApiService = MockApiService();
    mockVadHandler = MockVadHandler();

    speechStartController = StreamController<void>.broadcast();
    speechEndController = StreamController<List<double>>.broadcast();
    errorController = StreamController<String>.broadcast();

    when(() => mockVadHandler.onSpeechStart)
        .thenAnswer((_) => speechStartController.stream);
    when(() => mockVadHandler.onSpeechEnd)
        .thenAnswer((_) => speechEndController.stream);
    when(() => mockVadHandler.onError)
        .thenAnswer((_) => errorController.stream);

    when(() => mockVadHandler.startListening()).thenAnswer((_) async {});
    when(() => mockVadHandler.stopListening()).thenAnswer((_) async {});
    when(() => mockVadHandler.dispose()).thenAnswer((_) async {});

    voiceController =
        VoiceController(mockApiService, vadHandler: mockVadHandler);
  });

  tearDown(() {
    voiceController.dispose();
    speechStartController.close();
    speechEndController.close();
    errorController.close();
  });

  test('Initial state is correct', () {
    expect(voiceController.isListening, isFalse);
    expect(voiceController.isUserSpeaking, isFalse);
    expect(voiceController.isProcessing, isFalse);
  });

  test('Auto Mode toggle starts/stops recording', () async {
    const channel = MethodChannel('flutter.baseflow.com/permissions/methods');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      channel,
      (MethodCall methodCall) async {
        if (methodCall.method == 'requestPermissions') {
          final ListArguments = methodCall.arguments as List;
          final Map<int, int> result = {};
          if (ListArguments.isNotEmpty) {
            for (var perm in ListArguments) {
              result[perm] = 1; // Granted
            }
          }
          return result;
        }
        return null; // For checkPermissionStatus etc
      },
    );

    await voiceController.startRecording();
    verify(() => mockVadHandler.startListening()).called(1);
    expect(voiceController.isListening, isTrue);

    await voiceController.stopRecording();
    verify(() => mockVadHandler.stopListening()).called(1);
    expect(voiceController.isListening, isFalse);
  });

  test('Speech Start updates state', () async {
    voiceController.setTextCallback((_) {}); // Just to set it

    // Simulate speech start
    speechStartController.add(null);
    await Future.delayed(Duration.zero); // Wait for stream listener

    expect(voiceController.isUserSpeaking, isTrue);
  });

  test('Speech End triggers processing and transcription', () async {
    const channel = MethodChannel('flutter.baseflow.com/permissions/methods');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      channel,
      (MethodCall methodCall) async {
        if (methodCall.method == 'requestPermissions') {
          final ListArguments = methodCall.arguments as List;
          final Map<int, int> result = {};
          if (ListArguments.isNotEmpty) {
            for (var perm in ListArguments) {
              result[perm] = 1; // Granted
            }
          }
          return result;
        }
        return null;
      },
    );

    await voiceController.startRecording();

    // Mock API response
    when(() => mockApiService.transcribeAudioBytes(any()))
        .thenAnswer((_) async => "Hello World");

    bool callbackCalled = false;
    voiceController.setTextCallback((text) {
      if (text == "Hello World") callbackCalled = true;
    });

    // Simulate speech end with fake samples
    speechEndController.add([0.1, 0.2, 0.3]);

    // Wait for processing
    await Future.delayed(const Duration(milliseconds: 50));

    verify(() => mockApiService.transcribeAudioBytes(any())).called(1);
    expect(callbackCalled, isTrue);
    expect(voiceController.isUserSpeaking, isFalse);
  });
}

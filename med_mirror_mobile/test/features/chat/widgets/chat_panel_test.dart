import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mocktail/mocktail.dart';
import 'package:med_mirror_mobile/features/chat/widgets/chat_panel.dart';
import 'package:med_mirror_mobile/features/chat/controllers/voice_controller.dart';
import 'package:med_mirror_mobile/core/state/app_state.dart';

class MockVoiceController extends Mock implements VoiceController {}

class MockAppState extends Mock implements AppState {}

void main() {
  late MockVoiceController mockVoiceController;
  late MockAppState mockAppState;

  setUp(() {
    mockVoiceController = MockVoiceController();
    mockAppState = MockAppState();

    // Stub necessary properties
    when(() => mockVoiceController.isUserSpeaking).thenReturn(false);
    when(() => mockVoiceController.isListening).thenReturn(false);
    when(() => mockVoiceController.setTextCallback(any())).thenReturn(null);
    when(() => mockVoiceController.addListener(any())).thenReturn(null);
    when(() => mockVoiceController.removeListener(any())).thenReturn(null);

    when(() => mockAppState.segmentationUrl).thenReturn('http://test.url');
    when(() => mockAppState.agentUrl).thenReturn('http://test.url');
    when(() => mockAppState.addListener(any())).thenReturn(null);
    when(() => mockAppState.removeListener(any())).thenReturn(null);
  });

  Widget createWidgetUnderTest() {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<VoiceController>.value(
            value: mockVoiceController),
        ChangeNotifierProvider<AppState>.value(value: mockAppState),
      ],
      child: const MaterialApp(
        home: Scaffold(
          body: ChatPanel(),
        ),
      ),
    );
  }

  testWidgets('ChatPanel renders input and initial message',
      (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    expect(find.text("MedMirror Agent"), findsNothing); // Just verifying logic
    expect(find.textContaining("Start by analyzing your skin"), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);
  });

  testWidgets('Sending a message adds it to the list',
      (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    final inputFinder = find.byType(TextField);
    await tester.enterText(inputFinder, "Test Message");
    await tester.tap(find.byIcon(Icons.send));

    await tester.pump(); // Start animation
    await tester.pumpAndSettle(); // Finish animation

    expect(find.text("Test Message"), findsOneWidget);
  });
}

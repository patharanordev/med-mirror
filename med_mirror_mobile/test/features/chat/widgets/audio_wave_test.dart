import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:med_mirror_mobile/features/chat/widgets/audio_wave.dart';
import 'package:med_mirror_mobile/features/chat/controllers/voice_controller.dart';

class MockVoiceController extends Mock implements VoiceController {}

void main() {
  late MockVoiceController mockVoiceController;

  setUp(() {
    mockVoiceController = MockVoiceController();
    when(() => mockVoiceController.addListener(any())).thenReturn(null);
    when(() => mockVoiceController.removeListener(any())).thenReturn(null);
    when(() => mockVoiceController.audioLevel).thenReturn(0.5);
  });

  Widget createWidgetUnderTest({required bool isActive}) {
    return ChangeNotifierProvider<VoiceController>.value(
      value: mockVoiceController,
      child: MaterialApp(
        home: Scaffold(
          body: AudioWave(isActive: isActive),
        ),
      ),
    );
  }

  testWidgets('AudioWave builds successfully', (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest(isActive: false));
    expect(find.byType(AudioWave), findsOneWidget);
  });

  testWidgets('AudioWave shows 12 bars', (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest(isActive: true));
    // AudioWave now uses 12 AnimatedContainers
    expect(find.byType(AnimatedContainer), findsNWidgets(12));
  });

  testWidgets('AudioWave handles isActive change', (WidgetTester tester) async {
    await tester.pumpWidget(createWidgetUnderTest(isActive: false));

    await tester.pumpWidget(createWidgetUnderTest(isActive: true));
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.byType(AudioWave), findsOneWidget);
  });
}

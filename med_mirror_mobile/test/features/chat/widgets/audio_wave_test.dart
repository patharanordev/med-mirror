import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:med_mirror_mobile/features/chat/widgets/audio_wave.dart';

void main() {
  testWidgets('AudioWave builds successfully', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: AudioWave(isActive: false),
      ),
    ));

    expect(find.byType(AudioWave), findsOneWidget);
    expect(find.byType(Row), findsOneWidget); // Visual structure
  });

  testWidgets('AudioWave shows 5 bars', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: AudioWave(isActive: false),
      ),
    ));

    // AudioWave uses List.generate(5, ...) creating AnimatedContainer
    expect(find.byType(AnimatedContainer), findsNWidgets(5));
  });

  testWidgets('AudioWave handles isActive change', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: AudioWave(isActive: false),
      ),
    ));

    // Initially height 3 (min)
    // Finding specific heights is hard without keys,
    // but we can verify it pumps without error when switching state.

    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: AudioWave(isActive: true),
      ),
    ));

    // Should start timer and animate
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 100));

    // Verify it's still there
    expect(find.byType(AudioWave), findsOneWidget);
  });
}

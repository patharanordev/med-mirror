import 'dart:math';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../controllers/voice_controller.dart';

/// Audio wave visualization with 12 bars synced to real-time audio level.
class AudioWave extends StatelessWidget {
  final bool isActive;
  static const int barCount = 12;

  const AudioWave({
    super.key,
    required this.isActive,
  });

  @override
  Widget build(BuildContext context) {
    return Consumer<VoiceController>(
      builder: (context, voiceCtrl, child) {
        final level = voiceCtrl.audioLevel; // 0.0 to 1.0

        return AnimatedOpacity(
          duration: const Duration(milliseconds: 200),
          opacity: isActive ? 1.0 : 0.0,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: List.generate(barCount, (index) {
              // Create wave pattern: center bars higher, edge bars lower
              const centerIndex = barCount / 2;
              final distanceFromCenter = (index - centerIndex).abs();
              final waveFactor = 1.0 - (distanceFromCenter / centerIndex) * 0.4;

              // Add some pseudo-randomness based on index for more organic look
              final jitter = sin(index * 0.7) * 0.15;
              final barLevel = (level * waveFactor + jitter).clamp(0.1, 1.0);

              final height = max(6.0, barLevel * 50.0);

              return AnimatedContainer(
                duration: const Duration(milliseconds: 80),
                margin: const EdgeInsets.symmetric(horizontal: 2),
                width: 4,
                height: height,
                decoration: BoxDecoration(
                  color: const Color(0xFF4ADE80),
                  borderRadius: BorderRadius.circular(999),
                  boxShadow: isActive
                      ? [
                          BoxShadow(
                            color: const Color(0xFF4ADE80).withOpacity(0.4),
                            blurRadius: 4,
                            spreadRadius: 1,
                          )
                        ]
                      : [],
                ),
              );
            }),
          ),
        );
      },
    );
  }
}

import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';

class AudioWave extends StatefulWidget {
  final bool isActive;
  final List<double>? audioData;

  const AudioWave({
    super.key,
    required this.isActive,
    this.audioData,
  });

  @override
  State<AudioWave> createState() => _AudioWaveState();
}

class _AudioWaveState extends State<AudioWave> {
  final List<double> _scales = [0.2, 0.5, 1.0, 0.6, 0.3];
  Timer? _timer;
  final Random _random = Random();

  @override
  void initState() {
    super.initState();
    if (widget.isActive) {
      _startAnimation();
    }
  }

  @override
  void didUpdateWidget(AudioWave oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isActive != oldWidget.isActive) {
      if (widget.isActive) {
        _startAnimation();
      } else {
        _stopAnimation();
      }
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _startAnimation() {
    // If we have real audio data, use it. Otherwise simulate.
    if (widget.audioData != null) return;

    _timer = Timer.periodic(const Duration(milliseconds: 100), (_) {
      if (mounted) {
        setState(() {
          for (int i = 0; i < _scales.length; i++) {
            // Random height scaling between 0.1 and 1.0
            _scales[i] = 0.1 + _random.nextDouble() * 0.9;
          }
        });
      }
    });
  }

  void _stopAnimation() {
    _timer?.cancel();
    setState(() {
      // Reset to small bars
      for (int i = 0; i < _scales.length; i++) {
        _scales[i] = 0.1;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    // 5 bars
    return AnimatedOpacity(
      duration: const Duration(milliseconds: 300),
      opacity: widget.isActive ? 1.0 : 0.0,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: List.generate(5, (index) {
          // Calculate height
          // Max height approx 48px
          double height = 6.0;
          if (widget.isActive) {
            height = max(6.0, _scales[index] * 40.0);
          }

          return AnimatedContainer(
            duration: const Duration(milliseconds: 100),
            margin: const EdgeInsets.symmetric(horizontal: 2),
            width: 6,
            height: height,
            decoration: BoxDecoration(
              color: const Color(0xFF4ADE80), // Green-400
              borderRadius: BorderRadius.circular(999),
              boxShadow: widget.isActive
                  ? [
                      BoxShadow(
                        color: const Color(0xFF4ADE80).withOpacity(0.4),
                        blurRadius: 5,
                        spreadRadius: 2,
                      )
                    ]
                  : [],
            ),
          );
        }),
      ),
    );
  }
}

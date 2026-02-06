import 'package:flutter/material.dart';
import '../widgets/camera_overlay_view.dart';
import '../widgets/chat_panel.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  String _currentContext = "";
  double _skinVal = 0;

  void _updateAnalysis(String ctx, double val) {
    // Only update if changed significantly to avoid rebuilds
    if (_skinVal != val) {
      setState(() {
        _currentContext = ctx;
        _skinVal = val;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    // Row layout for iPad (Landscape)
    return Scaffold(
      body: Row(
        children: [
          // Left: Camera Feed (Takes remaining space)
          Expanded(
            child: CameraOverlayView(
              onAnalysisUpdate: _updateAnalysis,
            ),
          ),
          
          // Right: Chat Panel (Fixed width)
          ChatPanel(currentContext: _currentContext),
        ],
      ),
    );
  }
}

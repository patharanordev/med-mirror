import 'package:flutter/material.dart';
import '../widgets/camera_overlay_view.dart';
import '../../chat/widgets/chat_panel.dart';

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
    // Stack layout for Glassmorphism
    // 1. Camera Background
    // 2. Translucent Overlay for Controls and Chat
    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          // 1. Background Camera
          CameraOverlayView(
            onAnalysisUpdate: _updateAnalysis,
          ),
          
          // 2. Top Header (White text over screen)
          Positioned(
            top: 40, 
            left: 20, 
            right: 20,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  "MedMirror EDGE", 
                  style: TextStyle(
                    color: Colors.white, 
                    fontSize: 24, 
                    fontWeight: FontWeight.bold,
                    shadows: [Shadow(blurRadius: 4, color: Colors.black, offset: Offset(0, 2))],
                  )
                ),
                // Status Icons or other header info could go here
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.black54,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: Colors.white24),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.circle, size: 10, color: Colors.greenAccent),
                      SizedBox(width: 8),
                      Text("System Ready", style: TextStyle(color: Colors.white, fontSize: 12)),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // 3. Chat Panel (Bottom Right, Half Height)
          Positioned(
            right: 20,
            bottom: 20,
            width: 400, // Fixed width
            height: MediaQuery.of(context).size.height * 0.5, // Half screen height
            child: ChatPanel(currentContext: _currentContext),
          ),
          
          // 4. Controls (Bottom Left - if needed explicitly, otherwise CameraOverlayView might handle it)
          // For now assuming CameraOverlayView handles its own controls or we can add them here later.
        ],
      ),
    );
  }
}

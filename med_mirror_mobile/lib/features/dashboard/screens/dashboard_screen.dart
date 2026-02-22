import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../chat/controllers/voice_controller.dart';
import '../widgets/camera_overlay_view.dart';
import '../widgets/badge.dart';
import '../../chat/widgets/chat_panel.dart';
import '../../chat/widgets/audio_wave.dart';
import '../../../core/state/app_state.dart';
import 'package:flutter_animate/flutter_animate.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  String _currentContext = "";
  double _skinVal = 0;
  bool _isCameraReady = false; // Initial state false until detected
  final CameraOverlayController _cameraController = CameraOverlayController();
  final GlobalKey<ChatPanelState> _chatPanelKey = GlobalKey<ChatPanelState>();

  // Cached GoogleFonts style — computed once, not per build.
  static final _titleStyle = GoogleFonts.michroma(
    color: Colors.white,
    fontSize: 48,
    fontWeight: FontWeight.w400,
    height: 0.75,
  );

  @override
  void initState() {
    super.initState();
    // Start VAD automatically (using global controller)
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final voiceController = context.read<VoiceController>();
      voiceController.setAutoMode(true);
      voiceController.startRecording();

      // Register callback for voice-to-text, routing to ChatPanel via GlobalKey
      voiceController.setTextCallback((text) {
        print("MainScreen: Voice callback received '$text'");
        _chatPanelKey.currentState?.sendVoiceMessage(text);
      });
    });
  }

  @override
  void dispose() {
    _cameraController.dispose();
    // VoiceController is global, do not dispose here
    super.dispose();
  }

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
    // Cache size once to avoid repeated MediaQuery lookups during layout.
    final size = MediaQuery.of(context).size;
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
            controller: _cameraController,
            onCameraStatusChanged: (bool isReady) {
              // Update UI based on camera availability
              if (mounted && _isCameraReady != isReady) {
                setState(() {
                  _isCameraReady = isReady;
                });
              }
            },
          ),

          // 2. Top Header (White text over screen)
          Positioned(
            top: 30,
            left: 30,
            right: 30,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Text(
                      "MedMirror",
                      style: _titleStyle,
                    ),
                    const SizedBox(width: 8),
                    const AppBadge(text: "EDGE"),
                  ],
                ),

                // Right Side Controls: Camera + Mic
                Row(
                  children: [
                    // Brain Button (Thinking Panel Toggle)
                    Consumer<AppState>(builder: (context, appState, _) {
                      return Container(
                        margin: const EdgeInsets.only(right: 16),
                        decoration: BoxDecoration(
                          color: Colors.black54,
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: appState.isThinkingExpanded
                                ? Colors.cyanAccent
                                : Colors.white24,
                            width: 2,
                          ),
                        ),
                        child: IconButton(
                          icon: Icon(
                            Icons.psychology,
                            color: appState.isThinkingExpanded
                                ? Colors.cyanAccent
                                : Colors.white54,
                          ),
                          onPressed: () => appState.setThinkingExpanded(
                              !appState.isThinkingExpanded),
                          tooltip: "Thinking Process",
                        ),
                      );
                    }),

                    // Camera Button (Moved to top right)
                    Container(
                      decoration: BoxDecoration(
                        color: Colors.black54,
                        borderRadius: BorderRadius.circular(30),
                      ),
                      child: IconButton(
                        icon: Icon(
                            _isCameraReady
                                ? Icons.camera_alt
                                : Icons.no_photography,
                            color:
                                _isCameraReady ? Colors.white : Colors.white38),
                        onPressed: _isCameraReady
                            ? () {
                                // Trigger camera capture in overlay
                                _cameraController.triggerCapture();
                              }
                            : null, // Disable if not ready
                        tooltip: _isCameraReady
                            ? "Analyze Interface"
                            : "Camera Unavailable",
                      ),
                    ),

                    const SizedBox(width: 16),

                    // Mic Status Indicator (Icon Only)
                    Consumer<VoiceController>(builder: (context, vc, _) {
                      return Container(
                        padding: const EdgeInsets.all(10), // Circle-ish padding
                        decoration: BoxDecoration(
                          color: Colors.black54,
                          shape: BoxShape.circle,
                          border: Border.all(
                              color: vc.isListening
                                  ? Colors.greenAccent
                                  : Colors.white24,
                              width: 2),
                        ),
                        child: Icon(vc.isListening ? Icons.mic : Icons.mic_off,
                            size: 20,
                            color: vc.isListening
                                ? Colors.greenAccent
                                : Colors.white54),
                      );
                    }),
                  ],
                ),
              ],
            ),
          ),

          // 3. Thinking Panel (Overlay near header icons, faint text)
          Positioned(
            right: 20,
            top:
                100, // Just below the header (which is at top: 30 + ~50 height)
            width: 400,
            child: Consumer<AppState>(
              builder: (context, appState, _) {
                if (!appState.isThinkingExpanded ||
                    appState.thinkingText.isEmpty) {
                  return const SizedBox.shrink();
                }
                return ConstrainedBox(
                  constraints: BoxConstraints(
                    maxHeight: size.height * 0.2, // Max 20% of screen height
                  ),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors
                          .transparent, // Reverted to transparent as requested
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: SingleChildScrollView(
                      reverse: true, // Auto-scroll to bottom of thinking
                      child: Text(
                        appState.thinkingText,
                        style: const TextStyle(
                          color: Colors.white54,
                          fontSize: 15,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ),
                  ),
                ).animate().fadeIn().slideY(begin: 0.1, end: 0);
              },
            ),
          ),

          // 4. Chat Panel (Bottom Right, Half Height)
          Positioned(
            right: 20,
            bottom: 20,
            width: 400, // Fixed width
            height: size.height * 0.5, // Half screen height
            child:
                ChatPanel(key: _chatPanelKey, currentContext: _currentContext),
          ),

          // 4. Audio Wave Animation (Centered Horizontal, 4/5 Vertical)
          Positioned(
            top: size.height * 0.8, // 4/5 of screen height
            left: 0,
            right: 0,
            child: Center(
              child: Consumer<VoiceController>(
                builder: (context, vc, _) {
                  return AudioWave(
                    isActive: vc.isUserSpeaking, // Only animate on user speech
                  );
                },
              ),
            ),
          ),

          // 4. Controls (Bottom Left - if needed explicitly, otherwise CameraOverlayView might handle it)
          // For now assuming CameraOverlayView handles its own controls or we can add them here later.
        ],
      ),
    );
  }
}

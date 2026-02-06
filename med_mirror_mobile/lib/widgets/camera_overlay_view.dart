import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_state.dart';
import '../services/api_service.dart';

class CameraOverlayView extends StatefulWidget {
  final Function(String, double) onAnalysisUpdate; // Context, Skin%

  const CameraOverlayView({super.key, required this.onAnalysisUpdate});

  @override
  State<CameraOverlayView> createState() => _CameraOverlayViewState();
}

class _CameraOverlayViewState extends State<CameraOverlayView> {
  CameraController? _controller;
  bool _isCameraInitialized = false;
  
  // Segmentation State
  Uint8List? _segmentationOverlay;
  bool _isAutoMode = false;
  bool _isProcessing = false;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    // Prefer front camera for "Mirror" experience
    final frontCamera = cameras.firstWhere(
      (c) => c.lensDirection == CameraLensDirection.front,
      orElse: () => cameras.first,
    );

    _controller = CameraController(
      frontCamera,
      ResolutionPreset.high,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.jpeg,
    );

    await _controller!.initialize();
    if (mounted) {
      setState(() => _isCameraInitialized = true);
    }
  }

  void _toggleAuto(bool value) {
    setState(() => _isAutoMode = value);
    if (value) {
      _startSegmentationLoop();
    } else {
      _timer?.cancel();
    }
  }

  void _startSegmentationLoop() {
    _timer = Timer.periodic(const Duration(seconds: 2), (timer) async {
       if (_isProcessing || !_isCameraInitialized) return;
       await _captureAndAnalyze();
    });
  }

  Future<void> _captureAndAnalyze() async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    
    _isProcessing = true;
    try {
      // NOTE: takePicture can be slow and has shutter sound on some devices.
      // For MVP this is safest. Optimized: startImageStream + NV21 conversion.
      final file = await _controller!.takePicture();
      final bytes = await file.readAsBytes();
      
      final appState = context.read<AppState>();
      final api = ApiService(
          segmentationBaseUrl: appState.segmentationUrl, 
          agentBaseUrl: appState.agentUrl
      );

      final result = await api.segmentImage(bytes);
      
      // result = { skin_percentage: float, image: "data:image/jpeg;base64,..." }
      
      if (mounted) {
         final String base64Image = result['image'];
         // Remove header if present (data:image/jpeg;base64,)
         final cleanBase64 = base64Image.replaceFirst(RegExp(r'data:image\/.*?;base64,'), '');
         
         setState(() {
           _segmentationOverlay = base64Decode(cleanBase64);
         });
         
         final double skinVal = result['skin_percentage'];
         String contextStr = "";
         if (skinVal > 10) {
           contextStr = "Detected $skinVal% skin coverage.";
         }
         widget.onAnalysisUpdate(contextStr, skinVal);
      }
    } catch (e) {
      print("Segmentation loop error: $e");
    } finally {
      _isProcessing = false;
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_isCameraInitialized || _controller == null) {
      return const Center(child: CircularProgressIndicator());
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        // 1. Camera Feed
        CameraPreview(_controller!),
        
        // 2. Segmentation Overlay
        if (_segmentationOverlay != null)
          Opacity(
            opacity: 0.7,
            child: Image.memory(
              _segmentationOverlay!,
              fit: BoxFit.cover,
              gaplessPlayback: true,
            ),
          ),
          
        // 3. Scan Line Effect (CSS-like animation would utilize flutter_animate)
        if (_isAutoMode)
          const Positioned.fill(
             child: IgnorePointer(child: ScanLineEffect()),
          ),

        // 4. Controls (Positioned bottom left usually)
        Positioned(
          bottom: 20,
          left: 20,
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.black54,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              children: [
                Switch(value: _isAutoMode, onChanged: _toggleAuto),
                const SizedBox(width: 8),
                const Text("Auto Segment", style: TextStyle(color: Colors.white)),
                const SizedBox(width: 16),
                IconButton(
                  icon: const Icon(Icons.camera, color: Colors.white),
                  onPressed: _captureAndAnalyze,
                  tooltip: "Manual Analyze",
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

// Simple placeholder for scanline
class ScanLineEffect extends StatefulWidget {
  const ScanLineEffect({super.key});

  @override
  State<ScanLineEffect> createState() => _ScanLineEffectState();
}

class _ScanLineEffectState extends State<ScanLineEffect> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  
  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: const Duration(seconds: 2))..repeat();
  }
  
  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return CustomPaint(
          painter: ScanLinePainter(_controller.value),
        );
      },
    );
  }
}

class ScanLinePainter extends CustomPainter {
  final double progress;
  ScanLinePainter(this.progress);

  @override
  void paint(Canvas canvas, Size size) {
    final y = size.height * progress;
    final paint = Paint()
      ..color = Colors.white.withOpacity(0.5)
      ..strokeWidth = 4
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 10);
      
    canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
  }
  
  @override
  bool shouldRepaint(ScanLinePainter oldDelegate) => oldDelegate.progress != progress;
}

import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:vad/vad.dart';

import '../../../core/services/api_service.dart';
import '../../../core/utils/audio_utils.dart'; // Ensure this matches where you put AudioUtils

class VoiceController extends ChangeNotifier {
  ApiService _apiService;
  late VadHandler _vadHandler;

  bool _isListening = false;
  bool _isUserSpeaking = false;
  bool _isProcessing = false;
  bool _isAutoMode = false;
  double _audioLevel = 0.0; // 0.0 to 1.0 normalized audio level

  bool get isListening => _isListening;
  bool get isUserSpeaking => _isUserSpeaking;
  bool get isProcessing => _isProcessing;
  bool get isAutoMode => _isAutoMode;
  double get audioLevel => _audioLevel;

  VoiceController(this._apiService, {VadHandler? vadHandler}) {
    _initVad(vadHandler);
  }

  // Allow updating the API Service without disposing the controller
  void updateApiService(ApiService newService) {
    _apiService = newService;
  }

  void _initVad(VadHandler? handler) {
    _vadHandler = handler ?? VadHandler.create(isDebug: true);

    _vadHandler.onSpeechStart.listen((_) {
      print("VAD: Speech Start");
      _isUserSpeaking = true;
      notifyListenersSafe();
    });

    _vadHandler.onSpeechEnd.listen((List<double> samples) async {
      if (_isDisposed) return;
      print("VAD: Speech End (Samples: ${samples.length})");
      _isUserSpeaking = false;
      _isProcessing = true;
      notifyListenersSafe();

      // NOTE: We do NOT stop listening immediately here.
      // Attempting to stop/dispose synchronously causing "Bad state" race conditions
      // in the VAD library's internal loop.

      try {
        // Convert to WAV
        final wavBytes = AudioUtils.createWavFile(samples, 16000);
        print("VAD: WAV created (${wavBytes.length} bytes)");

        // Upload
        print("VAD: Sending to API...");
        final text = await _apiService.transcribeAudioBytes(wavBytes);
        print("VAD: API Response: '$text'");

        if (text != null && text.isNotEmpty && !_isDisposed) {
          print("VAD: Invoking Callback");
          _onTextRecognizedCallback?.call(text);
        } else {
          print("VAD: No text recognized or controller disposed");
        }
      } catch (e) {
        print("VAD Processing Error: $e");
      } catch (e) {
        print("VAD Processing Error: $e");
      } finally {
        _isProcessing = false;
        notifyListenersSafe();
      }
    });

    _vadHandler.onError.listen((msg) {
      print("VAD Error: $msg");
      _isListening = false;
      notifyListenersSafe();
    });

    // Listen for real-time audio frame data to update audio level
    _vadHandler.onFrameProcessed.listen((frame) {
      if (_isDisposed || !_isUserSpeaking) return;
      // frame.isSpeech is a probability (double 0.0-1.0), use directly as level
      _audioLevel = frame.isSpeech.clamp(0.0, 1.0);
      notifyListenersSafe();
    });
  }

  // Callback storage for the current session
  Function(String)? _onTextRecognizedCallback;

  void setTextCallback(Function(String) callback) {
    _onTextRecognizedCallback = callback;
  }

  bool _isDisposed = false;

  @override
  void dispose() {
    _isDisposed = true;
    try {
      // Best effort to stop internal loops before disposing streams
      _vadHandler.stopListening();
    } catch (_) {}

    try {
      _vadHandler.dispose();
    } catch (e) {
      print("Error disposing VAD handler: $e");
    }
    super.dispose();
  }

  void setAutoMode(bool enabled) {
    _isAutoMode = enabled;
    if (enabled && !_isListening && !_isProcessing) {
      startRecording();
    }
    notifyListenersSafe();
  }

  Future<void> toggleRecording() async {
    if (_isListening) {
      // Manual Stop
      _isAutoMode = false;
      await stopRecording();
    } else {
      // Manual Start
      _isAutoMode = true;
      await startRecording();
    }
  }

  bool _isInitializing = false;

  Future<void> startRecording() async {
    if (_isDisposed || _isListening || _isInitializing) return;

    _isInitializing = true;
    notifyListenersSafe();

    try {
      if (await Permission.microphone.request().isGranted) {
        try {
          await _vadHandler.startListening(
              positiveSpeechThreshold: 0.7,
              negativeSpeechThreshold: 0.4,
              minSpeechFrames: 5,
              model: 'v5', // V5 model for better accuracy
              baseAssetPath: 'assets/models/vad/',
              onnxWASMBasePath: 'assets/models/vad/');
          _isListening = true;
          print("VAD: Started Listening");
        } catch (e) {
          print("Error starting VAD: $e");
          _isListening = false;
        }
      }
    } finally {
      _isInitializing = false;
      notifyListenersSafe();
    }
  }

  Future<void> stopRecording() async {
    if (!_isListening) return;
    try {
      await _vadHandler.stopListening();
      _isListening = false;
      _isUserSpeaking = false;
      print("VAD: Stopped Listening");
    } catch (e) {
      print("Error stopping VAD: $e");
    } finally {
      notifyListenersSafe();
    }
  }

  void notifyListenersSafe() {
    if (!_isDisposed) {
      notifyListeners();
    }
  }
}

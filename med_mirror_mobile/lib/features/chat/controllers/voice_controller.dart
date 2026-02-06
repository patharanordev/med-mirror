import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:vad/vad.dart';

import '../../../core/services/api_service.dart';
import '../../../core/utils/audio_utils.dart'; // Ensure this matches where you put AudioUtils

class VoiceController extends ChangeNotifier {
  final ApiService _apiService;
  late final VadHandler _vadHandler;
  
  bool _isListening = false;
  bool _isUserSpeaking = false;
  bool _isProcessing = false;
  bool _isAutoMode = false;

  bool get isListening => _isListening;
  bool get isUserSpeaking => _isUserSpeaking;
  bool get isProcessing => _isProcessing;
  bool get isAutoMode => _isAutoMode;

  VoiceController(this._apiService) {
    _initVad();
  }

  void _initVad() {
    _vadHandler = VadHandler.create(isDebug: false);

    _vadHandler.onSpeechStart.listen((_) {
      print("VAD: Speech Start");
      _isUserSpeaking = true;
      notifyListeners();
    });

    _vadHandler.onSpeechEnd.listen((List<double> samples) async {
       print("VAD: Speech End (Samples: ${samples.length})");
       _isUserSpeaking = false;
       notifyListeners();

       // Stop listening to prevent overlapping inputs
       await _vadHandler.stopListening();
       _isListening = false;
       _isProcessing = true;
       notifyListeners();

       try {
         // Convert to WAV
         final wavBytes = AudioUtils.createWavFile(samples, 16000);
         
         // Upload
         final text = await _apiService.transcribeAudioBytes(wavBytes);
         if (text != null && text.isNotEmpty) {
            _onTextRecognizedCallback?.call(text);
         }
       } catch (e) {
         print("VAD Processing Error: $e");
       } finally {
         _isProcessing = false;
         notifyListeners();
       }
    });

    _vadHandler.onError.listen((msg) {
      print("VAD Error: $msg");
      _isListening = false;
      notifyListeners();
    });
  }

  // Callback storage for the current session
  Function(String)? _onTextRecognizedCallback;

  @override
  void dispose() {
    _vadHandler.dispose();
    super.dispose();
  }

  void setAutoMode(bool enabled) {
    _isAutoMode = enabled;
    notifyListeners();
  }

  Future<void> toggleRecording({required Function(String) onTextRecognized}) async {
    if (_isListening) {
      // Manual Stop
      _isAutoMode = false;
      await stopRecording(onTextRecognized: onTextRecognized);
    } else {
      // Manual Start
      _isAutoMode = true;
      await startRecording(onTextRecognized: onTextRecognized);
    }
  }

  Future<void> startRecording({required Function(String) onTextRecognized}) async {
    if (await Permission.microphone.request().isGranted) {
      _onTextRecognizedCallback = onTextRecognized;
      try {
        await _vadHandler.startListening();
        _isListening = true;
        notifyListeners();
        print("VAD: Started Listening");
      } catch (e) {
        print("Error starting VAD: $e");
        _isListening = false;
        notifyListeners();
      }
    }
  }

  Future<void> stopRecording({required Function(String) onTextRecognized}) async {
    if (!_isListening) return;
    try {
      await _vadHandler.stopListening();
      _isListening = false;
      _isUserSpeaking = false;
      notifyListeners();
      print("VAD: Stopped Listening");
    } catch (e) {
       print("Error stopping VAD: $e");
    }
  }
}

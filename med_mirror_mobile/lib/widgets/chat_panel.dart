import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import '../models/message.dart';
import '../providers/app_state.dart';
import '../services/api_service.dart';

class ChatPanel extends StatefulWidget {
  final String? currentContext; // Skin analysis context
  const ChatPanel({super.key, this.currentContext});

  @override
  State<ChatPanel> createState() => _ChatPanelState();
}

class _ChatPanelState extends State<ChatPanel> {
  final List<Message> _messages = [
    Message(role: 'assistant', content: 'Hello. I am MedMirror Agent.\\nStart by analyzing your skin.'),
  ];
  final TextEditingController _inputCtrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();
  bool _isTyping = false;
  
  // Voice State
  final AudioRecorder _audioRecorder = AudioRecorder();
  bool _isListening = false;
  bool _isUserSpeaking = false; 
  Timer? _amplitudeTimer;
  DateTime? _lastSpeechTime;

  @override
  void dispose() {
    _audioRecorder.dispose();
    _amplitudeTimer?.cancel();
    _inputCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _sendMessage({String? manualText}) async {
    final text = manualText ?? _inputCtrl.text.trim();
    if (text.isEmpty) return;

    if (manualText == null) _inputCtrl.clear();

    setState(() {
      _messages.add(Message(role: 'user', content: text));
      _isTyping = true;
    });
    _scrollToBottom();

    try {
      final appState = context.read<AppState>();
      final api = ApiService(
          segmentationBaseUrl: appState.segmentationUrl, 
          agentBaseUrl: appState.agentUrl
      );
      
      setState(() {
        _messages.add(Message(role: 'assistant', content: ''));
      });
      
      String fullContent = "";
      final stream = api.sendChat(text, _messages, context: widget.currentContext);
      
      await for (final chunk in stream) {
         fullContent += chunk;
         if (mounted) {
           setState(() {
              _messages.last = Message(role: 'assistant', content: fullContent);
           });
           _scrollToBottom();
         }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages.add(Message(role: 'assistant', content: '[Error: $e]'));
        });
      }
    } finally {
      if (mounted) setState(() => _isTyping = false);
    }
  }

  // --- Voice Logic ---
  Future<void> _toggleRecording() async {
    if (_isListening) {
      await _stopRecording();
    } else {
      await _startRecording();
    }
  }

  Future<void> _startRecording() async {
    if (await Permission.microphone.request().isGranted) {
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/temp_voice.m4a'; // m4a is standard for iOS
      
      await _audioRecorder.start(
        const RecordConfig(encoder: AudioEncoder.aacLc), 
        path: path
      );
      
      setState(() => _isListening = true);
      _startAmplitudeCheck();
    }
  }

  Future<void> _stopRecording() async {
    _amplitudeTimer?.cancel();
    final path = await _audioRecorder.stop();
    setState(() {
      _isListening = false;
      _isUserSpeaking = false;
    });

    if (path != null) {
      // Transcribe
      final appState = context.read<AppState>();
      final api = ApiService(segmentationBaseUrl: appState.segmentationUrl, agentBaseUrl: appState.agentUrl);
      
      // Note: Backend expects wav typically, but Whisper handles m4a/mp3 usually.
      // If backend STRICTLY needs wav, we might need ffmpeg or pcm recording.
      // Assuming backend uses OpenAI Whisper API or FasterWhisper which supports many formats.
      // BUT: The client/src/hooks/useVAD.ts sends 'audio/wav'.
      // If default backend (FastAPI) handles generic uploads, m4a should work.
      
      final text = await api.transcribeAudio(path);
      if (text != null && text.isNotEmpty) {
        _sendMessage(manualText: text);
      }
    }
  }

  void _startAmplitudeCheck() {
    _amplitudeTimer = Timer.periodic(const Duration(milliseconds: 100), (timer) async {
       final amp = await _audioRecorder.getAmplitude();
       final currentVol = amp.current; // dB
       
       // Threshold logic (simple)
       if (currentVol > -30) { // Speaking
          setState(() => _isUserSpeaking = true);
          _lastSpeechTime = DateTime.now();
       } else {
          // Silence
          // If silence > 1.5s AND we were speaking before inside this session -> Stop
          if (_isUserSpeaking && _lastSpeechTime != null) {
             final silenceDuration = DateTime.now().difference(_lastSpeechTime!);
             if (silenceDuration.inMilliseconds > 1500) {
                // Formatting: Stop
                timer.cancel(); // Prevent multiple triggers
                _stopRecording();
             }
          }
       }
    });
  }


  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 400, // Fixed width for iPad sidebar
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.1),
        border: const Border(left: BorderSide(color: Colors.white12)),
      ),
      child: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(
               border: Border(bottom: BorderSide(color: Colors.white10))
            ),
            child: Row(
              children: [
                 const CircleAvatar(backgroundColor: Colors.blueAccent, child: Text("AI")),
                 const SizedBox(width: 12),
                 const Column(
                   crossAxisAlignment: CrossAxisAlignment.start,
                   children: [
                     Text("MedMirror Assistant", style: TextStyle(fontWeight: FontWeight.bold)),
                     Text("Online • Gemma", style: TextStyle(fontSize: 12, color: Colors.white54)),
                   ],
                 ),
              ],
            ),
          ),
          
          // Chat List
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final msg = _messages[index];
                final isUser = msg.role == 'user';
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    constraints: const BoxConstraints(maxWidth: 280),
                    decoration: BoxDecoration(
                      color: isUser ? Colors.white24 : Colors.blue.withOpacity(0.2),
                      borderRadius: BorderRadius.only(
                        topLeft: const Radius.circular(16),
                        topRight: const Radius.circular(16),
                        bottomLeft: isUser ? const Radius.circular(16) : Radius.zero,
                        bottomRight: !isUser ? const Radius.circular(16) : Radius.zero,
                      ),
                      border: Border.all(color: Colors.white10),
                    ),
                    child: Text(msg.content.isEmpty && index == _messages.length-1 ? "Thinking..." : msg.content),
                  ).animate().fadeIn().slideY(begin: 0.2, end: 0),
                );
              },
            ),
          ),
          
          // Transcription indicator
          if (_isListening)
             Container(
               padding: const EdgeInsets.all(8),
               color: Colors.red.withOpacity(0.1),
               child: Row(
                 mainAxisAlignment: MainAxisAlignment.center,
                 children: [
                    const Icon(Icons.mic, color: Colors.redAccent, size: 16),
                    const SizedBox(width: 8),
                    Text(_isUserSpeaking ? "Listening..." : "Waiting...", style: const TextStyle(color: Colors.redAccent)),
                 ],
               ),
             ),

          // Input
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
               border: Border(top: BorderSide(color: Colors.white10))
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _inputCtrl,
                    decoration: InputDecoration(
                       hintText: "Type a message...",
                       hintStyle: const TextStyle(color: Colors.white30),
                       fillColor: Colors.white10,
                       filled: true,
                       border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                       contentPadding: const EdgeInsets.symmetric(horizontal: 20),
                    ),
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 8),
                // Mic Button
                GestureDetector(
                  onTap: _toggleRecording,
                  child: Container(
                    width: 48, height: 48,
                    decoration: BoxDecoration(
                      color: _isListening ? Colors.redAccent : Colors.white10,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(_isListening ? Icons.stop : Icons.mic, color: Colors.white),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: () => _sendMessage(),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

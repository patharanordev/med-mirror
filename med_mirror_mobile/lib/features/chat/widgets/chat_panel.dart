import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import '../models/message.dart';
import '../../../core/state/app_state.dart';
import '../../../core/services/api_service.dart';
import '../controllers/voice_controller.dart';

class ChatPanel extends StatefulWidget {
  final String? currentContext; // Skin analysis context
  const ChatPanel({super.key, this.currentContext});

  @override
  State<ChatPanel> createState() => _ChatPanelState();
}

class _ChatPanelState extends State<ChatPanel> {
  final List<Message> _messages = [
    Message(role: 'assistant', content: 'Hello. I am MedMirror Agent.\nStart by analyzing your skin.'),
  ];
  final TextEditingController _inputCtrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();
  
  bool _isTyping = false;
  late VoiceController _voiceController;

  @override
  void initState() {
    super.initState();
    // Initialize Voice Controller
    final appState = context.read<AppState>();
    final api = ApiService(segmentationBaseUrl: appState.segmentationUrl, agentBaseUrl: appState.agentUrl);
    _voiceController = VoiceController(api);
    _voiceController.addListener(_onVoiceStateChange);

    // Auto-Start VAD on access
    WidgetsBinding.instance.addPostFrameCallback((_) {
      // Small delay to ensure permissions/UI are ready
      // Note: Browsers might block audio start without user interaction.
      Future.delayed(const Duration(milliseconds: 500), () {
        if (mounted) {
           _voiceController.setAutoMode(true);
           _voiceController.startRecording(
             onTextRecognized: (text) => _sendMessage(manualText: text)
           );
        }
      });
    });
  }

  void _onVoiceStateChange() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _voiceController.removeListener(_onVoiceStateChange);
    _voiceController.dispose();
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
      if (mounted) {
        setState(() => _isTyping = false);
        // Automatic VAD: Restart listening if in Auto Mode
        if (_voiceController.isAutoMode) {
           _voiceController.startRecording(
             onTextRecognized: (text) => _sendMessage(manualText: text)
           );
        }
      }
    }
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
      // Width/Height controlled by parent Positioned
      decoration: BoxDecoration(
        color: Colors.transparent, // Fully transparent as requested ("back ground transparent")
        // Or if they wanted a very subtle gradient, we could add it, but "transparent" usually means see-through.
        // Let's add a gradient to ensure text readability without blocking view.
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Colors.transparent, Colors.black.withOpacity(0.6)],
        ),
      ),
      child: Column(
        children: [
          // Removed redundant Header since we have a top bar now, 
          // OR we keep a minimal "AI Assistant" label?
          // User said "white text over on the top of the screen", which we did in Dashboard.
          // Let's keep a small indicator here for the chat agent status.
          
          // Chat List
          
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
          
          // Transcription indicator removed for smoother UI
          // Status is indicated by the Mic button color.

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
                  onTap: () => _voiceController.toggleRecording(
                    onTextRecognized: (text) => _sendMessage(manualText: text)
                  ),
                  child: Container(
                    width: 48, height: 48,
                    decoration: BoxDecoration(
                      color: _voiceController.isListening ? Colors.redAccent : Colors.white10,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(_voiceController.isListening ? Icons.stop : Icons.mic, color: Colors.white),
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

import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/message.dart';
import '../../../core/state/app_state.dart';
import '../../../core/services/api_service.dart';
import 'package:uuid/uuid.dart';

class ChatPanel extends StatefulWidget {
  final String? currentContext; // Skin analysis context
  const ChatPanel({super.key, this.currentContext});

  @override
  State<ChatPanel> createState() => ChatPanelState();
}

class ChatPanelState extends State<ChatPanel> {
  final List<Message> _messages = [
    Message(
        role: 'assistant',
        content: 'Hello. I am MedMirror Agent.\nStart by analyzing your skin.'),
  ];
  final TextEditingController _inputCtrl = TextEditingController();
  final ScrollController _scrollCtrl = ScrollController();

  bool _isTyping = false;

  // Persist threadId for the session
  final String _threadId = const Uuid().v4();
  String? _currentRunId;

  @override
  void initState() {
    super.initState();
    // Callback registration moved to MainScreen to avoid stale references
  }

  /// Public method for MainScreen to send messages via GlobalKey
  void sendVoiceMessage(String text) {
    print("ChatPanel: sendVoiceMessage called with '$text'. Mounted: $mounted");
    if (mounted && text.isNotEmpty) {
      _sendMessage(manualText: text);
    }
  }

  @override
  void dispose() {
    // We don't own VoiceController anymore, so don't dispose it.
    // Ideally we should unregister callback, but for now it's fine as Screen disposes it.
    _inputCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  void _sendMessage({String? manualText}) async {
    final text = manualText ?? _inputCtrl.text.trim();
    if (text.isEmpty) return;

    print("ChatPanel: _sendMessage called with '$text'");

    if (manualText == null) _inputCtrl.clear();

    setState(() {
      _messages.add(Message(role: 'user', content: text));
      _isTyping = true;
    });
    print("ChatPanel: Added user message to list");
    _scrollToBottom();

    try {
      // Use Provider to get ApiService (allows mocking in tests)
      // If not provided, fall back to creating one (for backward compatibility if needed,
      // but better to rely on Provider)
      ApiService api;
      try {
        api = context.read<ApiService>();
      } catch (_) {
        // Fallback for MainScreen where it might not be provided explicitly yet,
        // though we should provide it in main.dart
        final appState = context.read<AppState>();
        api = ApiService(
            segmentationBaseUrl: appState.segmentationUrl,
            agentBaseUrl: appState.agentUrl);
      }

      setState(() {
        _messages.add(Message(role: 'assistant', content: ''));
      });

      String fullContent = "";
      // Pass _currentRunId to resume from interrupt if one exists
      print("ChatPanel: Sending message with runId: $_currentRunId");
      final stream = api.sendChat(text, _messages,
          threadId: _threadId,
          context: widget.currentContext,
          runId: _currentRunId);

      // Reset runId after use, assuming new turn clears previous interrupt state?
      // Actually, if we are answering an interrupt, we send the ID.
      // If we are starting new chat, ID is null.
      // Agent handles validation.
      _currentRunId = null;

      await for (final chunk in stream) {
        if (chunk is String) {
          fullContent += chunk;

          if (mounted) {
            setState(() {
              _messages.last = Message(role: 'assistant', content: fullContent);
            });
            _scrollToBottom();
          }
        } else if (chunk is Map) {
          if (chunk['type'] == 'interrupt') {
            final question = chunk['question'] ?? "";
            _currentRunId = chunk['run_id']; // Store new runId for NEXT answer

            // // Create a NEW message bubble for the interrupt/question
            // if (mounted) {
            //   setState(() {
            //     // If the explanation was empty, this might replace it visually if we reused the same index,
            //     // but we want a distinct new bubble.
            //     _messages.add(Message(role: 'assistant', content: ""));
            //   });
            // }

            // fullContent = question;

            if (mounted) {
              setState(() {
                _messages.last = Message(role: 'assistant', content: question);
              });
              _scrollToBottom();
            }
            fullContent = "";
            print("ChatPanel: Received Interrupt with runId: $_currentRunId");
          }
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
        // Auto-restart handled by VoiceController now
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
        color: Colors
            .transparent, // Fully transparent as requested ("back ground transparent")
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
                  alignment:
                      isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                    constraints: const BoxConstraints(maxWidth: 280),
                    decoration: BoxDecoration(
                      color: isUser
                          ? Colors.white24
                          : Colors.blue.withOpacity(0.2),
                      borderRadius: BorderRadius.only(
                        topLeft: const Radius.circular(16),
                        topRight: const Radius.circular(16),
                        bottomLeft:
                            isUser ? const Radius.circular(16) : Radius.zero,
                        bottomRight:
                            !isUser ? const Radius.circular(16) : Radius.zero,
                      ),
                      border: Border.all(color: Colors.white10),
                    ),
                    child: Text(
                      msg.content.isEmpty && index == _messages.length - 1
                          ? "Thinking..."
                          : msg.content,
                      style: const TextStyle(fontSize: 18),
                    ),
                  ).animate().fadeIn().slideY(begin: 0.2, end: 0),
                );
              },
            ),
          ),

          // Input
          Container(
            padding: const EdgeInsets.all(16),
            decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: Colors.white10))),
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
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide.none),
                      contentPadding:
                          const EdgeInsets.symmetric(horizontal: 20),
                    ),
                    onSubmitted: (_) => _sendMessage(),
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

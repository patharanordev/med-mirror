import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/message.dart';
import '../models/search_result_item.dart';
import '../widgets/search_result_carousel.dart';
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
          final chunkType = chunk['type'];

          if (chunkType == 'interrupt') {
            final question = chunk['question'] ?? "";
            _currentRunId = chunk['run_id']; // Store new runId for NEXT answer

            if (mounted) {
              setState(() {
                _messages.last = Message(role: 'assistant', content: question);
              });
              _scrollToBottom();
            }
            fullContent = "";
            print("ChatPanel: Received Interrupt with runId: $_currentRunId");
          } else if (chunkType == 'search_result') {
            final rawItems = chunk['items'] as List? ?? [];
            final items = rawItems
                .whereType<Map<String, dynamic>>()
                .map(SearchResultItem.fromJson)
                .toList();
            if (mounted && items.isNotEmpty) {
              _showSearchResults(items);
            }
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

  /// Shows the search result carousel as a centered overlay dialog.
  /// Uses showDialog so the carousel manages its own overlay layer —
  /// no setState needed in ChatPanel, preventing a full chat list rebuild.
  void _showSearchResults(List<SearchResultItem> items) {
    showDialog<void>(
      context: context,
      barrierColor: const Color(0x80000000), // 50% black barrier
      builder: (_) => SearchResultCarousel(items: items),
    );
  }

  // Pre-computed colors — avoids allocating new Color/LinearGradient objects each build.
  static const _gradientEnd = Color(0x99000000); // black 60% opacity
  static const _gradientDecoration = BoxDecoration(
    gradient: LinearGradient(
      begin: Alignment.topCenter,
      end: Alignment.bottomCenter,
      colors: [Colors.transparent, _gradientEnd],
    ),
  );

  @override
  Widget build(BuildContext context) {
    return Container(
      // Width/Height controlled by parent Positioned
      decoration: _gradientDecoration,
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
                          : const Color(0x330000FF), // blue ~20% opacity
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

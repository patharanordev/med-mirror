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

      // Holds an interrupt received mid-stream;
      // flushed as a new bubble after streaming completes.
      Map<String, dynamic>? pendingInterrupt;

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
            _currentRunId = chunk['run_id'];
            // Buffer the interrupt — do NOT touch the message list yet.
            pendingInterrupt = {'question': question};
            print("ChatPanel: Buffered interrupt (runId: $_currentRunId)");
          } else if (chunkType == 'search_result') {
            final rawItems = chunk['content'] as List? ?? [];
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
      // Stream done — finalize streaming bubble then flush any pending interrupt
      if (mounted && pendingInterrupt != null) {
        setState(() {
          // Lock in whatever explain text was streamed
          if (fullContent.isNotEmpty) {
            _messages.last = Message(role: 'assistant', content: fullContent);
          }
          // Append interrupt question as a separate bubble
          _messages.add(
            Message(
                role: 'assistant',
                content: pendingInterrupt!['question'] as String),
          );
        });
        _scrollToBottom();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages.add(Message(role: 'assistant', content: '[Error: $e]'));
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          // Clean up empty placeholder bubble if the turn produced no visible content
          // (e.g. ask_treatment → END with no text streamed)
          if (_messages.isNotEmpty &&
              _messages.last.role == 'assistant' &&
              _messages.last.content.isEmpty) {
            _messages.removeLast();
          }
          _isTyping = false;
        });
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
    final appState = context.read<AppState>();
    showDialog<void>(
      context: context,
      barrierColor: const Color(0x80000000), // 50% black barrier
      builder: (_) => SearchResultCarousel(
        items: items,
        agentBaseUrl: appState.agentUrl,
      ),
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
                final isLast = index == _messages.length - 1;
                final isUser = msg.role == 'user';

                // Skip empty bubbles that aren't the active streaming placeholder
                if (msg.content.isEmpty && !isLast) {
                  return const SizedBox.shrink();
                }

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
                          ? const Color.fromARGB(30, 255, 255, 255)
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
                      msg.content.isEmpty && isLast
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
                // 🧪 Mock search result trigger — simulates agent `search_result` stream chunk
                Tooltip(
                  message: 'Test: Show mock product recommendations',
                  child: IconButton(
                    key: const ValueKey('mock_search_trigger'),
                    icon: const Text('🧪', style: TextStyle(fontSize: 18)),
                    onPressed: () {
                      // Mirrors the exact payload shape from the agent stream:
                      // { "type": "search_result", "items": [...] }
                      // Each item matches SearchResultItem.fromJson fields.
                      final mockItems = [
                        SearchResultItem.fromJson({
                          'product_image':
                              'https://www.watsons.co.th/images/eye-relief-cream.jpg',
                          'description':
                              'ครีมช่วยลดอาการตาบวมและสีเข้มรอบตา ใช้ได้ดีสำหรับผู้ที่นั่งทำงานหน้าจอเป็นเวลานาน',
                          'price': '250 บาท',
                          'ref':
                              'https://www.watsons.co.th/product/eye-relief-cream'
                        }),
                        SearchResultItem.fromJson({
                          'product_image':
                              'https://www.sephora.co.th/images/dark-circle-corrector.jpg',
                          'description':
                              'ครีมปรับสีและลดอาการตาบวม ช่วยให้ผิวรอบตาสดใสขึ้น',
                          'price': '320 บาท',
                          'ref':
                              'https://www.sephora.co.th/product/dark-circle-corrector'
                        }),
                        SearchResultItem.fromJson({
                          'product_image':
                              'https://www.boots.co.th/images/eye-gel.jpg',
                          'description':
                              'ครีมเย็นช่วยลดอาการบวมและร้อนรอบตา ใช้ได้ดีหลังทำงานหน้าจอ',
                          'price': '180 บาท',
                          'ref': 'https://www.boots.co.th/product/eye-gel'
                        }),
                      ];
                      _showSearchResults(mockItems);
                    },
                  ),
                ),
                const SizedBox(width: 4),
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

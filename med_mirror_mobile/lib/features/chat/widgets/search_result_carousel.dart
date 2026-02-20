import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../models/search_result_item.dart';

/// A centered carousel popup dialog that displays Tavily search results.
///
/// Performance notes:
/// - Wrapped in [RepaintBoundary] to isolate its GPU layer.
/// - Uses [PageView.builder] for lazy card construction.
/// - [AnimationController] with [FadeTransition] — no per-frame setState.
/// - Static styles are `const` or `static final` to prevent per-build allocation.
class SearchResultCarousel extends StatefulWidget {
  final List<SearchResultItem> items;

  const SearchResultCarousel({super.key, required this.items});

  @override
  State<SearchResultCarousel> createState() => _SearchResultCarouselState();
}

class _SearchResultCarouselState extends State<SearchResultCarousel>
    with SingleTickerProviderStateMixin {
  late final AnimationController _fadeController;
  late final Animation<double> _fadeAnimation;
  final PageController _pageController = PageController();
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    )..forward();
    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    );
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return RepaintBoundary(
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: Center(
          child: Material(
            color: Colors.transparent,
            child: Container(
              width: size.width * 0.75,
              height: size.height * 0.7,
              decoration: BoxDecoration(
                color: const Color(0xE6121212), // ~90% opaque dark
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: const Color(0x33FFFFFF)),
              ),
              child: Column(
                children: [
                  // ── Header ──────────────────────────────────────────────
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 16, 8, 0),
                    child: Row(
                      children: [
                        const Text(
                          '🛍️ Product Recommendations',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const Spacer(),
                        // Close button — top right
                        IconButton(
                          key: const ValueKey('carousel_close'),
                          icon: const Icon(Icons.close, color: Colors.white70),
                          onPressed: () => Navigator.of(context).pop(),
                          tooltip: 'Close',
                        ),
                      ],
                    ),
                  ),

                  // ── Cards ────────────────────────────────────────────────
                  Expanded(
                    child: PageView.builder(
                      controller: _pageController,
                      itemCount: widget.items.length,
                      onPageChanged: (page) {
                        setState(() => _currentPage = page);
                      },
                      itemBuilder: (context, index) {
                        return _SearchCard(item: widget.items[index]);
                      },
                    ),
                  ),

                  // ── Page Indicator ───────────────────────────────────────
                  if (widget.items.length > 1)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: List.generate(widget.items.length, (index) {
                          final isActive = index == _currentPage;
                          return AnimatedContainer(
                            duration: const Duration(milliseconds: 200),
                            margin: const EdgeInsets.symmetric(horizontal: 4),
                            width: isActive ? 20 : 8,
                            height: 8,
                            decoration: BoxDecoration(
                              color: isActive
                                  ? Colors.cyanAccent
                                  : const Color(0x66FFFFFF),
                              borderRadius: BorderRadius.circular(4),
                            ),
                          );
                        }),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// A single result card — extracted to its own [StatelessWidget]
/// to avoid rebuilding the card when the page indicator re-renders.
class _SearchCard extends StatelessWidget {
  final SearchResultItem item;

  const _SearchCard({required this.item});

  static const _titleStyle = TextStyle(
    color: Colors.white,
    fontSize: 17,
    fontWeight: FontWeight.w600,
    height: 1.3,
  );

  static const _urlStyle = TextStyle(
    color: Colors.cyanAccent,
    fontSize: 13,
  );

  static const _contentStyle = TextStyle(
    color: Color(0xCCFFFFFF), // ~80% white
    fontSize: 14,
    height: 1.5,
  );

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Score badge
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: const Color(0x3300E5FF),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'Score: ${(item.score * 100).toStringAsFixed(0)}%',
              style: const TextStyle(color: Colors.cyanAccent, fontSize: 11),
            ),
          ),
          const SizedBox(height: 8),
          // Title
          Text(item.title,
              style: _titleStyle, maxLines: 2, overflow: TextOverflow.ellipsis),
          const SizedBox(height: 4),
          // URL
          Text(item.url,
              style: _urlStyle, maxLines: 1, overflow: TextOverflow.ellipsis),
          const SizedBox(height: 12),
          // Content — scrollable
          Expanded(
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              child: Text(item.content, style: _contentStyle),
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: const Duration(milliseconds: 250)).slideY(
          begin: 0.05,
          end: 0,
          duration: const Duration(milliseconds: 250),
        );
  }
}

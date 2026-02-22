/// Presentation layer — Search Result Carousel popup.
///
/// Performance notes:
/// - [RepaintBoundary] isolates the overlay GPU layer.
/// - [PageView.builder] lazily constructs cards.
/// - Static text styles are `static const` to avoid per-build allocations.
/// - [Image.network] with [cacheWidth] limits GPU texture memory.
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/search_result_item.dart';

/// Scale [base] font size proportionally to the screen's shortest side.
double _sp(double base, Size size) =>
    base * (size.shortestSide / 360).clamp(0.75, 1.8);

// ---------------------------------------------------------------------------
// Carousel root
// ---------------------------------------------------------------------------
class SearchResultCarousel extends StatefulWidget {
  final List<SearchResultItem> items;
  final String agentBaseUrl;

  const SearchResultCarousel({
    super.key,
    required this.items,
    required this.agentBaseUrl,
  });

  @override
  State<SearchResultCarousel> createState() => _SearchResultCarouselState();
}

String _proxiedUrl(String originalUrl, String baseUrl) {
  if (originalUrl.isEmpty) return '';
  // Avoid double-proxying
  if (originalUrl.contains('/proxy-image?url=')) return originalUrl;
  return '$baseUrl/proxy-image?url=${Uri.encodeComponent(originalUrl)}';
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
    final size = MediaQuery.sizeOf(context);

    return RepaintBoundary(
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: Center(
          child: Material(
            color: Colors.transparent,
            child: Container(
              width: size.width / 3,
              height: size.height * 0.72,
              decoration: BoxDecoration(
                color: Colors.black,
                borderRadius: BorderRadius.circular(20),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x66000000),
                    blurRadius: 32,
                    spreadRadius: 4,
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(19),
                child: Column(
                  children: [
                    _CarouselHeader(
                      currentPage: _currentPage,
                      totalPages: widget.items.length,
                    ),
                    Expanded(
                      child: PageView.builder(
                        controller: _pageController,
                        itemCount: widget.items.length,
                        onPageChanged: (page) =>
                            setState(() => _currentPage = page),
                        itemBuilder: (context, index) {
                          return _SearchCard(
                            item: widget.items[index],
                            baseUrl: widget.agentBaseUrl,
                          );
                        },
                      ),
                    ),
                    if (widget.items.length > 1)
                      _PageIndicator(
                        count: widget.items.length,
                        currentPage: _currentPage,
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------
class _CarouselHeader extends StatelessWidget {
  final int currentPage;
  final int totalPages;

  const _CarouselHeader({
    required this.currentPage,
    required this.totalPages,
  });

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 14, 8, 0),
      child: Row(
        children: [
          Text(
            'Product Recommendations',
            style: GoogleFonts.notoSansThai(
              color: Colors.white,
              fontSize: _sp(12, size),
              fontWeight: FontWeight.w600,
            ),
          ),
          const Spacer(),
          Text(
            '${currentPage + 1} / $totalPages',
            style: TextStyle(color: Colors.white38, fontSize: _sp(10, size)),
          ),
          IconButton(
            key: const ValueKey('carousel_close'),
            icon: const Icon(Icons.close, color: Colors.white70),
            onPressed: () => Navigator.of(context).pop(),
            tooltip: 'Close',
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Page indicator
// ---------------------------------------------------------------------------
class _PageIndicator extends StatelessWidget {
  final int count;
  final int currentPage;

  const _PageIndicator({required this.count, required this.currentPage});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(count, (index) {
          final isActive = index == currentPage;
          return AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            margin: const EdgeInsets.symmetric(horizontal: 4),
            width: isActive ? 20 : 8,
            height: 8,
            decoration: BoxDecoration(
              color: isActive ? Colors.cyanAccent : const Color(0x66FFFFFF),
              borderRadius: BorderRadius.circular(4),
            ),
          );
        }),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Card — Product Layout
// ---------------------------------------------------------------------------
class _SearchCard extends StatelessWidget {
  final SearchResultItem item;
  final String baseUrl;

  const _SearchCard({required this.item, required this.baseUrl});

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);

    final priceStyle = GoogleFonts.notoSansThai(
      color: Colors.cyanAccent,
      fontSize: _sp(13, size),
      fontWeight: FontWeight.bold,
    );
    final refStyle = GoogleFonts.notoSansThai(
      color: Colors.white38,
      fontSize: _sp(9, size),
      decoration: TextDecoration.underline,
    );
    final mdStyleSheet = MarkdownStyleSheet(
      p: GoogleFonts.notoSansThai(
        color: const Color(0xCCFFFFFF),
        fontSize: _sp(11, size),
        height: 1.5,
      ),
      strong: GoogleFonts.notoSansThai(
        color: Colors.white,
        fontWeight: FontWeight.w700,
        fontSize: _sp(11, size),
      ),
    );

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Zone 1: Product Image (45%) ──────────────────────────────────
          Flexible(
            flex: 45,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: item.productImage.isNotEmpty
                  ? Image.network(
                      _proxiedUrl(item.productImage, baseUrl),
                      width: double.infinity,
                      fit: BoxFit.cover,
                      cacheWidth: 800,
                      loadingBuilder: (context, child, loadingProgress) {
                        if (loadingProgress == null) return child;
                        return _buildPlaceholder();
                      },
                      errorBuilder: (_, __, ___) => _buildPlaceholder(),
                    )
                  : _buildPlaceholder(),
            ),
          ),

          const SizedBox(height: 12),

          // Price + View Details Row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(item.price, style: priceStyle),
              if (item.ref.isNotEmpty) Text('Tap to view', style: refStyle),
            ],
          ),

          const SizedBox(height: 10),

          // ── Zone 2: Description (55%) ────────────────────────────────────
          Flexible(
            flex: 55,
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: const Color(0x0DFFFFFF),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Markdown(
                data: item.description,
                styleSheet: mdStyleSheet,
                physics: const BouncingScrollPhysics(),
                padding: const EdgeInsets.all(12),
              ),
            ),
          ),
        ],
      ),
    )
        .animate()
        .fadeIn(duration: 250.ms)
        .slideY(begin: 0.04, end: 0, duration: 250.ms);
  }

  Widget _buildPlaceholder() {
    return Container(
      width: double.infinity,
      decoration: const BoxDecoration(
        color: Color(0x1AFFFFFF),
      ),
      child: const Center(
        child:
            Icon(Icons.shopping_bag_outlined, color: Colors.white30, size: 36),
      ),
    );
  }
}

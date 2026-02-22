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
import 'package:http/http.dart' as http;

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
            '🛍️ Product Recommendations',
            style: TextStyle(
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
class _SearchCard extends StatefulWidget {
  final SearchResultItem item;
  final String baseUrl;

  const _SearchCard({required this.item, required this.baseUrl});

  @override
  State<_SearchCard> createState() => _SearchCardState();
}

class _SearchCardState extends State<_SearchCard> {
  String? _resolvedImageUrl;
  bool _isLoadingFallback = false;
  bool _hasFailedCompletely = false;

  @override
  void initState() {
    super.initState();
    _initImage();
  }

  void _initImage() {
    if (widget.item.productImage.isNotEmpty) {
      _resolvedImageUrl = widget.item.productImage;
    } else {
      _fetchFallbackImage();
    }
  }

  Future<void> _fetchFallbackImage() async {
    if (widget.item.ref.isEmpty) {
      if (mounted) setState(() => _hasFailedCompletely = true);
      return;
    }

    if (widget.item.ref.endsWith('.jpg') ||
        widget.item.ref.endsWith('.png') ||
        widget.item.ref.endsWith('.jpeg')) {
      if (mounted) {
        setState(() {
          _resolvedImageUrl = widget.item.ref;
          _isLoadingFallback = false;
        });
      }
      return;
    }

    if (mounted) setState(() => _isLoadingFallback = true);

    try {
      final uri = Uri.parse(widget.item.ref);

      // 5-second timeout to prevent stalling the UI
      final response = await http.get(uri).timeout(
            const Duration(seconds: 5),
            onTimeout: () => http.Response('Error', 408),
          );

      if (response.statusCode == 200) {
        final html = response.body;

        var match = RegExp(r'<meta[^>]*property=["' +
                    "'" +
                    r']og:image["' +
                    "'" +
                    r'][^>]*content=["' +
                    "'" +
                    r']([^"' "'" ']+)')
                .firstMatch(html) ??
            RegExp(r'<meta[^>]*content=["' +
                    "'" +
                    r']([^"' "'" ']+)[^>]*property=["' +
                    "'" +
                    r']og:image')
                .firstMatch(html) ??
            RegExp(r'<meta[^>]*name=["' +
                    "'" +
                    r']twitter:image["' +
                    "'" +
                    r'][^>]*content=["' +
                    "'" +
                    r']([^"' "'" ']+)')
                .firstMatch(html);

        if (match != null && match.groupCount >= 1) {
          final imageUrl = match.group(1);
          if (imageUrl != null && imageUrl.isNotEmpty) {
            String finalUrl = imageUrl;
            if (imageUrl.startsWith('/')) {
              final uri = Uri.parse(widget.item.ref);
              finalUrl = '${uri.scheme}://${uri.host}$imageUrl';
            }

            if (mounted) {
              setState(() {
                _resolvedImageUrl = finalUrl;
                _isLoadingFallback = false;
              });
            }
            return;
          }
        }
      }
    } catch (e) {
      print("Fallback extract error: $e");
    }

    if (mounted) {
      setState(() {
        _hasFailedCompletely = true;
        _isLoadingFallback = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);

    final priceStyle = TextStyle(
      color: Colors.cyanAccent,
      fontSize: _sp(13, size),
      fontWeight: FontWeight.bold,
    );
    final refStyle = TextStyle(
      color: Colors.white38,
      fontSize: _sp(9, size),
      decoration: TextDecoration.underline,
    );
    final mdStyleSheet = MarkdownStyleSheet(
      p: TextStyle(
        color: const Color(0xCCFFFFFF),
        fontSize: _sp(11, size),
        height: 1.5,
      ),
      strong: TextStyle(
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
              child: _hasFailedCompletely
                  ? _buildPlaceholder()
                  : _isLoadingFallback
                      ? _buildLoadingState()
                      : _resolvedImageUrl != null
                          ? Image.network(
                              _proxiedUrl(_resolvedImageUrl!, widget.baseUrl),
                              width: double.infinity,
                              height: double.infinity,
                              fit: BoxFit.cover,
                              cacheWidth: 800,
                              errorBuilder: (_, __, ___) {
                                if (_resolvedImageUrl ==
                                        widget.item.productImage &&
                                    !_isLoadingFallback &&
                                    !_hasFailedCompletely) {
                                  WidgetsBinding.instance
                                      .addPostFrameCallback((_) {
                                    _fetchFallbackImage();
                                  });
                                  return _buildLoadingState();
                                }
                                return _buildPlaceholder();
                              },
                            )
                          : _buildPlaceholder(),
            ),
          ),

          const SizedBox(height: 12),

          // Product Name
          if (widget.item.productName.isNotEmpty) ...[
            Text(
              widget.item.productName,
              style: TextStyle(
                color: Colors.white,
                fontSize: _sp(13, size),
                fontWeight: FontWeight.bold,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
          ],

          // Price + View Details Row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(widget.item.price, style: priceStyle),
              if (widget.item.ref.isNotEmpty)
                Text('Tap to view', style: refStyle),
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
                data: widget.item.description,
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
      height: double.infinity,
      decoration: const BoxDecoration(
        color: Color(0x1AFFFFFF),
      ),
      child: const Center(
        child:
            Icon(Icons.shopping_bag_outlined, color: Colors.white30, size: 36),
      ),
    );
  }

  Widget _buildLoadingState() {
    return Container(
      width: double.infinity,
      height: double.infinity,
      color: const Color(0x1AFFFFFF),
      child: const Center(
        child: SizedBox(
          width: 24,
          height: 24,
          child:
              CircularProgressIndicator(strokeWidth: 2, color: Colors.white30),
        ),
      ),
    );
  }
}

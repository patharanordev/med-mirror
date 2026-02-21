/// Presentation layer — Search Result Carousel popup.
///
/// Performance notes:
/// - [RepaintBoundary] isolates the overlay GPU layer.
/// - [PageView.builder] lazily constructs cards.
/// - OG image fetch is driven by [SearchCardViewModel] (ChangeNotifier),
///   so only the image zone repaints on state change — not the whole card.
/// - [OgImageRepository] holds an in-memory cache; swiping back is instant.
/// - Static text styles are `static const` to avoid per-build allocations.
/// - [Image.network] with [cacheWidth] limits GPU texture memory.
library;

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:provider/provider.dart';

import '../data/og_image_service.dart';
import '../domain/og_image_repository.dart';
import '../models/search_result_item.dart';
import '../presentation/search_card_view_model.dart';

// ---------------------------------------------------------------------------
// Single shared repository — one per carousel instance (lives for carousel
// lifetime). Holds the in-memory og:image cache.
// ---------------------------------------------------------------------------
OgImageRepository _buildRepository() =>
    OgImageRepository(service: const OgImageService());

/// Scale [base] font size proportionally to the screen's shortest side.
/// Reference device: 360 logical pixels (typical compact Android phone).
/// Clamped to [0.75 × base … 1.8 × base] to avoid extreme sizes.
double _sp(double base, Size size) =>
    base * (size.shortestSide / 360).clamp(0.75, 1.8);

// ---------------------------------------------------------------------------
// Carousel root
// ---------------------------------------------------------------------------
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

  // One repository shared across all cards in this carousel session.
  late final OgImageRepository _repository;

  @override
  void initState() {
    super.initState();
    _repository = _buildRepository();
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
                // Pure black background
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
                    // ── Header ─────────────────────────────────────────────
                    _CarouselHeader(
                      currentPage: _currentPage,
                      totalPages: widget.items.length,
                    ),

                    // ── Cards ──────────────────────────────────────────────
                    Expanded(
                      child: PageView.builder(
                        controller: _pageController,
                        itemCount: widget.items.length,
                        onPageChanged: (page) =>
                            setState(() => _currentPage = page),
                        itemBuilder: (context, index) {
                          return ChangeNotifierProvider(
                            // Fresh ViewModel per card slot, but repository
                            // cache prevents duplicate network requests.
                            create: (_) => SearchCardViewModel(
                              repository: _repository,
                            ),
                            child: _SearchCard(item: widget.items[index]),
                          );
                        },
                      ),
                    ),

                    // ── Page indicator ─────────────────────────────────────
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
// Header — extracted to avoid rebuilding when page changes
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
// Card — 2-zone layout
// Top  (40%): OG image
// Bottom (60%): Markdown content
// ---------------------------------------------------------------------------
class _SearchCard extends StatefulWidget {
  final SearchResultItem item;

  const _SearchCard({required this.item});

  @override
  State<_SearchCard> createState() => _SearchCardState();
}

class _SearchCardState extends State<_SearchCard> {
  @override
  void initState() {
    super.initState();
    // Kick off image fetch after first frame so PageView layout is stable.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        context.read<SearchCardViewModel>().loadOgImage(widget.item.url);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);

    // ── Responsive styles (scale with screen shortest side) ─────────────────
    final titleStyle = TextStyle(
      color: Colors.white,
      fontSize: _sp(12, size),
      fontWeight: FontWeight.w600,
      height: 1.3,
    );
    final urlStyle = TextStyle(
      color: Colors.cyanAccent,
      fontSize: _sp(9, size),
    );
    final mdStyleSheet = MarkdownStyleSheet(
      p: TextStyle(
        color: const Color(0xCCFFFFFF),
        fontSize: _sp(11, size),
        height: 1.55,
      ),
      strong: TextStyle(
        color: Colors.white,
        fontWeight: FontWeight.w700,
        fontSize: _sp(11, size),
      ),
      h1: TextStyle(
          color: Colors.white,
          fontSize: _sp(14, size),
          fontWeight: FontWeight.bold),
      h2: TextStyle(
          color: Colors.white,
          fontSize: _sp(12, size),
          fontWeight: FontWeight.bold),
      h3: TextStyle(
          color: const Color(0xCCFFFFFF),
          fontSize: _sp(11, size),
          fontWeight: FontWeight.w600),
      listBullet: TextStyle(color: Colors.cyanAccent, fontSize: _sp(11, size)),
      blockquoteDecoration: const BoxDecoration(
        color: Color(0x1AFFFFFF),
        borderRadius: BorderRadius.all(Radius.circular(4)),
      ),
    );

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Zone 1: OG Image (40%) ────────────────────────────────────────
          Flexible(
            flex: 4,
            child: RepaintBoundary(
              child: _OgImageZone(item: widget.item),
            ),
          ),

          const SizedBox(height: 10),

          // Title + URL
          Text(
            widget.item.title,
            style: titleStyle,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 2),
          Text(
            widget.item.url,
            style: urlStyle,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),

          const SizedBox(height: 8),

          // ── Zone 2: Markdown content (60%) ────────────────────────────────
          Flexible(
            flex: 6,
            child: _ContentZone(
              content: widget.item.content,
              mdStyleSheet: mdStyleSheet,
            ),
          ),
        ],
      ),
    )
        .animate()
        .fadeIn(duration: 250.ms)
        .slideY(begin: 0.04, end: 0, duration: 250.ms);
  }
}

// ---------------------------------------------------------------------------
// OG Image Zone — listens to ViewModel, repaints only this zone
// ---------------------------------------------------------------------------
class _OgImageZone extends StatelessWidget {
  final SearchResultItem item;

  const _OgImageZone({required this.item});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<SearchCardViewModel>();

    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: switch (vm.status) {
        OgImageStatus.loading => _buildPlaceholder(isLoading: true),
        OgImageStatus.loaded => Image.network(
            vm.imageUrl!,
            width: double.infinity,
            fit: BoxFit.cover,
            // Limit GPU texture footprint — max 800px wide
            cacheWidth: 800,
            errorBuilder: (_, __, ___) => _buildPlaceholder(isLoading: false),
          ),
        OgImageStatus.error => _buildPlaceholder(isLoading: false),
      },
    );
  }

  Widget _buildPlaceholder({required bool isLoading}) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: const Color(0x1AFFFFFF),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Center(
        child: isLoading
            ? const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white38,
                ),
              )
            : const Icon(Icons.image_not_supported_outlined,
                color: Colors.white30, size: 36),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Content Zone — Markdown-rendered, scrollable
// ---------------------------------------------------------------------------
class _ContentZone extends StatelessWidget {
  final String content;
  final MarkdownStyleSheet mdStyleSheet;

  const _ContentZone({required this.content, required this.mdStyleSheet});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0x0DFFFFFF), // Very subtle white tint separator
        borderRadius: BorderRadius.circular(10),
      ),
      child: Markdown(
        data: content,
        styleSheet: mdStyleSheet,
        physics: const BouncingScrollPhysics(),
        padding: const EdgeInsets.all(12),
        shrinkWrap: false,
      ),
    );
  }
}

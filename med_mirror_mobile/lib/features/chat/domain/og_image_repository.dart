/// Domain layer — single source of truth for OG images.
///
/// Responsibilities:
/// - In-memory LRU-like cache keyed on URL to prevent duplicate network calls.
/// - Propagates null on failure (no throws — UI handles gracefully).
library;

import '../data/og_image_service.dart';

class OgImageRepository {
  OgImageRepository({OgImageService? service})
      : _service = service ?? const OgImageService();

  final OgImageService _service;
  // Simple in-memory cache: URL → og:image URL (or null = "known missing")
  final Map<String, String?> _cache = {};

  /// Returns cached og:image or fetches it once.
  Future<String?> getOgImage(String url) async {
    if (_cache.containsKey(url)) return _cache[url];
    final result = await _service.fetchOgImageUrl(url);
    _cache[url] = result;
    return result;
  }
}

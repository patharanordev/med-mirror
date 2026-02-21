/// Data layer — raw HTTP fetch of Open Graph metadata for a URL.
///
/// Responsibilities:
/// - Parse `og:image` from an HTML `<head>`.
/// - Return null if not found or on network error.
/// - Stateless; no caching (caching lives in the Repository).
library;

import 'package:metadata_fetch/metadata_fetch.dart';

class OgImageService {
  const OgImageService();

  /// Returns the `og:image` URL for [url], or `null` if unavailable.
  Future<String?> fetchOgImageUrl(String url) async {
    try {
      final data = await MetadataFetch.extract(url);
      return data?.image;
    } catch (_) {
      return null;
    }
  }
}

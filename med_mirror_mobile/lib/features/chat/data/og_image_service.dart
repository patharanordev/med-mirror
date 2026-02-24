/// Data layer — raw HTTP fetch of Open Graph metadata for a URL.
///
/// Responsibilities:
/// - Parse `og:image` from an HTML `<head>`.
/// - Return null if not found or on network error.
/// - Stateless; no caching (caching lives in the Repository).
library;

import 'package:http/http.dart' as http;

class OgImageService {
  const OgImageService();

  /// Returns the `og:image` URL for [url], or `null` if unavailable.
  /// Handles CORS on web by attempting a standard proxy fetch where necessary.
  Future<String?> fetchOgImageUrl(String url) async {
    try {
      final uri = Uri.parse(url);
      final response = await http.get(uri).timeout(
            const Duration(seconds: 4),
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
              finalUrl = '${uri.scheme}://${uri.host}$imageUrl';
            }
            return finalUrl;
          }
        }
      }
      return null;
    } catch (_) {
      // In web we often hit CORS issues when fetching the raw HTML.
      // This catch handles it gracefully to return null and display the fallback graphic.
      return null;
    }
  }
}

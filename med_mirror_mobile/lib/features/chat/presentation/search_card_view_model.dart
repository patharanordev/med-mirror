/// Presentation layer — ViewModel for a single search result card.
///
/// Responsibilities:
/// - Holds OG image fetch state (loading / loaded / error).
/// - One instance per card; disposed when PageView recycles the card.
/// - Uses the Repository so repeated swipes hit the in-memory cache.
library;

import 'package:flutter/foundation.dart';
import '../domain/og_image_repository.dart';

enum OgImageStatus { loading, loaded, error }

class SearchCardViewModel extends ChangeNotifier {
  SearchCardViewModel({required OgImageRepository repository})
      : _repository = repository;

  final OgImageRepository _repository;

  OgImageStatus _status = OgImageStatus.loading;
  String? _imageUrl;

  OgImageStatus get status => _status;
  String? get imageUrl => _imageUrl;

  Future<void> loadOgImage(String url) async {
    _status = OgImageStatus.loading;
    notifyListeners();

    final result = await _repository.getOgImage(url);

    if (result != null && result.isNotEmpty) {
      _imageUrl = result;
      _status = OgImageStatus.loaded;
    } else {
      _status = OgImageStatus.error;
    }
    notifyListeners();
  }
}

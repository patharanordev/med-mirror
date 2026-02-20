/// Immutable data class representing a single Tavily search result.
class SearchResultItem {
  final String title;
  final String url;
  final String content;
  final double score;

  const SearchResultItem({
    required this.title,
    required this.url,
    required this.content,
    required this.score,
  });

  factory SearchResultItem.fromJson(Map<String, dynamic> json) {
    return SearchResultItem(
      title: (json['title'] as String?) ?? '',
      url: (json['url'] as String?) ?? '',
      content: (json['content'] as String?) ?? '',
      score: ((json['score'] as num?) ?? 0).toDouble(),
    );
  }
}

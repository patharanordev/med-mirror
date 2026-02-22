class SearchResultItem {
  final String productName;
  final String productImage;
  final String description;
  final String price;
  final String ref;

  const SearchResultItem({
    required this.productName,
    required this.productImage,
    required this.description,
    required this.price,
    required this.ref,
  });

  factory SearchResultItem.fromJson(Map<String, dynamic> json) {
    return SearchResultItem(
      productName: (json['product_name'] as String?) ?? '',
      productImage: (json['product_image'] as String?) ?? '',
      description: (json['description'] as String?) ?? '',
      price: (json['price'] as String?) ?? '',
      ref: (json['ref'] as String?) ?? '',
    );
  }
}

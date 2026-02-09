import 'package:flutter/material.dart';

class AppBadge extends StatelessWidget {
  final String text;
  final Color? backgroundColor;
  final Color? textColor;
  final EdgeInsetsGeometry? padding;

  const AppBadge({
    super.key,
    required this.text,
    this.backgroundColor,
    this.textColor,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding ?? const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: backgroundColor ?? Colors.cyanAccent.withOpacity(0.2),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: (backgroundColor ?? Colors.cyanAccent).withOpacity(0.5),
          width: 1,
        ),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: textColor ?? Colors.cyanAccent,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

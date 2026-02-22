import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppState extends ChangeNotifier {
  String? _hostIp;
  bool _isConfigLoaded = false;
  String _thinkingText = "";
  bool _isThinkingExpanded = false;

  // Getters
  String? get hostIp => _hostIp;
  bool get isConfigLoaded => _isConfigLoaded;
  String get thinkingText => _thinkingText;
  bool get isThinkingExpanded => _isThinkingExpanded;

  // API URLs
  String get segmentationUrl => 'http://$_hostIp:8000';
  String get agentUrl => 'http://$_hostIp:8001';

  void updateThinking(String text, {bool? expanded}) {
    _thinkingText += text;
    if (expanded != null) {
      _isThinkingExpanded = expanded;
    }
    notifyListeners();
  }

  void setThinkingExpanded(bool expanded) {
    _isThinkingExpanded = expanded;
    notifyListeners();
  }

  void clearThinking() {
    _thinkingText = "";
    _isThinkingExpanded = false;
    notifyListeners();
  }

  Future<void> loadConfig() async {
    final prefs = await SharedPreferences.getInstance();
    _hostIp = prefs.getString('host_ip');
    _isConfigLoaded = true;
    notifyListeners();
  }

  void forceReady() {
    _isConfigLoaded = true;
    notifyListeners();
  }

  Future<void> setHostIp(String ip) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('host_ip', ip);
    _hostIp = ip;
    notifyListeners();
  }
}

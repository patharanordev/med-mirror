import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppState extends ChangeNotifier {
  String? _hostIp;
  bool _isConfigLoaded = false;
  
  // Getters
  String? get hostIp => _hostIp;
  bool get isConfigLoaded => _isConfigLoaded;
  
  // API URLs
  String get segmentationUrl => 'http://$_hostIp:8000';
  String get agentUrl => 'http://$_hostIp:8001';

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

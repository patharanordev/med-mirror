import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:med_mirror_mobile/core/state/app_state.dart';

void main() {
  group('AppState Tests', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('Initial properties are null/false', () {
      final appState = AppState();
      expect(appState.hostIp, isNull);
      expect(appState.isConfigLoaded, isFalse);
    });

    test('loadConfig loads IP from SharedPreferences', () async {
      SharedPreferences.setMockInitialValues({'host_ip': '192.168.1.100'});
      final appState = AppState();

      await appState.loadConfig();

      expect(appState.hostIp, '192.168.1.100');
      expect(appState.isConfigLoaded, isTrue);
      expect(appState.segmentationUrl, 'http://192.168.1.100:8000');
      expect(appState.agentUrl, 'http://192.168.1.100:8001');
    });

    test('setHostIp updates IP and SharedPreferences', () async {
      final appState = AppState();
      await appState.setHostIp('10.0.0.5');

      expect(appState.hostIp, '10.0.0.5');

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('host_ip'), '10.0.0.5');
    });

    test('forceReady sets isConfigLoaded to true', () {
      final appState = AppState();
      appState.forceReady();
      expect(appState.isConfigLoaded, isTrue);
    });
  });
}

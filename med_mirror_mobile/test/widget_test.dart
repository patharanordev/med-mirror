import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:camera_platform_interface/camera_platform_interface.dart';

import 'package:plugin_platform_interface/plugin_platform_interface.dart';
import 'package:med_mirror_mobile/main.dart';
import 'package:med_mirror_mobile/core/state/app_state.dart';
import 'package:med_mirror_mobile/features/chat/controllers/voice_controller.dart';
import 'package:med_mirror_mobile/features/settings/screens/config_screen.dart';
import 'package:med_mirror_mobile/features/dashboard/screens/dashboard_screen.dart';
import 'package:med_mirror_mobile/core/services/api_service.dart';

// Mocks
class MockVoiceController extends Mock implements VoiceController {}

class MockCameraPlatform extends Mock
    with MockPlatformInterfaceMixin
    implements CameraPlatform {}

class MockApiService extends Mock implements ApiService {}

void main() {
  late AppState appState;
  late MockVoiceController mockVoiceController;
  late MockCameraPlatform mockCameraPlatform;

  setUp(() {
    // Set a larger screen size for testing (iPad-like)
    final TestWidgetsFlutterBinding binding =
        TestWidgetsFlutterBinding.ensureInitialized();
    binding.window.physicalSizeTestValue = const Size(1024, 768);
    binding.window.devicePixelRatioTestValue = 1.0;

    SharedPreferences.setMockInitialValues({});

    appState = AppState(); // Use real AppState
    mockVoiceController = MockVoiceController();
    mockCameraPlatform = MockCameraPlatform();

    // Mock Camera Platform
    CameraPlatform.instance = mockCameraPlatform;
    when(() => mockCameraPlatform.availableCameras())
        .thenAnswer((_) async => []);
    when(() => mockCameraPlatform.onDeviceOrientationChanged())
        .thenAnswer((_) => Stream.empty());

    // Stub VoiceController ChangeNotifier methods
    when(() => mockVoiceController.addListener(any())).thenReturn(null);
    when(() => mockVoiceController.removeListener(any())).thenReturn(null);
    when(() => mockVoiceController.dispose()).thenReturn(null);
    // Removed protected members stubbing

    // Stub VoiceController specific methods called in MainScreen initState
    when(() => mockVoiceController.setAutoMode(any())).thenReturn(null);
    when(() => mockVoiceController.startRecording()).thenAnswer((_) async {});
    when(() => mockVoiceController.isListening).thenReturn(false); // Used in UI
    when(() => mockVoiceController.isUserSpeaking)
        .thenReturn(false); // Used in AudioWave
    when(() => mockVoiceController.setTextCallback(any()))
        .thenReturn(null); // Used in ChatPanel
  });

  tearDown(() {
    final TestWidgetsFlutterBinding binding =
        TestWidgetsFlutterBinding.ensureInitialized();
    binding.window.clearPhysicalSizeTestValue();
    binding.window.clearDevicePixelRatioTestValue();
  });

  Widget createWidgetUnderTest() {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AppState>.value(value: appState),
        ChangeNotifierProvider<VoiceController>.value(
            value: mockVoiceController),
        Provider<ApiService>(create: (_) => MockApiService()),
      ],
      child: const MedMirrorApp(),
    );
  }

  testWidgets('Show ConfigScreen when IP is not set',
      (WidgetTester tester) async {
    // Initial state: SharedPreferences empty (set in setUp)

    await tester.pumpWidget(createWidgetUnderTest());
    await tester.pumpAndSettle();

    // Verify ConfigScreen is present
    expect(find.byType(ConfigScreen), findsOneWidget);
    expect(find.byType(MainScreen), findsNothing);

    // Drain StartUpLogic timer
    await tester.pump(const Duration(seconds: 3));
  });

  testWidgets('Show MainScreen when IP is set', (WidgetTester tester) async {
    // Set a larger screen size for testing (iPad-like)
    tester.view.physicalSize = const Size(1024, 768);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    // Setup state: Pre-populate SharedPreferences
    SharedPreferences.setMockInitialValues({'host_ip': '192.168.1.50'});
    // Re-create AppState to load new prefs?
    // AppState loads config in StartUpLogic via loadConfig().
    // So new AppState instance is not strictly needed if we just rely on StartUpLogic calling loadConfig.
    // However, AppState.loadConfig gets a NEW instance of SharedPreferences.

    await tester.pumpWidget(createWidgetUnderTest());

    // We utilize pump() instead of pumpAndSettle() because ScanLineEffect
    // runs an infinite animation which causes pumpAndSettle to time out.

    // Pump to trigger initState
    await tester.pump();

    // Advance time to trigger StartUpLogic's 2-second fallback timer
    await tester.pump(const Duration(seconds: 3));

    // Verify MainScreen is present
    expect(find.byType(MainScreen), findsOneWidget);
    expect(find.byType(ConfigScreen), findsNothing);

    // Cleanup: Remove widget to cancel any active timers (like ScanLineEffect)
    await tester.pumpWidget(const SizedBox());
  });
}

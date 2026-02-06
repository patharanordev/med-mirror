import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import 'core/state/app_state.dart';
import 'features/settings/screens/config_screen.dart';
import 'features/dashboard/screens/dashboard_screen.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AppState()),
      ],
      child: const MedMirrorApp(),
    ),
  );
}

class MedMirrorApp extends StatelessWidget {
  const MedMirrorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MedMirror Edge',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: Colors.black,
        textTheme: GoogleFonts.interTextTheme(
          Theme.of(context).textTheme.apply(bodyColor: Colors.white, displayColor: Colors.white),
        ),
        colorScheme: const ColorScheme.dark(
          primary: Colors.white,
          secondary: Colors.cyanAccent,
          surface: Colors.black,
        ),
        useMaterial3: true,
      ),
      // Check if IP is configured, otherwise show ConfigScreen
      home: const StartUpLogic(),
    );
  }
}

class StartUpLogic extends StatefulWidget {
  const StartUpLogic({super.key});

  @override
  State<StartUpLogic> createState() => _StartUpLogicState();
}

class _StartUpLogicState extends State<StartUpLogic> {
  @override
  void initState() {
    super.initState();
    // In a real app, we check SharedPreferences here.
    // For now, we rely on AppState to decide or default to ConfigScreen.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AppState>().loadConfig();
      // Safety timeout
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted && !context.read<AppState>().isConfigLoaded) {
           context.read<AppState>().forceReady();
        }
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    
    if (!state.isConfigLoaded) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (state.hostIp == null || state.hostIp!.isEmpty) {
      return const ConfigScreen();
    }

    return const MainScreen();
  }
}

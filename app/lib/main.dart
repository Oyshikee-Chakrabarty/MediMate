import 'package:flutter/material.dart';

import 'core/theme.dart';
import 'screens/dashboard_screen.dart';
import 'screens/login_screen.dart';
import 'state/app_state.dart';

void main() {
  runApp(const MediMateApp());
}

class MediMateApp extends StatelessWidget {
  const MediMateApp({super.key});

  @override
  Widget build(BuildContext context) {
    final state = AppState();
    final loggedIn = state.user != null;

    return AppScope(
      state: state,
      child: MaterialApp(
        title: 'MediMate',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(seedColor: MmColors.cyan),
          scaffoldBackgroundColor: MmColors.authBg,
        ),
        home: loggedIn ? const DashboardScreen() : const LoginScreen(),
      ),
    );
  }
}

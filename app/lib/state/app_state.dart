import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../models/models.dart';

/// App-wide session + today's dose state. Demo seed data stands in for the
/// SQLite/sync layers that arrive in Phases 2-5 of the plan.
class AppState extends ChangeNotifier {
  User? _user;
  User? get user => _user;

  final List<Dose> doses = [
    Dose(
      id: 'dose-1',
      hour: 9,
      minute: 0,
      medicine: 'Thyrox 50mcg',
      doseInfo: '1 Tablet',
      dotColor: MmColors.yellow,
      iconBg: MmColors.greenIcon,
      icon: Icons.medication,
    ),
    Dose(
      id: 'dose-2',
      hour: 13,
      minute: 0,
      medicine: 'Sergel 20mg',
      doseInfo: '1 Capsule',
      dotColor: MmColors.orange,
      iconBg: const Color(0xFF22C55E),
      icon: Icons.medication,
    ),
    Dose(
      id: 'dose-3',
      hour: 22,
      minute: 0,
      medicine: 'D-cough 10mg',
      doseInfo: '2 Spoon',
      dotColor: MmColors.navy,
      iconBg: const Color(0xFFF9B94E),
      icon: Icons.local_pharmacy,
    ),
  ];

  int get takenCount => doses.where((d) => d.isTaken).length;
  int get remainingCount => doses.length - takenCount;
  double get progress =>
      doses.isEmpty ? 0 : (takenCount / doses.length).clamp(0.0, 1.0);

  /// Demo auth — accepts any name with a 4+ char password. Swap for the real
  /// POST /auth/login call in Phase 1 of the backend.
  bool login(String name, String password) {
    if (name.trim().isEmpty || password.length < 4) return false;
    _user = User(name: name.trim());
    notifyListeners();
    return true;
  }

  /// Demo register — mirrors POST /auth/register semantics (F1).
  bool signup({
    required String name,
    required String email,
    required String password,
    required UserRole role,
  }) {
    if (name.trim().isEmpty || password.length < 6 || !email.contains('@')) {
      return false;
    }
    _user = User(name: name.trim(), email: email.trim(), role: role);
    notifyListeners();
    return true;
  }

  /// F5 — mark a dose as taken (later also decrements stock + syncs).
  void takeDose(String id) {
    for (final dose in doses) {
      if (dose.id == id && !dose.isTaken) {
        dose.status = DoseStatus.taken;
        notifyListeners();
        return;
      }
    }
  }

  void logout() {
    _user = null;
    for (final dose in doses) {
      dose.status = DoseStatus.pending;
    }
    notifyListeners();
  }
}

/// Provides [AppState] to the whole tree and rebuilds dependents on change.
class AppScope extends InheritedNotifier<AppState> {
  const AppScope({super.key, required AppState state, required super.child})
      : super(notifier: state);

  static AppState of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<AppScope>()!.notifier!;
}

import 'package:flutter/material.dart';

/// F1 — Role-Based Accounts.
enum UserRole { patient, caretaker }

class User {
  const User({
    required this.name,
    this.email = '',
    this.role = UserRole.patient,
  });

  final String name;
  final String email;
  final UserRole role;

  String get firstName {
    final parts = name.trim().split(RegExp(r'\s+'));
    return parts.isEmpty || parts.first.isEmpty ? 'there' : parts.first;
  }
}

/// Dose lifecycle per plan §5.1 (skipped/missed arrive with the alarm phase).
enum DoseStatus { pending, taken, skipped }

/// One row of "Today's medicines" on the dashboard.
class Dose {
  Dose({
    required this.id,
    required this.hour,
    required this.minute,
    required this.medicine,
    required this.doseInfo,
    required this.dotColor,
    required this.iconBg,
    required this.icon,
    this.status = DoseStatus.pending,
  });

  final String id;
  final int hour; // 24h
  final int minute;
  final String medicine;
  final String doseInfo;
  final Color dotColor;
  final Color iconBg;
  final IconData icon;
  DoseStatus status;

  bool get isTaken => status == DoseStatus.taken;

  String get timeLabel {
    final h12 = hour % 12 == 0 ? 12 : hour % 12;
    final suffix = hour < 12 ? 'AM' : 'PM';
    return '$h12:${minute.toString().padLeft(2, '0')} $suffix';
  }
}

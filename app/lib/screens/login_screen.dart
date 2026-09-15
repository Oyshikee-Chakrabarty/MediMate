import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../state/app_state.dart';
import 'dashboard_screen.dart';
import 'signup_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    final state = AppScope.of(context);

    // Demo auth gate — replaced by POST /auth/login in Phase 1 backend work.
    await Future<void>.delayed(const Duration(milliseconds: 400));
    final ok = state.login(_name.text, _password.text);

    if (!mounted) return;
    setState(() => _busy = false);
    if (!ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Enter your name and a password of 4+ characters.'),
        ),
      );
      return;
    }
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(builder: (_) => const DashboardScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          const BubbleBackdrop(topHeight: 460),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(24, 48, 24, 32),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Center(child: MmLogo(size: 150)),
                    const SizedBox(height: 96),
                    Text('Login', style: MmText.title, textAlign: TextAlign.center),
                    const SizedBox(height: 8),
                    Text(
                      'Log in to continue.',
                      textAlign: TextAlign.center,
                      style: MmText.body.copyWith(color: const Color(0xFF8A97A8)),
                    ),
                    const SizedBox(height: 40),
                    MmTextField(
                      controller: _name,
                      label: 'Name',
                      textInputAction: TextInputAction.next,
                      validator: (v) =>
                          v == null || v.trim().isEmpty ? 'Name is required' : null,
                    ),
                    const SizedBox(height: 22),
                    MmTextField(
                      controller: _password,
                      label: 'Password',
                      obscure: true,
                      validator: (v) =>
                          v == null || v.length < 4 ? 'Min 4 characters' : null,
                    ),
                    const SizedBox(height: 32),
                    MmPrimaryButton(
                      label: 'Log in',
                      busy: _busy,
                      onPressed: _submit,
                    ),
                    const SizedBox(height: 48),
                    TextButton(
                      onPressed: () {}, // password reset arrives with backend Phase 1
                      child: Text(
                        'Forgot Password?',
                        style: MmText.body.copyWith(
                          color: const Color(0xFF8A97A8),
                        ),
                      ),
                    ),
                    TextButton(
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(builder: (_) => const SignupScreen()),
                      ),
                      child: Text(
                        'Signup !',
                        style: MmText.body.copyWith(color: MmColors.cyan),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../core/theme.dart';
import '../models/models.dart';
import '../state/app_state.dart';
import 'dashboard_screen.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});

  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  UserRole _role = UserRole.caretaker;
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    final state = AppScope.of(context);

    // Demo register — replaced by POST /auth/register in Phase 1 backend work.
    await Future<void>.delayed(const Duration(milliseconds: 400));
    final ok = state.signup(
      name: _name.text,
      email: _email.text,
      password: _password.text,
      role: _role,
    );

    if (!mounted) return;
    setState(() => _busy = false);
    if (!ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Check your details and try again.')),
      );
      return;
    }
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute<void>(builder: (_) => const DashboardScreen()),
      (_) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          const BubbleBackdrop(topHeight: 240, flip: true),
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(24, 40, 24, 32),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Center(child: MmLogo(size: 120)),
                    const SizedBox(height: 40),
                    Text('Sign in', style: MmText.title, textAlign: TextAlign.center),
                    const SizedBox(height: 8),
                    Text(
                      'Sign in to continue.',
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
                    _RoleField(
                      value: _role,
                      onChanged: (role) => setState(() => _role = role),
                    ),
                    const SizedBox(height: 22),
                    MmTextField(
                      controller: _email,
                      label: 'E-mail',
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      validator: (v) =>
                          v == null || !v.contains('@') ? 'Enter a valid e-mail' : null,
                    ),
                    const SizedBox(height: 22),
                    MmTextField(
                      controller: _password,
                      label: 'Password',
                      obscure: true,
                      validator: (v) =>
                          v == null || v.length < 6 ? 'Min 6 characters' : null,
                    ),
                    const SizedBox(height: 36),
                    MmPrimaryButton(
                      label: 'Sign in',
                      busy: _busy,
                      onPressed: _submit,
                    ),
                    const SizedBox(height: 24),
                    TextButton(
                      onPressed: () => Navigator.of(context).maybePop(),
                      child: Text(
                        'Already have an account? Log in',
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

/// Rounded ROLE dropdown styled like the mockup's input fields (F1).
class _RoleField extends StatelessWidget {
  const _RoleField({required this.value, required this.onChanged});

  final UserRole value;
  final ValueChanged<UserRole> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('ROLE', style: MmText.sectionLabel),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 22),
          decoration: BoxDecoration(
            color: MmColors.fieldBlue,
            borderRadius: BorderRadius.circular(32),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<UserRole>(
              value: value,
              isExpanded: true,
              icon: const Icon(Icons.arrow_drop_down, size: 34, color: Color(0xFF6FC3E0)),
              style: MmText.body,
              dropdownColor: MmColors.fieldBlueSoft,
              borderRadius: BorderRadius.circular(20),
              items: const [
                DropdownMenuItem(
                  value: UserRole.patient,
                  child: Text('Patient', style: MmText.body),
                ),
                DropdownMenuItem(
                  value: UserRole.caretaker,
                  child: Text('Caretaker', style: MmText.body),
                ),
              ],
              onChanged: (role) => {if (role != null) onChanged(role)},
            ),
          ),
        ),
      ],
    );
  }
}

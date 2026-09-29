import 'package:flutter/material.dart';

/// MediMate palette — matches the Figma mockups (auth + dashboard).
class MmColors {
  MmColors._();

  // Brand blues.
  static const Color deepBlue = Color(0xFF1A327E); // headings, text
  static const Color royalBlue = Color(0xFF2A5CE8); // logo tile
  static const Color sky = Color(0xFF8EE0F5); // logo bubble accent
  static const Color cyan = Color(0xFF17A9D6); // primary buttons
  static const Color cyanDark = Color(0xFF1391BC);
  static const Color fieldBlue = Color(0xFFBFEFF9); // input fills
  static const Color fieldBlueSoft = Color(0xFFD9F5FB); // alternate input fill
  static const Color authBg = Color(0xFFEDF3F8); // auth content background
  static const Color bubble = Color(0xFFA5E6F7); // bubble pattern
  static const Color bubbleSoft = Color(0xFFBCEBF8);

  // Dashboard.
  static const Color greenHeader = Color(0xFF6EC531); // Good Morning band
  static const Color greenIcon = Color(0xFF8BC34A);
  static const Color cardSky = Color(0xFFBDE6F5); // dose card fill
  static const Color cardBorder = Color(0xFF8FCBE8);
  static const Color yellow = Color(0xFFFFD54F); // 9 AM dot / progress
  static const Color orange = Color(0xFFF47B20); // 1 PM dot
  static const Color navy = Color(0xFF1A327E); // 10 PM dot / chips
  static const Color progressTrack = Color(0xFFE8F4F8);
}

/// Shared text styles used across screens.
class MmText {
  MmText._();

  static const TextStyle title = TextStyle(
    fontSize: 56,
    height: 1.1,
    fontWeight: FontWeight.w800,
    color: MmColors.deepBlue,
  );

  static const TextStyle sectionLabel = TextStyle(
    fontSize: 12,
    fontWeight: FontWeight.w800,
    letterSpacing: 2.4,
    color: Color(0xFF8A97A8),
  );

  static const TextStyle body = TextStyle(
    fontSize: 20,
    fontWeight: FontWeight.w600,
    color: MmColors.deepBlue,
  );
}

/// Decorative circle pattern behind the auth screens (top band + soft
/// overlapping bubbles), matching the PNG mockups.
class BubbleBackdrop extends StatelessWidget {
  const BubbleBackdrop({
    super.key,
    required this.topHeight,
    this.flip = false,
  });

  /// Height of the solid sky-blue band at the top of the screen.
  final double topHeight;

  /// Mirrors the bubble pattern horizontally.
  final bool flip;

  static const List<_Bubble> _bubbles = [
    _Bubble(0.02, 0.04, 0.09, 1),
    _Bubble(0.24, 0.00, 0.11, 1),
    _Bubble(0.52, 0.02, 0.08, 0.6),
    _Bubble(0.83, 0.00, 0.12, 1),
    _Bubble(0.10, 0.10, 0.13, 1),
    _Bubble(0.42, 0.08, 0.09, 0.5),
    _Bubble(0.70, 0.10, 0.10, 1),
    _Bubble(0.92, 0.14, 0.07, 0.55),
    _Bubble(0.00, 0.20, 0.10, 0.5),
    _Bubble(0.30, 0.18, 0.15, 1),
    _Bubble(0.60, 0.16, 0.08, 0.5),
    _Bubble(0.86, 0.22, 0.13, 1),
    _Bubble(0.15, 0.30, 0.09, 0.5),
    _Bubble(0.46, 0.28, 0.12, 1),
    _Bubble(0.75, 0.30, 0.09, 0.55),
  ];

  @override
  Widget build(BuildContext context) {
    final pattern = ClipRect(
      child: SizedBox(
        height: topHeight,
        width: double.infinity,
        child: CustomPaint(
          painter: _BubblePainter(bubbles: _bubbles, flip: flip),
        ),
      ),
    );

    return Stack(
      children: [
        Positioned.fill(
          child: Container(color: MmColors.authBg),
        ),
        Positioned(
          top: 0,
          left: 0,
          right: 0,
          height: topHeight,
          child: pattern,
        ),
      ],
    );
  }
}

class _Bubble {
  const _Bubble(this.dx, this.dy, this.r, this.opacity);

  /// Fractions of backdrop width/height.
  final double dx;
  final double dy;
  final double r;
  final double opacity;
}

class _BubblePainter extends CustomPainter {
  const _BubblePainter({required this.bubbles, required this.flip});

  final List<_Bubble> bubbles;
  final bool flip;

  @override
  void paint(Canvas canvas, Size size) {
    final solid = Paint()..color = MmColors.bubble;
    canvas.drawRect(Offset.zero & size, solid);

    for (final b in bubbles) {
      final paint = Paint()
        ..color = Colors.white.withValues(alpha: b.opacity * 0.9);
      final cx = (flip ? 1 - b.dx : b.dx) * size.width;
      final cy = b.dy * size.height;
      canvas.drawCircle(Offset(cx, cy), b.r * size.width, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _BubblePainter oldDelegate) =>
      oldDelegate.flip != flip;
}

/// The blue rounded-square "m" app logo.
class MmLogo extends StatelessWidget {
  const MmLogo({super.key, this.size = 140});

  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox.square(
      dimension: size,
      child: CustomPaint(painter: _LogoPainter()),
    );
  }
}

class _LogoPainter extends CustomPainter {
  static final RRect _tile = RRect.fromRectAndRadius(
    const Rect.fromLTWH(0, 0, 200, 200),
    const Radius.circular(56),
  );

  @override
  void paint(Canvas canvas, Size size) {
    canvas.scale(size.width / 200);
    canvas.drawRRect(_tile, Paint()..color = MmColors.royalBlue);

    // Left leg of the "m".
    final legPaint = Paint()..color = Colors.white;
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        const Rect.fromLTWH(36, 84, 40, 80),
        const Radius.circular(20),
      ),
      legPaint,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        const Rect.fromLTWH(124, 84, 40, 80),
        const Radius.circular(20),
      ),
      legPaint,
    );

    // Sky-blue arch connecting the two legs (the humps of the "m").
    final arch = Path()
      ..moveTo(36, 108)
      ..lineTo(36, 74)
      ..quadraticBezierTo(60, 44, 92, 66)
      ..quadraticBezierTo(100, 72, 108, 66)
      ..quadraticBezierTo(140, 44, 164, 74)
      ..lineTo(164, 112)
      ..lineTo(124, 112)
      ..lineTo(124, 92)
      ..quadraticBezierTo(112, 78, 100, 92)
      ..lineTo(100, 112)
      ..lineTo(76, 112)
      ..lineTo(76, 92)
      ..quadraticBezierTo(56, 78, 36, 108)
      ..close();
    canvas.drawPath(arch, Paint()..color = MmColors.sky);
  }

  @override
  bool shouldRepaint(covariant _LogoPainter oldDelegate) => false;
}

/// Sky-blue rounded text field used on auth screens.
class MmTextField extends StatelessWidget {
  const MmTextField({
    super.key,
    required this.controller,
    required this.label,
    this.hint,
    this.obscure = false,
    this.keyboardType,
    this.suffix,
    this.validator,
    this.textInputAction,
  });

  final TextEditingController controller;
  final String label;
  final String? hint;
  final bool obscure;
  final TextInputType? keyboardType;
  final Widget? suffix;
  final String? Function(String?)? validator;
  final TextInputAction? textInputAction;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label.toUpperCase(), style: MmText.sectionLabel),
        const SizedBox(height: 10),
        TextFormField(
          controller: controller,
          obscureText: obscure,
          keyboardType: keyboardType,
          validator: validator,
          textInputAction: textInputAction,
          style: MmText.body,
          decoration: InputDecoration(
            isDense: true,
            filled: true,
            fillColor: MmColors.fieldBlue,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 22,
              vertical: 22,
            ),
            suffixIcon: suffix,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(32),
              borderSide: BorderSide.none,
            ),
          ),
        ),
      ],
    );
  }
}

/// Solid cyan rounded action button.
class MmPrimaryButton extends StatelessWidget {
  const MmPrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.busy = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 64,
      child: FilledButton(
        onPressed: busy ? null : onPressed,
        style: FilledButton.styleFrom(
          backgroundColor: MmColors.cyan,
          disabledBackgroundColor: MmColors.cyan.withValues(alpha: 0.6),
          foregroundColor: Colors.white,
          disabledForegroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          textStyle: const TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w800,
          ),
        ),
        child: busy
            ? const SizedBox.square(
                dimension: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 3,
                  color: Colors.white,
                ),
              )
            : Text(label),
      ),
    );
  }
}

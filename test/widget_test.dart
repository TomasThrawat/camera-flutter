import 'package:black_camera/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('shows only Camera and Gallery as primary destinations', (
    tester,
  ) async {
    await tester.pumpWidget(const CameraApp());
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Camera'), findsOneWidget);
    expect(find.text('Gallery'), findsOneWidget);
  });
}

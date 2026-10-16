using Toybox.Application;
using Toybox.Lang;
using Toybox.Math;
using Toybox.Test;

(:test)
function nativeFontScalePolicy(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.fontScale(0.8), 0.8);
    Test.assertEqual(FaceModel.fontScale(1.0), 1.0);
    Test.assertEqual(FaceModel.fontScale(1.35), 1.35);
    Test.assertEqual(FaceModel.fontScale(0.7), 1.0);
    Test.assertEqual(FaceModel.fontScale(1.36), 1.0);
    Test.assertEqual(FaceModel.fontScale(null), 1.0);
    Test.assertEqual(FaceModel.fontScale("1.35"), 1.0);
    Test.assertEqual(FaceModel.fontScale(false), 1.0);
    Test.assertEqual(FaceModel.fontScale(Math.sqrt(-1)), 1.0);
    return true;
}

(:test)
function calendarAndLayoutBounds(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.shortDate(16, 10, 6), "FRI 16 OCT");
    Test.assertEqual(FaceModel.shortDate(1, 1, 1), "SUN 1 JAN");
    Test.assertEqual(FaceModel.shortDate(31, 12, 7), "SAT 31 DEC");
    Test.assertEqual(FaceModel.shortDate(0, 10, 6), "--- -- ---");
    Test.assertEqual(FaceModel.shortDate(16, 13, 6), "--- -- ---");
    Test.assertEqual(FaceModel.shortDate(16, 10, 0), "--- -- ---");
    Test.assert(FaceModel.fitsActiveBand(380, 154, 380, 113, 267));
    Test.assert(!FaceModel.fitsActiveBand(380, 173, 380, 113, 267));
    Test.assert(!FaceModel.fitsActiveBand(381, 100, 380, 113, 267));
    return true;
}

(:test)
function dataPropertyReadback(logger as Test.Logger) as Lang.Boolean {
    var left = Application.Properties.getValue("leftData");
    var right = Application.Properties.getValue("rightData");
    try {
        for (var choice = 0; choice < 3; choice += 1) {
            Application.Properties.setValue("leftData", choice);
            Application.Properties.setValue("rightData", choice);
            Test.assertEqual(FaceSettings.readSlot(0), choice);
            Test.assertEqual(FaceSettings.readSlot(1), choice);
        }
        Application.Properties.setValue("leftData", "weather");
        Application.Properties.setValue("rightData", 9);
        Test.assertEqual(FaceSettings.readSlot(0), 0);
        Test.assertEqual(FaceSettings.readSlot(1), 1);
        Test.assert(!FaceSettings.saveSlot(-1, 1));
        Test.assert(!FaceSettings.saveSlot(0, "steps"));
        Test.assert(!FaceSettings.saveSlot(1, 3));
    } finally {
        Application.Properties.setValue("leftData", left);
        Application.Properties.setValue("rightData", right);
    }
    return true;
}

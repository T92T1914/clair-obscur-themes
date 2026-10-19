using Toybox.Application;
using Toybox.Lang;
using Toybox.Math;
using Toybox.Test;
using Toybox.WatchUi;

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

(:test)
function analogAnglesAndCardinals(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.hourTurns(0, 0), 0.0);
    Test.assertEqual(FaceModel.hourTurns(3, 0), 0.25);
    Test.assertEqual(FaceModel.hourTurns(12, 0), 0.0);
    var quarter = FaceModel.hourTurns(3, 15);
    var half = FaceModel.hourTurns(6, 30);
    var boundary = FaceModel.hourTurns(11, 59);
    Test.assert(quarter != null && half != null && boundary != null);
    Test.assert((quarter as Lang.Float) > 0.270832 && (quarter as Lang.Float) < 0.270834);
    Test.assert((half as Lang.Float) > 0.541665 && (half as Lang.Float) < 0.541668);
    Test.assert((boundary as Lang.Float) > 0.998610 && (boundary as Lang.Float) < 0.998613);
    Test.assertEqual(FaceModel.hourTurns(23, 59), boundary);
    Test.assertEqual(FaceModel.minuteTurns(15), 0.25);
    Test.assertEqual(FaceModel.minuteTurns(30), 0.5);
    Test.assertEqual(FaceModel.minuteTurns(45), 0.75);
    Test.assertEqual(FaceModel.hourTurns(24, 0), null);
    Test.assertEqual(FaceModel.hourTurns(5.0, 0), null);
    Test.assertEqual(FaceModel.minuteTurns(60), null);
    Test.assertEqual(FaceModel.minuteTurns(false), null);
    var turns = [0.0, 0.25, 0.5, 0.75, 0.125, 0.375, 0.625, 0.875];
    var expected = [[227, 127], [327, 227], [227, 327], [127, 227],
        [298, 156], [298, 298], [156, 298], [156, 156]];
    for (var index = 0; index < turns.size(); index += 1) {
        var point = FaceModel.radialPoint(turns[index], 100, 0);
        Test.assertEqual(point[0], expected[index][0]);
        Test.assertEqual(point[1], expected[index][1]);
    }
    var hour = FaceModel.handPoints(3, 0, true);
    var minute = FaceModel.handPoints(3, 15, false);
    Test.assertEqual(hour[2][0], 341);
    Test.assertEqual(hour[2][1], 227);
    Test.assertEqual(minute[2][0], 395);
    Test.assertEqual(minute[2][1], 227);
    // The broad short hand and narrow long hand have separate real vertices.
    Test.assertEqual(hour[3][1] - hour[1][1], 18);
    Test.assertEqual(minute[3][1] - minute[1][1], 10);
    return true;
}

(:test)
function analogMinuteTrackAndOrientation(logger as Test.Logger) as Lang.Boolean {
    var top = FaceModel.minuteTick(0);
    Test.assertEqual(top[0][0], 227);
    Test.assertEqual(top[0][1], 19);
    Test.assertEqual(top[1][1], 25);
    var right = FaceModel.minuteTick(15);
    Test.assertEqual(right[0][0], 435);
    Test.assertEqual(right[0][1], 227);
    Test.assertEqual(FaceModel.minuteTick(-1).size(), 0);
    Test.assertEqual(FaceModel.minuteTick(60).size(), 0);
    Test.assertEqual(FaceModel.hourMarker(1, 1).size(), 0);
    Test.assertEqual(FaceModel.hourMarker(12, 0).size(), 0);
    var first = FaceModel.hourMarker(0, 0);
    var second = FaceModel.hourMarker(0, 1);
    Test.assertEqual(first[0][0], 217);
    Test.assertEqual(first[2][0], 223);
    Test.assertEqual(second[0][0], 231);
    Test.assertEqual(second[2][0], 237);
    Test.assertEqual(first[1][1], 31);
    for (var tick = 0; tick < 60; tick += 1) {
        var ends = FaceModel.minuteTick(tick);
        Test.assertEqual(ends.size(), 2);
        for (var p = 0; p < ends.size(); p += 1) {
            Test.assert(ends[p][0] >= 19 && ends[p][0] <= 435);
            Test.assert(ends[p][1] >= 19 && ends[p][1] <= 435);
        }
    }
    return true;
}

(:test)
function analogAllMinuteHandBounds(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.handPoints(null, 0, true).size(), 0);
    Test.assertEqual(FaceModel.handPoints(12, -1, false).size(), 0);
    // All 720 distinct analog minute positions, including overlap and opposition.
    for (var hour = 0; hour < 12; hour += 1) {
        for (var minute = 0; minute < 60; minute += 1) {
            for (var which = 0; which < 2; which += 1) {
                var points = FaceModel.handPoints(hour, minute, which == 0);
                Test.assertEqual(points.size(), 5);
                var limit = which == 0 ? 115 : 169;
                for (var p = 0; p < points.size(); p += 1) {
                    var x = points[p][0] - 227;
                    var y = points[p][1] - 227;
                    Test.assert(x * x + y * y <= limit * limit);
                    Test.assert(points[p][0] >= 58 && points[p][0] <= 396);
                    Test.assert(points[p][1] >= 58 && points[p][1] <= 396);
                }
            }
        }
    }
    Test.assert(FaceModel.ANALOG_DATA_BOTTOM - FaceModel.ANALOG_DATA_TOP >= 82);
    Test.assert(FaceModel.ANALOG_LEFT_X + FaceModel.ANALOG_DATA_WIDTH < FaceModel.ANALOG_RIGHT_X);
    Test.assert(FaceModel.ANALOG_CHARGE_TOP > FaceModel.ANALOG_DATA_BOTTOM);
    Test.assert(FaceModel.ANALOG_DATE_BOTTOM < 227);
    return true;
}

(:test)
function layoutValidationPersistenceAndMenu(logger as Test.Logger) as Lang.Boolean {
    var before = Application.Properties.getValue("layout");
    var appearance = Application.Properties.getValue("appearance");
    var left = Application.Properties.getValue("leftData");
    var right = Application.Properties.getValue("rightData");
    try {
        Test.assert(FaceModel.isLayout(0));
        Test.assert(FaceModel.isLayout(1));
        Test.assert(!FaceModel.isLayout(false));
        Test.assert(!FaceModel.isLayout(0.0));
        Test.assert(!FaceModel.isLayout("Analog"));
        Test.assert(!FaceModel.isLayout(-1));
        Test.assert(!FaceModel.isLayout(2));
        Test.assertEqual(FaceModel.sanitizeLayout(null), 0);
        Test.assertEqual(FaceModel.sanitizeLayout("Digital"), 0);
        Test.assert(FaceSettings.saveLayout(0));
        Test.assertEqual(Application.Properties.getValue("layout"), 0);
        Test.assertEqual(FaceSettings.readLayout(), 0);
        Test.assert(FaceSettings.saveLayout(1));
        Test.assertEqual(Application.Properties.getValue("layout"), 1);
        Test.assertEqual(FaceSettings.readLayout(), 1);
        Test.assert(!FaceSettings.saveLayout(2));
        Test.assert(!FaceSettings.saveLayout(0.0));
        Test.assert(!FaceSettings.saveLayout("Analog"));
        Test.assertEqual(FaceSettings.readLayout(), 1);
        var menu = FaceSettings.makeLayoutMenu();
        var analog = menu.getItem(0);
        var digital = menu.getItem(1);
        Test.assert(analog != null && digital != null);
        Test.assertEqual((analog as WatchUi.MenuItem).getId(), 0);
        Test.assertEqual((digital as WatchUi.MenuItem).getId(), 1);
        Test.assertEqual(menu.getItem(2), null);
        Application.Properties.setValue("layout", "invalid");
        Test.assertEqual(FaceSettings.readLayout(), 0);
        Test.assertEqual(Application.Properties.getValue("appearance"), appearance);
        Test.assertEqual(Application.Properties.getValue("leftData"), left);
        Test.assertEqual(Application.Properties.getValue("rightData"), right);
    } finally {
        Application.Properties.setValue("layout", before);
    }
    return true;
}

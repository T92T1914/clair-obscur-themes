using Toybox.Application;
using Toybox.Lang;
using Toybox.Math;
using Toybox.System;
using Toybox.Test;

(:test)
function clockFormatting(logger as Test.Logger) as Lang.Boolean {
    var hours24 = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11",
        "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"];
    var hours12 = ["12", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11",
        "12", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"];
    for (var hour = 0; hour < 24; hour += 1) {
        Test.assertEqual(FaceModel.formatTime(hour, 0, true), hours24[hour] + ":00");
        Test.assertEqual(FaceModel.formatTime(hour, 59, true), hours24[hour] + ":59");
        Test.assertEqual(FaceModel.formatTime(hour, 0, false), hours12[hour] + ":00");
        Test.assertEqual(FaceModel.formatTime(hour, 59, false), hours12[hour] + ":59");
    }
    Test.assertEqual(FaceModel.formatTime(0, 0, true), "00:00");
    Test.assertEqual(FaceModel.formatTime(23, 59, true), "23:59");
    Test.assertEqual(FaceModel.formatTime(0, 5, false), "12:05");
    Test.assertEqual(FaceModel.formatTime(12, 0, false), "12:00");
    Test.assertEqual(FaceModel.formatTime(13, 9, false), "1:09");
    Test.assertEqual(FaceModel.period(0, false), "AM");
    Test.assertEqual(FaceModel.period(12, false), "PM");
    Test.assertEqual(FaceModel.period(23, true), "");
    Test.assertEqual(FaceModel.formatActiveTime(0, 5, false), "12:05 AM");
    Test.assertEqual(FaceModel.formatActiveTime(12, 0, false), "12:00 PM");
    Test.assertEqual(FaceModel.formatActiveTime(13, 9, false), "1:09 PM");
    Test.assertEqual(FaceModel.formatActiveTime(23, 59, false), "11:59 PM");
    Test.assertEqual(FaceModel.formatActiveTime(23, 59, true), "23:59");
    Test.assertEqual(FaceModel.formatActiveTime(24, 0, false), "--:--");
    Test.assertEqual(FaceModel.formatActiveTime(5, 60, false), "--:--");
    Test.assertEqual(FaceModel.formatTime(24, 0, true), "--:--");
    Test.assertEqual(FaceModel.formatTime(5, 60, true), "--:--");
    Test.assertEqual(FaceModel.formatTime(-1, 0, true), "--:--");
    Test.assertEqual(FaceModel.formatTime(5, -1, true), "--:--");
    Test.assertEqual(FaceModel.formatTime(null, 0, true), "--:--");
    Test.assertEqual(FaceModel.formatTime(5.0, 0, true), "--:--");
    Test.assertEqual(FaceModel.formatTime(true, 0, true), "--:--");
    return true;
}

(:test)
function gregorianFormatting(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.formatDate(16, 10, 2026), "2026-10-16");
    Test.assertEqual(FaceModel.formatDate(29, 2, 2024), "2024-02-29");
    Test.assertEqual(FaceModel.formatDate(29, 2, 2000), "2000-02-29");
    Test.assertEqual(FaceModel.formatDate(1, 1, 2027), "2027-01-01");
    Test.assertEqual(FaceModel.formatDate(31, 12, 2026), "2026-12-31");
    Test.assertEqual(FaceModel.formatDate(1, 1, 1), "0001-01-01");
    Test.assertEqual(FaceModel.formatDate(31, 12, 9999), "9999-12-31");
    Test.assertEqual(FaceModel.formatDate(29, 2, 2023), "---- -- --");
    Test.assertEqual(FaceModel.formatDate(29, 2, 2100), "---- -- --");
    Test.assertEqual(FaceModel.formatDate(31, 4, 2026), "---- -- --");
    Test.assertEqual(FaceModel.formatDate(1, 13, 2026), "---- -- --");
    Test.assertEqual(FaceModel.formatDate(0, 1, 2026), "---- -- --");
    Test.assertEqual(FaceModel.formatDate(1, 1, 0), "---- -- --");
    Test.assertEqual(FaceModel.formatDate(1, 1, 10000), "---- -- --");
    Test.assertEqual(FaceModel.formatDate(null, 1, 2026), "---- -- --");
    Test.assertEqual(FaceModel.formatDate(1.0, 1, 2026), "---- -- --");
    Test.assertEqual(FaceModel.formatDate(1, false, 2026), "---- -- --");
    return true;
}

(:test)
function batteryFormatting(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.formatBattery(0), "0%");
    Test.assertEqual(FaceModel.formatBattery(100), "100%");
    Test.assertEqual(FaceModel.formatBattery(99.9), "99%");
    Test.assertEqual(FaceModel.formatBattery(0.5), "0%");
    Test.assertEqual(FaceModel.formatBattery(-1), "--%");
    Test.assertEqual(FaceModel.formatBattery(100.1), "--%");
    Test.assertEqual(FaceModel.formatBattery(null), "--%");
    Test.assertEqual(FaceModel.formatBattery(true), "--%");
    Test.assertEqual(FaceModel.formatBattery("50"), "--%");
    Test.assertEqualMessage(FaceModel.formatBattery(Math.sqrt(-1)), "--%",
        "Float NaN battery must use the invalid-data placeholder before numeric conversion");
    Test.assertEqualMessage(FaceModel.formatBattery(Math.sqrt(-1).toDouble()), "--%",
        "Double NaN battery must use the invalid-data placeholder before numeric conversion");
    return true;
}

(:test)
function appearanceValidation(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.sanitizeAppearance("Clair"), "Clair");
    Test.assertEqual(FaceModel.sanitizeAppearance("Obscur"), "Obscur");
    Test.assertEqual(FaceModel.sanitizeAppearance("clair"), "Obscur");
    Test.assertEqual(FaceModel.sanitizeAppearance(null), "Obscur");
    Test.assertEqual(FaceModel.sanitizeAppearance(1), "Obscur");
    Test.assert(!FaceModel.isAppearance("unknown"));
    Test.assertEqual(FaceSettings.appearanceFromProperty(0), "Clair");
    Test.assertEqual(FaceSettings.appearanceFromProperty(1), "Obscur");
    Test.assertEqual(FaceSettings.appearanceFromProperty(2), "Obscur");
    Test.assertEqual(FaceSettings.appearanceFromProperty(-1), "Obscur");
    Test.assertEqual(FaceSettings.appearanceFromProperty(null), "Obscur");
    Test.assertEqual(FaceSettings.appearanceFromProperty(false), "Obscur");
    Test.assertEqual(FaceSettings.appearanceFromProperty(0.0), "Obscur");
    Test.assertEqual(FaceSettings.appearanceFromProperty("0"), "Obscur");
    Test.assertEqual(FaceSettings.appearanceFromProperty("Clair"), "Obscur");
    return true;
}

(:test)
function declaredPropertyPersistence(logger as Test.Logger) as Lang.Boolean {
    var before = Application.Properties.getValue("appearance");
    try {
        FaceSettings.saveAppearance("Clair");
        Test.assertEqual(Application.Properties.getValue("appearance"), 0);
        Test.assertEqual(FaceSettings.readAppearance(), "Clair");
        FaceSettings.saveAppearance("Obscur");
        Test.assertEqual(Application.Properties.getValue("appearance"), 1);
        Test.assertEqual(FaceSettings.readAppearance(), "Obscur");
        Test.assert(!FaceSettings.saveAppearance("unknown"));
        Test.assertEqual(FaceSettings.readAppearance(), "Obscur");
        Application.Properties.setValue("appearance", "invalid");
        Test.assertEqual(FaceSettings.readAppearance(), "Obscur");
    } finally {
        Application.Properties.setValue("appearance", before);
    }
    return true;
}

(:test)
function powerAndGeometryContract(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.drawMode(false, System.DISPLAY_MODE_HIGH_POWER), :active);
    Test.assertEqual(FaceModel.drawMode(true, System.DISPLAY_MODE_HIGH_POWER), :aod);
    Test.assertEqual(FaceModel.drawMode(false, System.DISPLAY_MODE_LOW_POWER), :aod);
    Test.assertEqual(FaceModel.drawMode(true, System.DISPLAY_MODE_OFF), :off);
    Test.assertEqual(FaceModel.drawMode(false, null), :aod);
    Test.assert(FaceModel.aodFits(192, 64));
    Test.assert(!FaceModel.aodFits(193, 64));
    Test.assert(!FaceModel.aodFits(192, 65));
    Test.assert(!FaceModel.aodFits(0, 10));
    Test.assert(!FaceModel.aodFits(10.5, 10));
    var first = FaceModel.aodOffset(0);
    Test.assertEqual(first[0], -16);
    Test.assertEqual(first[1], -16);
    var last = FaceModel.aodOffset(8);
    Test.assertEqual(last[0], 16);
    Test.assertEqual(last[1], 16);
    var wrap = FaceModel.aodOffset(9);
    Test.assertEqual(wrap[0], -16);
    Test.assertEqual(wrap[1], -16);
    return true;
}

(:test)
function activeBandAdmission(logger as Test.Logger) as Lang.Boolean {
    Test.assert(FaceModel.fitsActiveBand(374, 110, 374, 150, 260));
    Test.assert(FaceModel.fitsActiveBand(180, 96, 374, 150, 260));
    // The exact target's173px FONT_NUMBER_HOT height cannot enter the110px time band.
    Test.assert(!FaceModel.fitsActiveBand(180, 173, 374, 150, 260));
    Test.assert(!FaceModel.fitsActiveBand(375, 96, 374, 150, 260));
    Test.assert(!FaceModel.fitsActiveBand(180, 111, 374, 150, 260));
    Test.assert(!FaceModel.fitsActiveBand(180, 0, 374, 150, 260));
    Test.assert(!FaceModel.fitsActiveBand(0, 96, 374, 150, 260));
    Test.assert(!FaceModel.fitsActiveBand(180.0, 96, 374, 150, 260));
    Test.assert(!FaceModel.fitsActiveBand(180, true, 374, 150, 260));
    Test.assert(!FaceModel.fitsActiveBand(180, 96, 374, 260, 150));
    Test.assert(!FaceModel.fitsActiveBand(180, 96, 374, -1, 150));
    Test.assert(!FaceModel.fitsActiveBand(180, 80, 374, 400, 480));
    // Conservative scaled-height controls are not actual runtime font observations.
    Test.assert(FaceModel.fitsActiveBand(300, 64, 300, 70, 140));
    Test.assert(FaceModel.fitsActiveBand(350, 64, 350, 280, 350));
    Test.assert(FaceModel.fitsActiveBand(200, 64, 200, 360, 425));
    Test.assert(!FaceModel.fitsActiveBand(200, 66, 200, 360, 425));
    return true;
}

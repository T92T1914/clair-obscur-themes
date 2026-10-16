using Toybox.Lang;
using Toybox.Math;
using Toybox.Test;

(:test)
function dataSlotValidation(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceData.sanitizeSlot(0, FaceData.STEPS), FaceData.WEATHER);
    Test.assertEqual(FaceData.sanitizeSlot(1, FaceData.WEATHER), FaceData.STEPS);
    Test.assertEqual(FaceData.sanitizeSlot(2, FaceData.WEATHER), FaceData.BODY_BATTERY);
    Test.assertEqual(FaceData.sanitizeSlot(-1, FaceData.STEPS), FaceData.STEPS);
    Test.assertEqual(FaceData.sanitizeSlot(3, FaceData.BODY_BATTERY), FaceData.BODY_BATTERY);
    Test.assertEqual(FaceData.sanitizeSlot(null, FaceData.WEATHER), FaceData.WEATHER);
    Test.assertEqual(FaceData.sanitizeSlot("1", FaceData.WEATHER), FaceData.WEATHER);
    Test.assertEqual(FaceData.sanitizeSlot(1.0, FaceData.WEATHER), FaceData.WEATHER);
    Test.assertEqual(FaceData.sanitizeSlot(true, FaceData.WEATHER), FaceData.WEATHER);
    Test.assertEqual(FaceData.sanitizeSlot(null, 99), FaceData.WEATHER);
    return true;
}

(:test)
function dataTemperatureFormatting(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceData.formatTemperature(0, false), "0 C");
    Test.assertEqual(FaceData.formatTemperature(0, true), "32 F");
    Test.assertEqual(FaceData.formatTemperature(20, true), "68 F");
    Test.assertEqual(FaceData.formatTemperature(-40, true), "-40 F");
    Test.assertEqual(FaceData.formatTemperature(-5, false), "-5 C");
    Test.assertEqual(FaceData.formatTemperature(20.4, false), "20 C");
    Test.assertEqual(FaceData.formatTemperature(null, false), "--");
    Test.assertEqual(FaceData.formatTemperature(true, false), "--");
    Test.assertEqual(FaceData.formatTemperature("0", true), "--");
    Test.assertEqual(FaceData.formatTemperature(1001, false), "--");
    Test.assertEqual(FaceData.formatTemperature(-1001, false), "--");
    Test.assertEqual(FaceData.formatTemperature(Math.sqrt(-1), false), "--");
    Test.assertEqual(FaceData.formatTemperature(Math.sqrt(-1).toDouble(), true), "--");
    return true;
}

(:test)
function dataWeatherAgePolicy(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceData.weatherAge(10000, 10000), "Cached <1h");
    Test.assertEqual(FaceData.weatherAge(10000, 13599), "Cached <1h");
    Test.assertEqual(FaceData.weatherAge(10000, 13600), "Cached 1h");
    Test.assertEqual(FaceData.weatherAge(10000, 17200), "Cached 2h");
    Test.assertEqual(FaceData.weatherAge(10000, 17201), "Stale 2h");
    Test.assertEqual(FaceData.weatherAge(10000, 20800), "Stale 3h");
    Test.assertEqual(FaceData.weatherAge(10001, 10000), "Age unknown");
    Test.assertEqual(FaceData.weatherAge(null, 10000), "Age unknown");
    Test.assertEqual(FaceData.weatherAge(10000, null), "Age unknown");
    Test.assertEqual(FaceData.weatherAge(-1, 10000), "Age unknown");
    Test.assertEqual(FaceData.weatherAge(10000.0, 17201), "Age unknown");
    return true;
}

(:test)
function dataWeatherPayload(logger as Test.Logger) as Lang.Boolean {
    var cached = FaceData.weatherPayload(0, 10000, 13600, true);
    Test.assertEqual(cached["value"], "32 F");
    Test.assertEqual(cached["label"], "Weather");
    Test.assertEqual(cached["detail"], "Cached 1h");
    var stale = FaceData.weatherPayload(-5, 10000, 20800, false);
    Test.assertEqual(stale["value"], "-5 C");
    Test.assertEqual(stale["detail"], "Stale 3h");
    var unknown = FaceData.weatherPayload(20, null, 20800, false);
    Test.assertEqual(unknown["value"], "20 C");
    Test.assertEqual(unknown["detail"], "Age unknown");
    var missing = FaceData.weatherPayload(null, 10000, 20800, true);
    Test.assertEqual(missing["value"], "--");
    Test.assertEqual(missing["detail"], "Unavailable");
    Test.assertEqual(missing.size(), 3);
    return true;
}

(:test)
function dataStepsPayload(logger as Test.Logger) as Lang.Boolean {
    var zero = FaceData.stepsPayload(0, 8000);
    Test.assertEqual(zero["value"], "0");
    Test.assertEqual(zero["label"], "Steps");
    Test.assertEqual(zero["detail"], "Goal 8000");
    var noGoal = FaceData.stepsPayload(12345, null);
    Test.assertEqual(noGoal["value"], "12345");
    Test.assertEqual(noGoal["detail"], "Today");
    Test.assertEqual(FaceData.stepsPayload(1, 0)["detail"], "Today");
    Test.assertEqual(FaceData.stepsPayload(1, -100)["detail"], "Today");
    Test.assertEqual(FaceData.stepsPayload(null, 8000)["value"], "--");
    Test.assertEqual(FaceData.stepsPayload(-1, 8000)["value"], "--");
    Test.assertEqual(FaceData.stepsPayload(1.0, 8000)["value"], "--");
    Test.assertEqual(FaceData.stepsPayload(true, 8000)["value"], "--");
    return true;
}

(:test)
function dataBodyBatteryPayload(logger as Test.Logger) as Lang.Boolean {
    var zero = FaceData.bodyBatteryPayload(0);
    Test.assertEqual(zero["value"], "0");
    Test.assertEqual(zero["label"], "Body Battery");
    Test.assertEqual(zero["detail"], "Garmin score");
    Test.assertEqual(FaceData.bodyBatteryPayload(100)["value"], "100");
    Test.assertEqual(FaceData.bodyBatteryPayload(5)["value"], "5");
    Test.assertEqual(FaceData.bodyBatteryPayload(null)["value"], "--");
    Test.assertEqual(FaceData.bodyBatteryPayload(-1)["value"], "--");
    Test.assertEqual(FaceData.bodyBatteryPayload(101)["value"], "--");
    Test.assertEqual(FaceData.bodyBatteryPayload(50.0)["value"], "--");
    Test.assertEqual(FaceData.bodyBatteryPayload("50")["value"], "--");
    Test.assertEqual(FaceData.bodyBatteryPayload(true)["value"], "--");
    Test.assertEqual(FaceData.bodyBatteryPayload(Math.sqrt(-1))["value"], "--");
    return true;
}

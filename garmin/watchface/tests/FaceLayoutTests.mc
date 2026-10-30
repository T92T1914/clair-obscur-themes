using Toybox.Application;
using Toybox.Graphics;
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
    Test.assert(FaceModel.hourTurns(24, 0) == null);
    Test.assert(FaceModel.hourTurns(5.0, 0) == null);
    Test.assert(FaceModel.minuteTurns(60) == null);
    Test.assert(FaceModel.minuteTurns(false) == null);
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
    Test.assertEqual(hour[2][0], 357);
    Test.assertEqual(hour[2][1], 227);
    Test.assertEqual(minute[2][0], 418);
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
    Test.assertEqual(top[0][1], 6);
    Test.assertEqual(top[1][1], 12);
    var right = FaceModel.minuteTick(15);
    Test.assertEqual(right[0][0], 448);
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
    Test.assertEqual(first[1][1], 9);
    for (var tick = 0; tick < 60; tick += 1) {
        var ends = FaceModel.minuteTick(tick);
        Test.assertEqual(ends.size(), 2);
        for (var p = 0; p < ends.size(); p += 1) {
            Test.assert(ends[p][0] >= 6 && ends[p][0] <= 448);
            Test.assert(ends[p][1] >= 6 && ends[p][1] <= 448);
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
                var limit = which == 0 ? 131 : 192;
                for (var p = 0; p < points.size(); p += 1) {
                    var x = points[p][0] - 227;
                    var y = points[p][1] - 227;
                    Test.assert(x * x + y * y <= limit * limit);
                    Test.assert(points[p][0] >= 35 && points[p][0] <= 419);
                    Test.assert(points[p][1] >= 35 && points[p][1] <= 419);
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
        Test.assert(FaceModel.isLayout(2));
        Test.assert(!FaceModel.isLayout(3));
        Test.assertEqual(FaceModel.sanitizeLayout(null), 2);
        Test.assertEqual(FaceModel.sanitizeLayout("Digital"), 2);
        Test.assert(FaceSettings.saveLayout(0));
        Test.assertEqual(Application.Properties.getValue("layout"), 0);
        Test.assertEqual(FaceSettings.readLayout(), 0);
        Test.assert(FaceSettings.saveLayout(1));
        Test.assertEqual(Application.Properties.getValue("layout"), 1);
        Test.assertEqual(FaceSettings.readLayout(), 1);
        Test.assert(!FaceSettings.saveLayout(3));
        Test.assert(!FaceSettings.saveLayout(0.0));
        Test.assert(!FaceSettings.saveLayout("Analog"));
        Test.assertEqual(FaceSettings.readLayout(), 1);
        var menu = FaceSettings.makeLayoutMenu();
        var analog = menu.getItem(0);
        var digital = menu.getItem(1);
        Test.assert(analog != null && digital != null);
        Test.assertEqual((analog as WatchUi.MenuItem).getId(), 0);
        Test.assertEqual((digital as WatchUi.MenuItem).getId(), 1);
        var hybrid = menu.getItem(2);
        Test.assert(hybrid != null);
        Test.assertEqual((hybrid as WatchUi.MenuItem).getId(), 2);
        Test.assert(menu.getItem(3) == null);
        Application.Properties.setValue("layout", "invalid");
        Test.assertEqual(FaceSettings.readLayout(), 2);
        Test.assertEqual(Application.Properties.getValue("appearance"), appearance);
        Test.assertEqual(Application.Properties.getValue("leftData"), left);
        Test.assertEqual(Application.Properties.getValue("rightData"), right);
    } finally {
        Application.Properties.setValue("layout", before);
        FaceSettings.refreshDataSubscriptions();
    }
    return true;
}

(:test)
function aodAnalogPhaseAndInvalidInput(logger as Test.Logger) as Lang.Boolean {
    var phases = [[-2, -2], [2, -2], [2, 2], [-2, 2]];
    for (var minute = 0; minute < 60; minute += 1) {
        var shift = FaceModel.aodAnalogOffset(minute);
        var expected = phases[minute % 4];
        Test.assertEqual(shift.size(), 2);
        Test.assertEqual(shift[0], expected[0]);
        Test.assertEqual(shift[1], expected[1]);
        var next = FaceModel.aodAnalogOffset((minute + 1) % 60);
        var dx = next[0] - shift[0];
        var dy = next[1] - shift[1];
        Test.assertEqual(dx * dx + dy * dy, 16);
    }
    Test.assertEqual(FaceModel.aodAnalogOffset(null).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogOffset(false).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogOffset("0").size(), 0);
    Test.assertEqual(FaceModel.aodAnalogOffset(0.0).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogOffset(-1).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogOffset(60).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogOffset(Math.sqrt(-1)).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogMarker(null, 0, 0).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogMarker(0, null, 0).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogMarker(0, 0, null).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogMarker(0.0, 0, 0).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogMarker(0, 0.0, 0).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogMarker(-1, 0, 0).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogMarker(12, 0, 0).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogMarker(1, 1, 0).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogMarker(0, 2, 0).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogMarker(0, 0, 60).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogHandPoints(null, 0, true).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogHandPoints(24, 0, false).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogHandPoints(12.0, 0, true).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogHandPoints(12, null, false).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogHandPoints(12, 0.0, true).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogHandPoints(12, -1, false).size(), 0);
    Test.assertEqual(FaceModel.aodAnalogHandPoints(12, 60, true).size(), 0);
    return true;
}

(:test)
function aodAnalogMarkerIdentityAndBounds(logger as Test.Logger) as Lang.Boolean {
    var first = FaceModel.aodAnalogMarker(0, 0, 0);
    var second = FaceModel.aodAnalogMarker(0, 1, 0);
    Test.assertEqual(first[0][0], 215);
    Test.assertEqual(first[0][1], 31);
    Test.assertEqual(first[1][0], 215);
    Test.assertEqual(first[1][1], 7);
    Test.assertEqual(first[2][0], 221);
    Test.assertEqual(second[0][0], 229);
    Test.assertEqual(second[2][0], 235);
    var phases = [[-2, -2], [2, -2], [2, 2], [-2, 2]];
    for (var minute = 0; minute < 60; minute += 1) {
        var expected = phases[minute % 4];
        var count = 0;
        for (var index = 0; index < 12; index += 1) {
            for (var part = 0; part < (index == 0 ? 2 : 1); part += 1) {
                var active = FaceModel.hourMarker(index, part);
                var points = FaceModel.aodAnalogMarker(index, part, minute);
                Test.assertEqual(points.size(), 4);
                count += 1;
                for (var p = 0; p < points.size(); p += 1) {
                    Test.assertEqual(points[p][0], active[p][0] + expected[0]);
                    Test.assertEqual(points[p][1], active[p][1] + expected[1]);
                    Test.assert(points[p][0] >= 7 && points[p][0] <= 447);
                    Test.assert(points[p][1] >= 7 && points[p][1] <= 447);
                    var x = points[p][0] - 227;
                    var y = points[p][1] - 227;
                    Test.assert(x * x + y * y < 222 * 222);
                }
            }
        }
        Test.assertEqual(count, 13);
    }
    return true;
}

(:test)
function aodAnalogAllMinuteHandIdentityAndBounds(logger as Test.Logger) as Lang.Boolean {
    var phases = [[-2, -2], [2, -2], [2, 2], [-2, 2]];
    // Every distinct analog minute, preserving both hand shapes under one shift.
    for (var hour = 0; hour < 12; hour += 1) {
        for (var minute = 0; minute < 60; minute += 1) {
            var expected = phases[minute % 4];
            for (var which = 0; which < 2; which += 1) {
                var active = FaceModel.handPoints(hour, minute, which == 0);
                var points = FaceModel.aodAnalogHandPoints(hour, minute, which == 0);
                Test.assertEqual(points.size(), 5);
                for (var p = 0; p < points.size(); p += 1) {
                    Test.assertEqual(points[p][0], active[p][0] + expected[0]);
                    Test.assertEqual(points[p][1], active[p][1] + expected[1]);
                    Test.assert(points[p][0] >= 34 && points[p][0] <= 420);
                    Test.assert(points[p][1] >= 34 && points[p][1] <= 420);
                    var x = points[p][0] - 227;
                    var y = points[p][1] - 227;
                    Test.assert(x * x + y * y <= 195 * 195);
                }
            }
        }
    }
    var noon = FaceModel.aodAnalogHandPoints(12, 0, true);
    var midnight = FaceModel.aodAnalogHandPoints(0, 0, true);
    for (var p = 0; p < noon.size(); p += 1) {
        Test.assertEqual(noon[p][0], midnight[p][0]);
        Test.assertEqual(noon[p][1], midnight[p][1]);
    }
    var hourTip = FaceModel.aodAnalogHandPoints(3, 0, true);
    var minuteTip = FaceModel.aodAnalogHandPoints(3, 15, false);
    Test.assertEqual(hourTip[2][0], 355);
    Test.assertEqual(hourTip[2][1], 225);
    Test.assertEqual(minuteTip[2][0], 416);
    Test.assertEqual(minuteTip[2][1], 229);
    return true;
}

(:test)
function sharedDialLiteralExtentsAndMinuteHierarchy(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.TICK_OUTER, 221);
    Test.assertEqual(FaceModel.TICK_INNER, 215);
    Test.assertEqual(FaceModel.MARKER_OUTER, 218);
    Test.assertEqual(FaceModel.HOUR_HAND_LENGTH, 130);
    Test.assertEqual(FaceModel.MINUTE_HAND_LENGTH, 191);
    var top = FaceModel.hourMarker(0, 0);
    var right = FaceModel.hourMarker(3, 0);
    var bottom = FaceModel.hourMarker(6, 0);
    var left = FaceModel.hourMarker(9, 0);
    Test.assertEqual(top[0][1], 33);
    Test.assertEqual(top[1][1], 9);
    Test.assertEqual(right[0][0], 421);
    Test.assertEqual(right[1][0], 445);
    Test.assertEqual(bottom[1][1], 445);
    Test.assertEqual(left[1][0], 9);
    Test.assertEqual(right[1][0] - left[1][0], 436);
    Test.assertEqual(2 * FaceModel.TICK_OUTER, 442);
    Test.assertEqual(FaceModel.hourMarker(1, 0).size(), 4);
    var strokes = 0;
    for (var tick = 0; tick < 60; tick += 1) {
        if (tick % 5 == 0) { continue; }
        strokes += 1;
        Test.assertEqual(FaceModel.minuteTick(tick).size(), 2);
    }
    Test.assertEqual(strokes, 48);
    // Active and always-on derive the same full-size baton, before translation.
    var lowPower = FaceModel.aodAnalogMarker(0, 0, 0);
    Test.assertEqual(lowPower[1][1], 7);
    Test.assertEqual(lowPower[1][1] + 2, top[1][1]);
    return true;
}

function assertSharedDialRoundGuard(points as Lang.Array<Graphics.Point2D>,
        shiftX as Lang.Number, shiftY as Lang.Number, guard as Lang.Number) as Void {
    Test.assert(points.size() >= 2 && points.size() <= 5);
    var guards = [-guard, guard];
    for (var point = 0; point < points.size(); point += 1) {
        for (var gx = 0; gx < guards.size(); gx += 1) {
            for (var gy = 0; gy < guards.size(); gy += 1) {
                var x = 2 * (points[point][0] + shiftX + guards[gx]) + 1 - 454;
                var y = 2 * (points[point][1] + shiftY + guards[gy]) + 1 - 454;
                Test.assert(x * x + y * y < 454 * 454);
            }
        }
    }
}

(:test)
function sharedDialAllMinutesAndEveryShiftStayRound(logger as Test.Logger) as Lang.Boolean {
    var phases = [[-2, -2], [2, -2], [2, 2], [-2, 2]];
    for (var tick = 0; tick < 60; tick += 1) {
        if (tick % 5 == 0) { continue; }
        assertSharedDialRoundGuard(FaceModel.minuteTick(tick), 0, 0, 3);
    }
    for (var index = 0; index < 12; index += 1) {
        for (var part = 0; part < (index == 0 ? 2 : 1); part += 1) {
            assertSharedDialRoundGuard(FaceModel.hourMarker(index, part), 0, 0, 3);
            for (var phase = 0; phase < phases.size(); phase += 1) {
                assertSharedDialRoundGuard(FaceModel.aodAnalogMarker(index, part, phase), 0, 0, 3);
            }
        }
    }
    for (var hour = 0; hour < 12; hour += 1) {
        for (var minute = 0; minute < 60; minute += 1) {
            for (var which = 0; which < 2; which += 1) {
                var active = FaceModel.handPoints(hour, minute, which == 0);
                assertSharedDialRoundGuard(active, 0, 0, 3);
                assertSharedDialRoundGuard(FaceModel.aodAnalogHandPoints(hour, minute, which == 0), 0, 0, 3);
                // Independently apply every supported shift to all 720 shapes.
                for (var phase = 0; phase < phases.size(); phase += 1) {
                    assertSharedDialRoundGuard(active, phases[phase][0], phases[phase][1], 3);
                }
            }
        }
    }
    var center = [[227, 227], [227, 227]] as Lang.Array<Graphics.Point2D>;
    for (var phase = 0; phase < phases.size(); phase += 1) {
        assertSharedDialRoundGuard(center, phases[phase][0], phases[phase][1], 6);
    }
    return true;
}

(:test)
function hybridSettingsPreserveLegacyFields(logger as Test.Logger) as Lang.Boolean {
    var layout = Application.Properties.getValue("layout");
    var left = Application.Properties.getValue("leftData");
    var right = Application.Properties.getValue("rightData");
    var date = Application.Properties.getValue("hybridDateFormat");
    try {
        Application.Properties.setValue("leftData", FaceData.BODY_BATTERY);
        Application.Properties.setValue("rightData", FaceData.BODY_BATTERY);
        Test.assert(FaceSettings.saveLayout(2));
        Test.assertEqual(FaceSettings.readLayout(), 2);
        Test.assertEqual(Application.Properties.getValue("leftData"), FaceData.BODY_BATTERY);
        Test.assertEqual(Application.Properties.getValue("rightData"), FaceData.BODY_BATTERY);
        var menu = FaceSettings.makeSettingsMenu();
        var layoutItem = menu.getItem(1);
        Test.assert(layoutItem != null);
        Test.assertEqual((layoutItem as WatchUi.MenuItem).getSubLabel(), "Hybrid / 0.10.0");
        var dateItem = menu.getItem(2);
        Test.assert(dateItem != null);
        Test.assertEqual((dateItem as WatchUi.MenuItem).getId(), "date");
        Test.assert(menu.getItem(3) == null);
        for (var order = 0; order <= 2; order += 1) {
            Test.assert(FaceSettings.saveDateFormat(order));
            Test.assertEqual(FaceSettings.readDateFormat(), order);
        }
        Test.assert(!FaceSettings.saveDateFormat(3));
        Test.assert(!FaceSettings.saveDateFormat(1.0));
        Test.assert(!FaceSettings.saveDateFormat("1"));
        Test.assertEqual(FaceSettings.readDateFormat(), 2);
        Test.assert(FaceSettings.saveLayout(0));
        var legacy = FaceSettings.makeSettingsMenu();
        Test.assertEqual((legacy.getItem(2) as WatchUi.MenuItem).getId(), "left");
        Test.assertEqual((legacy.getItem(3) as WatchUi.MenuItem).getId(), "right");
    } finally {
        Application.Properties.setValue("layout", layout);
        Application.Properties.setValue("leftData", left);
        Application.Properties.setValue("rightData", right);
        Application.Properties.setValue("hybridDateFormat", date);
        FaceSettings.refreshDataSubscriptions();
    }
    return true;
}

(:test)
function hybridFacetsPreserveSharedHandBounds(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.handFacetPoints(null, 0, true).size(), 0);
    Test.assertEqual(FaceModel.handFacetPoints(0, 60, false).size(), 0);
    Test.assert(!FaceModel.interClockEligible(FaceModel.LAYOUT_HYBRID, 1.0));
    for (var hour = 0; hour < 12; hour += 1) {
        for (var minute = 0; minute < 60; minute += 1) {
            for (var which = 0; which < 2; which += 1) {
                var facet = FaceModel.handFacetPoints(hour, minute, which == 0);
                Test.assertEqual(facet.size(), 4);
                assertSharedDialRoundGuard(facet, 0, 0, 3);
                var whole = FaceModel.handPoints(hour, minute, which == 0);
                Test.assertEqual(facet[1][0], whole[2][0]);
                Test.assertEqual(facet[1][1], whole[2][1]);
            }
        }
    }
    return true;
}

function assertHybridPoint(point as Lang.Array<Lang.Number>,
        x as Lang.Number, y as Lang.Number) as Void {
    Test.assertEqual(point.size(), 2);
    Test.assertEqual(point[0], x);
    Test.assertEqual(point[1], y);
}

(:test)
function hybridDiverLiteralGeometryAndCardinals(logger as Test.Logger) as Lang.Boolean {
    // Literal source contracts are independent of the rendering implementation.
    Test.assertEqual(FaceModel.HYBRID_CIRCLE_RADIUS, 12);
    Test.assertEqual(FaceModel.HYBRID_CIRCLE_INNER, 10);
    Test.assertEqual(FaceModel.HYBRID_HOUR_DISC_CENTER, 110);
    Test.assertEqual(FaceModel.HYBRID_HOUR_DISC_RADIUS, 15);
    Test.assertEqual(FaceModel.HYBRID_HOUR_DISC_INNER, 13);
    Test.assertEqual(FaceModel.HYBRID_BEZEL_OUTER, 224);
    Test.assertEqual(FaceModel.HYBRID_BEZEL_INNER, 184);
    Test.assertEqual(FaceModel.HYBRID_BEZEL_RADIUS, 206);
    var indices = [1, 2, 4, 5, 7, 8, 10, 11];
    var centers = [[309, 85], [369, 145], [369, 309], [309, 369],
        [145, 369], [85, 309], [85, 145], [145, 85]];
    for (var index = 0; index < indices.size(); index += 1) {
        assertHybridPoint(FaceModel.hybridCircleCenter(indices[index]),
            centers[index][0], centers[index][1]);
    }
    var tick = FaceModel.hybridMinuteTick(0);
    assertHybridPoint(tick[0], 227, 46);
    assertHybridPoint(tick[1], 227, 50);
    tick = FaceModel.hybridMinuteTick(15);
    assertHybridPoint(tick[0], 408, 227);
    assertHybridPoint(tick[1], 404, 227);
    var baton = FaceModel.hybridBaton(3, false);
    assertHybridPoint(baton[0], 377, 221);
    assertHybridPoint(baton[1], 403, 221);
    assertHybridPoint(baton[2], 403, 233);
    assertHybridPoint(baton[3], 377, 233);
    baton = FaceModel.hybridBaton(3, true);
    assertHybridPoint(baton[0], 379, 223);
    assertHybridPoint(baton[2], 401, 231);
    Test.assertEqual(FaceModel.hybridActiveBaton(3, false).size(), 0);
    Test.assertEqual(FaceModel.hybridActiveBaton(3, true).size(), 0);
    Test.assertEqual(FaceModel.hybridActiveBaton(6, false).size(), 4);
    Test.assertEqual(FaceModel.hybridActiveBaton(9, true).size(), 4);
    // The original3baton remains present for sparse AOD, not the active window.
    Test.assertEqual(FaceModel.hybridBaton(3, false).size(), 4);
    var triangle = FaceModel.hybridTriangle(false);
    assertHybridPoint(triangle[0], 211, 51);
    assertHybridPoint(triangle[1], 243, 51);
    assertHybridPoint(triangle[2], 227, 91);
    triangle = FaceModel.hybridTriangle(true);
    assertHybridPoint(triangle[0], 213, 53);
    assertHybridPoint(triangle[2], 227, 89);
    return true;
}

(:test)
function hybridDiverRejectsInvalidGeometry(logger as Test.Logger) as Lang.Boolean {
    var invalid = [null, false, "1", 1.0, -1, 12];
    for (var index = 0; index < invalid.size(); index += 1) {
        Test.assertEqual(FaceModel.hybridCircleCenter(invalid[index]).size(), 0);
        Test.assertEqual(FaceModel.hybridBaton(invalid[index], false).size(), 0);
        Test.assertEqual(FaceModel.hybridActiveBaton(invalid[index], false).size(), 0);
    }
    for (var cardinal = 0; cardinal < 12; cardinal += 3) {
        Test.assertEqual(FaceModel.hybridCircleCenter(cardinal).size(), 0);
    }
    Test.assertEqual(FaceModel.hybridBaton(0, true).size(), 0);
    Test.assertEqual(FaceModel.hybridBaton(1, true).size(), 0);
    Test.assertEqual(FaceModel.hybridMinuteTick(null).size(), 0);
    Test.assertEqual(FaceModel.hybridMinuteTick(1.0).size(), 0);
    Test.assertEqual(FaceModel.hybridMinuteTick(-1).size(), 0);
    Test.assertEqual(FaceModel.hybridMinuteTick(60).size(), 0);
    Test.assertEqual(FaceModel.hybridHourStem(24, 0, false).size(), 0);
    Test.assertEqual(FaceModel.hybridHourTip(0, 60, true).size(), 0);
    Test.assertEqual(FaceModel.hybridHourDiscCenter(null, 0).size(), 0);
    Test.assertEqual(FaceModel.hybridHourSpoke(0, 0, null).size(), 0);
    Test.assertEqual(FaceModel.hybridHourSpoke(0, 0, 1.0).size(), 0);
    Test.assertEqual(FaceModel.hybridHourSpoke(0, 0, -1).size(), 0);
    Test.assertEqual(FaceModel.hybridHourSpoke(0, 0, 3).size(), 0);
    Test.assertEqual(FaceModel.hybridHourSpoke(1.0, 0, 0).size(), 0);
    Test.assertEqual(FaceModel.hybridMinuteHand(24, 0, false).size(), 0);
    Test.assertEqual(FaceModel.hybridMinuteHand(0, null, true).size(), 0);
    return true;
}

(:test)
function hybridSeparatedHourPartsAndMinuteHierarchy(logger as Test.Logger) as Lang.Boolean {
    assertHybridPoint(FaceModel.hybridHourDiscCenter(0, 0), 227, 117);
    assertHybridPoint(FaceModel.hybridHourDiscCenter(3, 0), 337, 227);
    var stem = FaceModel.hybridHourStem(0, 0, false);
    Test.assertEqual(stem.size(), 4);
    assertHybridPoint(stem[0], 222, 245);
    assertHybridPoint(stem[1], 222, 131);
    assertHybridPoint(stem[2], 232, 131);
    var tip = FaceModel.hybridHourTip(0, 0, false);
    Test.assertEqual(tip.size(), 3);
    assertHybridPoint(tip[0], 220, 105);
    assertHybridPoint(tip[1], 227, 83);
    assertHybridPoint(tip[2], 234, 105);
    // Neither polygon spans through the head center at y117. It remains a
    // separately rendered circular face, including in sparse always-on mode.
    Test.assert(stem[1][1] > 117 && tip[0][1] < 117);
    var first = FaceModel.hybridHourSpoke(3, 0, 0);
    var second = FaceModel.hybridHourSpoke(3, 0, 1);
    var third = FaceModel.hybridHourSpoke(3, 0, 2);
    assertHybridPoint(first[0], 337, 227);
    assertHybridPoint(first[1], 350, 227);
    assertHybridPoint(second[1], 331, 216);
    assertHybridPoint(third[1], 331, 238);
    var minute = FaceModel.hybridMinuteHand(3, 15, false);
    Test.assertEqual(minute.size(), 5);
    assertHybridPoint(minute[0], 209, 223);
    assertHybridPoint(minute[1], 381, 221);
    assertHybridPoint(minute[2], 399, 227);
    assertHybridPoint(minute[3], 381, 233);
    Test.assertEqual(minute[3][1] - minute[1][1], 12);
    minute = FaceModel.hybridMinuteHand(3, 15, true);
    assertHybridPoint(minute[0], 211, 225);
    assertHybridPoint(minute[2], 397, 227);
    Test.assertEqual(minute[3][1] - minute[1][1], 8);
    return true;
}

function assertHybridRectSeparate(left as Lang.Number, top as Lang.Number,
        width as Lang.Number, bottom as Lang.Number,
        markerLeft as Lang.Number, markerTop as Lang.Number,
        markerRight as Lang.Number, markerBottom as Lang.Number) as Void {
    Test.assert(left + width < markerLeft || left > markerRight ||
        bottom < markerTop || top > markerBottom);
}

(:test)
function hybridDiverTextBandsAndIndicesStaySeparate(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.HYBRID_DATE_TOP, 140);
    Test.assertEqual(FaceModel.HYBRID_DATE_BOTTOM, 164);
    Test.assertEqual(FaceModel.HYBRID_DATE_WIDTH, 180);
    Test.assertEqual(FaceModel.HYBRID_DAY_LEFT, 356);
    Test.assertEqual(FaceModel.HYBRID_DAY_TOP, 211);
    Test.assertEqual(FaceModel.HYBRID_DAY_BOTTOM, 243);
    Test.assertEqual(FaceModel.HYBRID_DAY_WIDTH, 40);
    Test.assertEqual(FaceModel.HYBRID_CLOCK_LEFT, 165);
    Test.assertEqual(FaceModel.HYBRID_CLOCK_TOP, 258);
    Test.assertEqual(FaceModel.HYBRID_CLOCK_BOTTOM, 292);
    Test.assertEqual(FaceModel.HYBRID_CLOCK_WIDTH, 124);
    Test.assertEqual(FaceModel.HYBRID_DATA_TOP, 298);
    Test.assertEqual(FaceModel.HYBRID_DATA_BOTTOM, 342);
    Test.assertEqual(FaceModel.HYBRID_DATA_WIDTH, 112);
    Test.assertEqual(FaceModel.HYBRID_LEFT_X, 109);
    Test.assertEqual(FaceModel.HYBRID_RIGHT_X, 233);
    Test.assertEqual(FaceModel.HYBRID_CHARGE_TOP, 345);
    Test.assertEqual(FaceModel.HYBRID_CHARGE_BOTTOM, 369);
    Test.assertEqual(FaceModel.HYBRID_CHARGE_WIDTH, 126);
    // These fixed literal boxes test composition geometry, not glyph masks or
    // universal hand visibility. The opaque clock can occlude moving hands.
    var bands = [[137, 140, 180, 164], [356, 211, 40, 243],
        [165, 258, 124, 292], [109, 298, 112, 342],
        [233, 298, 112, 342], [164, 345, 126, 369]];
    var indices = [1, 2, 4, 5, 7, 8, 10, 11];
    for (var index = 0; index < indices.size(); index += 1) {
        var center = FaceModel.hybridCircleCenter(indices[index]);
        for (var band = 0; band < bands.size(); band += 1) {
            assertHybridRectSeparate(bands[band][0], bands[band][1], bands[band][2],
                bands[band][3], center[0] - 12, center[1] - 12,
                center[0] + 12, center[1] + 12);
        }
    }
    var fixed = [[221, 377, 233, 403],
        [51, 221, 77, 233], [211, 51, 243, 91]];
    for (var marker = 0; marker < fixed.size(); marker += 1) {
        for (var band = 0; band < bands.size(); band += 1) {
            assertHybridRectSeparate(bands[band][0], bands[band][1], bands[band][2],
                bands[band][3], fixed[marker][0], fixed[marker][1],
                fixed[marker][2], fixed[marker][3]);
        }
    }
    var window = [[356, 211], [396, 211], [396, 243], [356, 243]]
        as Lang.Array<Graphics.Point2D>;
    assertSharedDialRoundGuard(window, 0, 0, 2);
    var clock = [[165, 258], [289, 258], [289, 292], [165, 292]]
        as Lang.Array<Graphics.Point2D>;
    assertSharedDialRoundGuard(clock, 0, 0, 2);
    Test.assert(356 > 227 + 8 && 396 < 404);
    // This literal intersection distinguishes the removed active3baton from
    // an accidentally still-drawn marker beneath the new three-o'clock window.
    Test.assert(356 < 377 && 396 > 377 && 211 < 221 && 243 > 233);
    Test.assertEqual(FaceModel.hybridActiveBaton(3, false).size(), 0);
    Test.assertEqual(FaceModel.hybridBaton(3, false).size(), 4);
    // The new day window is small. Its40x32 light area is less than one
    // quarter of the old112x46 white digital-time window.
    Test.assert(40 * 32 * 4 < 112 * 46);
    return true;
}

function assertHybridHeadClearOfRect(head as Lang.Array<Lang.Number>,
        left as Lang.Number, top as Lang.Number,
        right as Lang.Number, bottom as Lang.Number) as Void {
    var dx = head[0] < left ? left - head[0] : (head[0] > right ? head[0] - right : 0);
    var dy = head[1] < top ? top - head[1] : (head[1] > bottom ? head[1] - bottom : 0);
    //15px ink radius plus2px clearance. This is a geometry assertion; it is
    // not an assertion that the tip, stem or every other reading stays clear.
    Test.assert(dx * dx + dy * dy > 17 * 17);
}

(:test)
function hybridProtectedFieldsClearTheHourHeadForEveryMinute(logger as Test.Logger) as Lang.Boolean {
    assertHybridPoint(FaceModel.hybridHourDiscCenter(0, 0), 227, 117);
    assertHybridPoint(FaceModel.hybridHourDiscCenter(3, 0), 337, 227);
    assertHybridPoint(FaceModel.hybridHourDiscCenter(6, 0), 227, 337);
    assertHybridPoint(FaceModel.hybridHourDiscCenter(9, 0), 117, 227);
    for (var hour = 0; hour < 12; hour += 1) {
        for (var minute = 0; minute < 60; minute += 1) {
            var head = FaceModel.hybridHourDiscCenter(hour, minute);
            assertHybridHeadClearOfRect(head, 165, 258, 289, 292);
            assertHybridHeadClearOfRect(head, 356, 211, 396, 243);
        }
    }
    return true;
}

(:test)
function hybridBezelGlyphsHaveBoundedEditablePaths(logger as Test.Logger) as Lang.Boolean {
    Test.assertEqual(FaceModel.hybridBezelDigit(-1).size(), 0);
    Test.assertEqual(FaceModel.hybridBezelDigit(6).size(), 0);
    Test.assertEqual(FaceModel.hybridBezelDigit(1).size(), 2);
    for (var digit = 0; digit <= 5; digit += 1) {
        var paths = FaceModel.hybridBezelDigit(digit);
        Test.assert(paths.size() > 0);
        for (var path = 0; path < paths.size(); path += 1) {
            Test.assert(paths[path].size() >= 2);
            for (var point = 0; point < paths[path].size(); point += 1) {
                var p = paths[path][point];
                Test.assert(p[0] >= 0 && p[0] <= 10 && p[1] >= 0 && p[1] <= 24);
                for (var value = 10; value <= 50; value += 10) {
                    var turn = (value / 60.0).toFloat();
                    for (var offset = -12; offset <= 2; offset += 14) {
                        var projected = FaceModel.radialPoint(turn, 218 - p[1], p[0] + offset);
                        var previous = point > 0 ? paths[path][point - 1] : p;
                        var first = FaceModel.radialPoint(turn, 218 - previous[1], previous[0] + offset);
                        var ends = [first, projected] as Lang.Array<Graphics.Point2D>;
                        assertSharedDialRoundGuard(ends, 0, 0, 3);
                    }
                }
            }
        }
    }
    return true;
}

(:test)
function hybridTranslationIsPureAndInvalidMinuteStaysEmpty(logger as Test.Logger) as Lang.Boolean {
    var source = [[227, 97], [220, 117], [234, 117]] as Lang.Array<Graphics.Point2D>;
    var expected = [[225, 95], [218, 115], [232, 115]];
    var shifted = FaceModel.hybridShiftPoints(source, 0);
    for (var point = 0; point < source.size(); point += 1) {
        assertHybridPoint(shifted[point], expected[point][0], expected[point][1]);
    }
    assertHybridPoint(source[0], 227, 97);
    assertHybridPoint(source[1], 220, 117);
    assertHybridPoint(source[2], 234, 117);
    Test.assertEqual(FaceModel.hybridShiftPoints(source, null).size(), 0);
    Test.assertEqual(FaceModel.hybridShiftPoints(source, 1.0).size(), 0);
    Test.assertEqual(FaceModel.hybridShiftPoints(source, -1).size(), 0);
    Test.assertEqual(FaceModel.hybridShiftPoints(source, 60).size(), 0);
    return true;
}

(:test)
function hybridAllMinuteShapesAndFourShiftsStayRound(logger as Test.Logger) as Lang.Boolean {
    var phases = [[-2, -2], [2, -2], [2, 2], [-2, 2]];
    for (var tick = 0; tick < 60; tick += 1) {
        assertSharedDialRoundGuard(FaceModel.hybridMinuteTick(tick), 0, 0, 3);
    }
    var indices = [1, 2, 4, 5, 7, 8, 10, 11];
    for (var index = 0; index < indices.size(); index += 1) {
        var center = FaceModel.hybridCircleCenter(indices[index]);
        var bounds = [[center[0] - 12, center[1] - 12],
            [center[0] + 12, center[1] + 12]] as Lang.Array<Graphics.Point2D>;
        for (var phase = 0; phase < phases.size(); phase += 1) {
            assertSharedDialRoundGuard(bounds, phases[phase][0], phases[phase][1], 3);
        }
    }
    for (var inset = 0; inset < 2; inset += 1) {
        for (var cardinal = 3; cardinal < 12; cardinal += 3) {
            for (var phase = 0; phase < phases.size(); phase += 1) {
                assertSharedDialRoundGuard(FaceModel.hybridShiftPoints(
                    FaceModel.hybridBaton(cardinal, inset == 1), phase), 0, 0, 3);
            }
        }
        for (var phase = 0; phase < phases.size(); phase += 1) {
            assertSharedDialRoundGuard(FaceModel.hybridShiftPoints(
                FaceModel.hybridTriangle(inset == 1), phase), 0, 0, 3);
        }
        for (var hour = 0; hour < 12; hour += 1) {
            for (var minute = 0; minute < 60; minute += 1) {
                var polygons = [FaceModel.hybridHourStem(hour, minute, inset == 1),
                    FaceModel.hybridHourTip(hour, minute, inset == 1),
                    FaceModel.hybridMinuteHand(hour, minute, inset == 1)];
                for (var polygon = 0; polygon < polygons.size(); polygon += 1) {
                    assertSharedDialRoundGuard(polygons[polygon], 0, 0, 3);
                    for (var phase = 0; phase < phases.size(); phase += 1) {
                        assertSharedDialRoundGuard(polygons[polygon],
                            phases[phase][0], phases[phase][1], 3);
                    }
                }
                var head = FaceModel.hybridHourDiscCenter(hour, minute);
                var headBounds = [[head[0] - 15, head[1] - 15],
                    [head[0] + 15, head[1] + 15]] as Lang.Array<Graphics.Point2D>;
                for (var phase = 0; phase < phases.size(); phase += 1) {
                    assertSharedDialRoundGuard(headBounds,
                        phases[phase][0], phases[phase][1], 3);
                }
                for (var spoke = 0; spoke < 3; spoke += 1) {
                    var line = FaceModel.hybridHourSpoke(hour, minute, spoke);
                    Test.assertEqual(line.size(), 2);
                    for (var phase = 0; phase < phases.size(); phase += 1) {
                        assertSharedDialRoundGuard(line, phases[phase][0], phases[phase][1], 3);
                    }
                }
            }
        }
    }
    return true;
}

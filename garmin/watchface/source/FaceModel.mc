using Toybox.Graphics;
using Toybox.Lang;
using Toybox.Math;
using Toybox.System;

module FaceModel {
    const DISPLAY_SIZE = 454;
    const AOD_MAX_WIDTH = 192;
    const AOD_MAX_HEIGHT = 64;
    const AOD_SHIFT = 16;
    const CALENDAR_TOP = 55;
    const CALENDAR_BOTTOM = 105;
    const CALENDAR_WIDTH = 270;
    const TIME_TOP = 113;
    const TIME_BOTTOM = 267;
    const TIME_WIDTH = 380;
    const DATA_TOP = 278;
    const DATA_BOTTOM = 390;
    const DATA_WIDTH = 300;
    const BATTERY_TOP = 395;
    const BATTERY_BOTTOM = 427;
    const BATTERY_WIDTH = 172;
    const LAYOUT_ANALOG = 0;
    const LAYOUT_DIGITAL = 1;
    const LAYOUT_HYBRID = 2;
    const HYBRID_DATE_TOP = 140;
    const HYBRID_DATE_BOTTOM = 164;
    const HYBRID_DATE_WIDTH = 180;
    const HYBRID_DAY_LEFT = 356;
    const HYBRID_DAY_TOP = 211;
    const HYBRID_DAY_BOTTOM = 243;
    const HYBRID_DAY_WIDTH = 40;
    const HYBRID_CLOCK_LEFT = 165;
    const HYBRID_CLOCK_TOP = 258;
    const HYBRID_CLOCK_BOTTOM = 292;
    const HYBRID_CLOCK_WIDTH = 124;
    const HYBRID_DATA_TOP = 298;
    const HYBRID_DATA_BOTTOM = 342;
    const HYBRID_DATA_WIDTH = 112;
    const HYBRID_LEFT_X = 109;
    const HYBRID_RIGHT_X = 233;
    const HYBRID_CHARGE_TOP = 345;
    const HYBRID_CHARGE_BOTTOM = 369;
    const HYBRID_CHARGE_WIDTH = 126;
    // The original Analog/Digital geometry below remains independent of Hybrid.
    const HYBRID_MARKER_CENTER = 164;
    const HYBRID_CIRCLE_RADIUS = 12;
    const HYBRID_CIRCLE_INNER = 10;
    const HYBRID_BATON_INNER = 150;
    const HYBRID_BATON_OUTER = 176;
    const HYBRID_BATON_HALF = 6;
    const HYBRID_TRIANGLE_INNER = 136;
    const HYBRID_TRIANGLE_OUTER = 176;
    const HYBRID_TRIANGLE_HALF = 16;
    const HYBRID_TICK_OUTER = 181;
    const HYBRID_TICK_INNER = 177;
    const HYBRID_HOUR_DISC_CENTER = 110;
    const HYBRID_HOUR_DISC_RADIUS = 15;
    const HYBRID_HOUR_DISC_INNER = 13;
    const HYBRID_HOUR_STEM_INNER = -18;
    const HYBRID_HOUR_STEM_OUTER = 96;
    const HYBRID_HOUR_STEM_HALF = 5;
    const HYBRID_HOUR_TIP_BASE = 122;
    const HYBRID_HOUR_TIP_HALF = 7;
    const HYBRID_HOUR_TIP_LENGTH = 144;
    const HYBRID_MINUTE_LENGTH = 172;
    const HYBRID_MINUTE_HALF = 6;
    const HYBRID_MINUTE_TAIL_HALF = 4;
    const HYBRID_BEZEL_OUTER = 224;
    const HYBRID_BEZEL_INNER = 184;
    const HYBRID_BEZEL_RADIUS = 206;
    const INTER_CLOCK_CHARACTERS = "0123456789:-";
    const DIAL_CENTER = 227;
    const TICK_OUTER = 221;
    const TICK_INNER = 215;
    const MARKER_OUTER = 218;
    const HOUR_HAND_LENGTH = 130;
    const MINUTE_HAND_LENGTH = 191;
    const ANALOG_DATE_TOP = 94;
    const ANALOG_DATE_BOTTOM = 124;
    const ANALOG_DATE_WIDTH = 230;
    const ANALOG_DATA_TOP = 270;
    const ANALOG_DATA_BOTTOM = 352;
    const ANALOG_DATA_WIDTH = 132;
    const ANALOG_LEFT_X = 84;
    const ANALOG_RIGHT_X = 238;
    const ANALOG_CHARGE_TOP = 364;
    const ANALOG_CHARGE_BOTTOM = 390;
    const ANALOG_CHARGE_WIDTH = 180;

    function isLayout(value as Lang.Object or Null) as Lang.Boolean {
        if (!(value instanceof Lang.Number)) { return false; }
        var choice = value as Lang.Number;
        return choice == LAYOUT_ANALOG || choice == LAYOUT_DIGITAL || choice == LAYOUT_HYBRID;
    }

    function interClockEligible(layout as Lang.Number, scale as Lang.Float) as Lang.Boolean {
        // Fixed bitmap metrics never replace the device's scaled native type.
        return layout == LAYOUT_DIGITAL && scale == 1.0;
    }

    function interClockText(text as Lang.String) as Lang.Boolean {
        if (text.length() == 0) { return false; }
        for (var index = 0; index < text.length(); index += 1) {
            var glyph = text.substring(index, index + 1);
            if (glyph == null || INTER_CLOCK_CHARACTERS.find(glyph) == null) {
                return false;
            }
        }
        return true;
    }

    function sanitizeLayout(value as Lang.Object or Null) as Lang.Number {
        return isLayout(value) ? (value as Lang.Number) : LAYOUT_HYBRID;
    }

    function sanitizeDateFormat(value as Lang.Object or Null) as Lang.Number {
        if (value instanceof Lang.Number && (value as Lang.Number) >= 0 &&
                (value as Lang.Number) <= 2) { return value as Lang.Number; }
        return 0;
    }

    function hybridDate(day as Lang.Number, month as Lang.Number, year as Lang.Number,
            monthName as Lang.Object or Null, weekdayName as Lang.Object or Null,
            order as Lang.Number) as Lang.String {
        var iso = formatDate(day, month, year);
        if (iso.equals("---- -- --")) { return "--- -- ---"; }
        // Abbreviations are device/language dependent. The reviewed public
        // DeviceSettings API does not expose a native date-order preference.
        if (!(monthName instanceof Lang.String) || !(weekdayName instanceof Lang.String)) {
            return iso;
        }
        var mon = monthName as Lang.String;
        var week = weekdayName as Lang.String;
        if (mon.length() == 0 || week.length() == 0) { return iso; }
        if (order == 2) { return week + " " + iso; }
        var date = order == 1 ? mon + " " + day.format("%d") : day.format("%d") + " " + mon;
        return week + " " + date;
    }

    function hybridCharge(value as Lang.Object or Null,
            charging as Lang.Object or Null) as Lang.String {
        return (charging instanceof Lang.Boolean && (charging as Lang.Boolean) ? "CHG " : "BAT ") +
            formatBattery(value);
    }

    function hybridDay(day as Lang.Number, month as Lang.Number, year as Lang.Number) as Lang.String {
        return formatDate(day, month, year).equals("---- -- --") ? "--" : day.format("%d");
    }

    function hybridDetail(data as Lang.Dictionary<Lang.String, Lang.String>) as Lang.String {
        // Only Hybrid compresses its presentation. Provider values, freshness
        // boundaries and the legacy layouts retain their original contracts.
        if (data["label"].equals("Steps")) { return "STEPS"; }
        var detail = data["detail"];
        if (detail.equals("Unavailable")) { return "NO WEATHER"; }
        if (detail.equals("Cached <1h")) { return "CACHE <1h"; }
        if (detail.find("Cached ") == 0) { return "CACHE " + detail.substring(7, detail.length()); }
        if (detail.find("Stale ") == 0) { return "STALE " + detail.substring(6, detail.length()); }
        return "AGE UNKNOWN";
    }

    function hybridBezelDigit(digit as Lang.Number) as Lang.Array<Lang.Array<Graphics.Point2D>> {
        // Original chamfered line glyphs, 10 by 24 units. Dynamic data never
        // uses these fixed bezel shapes or depends on a decorative font.
        if (digit == 0) { return [[[2,0],[8,0],[10,2],[10,22],[8,24],[2,24],[0,22],[0,2],[2,0]]]; }
        if (digit == 1) { return [[[1,4],[5,0],[5,24]], [[1,24],[9,24]]]; }
        if (digit == 2) { return [[[0,2],[2,0],[8,0],[10,2],[10,9],[0,24],[10,24]]]; }
        if (digit == 3) { return [[[0,0],[8,0],[10,2],[10,10],[7,12],[10,14],[10,22],[8,24],[0,24]], [[3,12],[7,12]]]; }
        if (digit == 4) { return [[[7,24],[7,0],[0,16],[10,16]]]; }
        if (digit == 5) { return [[[10,0],[0,0],[0,11],[8,11],[10,13],[10,22],[8,24],[0,24]]]; }
        return [];
    }

    function hybridMinuteTick(index as Lang.Object or Null)
            as Lang.Array<Graphics.Point2D> {
        var i = integerValue(index);
        if (i == null || i < 0 || i >= 60) { return []; }
        var turn = (i / 60.0).toFloat();
        return [radialPoint(turn, HYBRID_TICK_OUTER, 0),
            radialPoint(turn, HYBRID_TICK_INNER, 0)];
    }

    function hybridCircleCenter(index as Lang.Object or Null) as Lang.Array<Lang.Number> {
        var i = integerValue(index);
        if (i == null || i < 1 || i >= 12 || i % 3 == 0) { return []; }
        return radialPoint((i / 12.0).toFloat(), HYBRID_MARKER_CENTER, 0);
    }

    function hybridBaton(index as Lang.Object or Null, inset as Lang.Boolean)
            as Lang.Array<Graphics.Point2D> {
        var i = integerValue(index);
        if (i == null || (i != 3 && i != 6 && i != 9)) { return []; }
        var turn = (i / 12.0).toFloat();
        var amount = inset ? 2 : 0;
        var inner = HYBRID_BATON_INNER + amount;
        var outer = HYBRID_BATON_OUTER - amount;
        var half = HYBRID_BATON_HALF - amount;
        return [radialPoint(turn, inner, -half), radialPoint(turn, outer, -half),
            radialPoint(turn, outer, half), radialPoint(turn, inner, half)];
    }

    function hybridActiveBaton(index as Lang.Object or Null, inset as Lang.Boolean)
            as Lang.Array<Graphics.Point2D> {
        // The active three-o'clock aperture replaces this baton. Sparse AOD
        // omits the aperture and can retain the same original three batons.
        var i = integerValue(index);
        if (i == null || i == 3) { return []; }
        return hybridBaton(i, inset);
    }

    function hybridTriangle(inset as Lang.Boolean) as Lang.Array<Graphics.Point2D> {
        var amount = inset ? 2 : 0;
        return [radialPoint(0.0, HYBRID_TRIANGLE_OUTER - amount, -HYBRID_TRIANGLE_HALF + amount),
            radialPoint(0.0, HYBRID_TRIANGLE_OUTER - amount, HYBRID_TRIANGLE_HALF - amount),
            radialPoint(0.0, HYBRID_TRIANGLE_INNER + amount, 0)];
    }

    function hybridHourStem(hour as Lang.Object or Null, minute as Lang.Object or Null,
            inset as Lang.Boolean) as Lang.Array<Graphics.Point2D> {
        var turn = hourTurns(hour, minute);
        if (turn == null) { return []; }
        var amount = inset ? 2 : 0;
        var inner = HYBRID_HOUR_STEM_INNER + amount;
        var outer = HYBRID_HOUR_STEM_OUTER - amount;
        var half = HYBRID_HOUR_STEM_HALF - amount;
        return [radialPoint(turn, inner, -half), radialPoint(turn, outer, -half),
            radialPoint(turn, outer, half), radialPoint(turn, inner, half)];
    }

    function hybridHourTip(hour as Lang.Object or Null, minute as Lang.Object or Null,
            inset as Lang.Boolean) as Lang.Array<Graphics.Point2D> {
        var turn = hourTurns(hour, minute);
        if (turn == null) { return []; }
        var amount = inset ? 2 : 0;
        var base = HYBRID_HOUR_TIP_BASE + amount;
        var half = HYBRID_HOUR_TIP_HALF - amount;
        return [radialPoint(turn, base, -half),
            radialPoint(turn, HYBRID_HOUR_TIP_LENGTH - amount, 0),
            radialPoint(turn, base, half)];
    }

    function hybridHourDiscCenter(hour as Lang.Object or Null, minute as Lang.Object or Null)
            as Lang.Array<Lang.Number> {
        var turn = hourTurns(hour, minute);
        if (turn == null) { return []; }
        return radialPoint(turn, HYBRID_HOUR_DISC_CENTER, 0);
    }

    function hybridHourSpoke(hour as Lang.Object or Null, minute as Lang.Object or Null,
            part as Lang.Object or Null) as Lang.Array<Graphics.Point2D> {
        var turn = hourTurns(hour, minute);
        var p = integerValue(part);
        if (turn == null || p == null || p < 0 || p >= 3) { return []; }
        // Local radial/lateral endpoints give three clear sectors. The stem and
        // arrow are separate, so sparse always-on never runs a line through it.
        var radial = p == 0 ? 13 : -6;
        var lateral = p == 0 ? 0 : (p == 1 ? -11 : 11);
        return [radialPoint(turn, HYBRID_HOUR_DISC_CENTER, 0),
            radialPoint(turn, HYBRID_HOUR_DISC_CENTER + radial, lateral)];
    }

    function hybridMinuteHand(hour as Lang.Object or Null, minute as Lang.Object or Null,
            inset as Lang.Boolean) as Lang.Array<Graphics.Point2D> {
        if (!validClock(hour, minute)) { return []; }
        var turn = minuteTurns(minute);
        if (turn == null) { return []; }
        var amount = inset ? 2 : 0;
        var tail = -18 + amount;
        var half = HYBRID_MINUTE_HALF - amount;
        var tailHalf = HYBRID_MINUTE_TAIL_HALF - amount;
        return [radialPoint(turn, tail, -tailHalf),
            radialPoint(turn, HYBRID_MINUTE_LENGTH - 18, -half),
            radialPoint(turn, HYBRID_MINUTE_LENGTH - amount, 0),
            radialPoint(turn, HYBRID_MINUTE_LENGTH - 18, half),
            radialPoint(turn, tail, tailHalf)];
    }

    function hybridShiftPoints(points as Lang.Array<Graphics.Point2D>,
            minute as Lang.Object or Null) as Lang.Array<Graphics.Point2D> {
        var shift = aodAnalogOffset(minute);
        if (shift.size() != 2) { return []; }
        var result = [] as Lang.Array<Graphics.Point2D>;
        for (var point = 0; point < points.size(); point += 1) {
            result.add([points[point][0] + shift[0], points[point][1] + shift[1]]);
        }
        return result;
    }

    function handFacetPoints(hour as Lang.Object or Null, minute as Lang.Object or Null,
            hourHand as Lang.Boolean) as Lang.Array<Graphics.Point2D> {
        if (!validClock(hour, minute)) { return []; }
        var turn = hourHand ? hourTurns(hour, minute) : minuteTurns(minute);
        if (turn == null) { return []; }
        var length = hourHand ? HOUR_HAND_LENGTH : MINUTE_HAND_LENGTH;
        return [radialPoint(turn, -18, 0), radialPoint(turn, length, 0),
            radialPoint(turn, length - 18, hourHand ? 9 : 5),
            radialPoint(turn, -18, hourHand ? 6 : 3)];
    }

    // Turns run clockwise from twelve. The lateral component follows the same
    // rotation, so markers and hand widths use the renderer's actual geometry.
    function radialPoint(turn as Lang.Float, radius as Lang.Number,
            lateral as Lang.Number) as Graphics.Point2D {
        var angle = turn * 2.0 * Math.PI;
        var sine = Math.sin(angle);
        var cosine = Math.cos(angle);
        return [Math.round(DIAL_CENTER + sine * radius + cosine * lateral).toNumber(),
            Math.round(DIAL_CENTER - cosine * radius + sine * lateral).toNumber()];
    }

    function hourTurns(hour as Lang.Object or Null, minute as Lang.Object or Null)
            as Lang.Float or Null {
        if (!validClock(hour, minute)) { return null; }
        return (((hour as Lang.Number) % 12) / 12.0 +
            (minute as Lang.Number) / 720.0).toFloat();
    }

    function minuteTurns(minute as Lang.Object or Null) as Lang.Float or Null {
        if (!validClock(0, minute)) { return null; }
        return ((minute as Lang.Number) / 60.0).toFloat();
    }

    function minuteTick(index as Lang.Number) as Lang.Array<Graphics.Point2D> {
        if (index < 0 || index >= 60) { return []; }
        var turn = (index / 60.0).toFloat();
        return [radialPoint(turn, TICK_OUTER, 0), radialPoint(turn, TICK_INNER, 0)];
    }

    function hourMarker(index as Lang.Number, part as Lang.Number)
            as Lang.Array<Graphics.Point2D> {
        if (index < 0 || index >= 12 || part < 0 || part > (index == 0 ? 1 : 0)) { return []; }
        var turn = (index / 12.0).toFloat();
        var offset = index == 0 ? (part == 0 ? -7 : 7) : 0;
        var half = index != 0 && index % 3 == 0 ? 4 : 3;
        var inner = index % 3 == 0 ? 194 : 200;
        return [radialPoint(turn, inner, offset - half),
            radialPoint(turn, MARKER_OUTER, offset - half),
            radialPoint(turn, MARKER_OUTER, offset + half),
            radialPoint(turn, inner, offset + half)];
    }

    function handPoints(hour as Lang.Object or Null, minute as Lang.Object or Null,
            hourHand as Lang.Boolean) as Lang.Array<Graphics.Point2D> {
        if (!validClock(hour, minute)) { return []; }
        var turn = hourHand ? hourTurns(hour, minute) : minuteTurns(minute);
        if (turn == null) { return []; }
        var length = hourHand ? HOUR_HAND_LENGTH : MINUTE_HAND_LENGTH;
        var half = hourHand ? 9 : 5;
        var tailHalf = hourHand ? 6 : 3;
        return [radialPoint(turn, -18, -tailHalf),
            radialPoint(turn, length - 18, -half), radialPoint(turn, length, 0),
            radialPoint(turn, length - 18, half), radialPoint(turn, -18, tailHalf)];
    }

    function aodAnalogOffset(minute as Lang.Object or Null) as Lang.Array<Lang.Number> {
        var m = integerValue(minute);
        if (m == null || m < 0 || m >= 60) { return []; }
        var phase = m % 4;
        if (phase == 0) { return [-2, -2]; }
        if (phase == 1) { return [2, -2]; }
        if (phase == 2) { return [2, 2]; }
        return [-2, 2];
    }

    function aodAnalogMarker(index as Lang.Object or Null, part as Lang.Object or Null,
            minute as Lang.Object or Null) as Lang.Array<Graphics.Point2D> {
        var i = integerValue(index);
        var p = integerValue(part);
        var shift = aodAnalogOffset(minute);
        if (i == null || p == null || shift.size() != 2) { return []; }
        var points = hourMarker(i, p);
        var result = [] as Lang.Array<Graphics.Point2D>;
        for (var point = 0; point < points.size(); point += 1) {
            result.add([points[point][0] + shift[0], points[point][1] + shift[1]]);
        }
        return result;
    }

    function aodAnalogHandPoints(hour as Lang.Object or Null, minute as Lang.Object or Null,
            hourHand as Lang.Boolean) as Lang.Array<Graphics.Point2D> {
        var shift = aodAnalogOffset(minute);
        if (shift.size() != 2) { return []; }
        var points = handPoints(hour, minute, hourHand);
        var result = [] as Lang.Array<Graphics.Point2D>;
        for (var point = 0; point < points.size(); point += 1) {
            result.add([points[point][0] + shift[0], points[point][1] + shift[1]]);
        }
        return result;
    }

    function fontScale(value as Lang.Object or Null) as Lang.Float {
        if (!(value instanceof Lang.Float) && !(value instanceof Lang.Double) &&
                !(value instanceof Lang.Number)) { return 1.0; }
        var scale = value as Lang.Numeric;
        if (scale != scale || !(scale >= 0.8) || !(scale <= 1.35)) { return 1.0; }
        return scale.toFloat();
    }

    function shortDate(day as Lang.Number, month as Lang.Number,
            weekday as Lang.Number) as Lang.String {
        if (day < 1 || day > 31 || month < 1 || month > 12 ||
                weekday < 1 || weekday > 7) { return "--- -- ---"; }
        var weekdays = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
        var months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
            "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
        return weekdays[weekday - 1] + " " + day.format("%d") + " " + months[month - 1];
    }

    function integerValue(value as Lang.Object or Null) as Lang.Number or Null {
        if (value instanceof Lang.Number) {
            return value as Lang.Number;
        }
        return null;
    }

    function isAppearance(value as Lang.Object or Null) as Lang.Boolean {
        if (!(value instanceof Lang.String)) {
            return false;
        }
        var text = value as Lang.String;
        if (text.equals("Clair")) {
            return true;
        }
        return text.equals("Obscur");
    }

    function sanitizeAppearance(value as Lang.Object or Null) as Lang.String {
        if (!(value instanceof Lang.String)) {
            return "Obscur";
        }
        var text = value as Lang.String;
        if (text.equals("Clair")) {
            return "Clair";
        }
        return "Obscur";
    }

    function validClock(hour as Lang.Object or Null, minute as Lang.Object or Null) as Lang.Boolean {
        var h = integerValue(hour);
        if (h == null) { return false; }
        var m = integerValue(minute);
        if (m == null) { return false; }
        if (h < 0 || h >= 24) { return false; }
        return m >= 0 && m < 60;
    }

    function formatTime(hour as Lang.Object or Null, minute as Lang.Object or Null,
            is24Hour as Lang.Boolean) as Lang.String {
        if (!validClock(hour, minute)) {
            return "--:--";
        }
        var h = hour as Lang.Number;
        var m = minute as Lang.Number;
        if (is24Hour != false) {
            return h.format("%02d") + ":" + m.format("%02d");
        }
        var twelve = h % 12;
        if (twelve == 0) {
            twelve = 12;
        }
        return twelve.format("%d") + ":" + m.format("%02d");
    }

    function period(hour as Lang.Object or Null, is24Hour as Lang.Boolean) as Lang.String {
        if (is24Hour != false || !validClock(hour, 0)) {
            return "";
        }
        return (hour as Lang.Number) < 12 ? "AM" : "PM";
    }

    function formatActiveTime(hour as Lang.Object or Null, minute as Lang.Object or Null,
            is24Hour as Lang.Boolean) as Lang.String {
        var time = formatTime(hour, minute, is24Hour);
        if (!validClock(hour, minute)) {
            return time;
        }
        var suffix = period(hour, is24Hour);
        return suffix.length() == 0 ? time : time + " " + suffix;
    }

    function isLeapYear(year as Lang.Number) as Lang.Boolean {
        return year % 400 == 0 || (year % 4 == 0 && year % 100 != 0);
    }

    function daysInMonth(month as Lang.Number, year as Lang.Number) as Lang.Number {
        if (month == 2) {
            return isLeapYear(year) ? 29 : 28;
        }
        if (month == 4 || month == 6 || month == 9 || month == 11) {
            return 30;
        }
        return 31;
    }

    function formatDate(day as Lang.Object or Null, month as Lang.Object or Null,
            year as Lang.Object or Null) as Lang.String {
        var d = integerValue(day);
        if (d == null) { return "---- -- --"; }
        var m = integerValue(month);
        if (m == null) { return "---- -- --"; }
        var y = integerValue(year);
        if (y == null) { return "---- -- --"; }
        if (y < 1 || y > 9999) { return "---- -- --"; }
        if (m < 1 || m > 12) { return "---- -- --"; }
        if (d < 1 || d > daysInMonth(m, y)) { return "---- -- --"; }
        return y.format("%04d") + "-" + m.format("%02d") + "-" + d.format("%02d");
    }

    function formatBattery(value as Lang.Object or Null) as Lang.String {
        if (value instanceof Lang.Number) { return boundedBattery(value as Lang.Number); }
        if (value instanceof Lang.Long) { return boundedBattery(value as Lang.Long); }
        if (value instanceof Lang.Float) { return boundedBattery(value as Lang.Float); }
        if (value instanceof Lang.Double) { return boundedBattery(value as Lang.Double); }
        return "--%";
    }

    function boundedBattery(value as Lang.Numeric) as Lang.String {
        // NaN can pass ordered comparisons on the target runtime, so reject it first.
        if (value != value) {
            return "--%";
        }
        if (!(value >= 0)) {
            return "--%";
        }
        if (!(value <= 100)) {
            return "--%";
        }
        return value.toNumber().format("%d") + "%";
    }

    function drawMode(sleeping as Lang.Boolean, displayMode as Lang.Object or Null) as Lang.Symbol {
        if (displayMode == System.DISPLAY_MODE_OFF) {
            return :off;
        }
        if (sleeping || displayMode == System.DISPLAY_MODE_LOW_POWER) {
            return :aod;
        }
        if (displayMode == System.DISPLAY_MODE_HIGH_POWER) {
            return :active;
        }
        // An unrecognized display mode must never admit a full active background.
        return :aod;
    }

    function aodFits(width as Lang.Object or Null, height as Lang.Object or Null) as Lang.Boolean {
        var w = integerValue(width);
        if (w == null) { return false; }
        var h = integerValue(height);
        if (h == null) { return false; }
        if (w <= 0 || w > AOD_MAX_WIDTH) { return false; }
        return h > 0 && h <= AOD_MAX_HEIGHT;
    }

    function fitsActiveBand(width as Lang.Object or Null, height as Lang.Object or Null,
            maxWidth as Lang.Object or Null, top as Lang.Object or Null,
            bottom as Lang.Object or Null) as Lang.Boolean {
        var w = integerValue(width);
        if (w == null) { return false; }
        var h = integerValue(height);
        if (h == null) { return false; }
        var limit = integerValue(maxWidth);
        if (limit == null) { return false; }
        var start = integerValue(top);
        if (start == null) { return false; }
        var end = integerValue(bottom);
        if (end == null) { return false; }
        if (w <= 0 || h <= 0) { return false; }
        if (limit <= 0 || limit > DISPLAY_SIZE) { return false; }
        if (start < 0 || end > DISPLAY_SIZE || end <= start) { return false; }
        if (w > limit) { return false; }
        return h <= end - start;
    }

    function aodOffset(minute as Lang.Object or Null) as Lang.Array<Lang.Number> {
        var m = integerValue(minute);
        if (m == null) {
            return [0, 0];
        }
        if (m < 0 || m >= 60) {
            return [0, 0];
        }
        return [(m % 3 - 1) * AOD_SHIFT,
            (((m / 3).toNumber() % 3) - 1) * AOD_SHIFT];
    }
}

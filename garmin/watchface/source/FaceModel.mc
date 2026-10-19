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
    const DIAL_CENTER = 227;
    const TICK_OUTER = 208;
    const TICK_INNER = 202;
    const MARKER_OUTER = 196;
    const HOUR_HAND_LENGTH = 114;
    const MINUTE_HAND_LENGTH = 168;
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
        return choice == LAYOUT_ANALOG || choice == LAYOUT_DIGITAL;
    }

    function sanitizeLayout(value as Lang.Object or Null) as Lang.Number {
        return isLayout(value) ? (value as Lang.Number) : LAYOUT_ANALOG;
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
        var inner = index % 3 == 0 ? 172 : 178;
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

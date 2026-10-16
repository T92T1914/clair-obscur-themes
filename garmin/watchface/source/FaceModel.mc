using Toybox.Lang;
using Toybox.System;

module FaceModel {
    const DISPLAY_SIZE = 454;
    const AOD_MAX_WIDTH = 192;
    const AOD_MAX_HEIGHT = 64;
    const AOD_SHIFT = 16;
    const HEADER_TOP = 70;
    const HEADER_BOTTOM = 140;
    const HEADER_WIDTH = 300;
    const TIME_TOP = 150;
    const TIME_BOTTOM = 260;
    const TIME_WIDTH = 374;
    const DATE_TOP = 280;
    const DATE_BOTTOM = 350;
    const DATE_WIDTH = 350;
    const BATTERY_TOP = 360;
    const BATTERY_BOTTOM = 425;
    const BATTERY_WIDTH = 200;

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
        // Separate bounded checks reject NaN without coercing Boolean or String values.
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

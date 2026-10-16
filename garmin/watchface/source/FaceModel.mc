using Toybox.Lang;
using Toybox.System;

module FaceModel {
    const DISPLAY_SIZE = 454;
    const AOD_MAX_WIDTH = 144;
    const AOD_MAX_HEIGHT = 64;
    const AOD_SHIFT = 16;

    function isAppearance(value) {
        return value instanceof Lang.String &&
            (value.equals("Clair") || value.equals("Obscur"));
    }

    function sanitizeAppearance(value) {
        if (value instanceof Lang.String && value.equals("Clair")) {
            return "Clair";
        }
        return "Obscur";
    }

    function validClock(hour, minute) {
        return hour instanceof Lang.Number && minute instanceof Lang.Number &&
            hour >= 0 && hour < 24 && minute >= 0 && minute < 60;
    }

    function formatTime(hour, minute, is24Hour) {
        if (!validClock(hour, minute)) {
            return "--:--";
        }
        if (is24Hour != false) {
            return hour.format("%02d") + ":" + minute.format("%02d");
        }
        var twelve = hour % 12;
        if (twelve == 0) {
            twelve = 12;
        }
        return twelve.format("%d") + ":" + minute.format("%02d");
    }

    function period(hour, is24Hour) {
        if (is24Hour != false || !validClock(hour, 0)) {
            return "";
        }
        return hour < 12 ? "AM" : "PM";
    }

    function isLeapYear(year) {
        return year % 400 == 0 || (year % 4 == 0 && year % 100 != 0);
    }

    function daysInMonth(month, year) {
        if (month == 2) {
            return isLeapYear(year) ? 29 : 28;
        }
        if (month == 4 || month == 6 || month == 9 || month == 11) {
            return 30;
        }
        return 31;
    }

    function formatDate(day, month, year) {
        if (!(day instanceof Lang.Number) || !(month instanceof Lang.Number) ||
            !(year instanceof Lang.Number) || year < 1 || year > 9999 ||
            month < 1 || month > 12 || day < 1 || day > daysInMonth(month, year)) {
            return "---- -- --";
        }
        return year.format("%04d") + "-" + month.format("%02d") + "-" + day.format("%02d");
    }

    function formatBattery(value) {
        var numeric = value instanceof Lang.Number || value instanceof Lang.Long ||
            value instanceof Lang.Float || value instanceof Lang.Double;
        // The conjunction also rejects NaN without coercing Boolean or String values.
        if (!numeric || !(value >= 0 && value <= 100)) {
            return "--%";
        }
        return value.toNumber().format("%d") + "%";
    }

    function drawMode(sleeping, displayMode) {
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

    function aodFits(width, height) {
        return width instanceof Lang.Number && height instanceof Lang.Number &&
            width > 0 && height > 0 && width <= AOD_MAX_WIDTH && height <= AOD_MAX_HEIGHT;
    }

    function aodOffset(minute) {
        if (!(minute instanceof Lang.Number) || minute < 0 || minute >= 60) {
            return [0, 0];
        }
        return [(minute % 3 - 1) * AOD_SHIFT,
            (((minute / 3).toNumber() % 3) - 1) * AOD_SHIFT];
    }
}

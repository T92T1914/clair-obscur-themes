using Toybox.Graphics;
using Toybox.System;
using Toybox.Time;
using Toybox.Time.Gregorian;
using Toybox.WatchUi;

class ClairObscurView extends WatchUi.WatchFace {
    var _sleeping = false;

    function initialize() {
        WatchFace.initialize();
    }

    function onEnterSleep() {
        _sleeping = true;
        WatchUi.requestUpdate();
    }

    function onExitSleep() {
        _sleeping = false;
        WatchUi.requestUpdate();
    }

    function onUpdate(dc) {
        var mode = FaceModel.drawMode(_sleeping, System.getDisplayMode());
        if (dc.getWidth() != FaceModel.DISPLAY_SIZE || dc.getHeight() != FaceModel.DISPLAY_SIZE) {
            mode = :off;
        }
        var appearance = FaceSettings.readAppearance();
        var clair = appearance.equals("Clair");
        var canvas = mode == :active ?
            (clair ? ThemePalette.CLAIR_CANVAS : ThemePalette.OBSCUR_CANVAS) : 0x000000;

        // Full clearing also removes the old active view and every previous minute position.
        dc.clearClip();
        dc.setColor(canvas, canvas);
        dc.clear();
        if (mode == :off) {
            return;
        }
        // One local-time snapshot keeps the displayed date and clock coherent at midnight.
        var local = Gregorian.info(Time.now(), Time.FORMAT_SHORT);
        var is24Hour = System.getDeviceSettings().is24Hour;
        var time = FaceModel.formatTime(local.hour, local.min, is24Hour);
        if (mode == :aod) {
            drawAlwaysOn(dc, time, local.min);
            return;
        }
        drawActive(dc, appearance, time, FaceModel.period(local.hour, is24Hour),
            FaceModel.formatDate(local.day, local.month, local.year),
            FaceModel.formatBattery(System.getSystemStats().battery));
    }

    function drawActive(dc, appearance, time, period, date, battery) {
        var clair = appearance.equals("Clair");
        var canvas = clair ? ThemePalette.CLAIR_CANVAS : ThemePalette.OBSCUR_CANVAS;
        var text = clair ? ThemePalette.CLAIR_TEXT : ThemePalette.OBSCUR_TEXT;
        var muted = clair ? ThemePalette.CLAIR_MUTED : ThemePalette.OBSCUR_MUTED;
        var accent = clair ? ThemePalette.CLAIR_ACCENT : ThemePalette.OBSCUR_ACCENT;
        var center = dc.getWidth() / 2;

        // This prototype uses only the target's built-in fonts, without claiming Inter.
        dc.setColor(accent, canvas);
        dc.drawText(center, 99, Graphics.FONT_TINY, appearance, Graphics.TEXT_JUSTIFY_CENTER);
        dc.setColor(text, canvas);
        var timeFont = Graphics.FONT_NUMBER_HOT;
        if (dc.getTextWidthInPixels(time, timeFont) > dc.getWidth() - 80) {
            timeFont = Graphics.FONT_LARGE;
        }
        dc.drawText(center, 165, timeFont, time, Graphics.TEXT_JUSTIFY_CENTER);
        dc.setColor(muted, canvas);
        dc.drawText(center, 254, Graphics.FONT_TINY, period, Graphics.TEXT_JUSTIFY_CENTER);
        dc.drawText(center, 299, Graphics.FONT_SMALL, date, Graphics.TEXT_JUSTIFY_CENTER);
        dc.setColor(accent, canvas);
        dc.drawText(center, 347, Graphics.FONT_TINY, battery, Graphics.TEXT_JUSTIFY_CENTER);
    }

    function drawAlwaysOn(dc, time, minute) {
        var font = Graphics.FONT_TINY;
        var width = dc.getTextWidthInPixels(time, font);
        var height = dc.getFontHeight(font);
        if (!FaceModel.aodFits(width, height)) {
            return;
        }
        var shift = FaceModel.aodOffset(minute);
        var x = ((dc.getWidth() - width) / 2).toNumber() + shift[0];
        var y = ((dc.getHeight() - height) / 2).toNumber() + shift[1];

        // Even a completely lit 144x64 box is below 10% of this round454 display.
        // This geometric project bound is separate from target runtime/luminance rules.
        dc.setClip(x, y, width, height);
        dc.setColor(ThemePalette.OBSCUR_MUTED, 0x000000);
        dc.drawText(x, y, font, time, Graphics.TEXT_JUSTIFY_LEFT);
        dc.clearClip();
    }
}

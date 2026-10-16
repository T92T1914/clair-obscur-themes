using Toybox.Graphics;
using Toybox.Lang;
using Toybox.System;
using Toybox.Time;
using Toybox.Time.Gregorian;
using Toybox.WatchUi;

class ClairObscurView extends WatchUi.WatchFace {
    var _sleeping as Lang.Boolean = false;

    function initialize() {
        WatchFace.initialize();
    }

    function onEnterSleep() as Void {
        _sleeping = true;
        WatchUi.requestUpdate();
    }

    function onExitSleep() as Void {
        _sleeping = false;
        WatchUi.requestUpdate();
    }

    function onUpdate(dc as Graphics.Dc) as Void {
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
        drawActive(dc, appearance, FaceModel.formatActiveTime(local.hour, local.min, is24Hour),
            FaceModel.formatDate(local.day, local.month, local.year),
            FaceModel.formatBattery(System.getSystemStats().battery));
    }

    function drawActive(dc as Graphics.Dc, appearance as Lang.String, time as Lang.String,
            date as Lang.String, battery as Lang.String) as Void {
        var clair = appearance.equals("Clair");
        var canvas = clair ? ThemePalette.CLAIR_CANVAS : ThemePalette.OBSCUR_CANVAS;
        var text = clair ? ThemePalette.CLAIR_TEXT : ThemePalette.OBSCUR_TEXT;
        var muted = clair ? ThemePalette.CLAIR_MUTED : ThemePalette.OBSCUR_MUTED;
        var accent = clair ? ThemePalette.CLAIR_ACCENT : ThemePalette.OBSCUR_ACCENT;
        // This prototype uses only the target's built-in fonts, without claiming Inter.
        dc.setColor(accent, canvas);
        drawActiveBand(dc, appearance, [Graphics.FONT_TINY, Graphics.FONT_XTINY],
            FaceModel.HEADER_WIDTH, FaceModel.HEADER_TOP, FaceModel.HEADER_BOTTOM);
        dc.setColor(text, canvas);
        drawActiveBand(dc, time, [Graphics.FONT_LARGE, Graphics.FONT_SMALL,
            Graphics.FONT_TINY, Graphics.FONT_XTINY],
            FaceModel.TIME_WIDTH, FaceModel.TIME_TOP, FaceModel.TIME_BOTTOM);
        dc.setColor(muted, canvas);
        drawActiveBand(dc, date, [Graphics.FONT_SMALL, Graphics.FONT_TINY, Graphics.FONT_XTINY],
            FaceModel.DATE_WIDTH, FaceModel.DATE_TOP, FaceModel.DATE_BOTTOM);
        dc.setColor(accent, canvas);
        drawActiveBand(dc, battery, [Graphics.FONT_TINY, Graphics.FONT_XTINY],
            FaceModel.BATTERY_WIDTH, FaceModel.BATTERY_TOP, FaceModel.BATTERY_BOTTOM);
    }

    function drawActiveBand(dc as Graphics.Dc, text as Lang.String,
            fonts as Lang.Array<Graphics.FontDefinition>, maxWidth as Lang.Number,
            top as Lang.Number, bottom as Lang.Number) as Lang.Boolean {
        for (var index = 0; index < fonts.size(); index += 1) {
            var font = fonts[index];
            var width = dc.getTextWidthInPixels(text, font);
            var height = dc.getFontHeight(font);
            if (FaceModel.fitsActiveBand(width, height, maxWidth, top, bottom)) {
                var x = ((dc.getWidth() - maxWidth) / 2).toNumber();
                var y = top + ((bottom - top - height) / 2).toNumber();
                dc.setClip(x, top, maxWidth, bottom - top);
                dc.drawText(dc.getWidth() / 2, y, font, text, Graphics.TEXT_JUSTIFY_CENTER);
                dc.clearClip();
                return true;
            }
        }
        return false;
    }

    function drawAlwaysOn(dc as Graphics.Dc, time as Lang.String, minute as Lang.Number) as Void {
        var fonts = [Graphics.FONT_TINY, Graphics.FONT_XTINY];
        for (var index = 0; index < fonts.size(); index += 1) {
            var font = fonts[index];
            var width = dc.getTextWidthInPixels(time, font);
            var height = dc.getFontHeight(font);
            if (!FaceModel.aodFits(width, height)) {
                continue;
            }
            var shift = FaceModel.aodOffset(minute);
            var x = ((dc.getWidth() - width) / 2).toNumber() + shift[0];
            var y = ((dc.getHeight() - height) / 2).toNumber() + shift[1];

            // Even a completely lit 192x64 box is below 10% of this round454 display.
            // This geometric project bound is separate from target runtime/luminance rules.
            dc.setClip(x, y, width, height);
            dc.setColor(ThemePalette.OBSCUR_MUTED, 0x000000);
            dc.drawText(x, y, font, time, Graphics.TEXT_JUSTIFY_LEFT);
            dc.clearClip();
            return;
        }
    }
}

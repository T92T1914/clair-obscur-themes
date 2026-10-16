using Toybox.Graphics;
using Toybox.Lang;
using Toybox.System;
using Toybox.Time;
using Toybox.Time.Gregorian;
using Toybox.WatchUi;

class ClairObscurView extends WatchUi.WatchFace {
    var _sleeping as Lang.Boolean = false;
    var _fontScale as Lang.Float = 0.0;
    var _clockFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _calendarFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _valueFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _labelFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _detailFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _batteryFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];

    function initialize() { WatchFace.initialize(); }
    function onEnterSleep() as Void { _sleeping = true; WatchUi.requestUpdate(); }
    function onExitSleep() as Void { _sleeping = false; WatchUi.requestUpdate(); }

    function fonts(face as Lang.String, sizes as Lang.Array<Lang.Number>,
            fallback as Graphics.FontDefinition, scale as Lang.Float)
            as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> {
        var result = [] as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont>;
        for (var i = 0; i < sizes.size(); i += 1) {
            var font = Graphics.getVectorFont({:face => face, :size => sizes[i] * scale});
            if (font != null) { result.add(font); }
        }
        var scaledFallback = Graphics.getVectorFont({:font => fallback, :scale => scale});
        result.add(scaledFallback != null ? scaledFallback : fallback);
        return result;
    }

    function refreshFonts() as Void {
        var settings = System.getDeviceSettings();
        var scale = settings has :fontScale ? FaceModel.fontScale(settings.fontScale) : 1.0;
        if (_fontScale == scale) { return; }
        _fontScale = scale;
        // Reference native target faces without copying or claiming Inter fonts.
        _clockFonts = fonts("BionicBold", [108, 96, 84], Graphics.FONT_LARGE, scale);
        _calendarFonts = fonts("RobotoMedium", [23, 20, 18], Graphics.FONT_XTINY, scale);
        _valueFonts = fonts("BionicBold", [42, 34, 24, 18], Graphics.FONT_XTINY, scale);
        _labelFonts = fonts("RobotoCondensedRegular", [20, 18, 16], Graphics.FONT_XTINY, scale);
        _detailFonts = fonts("RobotoCondensedRegular", [16, 14, 12], Graphics.FONT_XTINY, scale);
        _batteryFonts = fonts("RobotoMedium", [20, 18, 16], Graphics.FONT_XTINY, scale);
    }

    function pickFont(dc as Graphics.Dc, text as Lang.String,
            candidates as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont>,
            width as Lang.Number, height as Lang.Number)
            as Graphics.FontDefinition or Graphics.VectorFont or Null {
        for (var i = 0; i < candidates.size(); i += 1) {
            if (dc.getTextWidthInPixels(text, candidates[i]) <= width &&
                    dc.getFontHeight(candidates[i]) <= height) { return candidates[i]; }
        }
        return null;
    }

    function line(dc as Graphics.Dc, text as Lang.String,
            candidates as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont>,
            width as Lang.Number, top as Lang.Number, bottom as Lang.Number) as Lang.Boolean {
        var font = pickFont(dc, text, candidates, width, bottom - top);
        if (font == null) { return false; }
        var left = ((dc.getWidth() - width) / 2).toNumber();
        dc.setClip(left, top, width, bottom - top);
        dc.drawText(dc.getWidth() / 2, top + ((bottom - top - dc.getFontHeight(font)) / 2),
            font, text, Graphics.TEXT_JUSTIFY_CENTER);
        dc.clearClip();
        return true;
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
        dc.clearClip();
        dc.setColor(canvas, canvas);
        dc.clear();
        if (mode == :off) { return; }
        var moment = Time.now();
        var local = Gregorian.info(moment, Time.FORMAT_SHORT);
        var is24Hour = System.getDeviceSettings().is24Hour;
        var time = FaceModel.formatTime(local.hour, local.min, is24Hour);
        if (mode == :aod) { drawAlwaysOn(dc, time, local.min); return; }
        refreshFonts();
        var date = FaceModel.shortDate(local.day, local.month, local.day_of_week);
        var period = FaceModel.period(local.hour, is24Hour);
        if (period.length() > 0) { date += "  " + period; }
        var text = clair ? ThemePalette.CLAIR_TEXT : ThemePalette.OBSCUR_TEXT;
        var muted = clair ? ThemePalette.CLAIR_MUTED : ThemePalette.OBSCUR_MUTED;
        var accent = clair ? ThemePalette.CLAIR_ACCENT : ThemePalette.OBSCUR_ACCENT;
        dc.setColor(muted, canvas);
        line(dc, date, _calendarFonts, FaceModel.CALENDAR_WIDTH,
            FaceModel.CALENDAR_TOP, FaceModel.CALENDAR_BOTTOM);
        dc.setColor(text, canvas);
        line(dc, time, _clockFonts, FaceModel.TIME_WIDTH, FaceModel.TIME_TOP, FaceModel.TIME_BOTTOM);
        var left = FaceData.readSlot(FaceSettings.readSlot(0), moment.value());
        var right = FaceData.readSlot(FaceSettings.readSlot(1), moment.value());
        drawSlot(dc, left, 77, 140, text, muted, canvas);
        drawSlot(dc, right, 237, 140, text, muted, canvas);
        dc.setColor(accent, canvas);
        line(dc, "BAT " + FaceModel.formatBattery(System.getSystemStats().battery), _batteryFonts,
            FaceModel.BATTERY_WIDTH, FaceModel.BATTERY_TOP, FaceModel.BATTERY_BOTTOM);
    }

    function drawSlot(dc as Graphics.Dc, data as Lang.Dictionary<Lang.String, Lang.String>,
            x as Lang.Number, width as Lang.Number, text as Lang.Number,
            muted as Lang.Number, canvas as Lang.Number) as Void {
        var height = FaceModel.DATA_BOTTOM - FaceModel.DATA_TOP;
        var label = pickFont(dc, data["label"], _labelFonts, width, 34);
        var detail = pickFont(dc, data["detail"], _detailFonts, width, 28);
        if (label == null || detail == null) { return; }
        var available = height - dc.getFontHeight(label) - dc.getFontHeight(detail) - 6;
        var value = pickFont(dc, data["value"], _valueFonts, width, available);
        if (value == null) { return; }
        var total = dc.getFontHeight(label) + dc.getFontHeight(value) + dc.getFontHeight(detail) + 6;
        var y = FaceModel.DATA_TOP + ((height - total) / 2);
        var center = x + width / 2;
        dc.setClip(x, FaceModel.DATA_TOP, width, height);
        dc.setColor(muted, canvas);
        dc.drawText(center, y, label, data["label"], Graphics.TEXT_JUSTIFY_CENTER);
        y += dc.getFontHeight(label) + 3;
        dc.setColor(text, canvas);
        dc.drawText(center, y, value, data["value"], Graphics.TEXT_JUSTIFY_CENTER);
        y += dc.getFontHeight(value) + 3;
        dc.setColor(muted, canvas);
        dc.drawText(center, y, detail, data["detail"], Graphics.TEXT_JUSTIFY_CENTER);
        dc.clearClip();
    }

    function drawAlwaysOn(dc as Graphics.Dc, time as Lang.String, minute as Lang.Number) as Void {
        var candidates = [Graphics.FONT_TINY, Graphics.FONT_XTINY];
        for (var index = 0; index < candidates.size(); index += 1) {
            var font = candidates[index];
            var width = dc.getTextWidthInPixels(time, font);
            var height = dc.getFontHeight(font);
            if (!FaceModel.aodFits(width, height)) { continue; }
            var shift = FaceModel.aodOffset(minute);
            var x = ((dc.getWidth() - width) / 2).toNumber() + shift[0];
            var y = ((dc.getHeight() - height) / 2).toNumber() + shift[1];
            dc.setClip(x, y, width, height);
            dc.setColor(ThemePalette.OBSCUR_MUTED, 0x000000);
            dc.drawText(x, y, font, time, Graphics.TEXT_JUSTIFY_LEFT);
            dc.clearClip();
            return;
        }
    }
}

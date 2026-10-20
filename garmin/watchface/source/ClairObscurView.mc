using Toybox.Graphics;
using Toybox.Lang;
using Toybox.System;
using Toybox.Time;
using Toybox.Time.Gregorian;
using Toybox.WatchUi;

class ClairObscurView extends WatchUi.WatchFace {
    var _sleeping as Lang.Boolean = false;
    var _fontScale as Lang.Float = 0.0;
    var _fontLayout as Lang.Number = -1;
    var _interClock as Graphics.FontReference or Null = null;
    var _clockFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _calendarFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _valueFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _labelFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _detailFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _batteryFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];

    function initialize() {
        WatchFace.initialize();
        // One bounded resource, loaded outside the update handler.
        _interClock = WatchUi.loadResource(Rez.Fonts.InterClock) as Graphics.FontReference;
    }
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

    function refreshFonts(layout as Lang.Number) as Void {
        var settings = System.getDeviceSettings();
        var scale = settings has :fontScale ? FaceModel.fontScale(settings.fontScale) : 1.0;
        if (_fontScale == scale && _fontLayout == layout) { return; }
        _fontScale = scale;
        _fontLayout = layout;
        // Reference native target faces without copying or claiming Inter fonts.
        // Build only the selected active layout's candidates, not two font caches.
        if (layout == FaceModel.LAYOUT_ANALOG) {
            _clockFonts = [];
            _calendarFonts = fonts("RobotoMedium", [20, 18, 16], Graphics.FONT_XTINY, scale);
            _valueFonts = fonts("RobotoMedium", [30, 26, 22, 18, 16], Graphics.FONT_XTINY, scale);
            _labelFonts = fonts("RobotoCondensedRegular", [18, 16, 14], Graphics.FONT_XTINY, scale);
            _batteryFonts = fonts("RobotoMedium", [18, 16, 14], Graphics.FONT_XTINY, scale);
        } else {
            _clockFonts = fonts("BionicBold", [108, 96, 84], Graphics.FONT_LARGE, scale);
            _calendarFonts = fonts("RobotoMedium", [23, 20, 18], Graphics.FONT_XTINY, scale);
            _valueFonts = fonts("BionicBold", [42, 34, 24, 18], Graphics.FONT_XTINY, scale);
            _labelFonts = fonts("RobotoCondensedRegular", [20, 18, 16], Graphics.FONT_XTINY, scale);
            _batteryFonts = fonts("RobotoMedium", [20, 18, 16], Graphics.FONT_XTINY, scale);
        }
        _detailFonts = fonts("RobotoCondensedRegular", [16, 14, 12], Graphics.FONT_XTINY, scale);
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

    function interClock(dc as Graphics.Dc, text as Lang.String) as Lang.Boolean {
        if (!FaceModel.interClockEligible(_fontLayout, _fontScale) ||
                !FaceModel.interClockText(text)) { return false; }
        var font = _interClock;
        if (font == null || dc.getTextWidthInPixels(text, font) > FaceModel.TIME_WIDTH ||
                dc.getFontHeight(font) > FaceModel.TIME_BOTTOM - FaceModel.TIME_TOP) {
            return false;
        }
        var height = dc.getFontHeight(font);
        dc.setClip(((dc.getWidth() - FaceModel.TIME_WIDTH) / 2).toNumber(),
            FaceModel.TIME_TOP, FaceModel.TIME_WIDTH, FaceModel.TIME_BOTTOM - FaceModel.TIME_TOP);
        dc.drawText(dc.getWidth() / 2,
            FaceModel.TIME_TOP + ((FaceModel.TIME_BOTTOM - FaceModel.TIME_TOP - height) / 2),
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
        var layout = FaceSettings.readLayout();
        refreshFonts(layout);
        var date = FaceModel.shortDate(local.day, local.month, local.day_of_week);
        var period = FaceModel.period(local.hour, is24Hour);
        if (period.length() > 0) { date += "  " + period; }
        var text = clair ? ThemePalette.CLAIR_TEXT : ThemePalette.OBSCUR_TEXT;
        var muted = clair ? ThemePalette.CLAIR_MUTED : ThemePalette.OBSCUR_MUTED;
        var accent = clair ? ThemePalette.CLAIR_ACCENT : ThemePalette.OBSCUR_ACCENT;
        var left = FaceData.readSlot(FaceSettings.readSlot(0), moment.value());
        var right = FaceData.readSlot(FaceSettings.readSlot(1), moment.value());
        var charge = FaceModel.formatBattery(System.getSystemStats().battery);
        if (layout == FaceModel.LAYOUT_ANALOG) {
            var border = clair ? ThemePalette.CLAIR_BORDER : ThemePalette.OBSCUR_BORDER;
            drawAnalog(dc, local.hour, local.min, date, charge, left, right, text, muted, border, canvas);
            return;
        }
        dc.setColor(muted, canvas);
        line(dc, date, _calendarFonts, FaceModel.CALENDAR_WIDTH,
            FaceModel.CALENDAR_TOP, FaceModel.CALENDAR_BOTTOM);
        dc.setColor(text, canvas);
        if (!interClock(dc, time)) {
            line(dc, time, _clockFonts, FaceModel.TIME_WIDTH, FaceModel.TIME_TOP, FaceModel.TIME_BOTTOM);
        }
        drawSlot(dc, left, 77, 140, FaceModel.DATA_TOP, FaceModel.DATA_BOTTOM, text, muted, canvas);
        drawSlot(dc, right, 237, 140, FaceModel.DATA_TOP, FaceModel.DATA_BOTTOM, text, muted, canvas);
        dc.setColor(accent, canvas);
        line(dc, "BAT " + charge, _batteryFonts,
            FaceModel.BATTERY_WIDTH, FaceModel.BATTERY_TOP, FaceModel.BATTERY_BOTTOM);
    }

    function analogSlotFonts(dc as Graphics.Dc, data as Lang.Dictionary<Lang.String, Lang.String>,
            width as Lang.Number, height as Lang.Number)
            as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> or Null {
        // Admit the whole three-row group using actual target measurements.
        // Shrinking the value alone can never fix oversized label/detail rows.
        for (var v = 0; v < _valueFonts.size(); v += 1) {
            var value = _valueFonts[v];
            if (dc.getTextWidthInPixels(data["value"], value) > width) { continue; }
            for (var l = 0; l < _labelFonts.size(); l += 1) {
                var label = _labelFonts[l];
                if (dc.getTextWidthInPixels(data["label"], label) > width) { continue; }
                for (var d = 0; d < _detailFonts.size(); d += 1) {
                    var detail = _detailFonts[d];
                    if (dc.getTextWidthInPixels(data["detail"], detail) > width) { continue; }
                    var total = dc.getFontHeight(label) + dc.getFontHeight(value) +
                        dc.getFontHeight(detail) + 6;
                    if (total <= height) { return [label, value, detail]; }
                }
            }
        }
        return null;
    }

    function drawSlot(dc as Graphics.Dc, data as Lang.Dictionary<Lang.String, Lang.String>,
            x as Lang.Number, width as Lang.Number, top as Lang.Number,
            bottom as Lang.Number, text as Lang.Number,
            muted as Lang.Number, canvas as Lang.Number) as Void {
        var height = bottom - top;
        var label = null;
        var detail = null;
        var value = null;
        if (height < 100) {
            var selected = analogSlotFonts(dc, data, width, height);
            if (selected == null) { return; }
            label = selected[0]; value = selected[1]; detail = selected[2];
        } else {
            // Preserve the digital layout's existing 112-pixel row policy.
            label = pickFont(dc, data["label"], _labelFonts, width, 34);
            detail = pickFont(dc, data["detail"], _detailFonts, width, 28);
            if (label == null || detail == null) { return; }
            var available = height - dc.getFontHeight(label) - dc.getFontHeight(detail) - 6;
            value = pickFont(dc, data["value"], _valueFonts, width, available);
        }
        if (label == null || detail == null || value == null) { return; }
        var total = dc.getFontHeight(label) + dc.getFontHeight(value) + dc.getFontHeight(detail) + 6;
        var y = top + ((height - total) / 2);
        var center = x + width / 2;
        dc.setClip(x, top, width, height);
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

    function drawHand(dc as Graphics.Dc, points as Lang.Array<Graphics.Point2D>,
            text as Lang.Number, canvas as Lang.Number) as Void {
        if (points.size() != 5) { return; }
        // A narrow opposing edge keeps the hand legible when it crosses text.
        dc.setColor(canvas, canvas);
        dc.setPenWidth(4);
        for (var index = 0; index < points.size(); index += 1) {
            var next = (index + 1) % points.size();
            dc.drawLine(points[index][0], points[index][1], points[next][0], points[next][1]);
        }
        dc.setColor(text, canvas);
        dc.fillPolygon(points);
        dc.setPenWidth(1);
    }

    function drawAnalog(dc as Graphics.Dc, hour as Lang.Number, minute as Lang.Number,
            date as Lang.String, charge as Lang.String,
            left as Lang.Dictionary<Lang.String, Lang.String>,
            right as Lang.Dictionary<Lang.String, Lang.String>, text as Lang.Number,
            muted as Lang.Number, border as Lang.Number, canvas as Lang.Number) as Void {
        dc.setColor(border, canvas);
        dc.setPenWidth(1);
        for (var tick = 0; tick < 60; tick += 1) {
            var ends = FaceModel.minuteTick(tick);
            dc.drawLine(ends[0][0], ends[0][1], ends[1][0], ends[1][1]);
        }
        dc.setColor(text, canvas);
        for (var index = 0; index < 12; index += 1) {
            dc.fillPolygon(FaceModel.hourMarker(index, 0));
            if (index == 0) { dc.fillPolygon(FaceModel.hourMarker(index, 1)); }
        }
        dc.setColor(muted, canvas);
        line(dc, date, _calendarFonts, FaceModel.ANALOG_DATE_WIDTH,
            FaceModel.ANALOG_DATE_TOP, FaceModel.ANALOG_DATE_BOTTOM);
        drawSlot(dc, left, FaceModel.ANALOG_LEFT_X, FaceModel.ANALOG_DATA_WIDTH,
            FaceModel.ANALOG_DATA_TOP, FaceModel.ANALOG_DATA_BOTTOM, text, muted, canvas);
        drawSlot(dc, right, FaceModel.ANALOG_RIGHT_X, FaceModel.ANALOG_DATA_WIDTH,
            FaceModel.ANALOG_DATA_TOP, FaceModel.ANALOG_DATA_BOTTOM, text, muted, canvas);
        dc.setColor(muted, canvas);
        line(dc, "CHARGE " + charge, _batteryFonts, FaceModel.ANALOG_CHARGE_WIDTH,
            FaceModel.ANALOG_CHARGE_TOP, FaceModel.ANALOG_CHARGE_BOTTOM);
        // Time stays in front. Inner readings can be temporarily crossed by a
        // hand; Digital remains available for an unobscured full-data layout.
        drawHand(dc, FaceModel.handPoints(hour, minute, true), text, canvas);
        drawHand(dc, FaceModel.handPoints(hour, minute, false), text, canvas);
        dc.setColor(text, canvas);
        dc.fillCircle(FaceModel.DIAL_CENTER, FaceModel.DIAL_CENTER, 8);
        dc.setColor(canvas, canvas);
        dc.fillCircle(FaceModel.DIAL_CENTER, FaceModel.DIAL_CENTER, 3);
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

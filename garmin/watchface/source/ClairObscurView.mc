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
    var _bezelFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _periodFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];
    var _dayFonts as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> = [];

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
            _dayFonts = [];
            _bezelFonts = [];
            _periodFonts = [];
            _clockFonts = [];
            _calendarFonts = fonts("RobotoMedium", [20, 18, 16], Graphics.FONT_XTINY, scale);
            _valueFonts = fonts("RobotoMedium", [30, 26, 22, 18, 16], Graphics.FONT_XTINY, scale);
            _labelFonts = fonts("RobotoCondensedRegular", [18, 16, 14], Graphics.FONT_XTINY, scale);
            _batteryFonts = fonts("RobotoMedium", [18, 16, 14], Graphics.FONT_XTINY, scale);
        } else if (layout == FaceModel.LAYOUT_HYBRID) {
            _clockFonts = fonts("RobotoMedium", [30, 28, 26, 24, 22, 20, 18, 16], Graphics.FONT_SMALL, scale);
            _calendarFonts = fonts("RobotoMedium", [18, 16, 14, 12], Graphics.FONT_XTINY, scale);
            _dayFonts = fonts("RobotoMedium", [28, 26, 24, 22, 20, 18, 16], Graphics.FONT_XTINY, scale);
            _valueFonts = fonts("RobotoMedium", [24, 22, 20, 18, 16, 14], Graphics.FONT_XTINY, scale);
            _labelFonts = fonts("RobotoCondensedRegular", [14, 12], Graphics.FONT_XTINY, scale);
            _batteryFonts = fonts("RobotoMedium", [18, 16, 14, 12], Graphics.FONT_XTINY, scale);
            _bezelFonts = [];
            _periodFonts = fonts("RobotoMedium", [14, 12, 10], Graphics.FONT_XTINY, scale);
        } else {
            _dayFonts = [];
            _bezelFonts = [];
            _periodFonts = [];
            _clockFonts = fonts("BionicBold", [108, 96, 84], Graphics.FONT_LARGE, scale);
            _calendarFonts = fonts("RobotoMedium", [23, 20, 18], Graphics.FONT_XTINY, scale);
            _valueFonts = fonts("BionicBold", [42, 34, 24, 18], Graphics.FONT_XTINY, scale);
            _labelFonts = fonts("RobotoCondensedRegular", [20, 18, 16], Graphics.FONT_XTINY, scale);
            _batteryFonts = fonts("RobotoMedium", [20, 18, 16], Graphics.FONT_XTINY, scale);
        }
        _detailFonts = fonts("RobotoCondensedRegular",
            layout == FaceModel.LAYOUT_HYBRID ? [14, 12, 10] : [16, 14, 12], Graphics.FONT_XTINY, scale);
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
        var layout = FaceSettings.readLayout();
        if (mode == :aod && layout == FaceModel.LAYOUT_HYBRID) {
            drawHybridAlwaysOn(dc, local.hour, local.min);
            return;
        }
        if (mode == :aod && layout == FaceModel.LAYOUT_ANALOG) {
            drawAnalogAlwaysOn(dc, local.hour, local.min);
            return;
        }
        var is24Hour = System.getDeviceSettings().is24Hour;
        var time = FaceModel.formatTime(local.hour, local.min, is24Hour);
        if (mode == :aod) { drawAlwaysOn(dc, time, local.min); return; }
        refreshFonts(layout);
        var date = FaceModel.shortDate(local.day, local.month, local.day_of_week);
        var period = FaceModel.period(local.hour, is24Hour);
        if (period.length() > 0) { date += "  " + period; }
        var text = clair ? ThemePalette.CLAIR_TEXT : ThemePalette.OBSCUR_TEXT;
        var muted = clair ? ThemePalette.CLAIR_MUTED : ThemePalette.OBSCUR_MUTED;
        var accent = clair ? ThemePalette.CLAIR_ACCENT : ThemePalette.OBSCUR_ACCENT;
        if (layout == FaceModel.LAYOUT_HYBRID) {
            // Same Moment for the numeric clock and device-localized date.
            var names = Gregorian.info(moment, Time.FORMAT_MEDIUM);
            var hybridDate = FaceModel.hybridDate(local.day, local.month as Lang.Number, local.year,
                names.month as Lang.Object, names.day_of_week as Lang.Object, FaceSettings.readDateFormat());
            var day = FaceModel.hybridDay(local.day, local.month as Lang.Number, local.year);
            var weather = FaceData.readSlot(FaceData.WEATHER, moment.value());
            var steps = FaceData.readSlot(FaceData.STEPS, moment.value());
            var stats = System.getSystemStats();
            var battery = FaceModel.hybridCharge(stats.battery as Lang.Object, stats.charging as Lang.Object);
            var frame = clair ? ThemePalette.CLAIR_BORDER : ThemePalette.OBSCUR_BORDER;
            drawHybrid(dc, local.hour, local.min, time, period,
                hybridDate, day, battery, weather, steps, text, muted, frame, canvas);
            return;
        }
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
            if (tick % 5 == 0) { continue; }
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

    function drawAlwaysOnOutline(dc as Graphics.Dc, points as Lang.Array<Graphics.Point2D>) as Void {
        if (points.size() < 3) { return; }
        for (var point = 0; point < points.size(); point += 1) {
            var next = (point + 1) % points.size();
            dc.drawLine(points[point][0], points[point][1], points[next][0], points[next][1]);
        }
    }

    function hybridLine(dc as Graphics.Dc, text as Lang.String,
            candidates as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont>,
            width as Lang.Number, top as Lang.Number, bottom as Lang.Number,
            ink as Lang.Number, canvas as Lang.Number) as Void {
        var font = pickFont(dc, text, candidates, width - 4, bottom - top - 4);
        var shown = text;
        if (font == null) {
            shown = "--";
            font = pickFont(dc, shown, candidates, width - 4, bottom - top - 4);
        }
        if (font == null) { return; }
        var x = ((dc.getWidth() - width) / 2).toNumber();
        dc.setClip(x, top, width, bottom - top);
        dc.setColor(ink, canvas);
        dc.drawText(FaceModel.DIAL_CENTER, top + (bottom - top - dc.getFontHeight(font)) / 2,
            font, shown, Graphics.TEXT_JUSTIFY_CENTER);
        dc.clearClip();
    }

    function hybridSlotFonts(dc as Graphics.Dc, data as Lang.Dictionary<Lang.String, Lang.String>,
            width as Lang.Number, height as Lang.Number)
            as Lang.Array<Graphics.FontDefinition or Graphics.VectorFont> or Null {
        // Hybrid uses two rows. Fit its truthful status and value together;
        // shrinking a three-row legacy field into this band would hide data.
        var shownDetail = FaceModel.hybridDetail(data);
        for (var d = 0; d < _detailFonts.size(); d += 1) {
            var detail = _detailFonts[d];
            if (dc.getTextWidthInPixels(shownDetail, detail) > width) { continue; }
            for (var v = 0; v < _valueFonts.size(); v += 1) {
                var value = _valueFonts[v];
                if (dc.getTextWidthInPixels(data["value"], value) > width) { continue; }
                if (dc.getFontHeight(value) + dc.getFontHeight(detail) + 2 <= height) {
                    return [value, detail];
                }
            }
        }
        return null;
    }

    function hybridSlot(dc as Graphics.Dc, data as Lang.Dictionary<Lang.String, Lang.String>,
            x as Lang.Number, ink as Lang.Number, muted as Lang.Number, canvas as Lang.Number) as Void {
        var top = FaceModel.HYBRID_DATA_TOP;
        var height = FaceModel.HYBRID_DATA_BOTTOM - top;
        var width = FaceModel.HYBRID_DATA_WIDTH;
        var selected = hybridSlotFonts(dc, data, width - 2, height - 2);
        if (selected == null) {
            // Never turn a failed-fit data field into an invented live value.
            var fallback = pickFont(dc, "--", _valueFonts, width - 4, height - 4);
            if (fallback != null) {
                dc.setClip(x, top, width, height);
                dc.setColor(ink, canvas);
                dc.drawText(x + width / 2, top + (height - dc.getFontHeight(fallback)) / 2,
                    fallback, "--", Graphics.TEXT_JUSTIFY_CENTER);
                dc.clearClip();
            }
            return;
        }
        var value = selected[0]; var detail = selected[1];
        var total = dc.getFontHeight(value) + dc.getFontHeight(detail) + 2;
        var y = top + (height - total) / 2;
        var center = x + width / 2;
        dc.setClip(x, top, width, height);
        dc.setColor(ink, canvas);
        dc.drawText(center, y, value, data["value"], Graphics.TEXT_JUSTIFY_CENTER);
        y += dc.getFontHeight(value) + 2;
        dc.setColor(muted, canvas);
        dc.drawText(center, y, detail, FaceModel.hybridDetail(data), Graphics.TEXT_JUSTIFY_CENTER);
        dc.clearClip();
    }

    function hybridMetalPolygon(dc as Graphics.Dc, outer as Lang.Array<Graphics.Point2D>,
            inset as Lang.Array<Graphics.Point2D>, ink as Lang.Number,
            metal as Lang.Number, canvas as Lang.Number) as Void {
        if (outer.size() < 3 || inset.size() != outer.size()) { return; }
        dc.setColor(canvas, canvas); dc.setPenWidth(4);
        drawAlwaysOnOutline(dc, outer);
        dc.setColor(metal, canvas); dc.fillPolygon(outer);
        dc.setColor(ink, canvas); dc.fillPolygon(inset);
        dc.setPenWidth(1);
    }

    function drawHybridBezel(dc as Graphics.Dc, ink as Lang.Number,
            metal as Lang.Number, canvas as Lang.Number) as Void {
        // A shallow dark annulus and two controlled edges, not a photographed
        // case or an interactive dive timer. Keep the dial's black area intact.
        var clair = canvas == ThemePalette.CLAIR_CANVAS;
        var body = clair ? ThemePalette.CLAIR_CODE : ThemePalette.OBSCUR_CODE;
        var edge = clair ? ThemePalette.CLAIR_DIVIDER : ThemePalette.OBSCUR_DIVIDER;
        dc.setColor(body, canvas);
        dc.fillCircle(FaceModel.DIAL_CENTER, FaceModel.DIAL_CENTER, FaceModel.HYBRID_BEZEL_OUTER);
        dc.setColor(canvas, canvas);
        dc.fillCircle(FaceModel.DIAL_CENTER, FaceModel.DIAL_CENTER, FaceModel.HYBRID_BEZEL_INNER);
        dc.setColor(metal, canvas); dc.setPenWidth(1);
        dc.drawCircle(FaceModel.DIAL_CENTER, FaceModel.DIAL_CENTER, FaceModel.HYBRID_BEZEL_OUTER);
        dc.setColor(edge, canvas);
        dc.drawCircle(FaceModel.DIAL_CENTER, FaceModel.DIAL_CENTER, FaceModel.HYBRID_BEZEL_INNER);
        dc.setColor(ink, canvas); dc.setPenWidth(2);
        for (var tick = 1; tick < 15; tick += 1) {
            if (tick % 5 == 0) { continue; }
            var turn = (tick / 60.0).toFloat();
            var inner = FaceModel.radialPoint(turn, 207, 0);
            var outer = FaceModel.radialPoint(turn, 218, 0);
            dc.drawLine(inner[0], inner[1], outer[0], outer[1]);
        }
        for (var tick = 5; tick < 60; tick += 10) {
            var turn = (tick / 60.0).toFloat();
            dc.setColor(ink, canvas);
            dc.fillPolygon([FaceModel.radialPoint(turn, 197, -2),
                FaceModel.radialPoint(turn, 219, -2), FaceModel.radialPoint(turn, 219, 2),
                FaceModel.radialPoint(turn, 197, 2)]);
        }
        for (var value = 10; value <= 50; value += 10) {
            var turn = (value / 60.0).toFloat();
            drawHybridBezelDigit(dc, (value / 10).toNumber(), turn, -12, ink, canvas);
            drawHybridBezelDigit(dc, 0, turn, 2, ink, canvas);
        }
        dc.setPenWidth(1);
        dc.setColor(metal, canvas); dc.fillPolygon([[215, 8], [239, 8], [227, 36]]);
        dc.setColor(body, canvas); dc.fillPolygon([[218, 10], [236, 10], [227, 31]]);
        dc.setColor(ink, canvas); dc.fillCircle(227, 17, 4);
    }

    function drawHybridBezelDigit(dc as Graphics.Dc, digit as Lang.Number,
            turn as Lang.Float, offset as Lang.Number, ink as Lang.Number,
            canvas as Lang.Number) as Void {
        var paths = FaceModel.hybridBezelDigit(digit);
        dc.setColor(ink, canvas); dc.setPenWidth(2);
        for (var path = 0; path < paths.size(); path += 1) {
            for (var point = 1; point < paths[path].size(); point += 1) {
                var a = paths[path][point - 1]; var b = paths[path][point];
                var first = FaceModel.radialPoint(turn, FaceModel.HYBRID_BEZEL_RADIUS + 12 - a[1], a[0] + offset);
                var next = FaceModel.radialPoint(turn, FaceModel.HYBRID_BEZEL_RADIUS + 12 - b[1], b[0] + offset);
                dc.drawLine(first[0], first[1], next[0], next[1]);
            }
        }
        dc.setPenWidth(1);
    }

    function drawHybridHour(dc as Graphics.Dc, hour as Lang.Number, minute as Lang.Number,
            ink as Lang.Number, metal as Lang.Number, canvas as Lang.Number) as Void {
        var center = FaceModel.hybridHourDiscCenter(hour, minute);
        if (center.size() != 2) { return; }
        // Clear the head's opposing edge first. Draw its neck and arrow after
        // that clear so the metal joins remain connected to the circular rim.
        dc.setColor(canvas, canvas);
        dc.fillCircle(center[0], center[1], FaceModel.HYBRID_HOUR_DISC_RADIUS + 2);
        hybridMetalPolygon(dc, FaceModel.hybridHourStem(hour, minute, false),
            FaceModel.hybridHourStem(hour, minute, true), ink, metal, canvas);
        hybridMetalPolygon(dc, FaceModel.hybridHourTip(hour, minute, false),
            FaceModel.hybridHourTip(hour, minute, true), ink, metal, canvas);
        dc.setColor(metal, canvas);
        dc.fillCircle(center[0], center[1], FaceModel.HYBRID_HOUR_DISC_RADIUS);
        dc.setColor(ink, canvas);
        dc.fillCircle(center[0], center[1], FaceModel.HYBRID_HOUR_DISC_INNER);
        dc.setColor(canvas, canvas); dc.setPenWidth(2);
        for (var part = 0; part < 3; part += 1) {
            var spoke = FaceModel.hybridHourSpoke(hour, minute, part);
            dc.drawLine(spoke[0][0], spoke[0][1], spoke[1][0], spoke[1][1]);
        }
        dc.setPenWidth(1);
    }

    function drawHybridClock(dc as Graphics.Dc, time as Lang.String, period as Lang.String,
            ink as Lang.Number, metal as Lang.Number, canvas as Lang.Number) as Void {
        var left = FaceModel.HYBRID_CLOCK_LEFT;
        var top = FaceModel.HYBRID_CLOCK_TOP;
        var width = FaceModel.HYBRID_CLOCK_WIDTH;
        var height = FaceModel.HYBRID_CLOCK_BOTTOM - top;
        // A small same-canvas clearing protects the secondary clock below the
        // pivot. Its entire box is inside the circular hour head's inner sweep.
        dc.setColor(canvas, canvas); dc.fillRectangle(left, top, width, height);
        var hasPeriod = period.length() > 0;
        var mainWidth = hasPeriod ? 92 : 120;
        var font = pickFont(dc, time, _clockFonts, mainWidth, height - 4);
        var shown = time;
        if (font == null) {
            shown = "--:--";
            font = pickFont(dc, shown, _clockFonts, mainWidth, height - 4);
        }
        dc.setClip(left + 2, top + 2, mainWidth, height - 4);
        if (font != null) {
            dc.setColor(ink, canvas);
            dc.drawText(left + 2 + mainWidth / 2, top + (height - dc.getFontHeight(font)) / 2,
                font, shown, Graphics.TEXT_JUSTIFY_CENTER);
        }
        dc.clearClip();
        if (hasPeriod) {
            var small = pickFont(dc, period, _periodFonts, 22, height - 4);
            if (small != null) {
                dc.setClip(left + 98, top + 2, 22, height - 4);
                dc.setColor(ink, canvas);
                dc.drawText(left + 109, top + (height - dc.getFontHeight(small)) / 2,
                    small, period, Graphics.TEXT_JUSTIFY_CENTER);
                dc.clearClip();
            }
        }
    }

    function drawHybridDay(dc as Graphics.Dc, day as Lang.String,
            ink as Lang.Number, metal as Lang.Number, canvas as Lang.Number) as Void {
        var left = FaceModel.HYBRID_DAY_LEFT;
        var top = FaceModel.HYBRID_DAY_TOP;
        var width = FaceModel.HYBRID_DAY_WIDTH;
        var height = FaceModel.HYBRID_DAY_BOTTOM - top;
        dc.setColor(metal, canvas); dc.fillRectangle(left, top, width, height);
        dc.setColor(ink, ink); dc.fillRectangle(left + 1, top + 1, width - 2, height - 2);
        var font = pickFont(dc, day, _dayFonts, width - 4, height - 4);
        var shown = day;
        if (font == null) {
            shown = "--";
            font = pickFont(dc, shown, _dayFonts, width - 4, height - 4);
        }
        if (font == null) { return; }
        dc.setClip(left + 2, top + 2, width - 4, height - 4);
        dc.setColor(canvas, ink);
        dc.drawText(left + width / 2, top + (height - dc.getFontHeight(font)) / 2,
            font, shown, Graphics.TEXT_JUSTIFY_CENTER);
        dc.clearClip();
    }

    function drawHybrid(dc as Graphics.Dc, hour as Lang.Number, minute as Lang.Number,
            time as Lang.String, period as Lang.String, date as Lang.String,
            day as Lang.String, charge as Lang.String,
            weather as Lang.Dictionary<Lang.String, Lang.String>,
            steps as Lang.Dictionary<Lang.String, Lang.String>, ink as Lang.Number,
            muted as Lang.Number, facet as Lang.Number, canvas as Lang.Number) as Void {
        drawHybridBezel(dc, ink, facet, canvas);
        dc.setColor(facet, canvas); dc.setPenWidth(1);
        for (var tick = 0; tick < 60; tick += 1) {
            var ends = FaceModel.hybridMinuteTick(tick);
            dc.drawLine(ends[0][0], ends[0][1], ends[1][0], ends[1][1]);
        }
        dc.setColor(facet, canvas); dc.fillPolygon(FaceModel.hybridTriangle(false));
        dc.setColor(ink, canvas); dc.fillPolygon(FaceModel.hybridTriangle(true));
        for (var index = 0; index < 12; index += 1) {
            var center = FaceModel.hybridCircleCenter(index);
            if (center.size() == 2) {
                dc.setColor(facet, canvas);
                dc.fillCircle(center[0], center[1], FaceModel.HYBRID_CIRCLE_RADIUS);
                dc.setColor(ink, canvas);
                dc.fillCircle(center[0], center[1], FaceModel.HYBRID_CIRCLE_INNER);
            } else {
                var baton = FaceModel.hybridActiveBaton(index, false);
                if (baton.size() == 4) {
                    dc.setColor(facet, canvas); dc.fillPolygon(baton);
                    dc.setColor(ink, canvas); dc.fillPolygon(FaceModel.hybridActiveBaton(index, true));
                }
            }
        }
        // Quiet dial printing sits behind the hands. Only the compact date and
        // digital clock clear a rectangle afterward; no glyph halos cut hands
        // into fragments. Hands can cross the other information temporarily.
        hybridLine(dc, date, _calendarFonts, FaceModel.HYBRID_DATE_WIDTH,
            FaceModel.HYBRID_DATE_TOP, FaceModel.HYBRID_DATE_BOTTOM, muted, canvas);
        hybridLine(dc, canvas == ThemePalette.CLAIR_CANVAS ? "CLAIR" : "OBSCUR",
            _labelFonts, 130, 112, 134, ink, canvas);
        hybridSlot(dc, weather, FaceModel.HYBRID_LEFT_X, ink, muted, canvas);
        hybridSlot(dc, steps, FaceModel.HYBRID_RIGHT_X, ink, muted, canvas);
        hybridLine(dc, charge, _batteryFonts, FaceModel.HYBRID_CHARGE_WIDTH,
            FaceModel.HYBRID_CHARGE_TOP, FaceModel.HYBRID_CHARGE_BOTTOM, muted, canvas);
        drawHybridHour(dc, hour, minute, ink, facet, canvas);
        hybridMetalPolygon(dc, FaceModel.hybridMinuteHand(hour, minute, false),
            FaceModel.hybridMinuteHand(hour, minute, true), ink, facet, canvas);
        dc.setColor(facet, canvas); dc.fillCircle(FaceModel.DIAL_CENTER, FaceModel.DIAL_CENTER, 8);
        dc.setColor(ink, canvas); dc.fillCircle(FaceModel.DIAL_CENTER, FaceModel.DIAL_CENTER, 5);
        dc.setColor(canvas, canvas); dc.fillCircle(FaceModel.DIAL_CENTER, FaceModel.DIAL_CENTER, 2);
        drawHybridClock(dc, time, period, ink, facet, canvas);
        drawHybridDay(dc, day, ink, facet, canvas);
    }

    function drawHybridAlwaysOn(dc as Graphics.Dc, hour as Lang.Number, minute as Lang.Number) as Void {
        var shift = FaceModel.aodAnalogOffset(minute);
        if (!FaceModel.validClock(hour, minute) || shift.size() != 2) { return; }
        var dim = ThemePalette.OBSCUR_BORDER;
        dc.setColor(dim, 0x000000); dc.setPenWidth(1);
        drawAlwaysOnOutline(dc, FaceModel.hybridShiftPoints(FaceModel.hybridTriangle(false), minute));
        for (var index = 0; index < 12; index += 1) {
            var center = FaceModel.hybridCircleCenter(index);
            if (center.size() == 2) {
                dc.drawCircle(center[0] + shift[0], center[1] + shift[1], FaceModel.HYBRID_CIRCLE_RADIUS);
            } else {
                drawAlwaysOnOutline(dc, FaceModel.hybridShiftPoints(FaceModel.hybridBaton(index, false), minute));
            }
        }
        drawAlwaysOnOutline(dc, FaceModel.hybridShiftPoints(FaceModel.hybridHourStem(hour, minute, false), minute));
        drawAlwaysOnOutline(dc, FaceModel.hybridShiftPoints(FaceModel.hybridHourTip(hour, minute, false), minute));
        var head = FaceModel.hybridHourDiscCenter(hour, minute);
        // Black clears the two hidden join edges inside the otherwise hollow
        // hour head. It adds no lit area and keeps the three spokes distinct.
        dc.setColor(0x000000, 0x000000);
        dc.fillCircle(head[0] + shift[0], head[1] + shift[1], FaceModel.HYBRID_HOUR_DISC_RADIUS - 1);
        dc.setColor(dim, 0x000000);
        dc.drawCircle(head[0] + shift[0], head[1] + shift[1], FaceModel.HYBRID_HOUR_DISC_RADIUS);
        for (var part = 0; part < 3; part += 1) {
            var spoke = FaceModel.hybridShiftPoints(FaceModel.hybridHourSpoke(hour, minute, part), minute);
            dc.drawLine(spoke[0][0], spoke[0][1], spoke[1][0], spoke[1][1]);
        }
        drawAlwaysOnOutline(dc, FaceModel.hybridShiftPoints(FaceModel.hybridMinuteHand(hour, minute, false), minute));
        dc.drawCircle(FaceModel.DIAL_CENTER + shift[0], FaceModel.DIAL_CENTER + shift[1], 3);
    }

    function drawAnalogAlwaysOn(dc as Graphics.Dc, hour as Lang.Number, minute as Lang.Number) as Void {
        var shift = FaceModel.aodAnalogOffset(minute);
        if (!FaceModel.validClock(hour, minute) || shift.size() != 2) { return; }
        // Preserve the active dial's positions, with only thin shifted outlines.
        dc.setColor(ThemePalette.OBSCUR_BORDER, 0x000000);
        dc.setPenWidth(1);
        for (var index = 0; index < 12; index += 1) {
            drawAlwaysOnOutline(dc, FaceModel.aodAnalogMarker(index, 0, minute));
            if (index == 0) {
                drawAlwaysOnOutline(dc, FaceModel.aodAnalogMarker(index, 1, minute));
            }
        }
        drawAlwaysOnOutline(dc, FaceModel.aodAnalogHandPoints(hour, minute, true));
        drawAlwaysOnOutline(dc, FaceModel.aodAnalogHandPoints(hour, minute, false));
        dc.drawCircle(FaceModel.DIAL_CENTER + shift[0], FaceModel.DIAL_CENTER + shift[1], 3);
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

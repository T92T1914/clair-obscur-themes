using Toybox.ActivityMonitor;
using Toybox.Complications;
using Toybox.Lang;
using Toybox.System;
using Toybox.Time;
using Toybox.WatchUi;
using Toybox.Weather;

module FaceData {
    const WEATHER = 0;
    const STEPS = 1;
    const BODY_BATTERY = 2;
    // This is the face's stale-data policy, not a Garmin refresh guarantee.
    const WEATHER_STALE_SECONDS = 7200;
    // Bound presentation before formatting or converting an untrusted provider value.
    const TEMPERATURE_DISPLAY_LIMIT_C = 1000;

    var _bodyBatteryId as Complications.Id or Null = null;
    var _bodyBatteryValue as Lang.Object or Null = null;
    var _bodyBatterySubscribed as Lang.Boolean = false;
    var _callbackRegistered as Lang.Boolean = false;
    var _callbackOwner as FaceDataCallback or Null = null;

    function sanitizeSlot(value as Lang.Object or Null,
            defaultChoice as Lang.Number) as Lang.Number {
        if (value instanceof Lang.Number) {
            var choice = value as Lang.Number;
            if (choice == WEATHER || choice == STEPS || choice == BODY_BATTERY) {
                return choice;
            }
        }
        if (defaultChoice == STEPS || defaultChoice == BODY_BATTERY) {
            return defaultChoice;
        }
        return WEATHER;
    }

    function payload(value as Lang.String, label as Lang.String,
            detail as Lang.String) as Lang.Dictionary<Lang.String, Lang.String> {
        return {"value" => value, "label" => label, "detail" => detail};
    }

    function unavailable(label as Lang.String) as Lang.Dictionary<Lang.String, Lang.String> {
        return payload("--", label, "Unavailable");
    }

    function numericValue(value as Lang.Object or Null) as Lang.Numeric or Null {
        if (value instanceof Lang.Number) { return value as Lang.Number; }
        if (value instanceof Lang.Long) { return value as Lang.Long; }
        if (value instanceof Lang.Float) { return value as Lang.Float; }
        if (value instanceof Lang.Double) { return value as Lang.Double; }
        return null;
    }

    function formatTemperature(value as Lang.Object or Null,
            fahrenheit as Lang.Boolean) as Lang.String {
        var temperature = numericValue(value);
        if (temperature == null) { return "--"; }
        // The target's NaN comparisons require rejection before ordered bounds.
        if (temperature != temperature) { return "--"; }
        if (!(temperature >= -TEMPERATURE_DISPLAY_LIMIT_C) ||
                !(temperature <= TEMPERATURE_DISPLAY_LIMIT_C)) {
            return "--";
        }
        var celsius = temperature.toDouble();
        var displayed = fahrenheit ? celsius * 9.0 / 5.0 + 32.0 : celsius;
        return displayed.format("%.0f") + (fahrenheit ? " F" : " C");
    }

    function weatherAge(observedSeconds as Lang.Object or Null,
            nowSeconds as Lang.Object or Null) as Lang.String {
        if (!(observedSeconds instanceof Lang.Number) ||
                !(nowSeconds instanceof Lang.Number)) {
            return "Age unknown";
        }
        var observed = observedSeconds as Lang.Number;
        var now = nowSeconds as Lang.Number;
        if (observed < 0 || now < 0 || observed > now) {
            return "Age unknown";
        }
        var age = now - observed;
        if (age < 3600) { return "Cached <1h"; }
        var hours = (age / 3600).toNumber().format("%d") + "h";
        return (age > WEATHER_STALE_SECONDS ? "Stale " : "Cached ") + hours;
    }

    function weatherPayload(temperatureC as Lang.Object or Null,
            observedSeconds as Lang.Object or Null, nowSeconds as Lang.Object or Null,
            fahrenheit as Lang.Boolean) as Lang.Dictionary<Lang.String, Lang.String> {
        var value = formatTemperature(temperatureC, fahrenheit);
        if (value.equals("--")) { return unavailable("Weather"); }
        return payload(value, "Weather", weatherAge(observedSeconds, nowSeconds));
    }

    function stepsPayload(steps as Lang.Object or Null,
            goal as Lang.Object or Null) as Lang.Dictionary<Lang.String, Lang.String> {
        if (!(steps instanceof Lang.Number)) { return unavailable("Steps"); }
        var count = steps as Lang.Number;
        if (count < 0) { return unavailable("Steps"); }
        var detail = "Today";
        if (goal instanceof Lang.Number && (goal as Lang.Number) > 0) {
            detail = "Goal " + (goal as Lang.Number).format("%d");
        }
        return payload(count.format("%d"), "Steps", detail);
    }

    function bodyBatteryPayload(value as Lang.Object or Null)
            as Lang.Dictionary<Lang.String, Lang.String> {
        // Keep a supplied zero distinct from absence; do not relabel this as charge.
        if (!(value instanceof Lang.Number)) { return unavailable("Body Battery"); }
        var score = value as Lang.Number;
        if (score < 0 || score > 100) { return unavailable("Body Battery"); }
        return payload(score.format("%d"), "Body Battery", "Garmin score");
    }

    function readSlot(choice as Lang.Number, nowSeconds as Lang.Number)
            as Lang.Dictionary<Lang.String, Lang.String> {
        if (choice == WEATHER) {
            if (!(Weather has :getCurrentConditions)) { return unavailable("Weather"); }
            var conditions = Weather.getCurrentConditions();
            if (conditions == null) { return unavailable("Weather"); }
            var observed = null;
            var observation = conditions.observationTime;
            if (observation != null) { observed = observation.value(); }
            return weatherPayload(conditions.temperature as Lang.Object, observed,
                nowSeconds, System.getDeviceSettings().temperatureUnits == System.UNIT_STATUTE);
        }
        if (choice == STEPS) {
            var info = ActivityMonitor.getInfo();
            return stepsPayload(info.steps as Lang.Object, info.stepGoal as Lang.Object);
        }
        if (choice == BODY_BATTERY) {
            if (!_bodyBatterySubscribed) { refreshBodyBattery(); }
            return bodyBatteryPayload(_bodyBatteryValue);
        }
        return unavailable("Data");
    }

    function refreshBodyBattery() as Void {
        _bodyBatteryValue = null;
        var id = _bodyBatteryId;
        if (id == null) { return; }
        try {
            var current = Complications.getComplication(id);
            _bodyBatteryValue = current.value as Lang.Object;
        } catch (error instanceof Complications.ComplicationNotFoundException) {
            // A native provider can become unavailable after it was enumerated.
        }
    }

    function onComplicationChanged(id as Complications.Id) as Void {
        var selected = _bodyBatteryId;
        if (!_bodyBatterySubscribed || selected == null || !selected.equals(id)) { return; }
        refreshBodyBattery();
        // The view still chooses its own active/AOD/off rendering contract.
        WatchUi.requestUpdate();
    }

    function refreshSubscriptions(slot1 as Lang.Number, slot2 as Lang.Number) as Void {
        if (slot1 != BODY_BATTERY && slot2 != BODY_BATTERY) {
            shutdown();
            return;
        }
        if (!(Complications has :COMPLICATION_TYPE_BODY_BATTERY)) { return; }
        if (_bodyBatterySubscribed) {
            refreshBodyBattery();
            return;
        }
        _bodyBatteryId = null;
        _bodyBatteryValue = null;
        var iterator = Complications.getComplications();
        var candidate = iterator.next();
        while (candidate != null) {
            if (candidate.getType() == Complications.COMPLICATION_TYPE_BODY_BATTERY &&
                    candidate.complicationId != null) {
                _bodyBatteryId = candidate.complicationId;
                break;
            }
            candidate = iterator.next();
        }
        var id = _bodyBatteryId;
        if (id == null) { return; }
        var owner = new FaceDataCallback();
        _callbackOwner = owner;
        Complications.registerComplicationChangeCallback(owner.method(:changed));
        _callbackRegistered = true;
        try {
            _bodyBatterySubscribed = Complications.subscribeToUpdates(id);
        } catch (error instanceof Complications.ComplicationNotFoundException) {
            _bodyBatterySubscribed = false;
        } catch (error instanceof Lang.OperationNotAllowedException) {
            _bodyBatterySubscribed = false;
        }
        // Direct lookup can still supply a value if a subscription was not available.
        refreshBodyBattery();
    }

    function shutdown() as Void {
        var id = _bodyBatteryId;
        if (_bodyBatterySubscribed && id != null) {
            Complications.unsubscribeFromUpdates(id);
        }
        if (_callbackRegistered) {
            Complications.registerComplicationChangeCallback(null);
        }
        _callbackOwner = null;
        _bodyBatteryId = null;
        _bodyBatteryValue = null;
        _bodyBatterySubscribed = false;
        _callbackRegistered = false;
    }
}

class FaceDataCallback {
    function initialize() {
    }

    function changed(id as Complications.Id) as Void {
        FaceData.onComplicationChanged(id);
    }
}

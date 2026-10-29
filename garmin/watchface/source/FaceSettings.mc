using Toybox.Application;
using Toybox.Lang;
using Toybox.WatchUi;

module FaceSettings {
    function readLayout() as Lang.Number {
        try {
            var stored = Application.Properties.getValue("layout") as Lang.Object;
            return FaceModel.sanitizeLayout(stored);
        } catch (error instanceof Application.Properties.InvalidKeyException) {
            return FaceModel.LAYOUT_HYBRID;
        }
    }

    function saveLayout(value as Lang.Object or Null) as Lang.Boolean {
        if (!FaceModel.isLayout(value)) { return false; }
        Application.Properties.setValue("layout", value as Lang.Number);
        refreshDataSubscriptions();
        WatchUi.requestUpdate();
        return true;
    }

    function layoutName(choice as Lang.Number) as Lang.String {
        if (choice == FaceModel.LAYOUT_DIGITAL) { return "Digital"; }
        return choice == FaceModel.LAYOUT_HYBRID ? "Hybrid" : "Analog";
    }

    function refreshDataSubscriptions() as Void {
        // Hybrid has fixed Weather/Steps. Retain the legacy preferences, but
        // subscribe only to a Body Battery provider that is actually displayed.
        if (readLayout() == FaceModel.LAYOUT_HYBRID) { FaceData.shutdown(); }
        else { FaceData.refreshSubscriptions(readSlot(0), readSlot(1)); }
    }

    function readDateFormat() as Lang.Number {
        try {
            var value = Application.Properties.getValue("hybridDateFormat") as Lang.Object;
            return FaceModel.sanitizeDateFormat(value);
        } catch (error instanceof Application.Properties.InvalidKeyException) { return 0; }
    }

    function saveDateFormat(value as Lang.Object or Null) as Lang.Boolean {
        if (!(value instanceof Lang.Number) || (value as Lang.Number) < 0 ||
                (value as Lang.Number) > 2) { return false; }
        Application.Properties.setValue("hybridDateFormat", value as Lang.Number);
        WatchUi.requestUpdate();
        return true;
    }

    function dateFormatName(choice as Lang.Number) as Lang.String {
        if (choice == 1) { return "Month Day"; }
        return choice == 2 ? "ISO date" : "Day Month";
    }

    function appearanceFromProperty(value as Lang.Object or Null) as Lang.String {
        if (!(value instanceof Lang.Number)) {
            return "Obscur";
        }
        var encoded = value as Lang.Number;
        return encoded == 0 ? "Clair" : "Obscur";
    }

    function readAppearance() as Lang.String {
        try {
            // Keep the SDK's recursive ValueType outside validation's type-inference boundary.
            var stored = Application.Properties.getValue("appearance") as Lang.Object;
            return appearanceFromProperty(stored);
        } catch (error instanceof Application.Properties.InvalidKeyException) {
            return "Obscur";
        }
    }

    function saveAppearance(value as Lang.Object or Null) as Lang.Boolean {
        if (!FaceModel.isAppearance(value)) {
            return false;
        }
        var choice = value as Lang.String;
        Application.Properties.setValue("appearance", choice.equals("Clair") ? 0 : 1);
        WatchUi.requestUpdate();
        return true;
    }

    function readSlot(index as Lang.Number) as Lang.Number {
        var fallback = index == 1 ? FaceData.STEPS : FaceData.WEATHER;
        try {
            var stored = Application.Properties.getValue(index == 1 ? "rightData" : "leftData") as Lang.Object;
            return FaceData.sanitizeSlot(stored, fallback);
        } catch (error instanceof Application.Properties.InvalidKeyException) {
            return fallback;
        }
    }

    function saveSlot(index as Lang.Number, value as Lang.Object or Null) as Lang.Boolean {
        if (index != 0 && index != 1) { return false; }
        if (!(value instanceof Lang.Number)) { return false; }
        var choice = value as Lang.Number;
        if (choice < FaceData.WEATHER || choice > FaceData.BODY_BATTERY) { return false; }
        Application.Properties.setValue(index == 1 ? "rightData" : "leftData", choice);
        refreshDataSubscriptions();
        WatchUi.requestUpdate();
        return true;
    }

    function slotName(choice as Lang.Number) as Lang.String {
        if (choice == FaceData.STEPS) { return "Steps"; }
        if (choice == FaceData.BODY_BATTERY) { return "Body Battery"; }
        return "Weather";
    }

    function makeSettingsMenu() as WatchUi.Menu2 {
        var menu = new WatchUi.Menu2({:title => Rez.Strings.AppName});
        menu.addItem(new WatchUi.MenuItem(Rez.Strings.AppearanceTitle, readAppearance(), "appearance", {}));
        menu.addItem(new WatchUi.MenuItem(Rez.Strings.LayoutTitle, layoutName(readLayout()), "layout", {}));
        if (readLayout() == FaceModel.LAYOUT_HYBRID) {
            menu.addItem(new WatchUi.MenuItem(Rez.Strings.HybridDateTitle, dateFormatName(readDateFormat()), "date", {}));
        } else {
            menu.addItem(new WatchUi.MenuItem(Rez.Strings.LeftDataTitle, slotName(readSlot(0)), "left", {}));
            menu.addItem(new WatchUi.MenuItem(Rez.Strings.RightDataTitle, slotName(readSlot(1)), "right", {}));
        }
        return menu;
    }

    function makeLayoutMenu() as WatchUi.Menu2 {
        var menu = new WatchUi.Menu2({:title => Rez.Strings.LayoutTitle});
        var selected = readLayout();
        menu.addItem(new WatchUi.MenuItem(Rez.Strings.AnalogLabel,
            selected == FaceModel.LAYOUT_ANALOG ? Rez.Strings.SelectedLabel : null, FaceModel.LAYOUT_ANALOG, {}));
        menu.addItem(new WatchUi.MenuItem(Rez.Strings.DigitalLabel,
            selected == FaceModel.LAYOUT_DIGITAL ? Rez.Strings.SelectedLabel : null, FaceModel.LAYOUT_DIGITAL, {}));
        menu.addItem(new WatchUi.MenuItem(Rez.Strings.HybridLabel,
            selected == FaceModel.LAYOUT_HYBRID ? Rez.Strings.SelectedLabel : null, FaceModel.LAYOUT_HYBRID, {}));
        return menu;
    }

    function makeDateMenu() as WatchUi.Menu2 {
        var menu = new WatchUi.Menu2({:title => Rez.Strings.HybridDateTitle});
        for (var choice = 0; choice <= 2; choice += 1) {
            menu.addItem(new WatchUi.MenuItem(dateFormatName(choice),
                readDateFormat() == choice ? Rez.Strings.SelectedLabel : null, choice, {}));
        }
        return menu;
    }

    function makeSlotMenu(index as Lang.Number) as WatchUi.Menu2 {
        var menu = new WatchUi.Menu2({:title => index == 1 ? Rez.Strings.RightDataTitle : Rez.Strings.LeftDataTitle});
        var selected = readSlot(index);
        for (var choice = FaceData.WEATHER; choice <= FaceData.BODY_BATTERY; choice += 1) {
            menu.addItem(new WatchUi.MenuItem(slotName(choice),
                selected == choice ? Rez.Strings.SelectedLabel : null, choice, {}));
        }
        return menu;
    }

    function makeMenu() as WatchUi.Menu2 {
        var menu = new WatchUi.Menu2({:title => Rez.Strings.AppearanceTitle});
        var selected = readAppearance();
        menu.addItem(new WatchUi.MenuItem(Rez.Strings.ClairLabel,
            selected.equals("Clair") ? Rez.Strings.SelectedLabel : null, "Clair", {}));
        menu.addItem(new WatchUi.MenuItem(Rez.Strings.ObscurLabel,
            selected.equals("Obscur") ? Rez.Strings.SelectedLabel : null, "Obscur", {}));
        return menu;
    }
}

class AppearanceMenuDelegate extends WatchUi.Menu2InputDelegate {
    function initialize() {
        Menu2InputDelegate.initialize();
    }

    function onSelect(item as WatchUi.MenuItem) as Void {
        if (FaceSettings.saveAppearance(item.getId())) {
            WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
            WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
        }
    }
}

class FaceConfigurationDelegate extends WatchUi.Menu2InputDelegate {
    function initialize() { Menu2InputDelegate.initialize(); }
    function onSelect(item as WatchUi.MenuItem) as Void {
        var id = item.getId();
        if (!(id instanceof Lang.String)) { return; }
        if (id.equals("appearance")) {
            WatchUi.pushView(FaceSettings.makeMenu(), new AppearanceMenuDelegate(), WatchUi.SLIDE_IMMEDIATE);
        } else if (id.equals("layout")) {
            WatchUi.pushView(FaceSettings.makeLayoutMenu(), new FaceLayoutDelegate(), WatchUi.SLIDE_IMMEDIATE);
        } else if (id.equals("date")) {
            WatchUi.pushView(FaceSettings.makeDateMenu(), new FaceDateDelegate(), WatchUi.SLIDE_IMMEDIATE);
        } else if (id.equals("left") || id.equals("right")) {
            var index = id.equals("right") ? 1 : 0;
            WatchUi.pushView(FaceSettings.makeSlotMenu(index), new FaceSlotDelegate(index), WatchUi.SLIDE_IMMEDIATE);
        }
    }
}

class FaceLayoutDelegate extends WatchUi.Menu2InputDelegate {
    function initialize() { Menu2InputDelegate.initialize(); }
    function onSelect(item as WatchUi.MenuItem) as Void {
        if (FaceSettings.saveLayout(item.getId())) {
            WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
            WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
        }
    }
}

class FaceSlotDelegate extends WatchUi.Menu2InputDelegate {
    var _index as Lang.Number;
    function initialize(index as Lang.Number) { Menu2InputDelegate.initialize(); _index = index; }
    function onSelect(item as WatchUi.MenuItem) as Void {
        if (FaceSettings.saveSlot(_index, item.getId())) {
            WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
            WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
        }
    }
}

class FaceDateDelegate extends WatchUi.Menu2InputDelegate {
    function initialize() { Menu2InputDelegate.initialize(); }
    function onSelect(item as WatchUi.MenuItem) as Void {
        if (FaceSettings.saveDateFormat(item.getId())) {
            WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
            WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
        }
    }
}

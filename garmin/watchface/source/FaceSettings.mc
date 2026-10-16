using Toybox.Application;
using Toybox.Lang;
using Toybox.WatchUi;

module FaceSettings {
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
        FaceData.refreshSubscriptions(readSlot(0), readSlot(1));
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
        menu.addItem(new WatchUi.MenuItem(Rez.Strings.LeftDataTitle, slotName(readSlot(0)), "left", {}));
        menu.addItem(new WatchUi.MenuItem(Rez.Strings.RightDataTitle, slotName(readSlot(1)), "right", {}));
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
        } else {
            var index = id.equals("right") ? 1 : 0;
            WatchUi.pushView(FaceSettings.makeSlotMenu(index), new FaceSlotDelegate(index), WatchUi.SLIDE_IMMEDIATE);
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

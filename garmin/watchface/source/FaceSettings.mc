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
        }
    }
}

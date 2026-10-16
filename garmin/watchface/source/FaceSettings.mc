using Toybox.Application;
using Toybox.WatchUi;

module FaceSettings {
    function readAppearance() {
        try {
            return FaceModel.sanitizeAppearance(Application.Properties.getValue("appearance"));
        } catch (error instanceof Application.Properties.InvalidKeyException) {
            return "Obscur";
        }
    }

    function saveAppearance(value) {
        if (!FaceModel.isAppearance(value)) {
            return false;
        }
        Application.Properties.setValue("appearance", value);
        WatchUi.requestUpdate();
        return true;
    }

    function makeMenu() {
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

    function onSelect(item) {
        if (FaceSettings.saveAppearance(item.getId())) {
            WatchUi.popView(WatchUi.SLIDE_IMMEDIATE);
        }
    }
}

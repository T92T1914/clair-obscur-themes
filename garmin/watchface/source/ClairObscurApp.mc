using Toybox.Application;
using Toybox.WatchUi;

class ClairObscurApp extends Application.AppBase {
    function initialize() {
        AppBase.initialize();
    }

    function getInitialView() {
        return [new ClairObscurView()];
    }

    // The host invokes this watch-face configuration entry point on supported devices.
    function getSettingsView() {
        return [FaceSettings.makeMenu(), new AppearanceMenuDelegate()];
    }

    function onSettingsChanged() {
        WatchUi.requestUpdate();
    }

    function onDeviceSettingChanged(setting, value) {
        WatchUi.requestUpdate();
    }

    function onDisplayModeChanged() {
        WatchUi.requestUpdate();
    }
}

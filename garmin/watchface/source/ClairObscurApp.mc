using Toybox.Application;
using Toybox.Lang;
using Toybox.WatchUi;

class ClairObscurApp extends Application.AppBase {
    function initialize() {
        AppBase.initialize();
    }

    function getInitialView() as [WatchUi.Views] or [WatchUi.Views, WatchUi.InputDelegates] {
        return [new ClairObscurView()];
    }

    // The host invokes this watch-face configuration entry point on supported devices.
    function getSettingsView() as [WatchUi.Views] or [WatchUi.Views, WatchUi.InputDelegates] or Null {
        return [FaceSettings.makeMenu(), new AppearanceMenuDelegate()];
    }

    function onSettingsChanged() as Void {
        WatchUi.requestUpdate();
    }

    function onDeviceSettingChanged(setting as Lang.Symbol, value as Lang.Object) as Void {
        WatchUi.requestUpdate();
    }

    function onDisplayModeChanged() as Void {
        WatchUi.requestUpdate();
    }
}

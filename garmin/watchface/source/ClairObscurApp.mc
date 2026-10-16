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

    function onStart(state as Lang.Dictionary or Null) as Void {
        FaceData.refreshSubscriptions(FaceSettings.readSlot(0), FaceSettings.readSlot(1));
    }

    function onStop(state as Lang.Dictionary or Null) as Void { FaceData.shutdown(); }

    // The host invokes this watch-face configuration entry point on supported devices.
    function getSettingsView() as [WatchUi.Views] or [WatchUi.Views, WatchUi.InputDelegates] or Null {
        return [FaceSettings.makeSettingsMenu(), new FaceConfigurationDelegate()];
    }

    function onSettingsChanged() as Void {
        FaceData.refreshSubscriptions(FaceSettings.readSlot(0), FaceSettings.readSlot(1));
        WatchUi.requestUpdate();
    }

    function onDeviceSettingChanged(setting as Lang.Symbol, value as Lang.Object) as Void {
        WatchUi.requestUpdate();
    }

    function onDisplayModeChanged() as Void {
        WatchUi.requestUpdate();
    }
}

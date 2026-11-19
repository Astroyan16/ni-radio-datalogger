from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
import pytest

from radio_datalogger import main_window as ui
from radio_datalogger.models import DeviceInfo


@pytest.fixture
def window(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr(ui, "QSettings", lambda: settings)
    device = DeviceInfo(
        "DevTest", "USB-6009", ("DevTest/ai0", "DevTest/ai1", "DevTest/ai5"),
        terminal_modes_by_channel={
            "DevTest/ai0": ("DEFAULT", "DIFFERENTIAL", "RSE"),
            "DevTest/ai1": ("DEFAULT", "DIFFERENTIAL", "RSE"),
            "DevTest/ai5": ("DEFAULT", "RSE"),
        },
    )
    monkeypatch.setattr(ui, "discover_devices", lambda: ([device], None))
    instance = ui.MainWindow()
    instance.refresh_devices()
    yield instance
    instance._device_timer.stop()
    instance.close()
    instance.deleteLater()
    app.processEvents()


@pytest.mark.parametrize("saved, expected", [
    (None, "DIFFERENTIAL"), ("DEFAULT", "DIFFERENTIAL"), ("RSE", "RSE"),
])
def test_default_migration_and_explicit_settings(window, saved, expected):
    if saved is not None:
        window._settings.setValue("terminal_mode", saved)
    window._restore_settings()
    window.refresh_devices()
    config, _ = window._current_config()
    assert config.physical_channel == "DevTest/ai1"
    assert config.terminal_mode == expected
    window._save_settings()
    assert window._settings.value("terminal_mode") == expected


def test_channel_without_differential_only_offers_supported_modes(window):
    window.channel_combo.setCurrentIndex(window.channel_combo.findData("DevTest/ai5"))
    assert window.terminal_combo.findData("DIFFERENTIAL") == -1
    assert window.terminal_combo.currentData() in ("DEFAULT", "RSE")
    window.channel_combo.setCurrentIndex(window.channel_combo.findData("DevTest/ai1"))
    assert window.terminal_combo.findData("DIFFERENTIAL") >= 0


def test_initial_voltage_range_and_saved_values(window):
    config, _ = window._current_config()
    assert (config.voltage_min, config.voltage_max) == (0.0, 5.0)
    window.voltage_min_spin.setValue(-2)
    window.voltage_max_spin.setValue(2)
    window._save_settings()
    window._restore_settings()
    config, _ = window._current_config()
    assert (config.voltage_min, config.voltage_max) == (-2.0, 2.0)


def test_saved_channel_is_restored(window):
    window._settings.setValue("physical_channel", "DevTest/ai0")
    window._device_changed()
    assert window.channel_combo.currentData() == "DevTest/ai0"


@pytest.mark.parametrize("channels, modes", [
    (("DevTest/ai0", "DevTest/ai5"), {}),
    (("DevTest/ai0", "DevTest/ai1"), {"DevTest/ai1": ("DEFAULT", "RSE")}),
])
def test_channel_fallback_without_differential_ai1(window, channels, modes):
    window._devices["DevTest"] = DeviceInfo(
        "DevTest", "Test", channels, terminal_modes_by_channel=modes,
    )
    window._device_changed()
    assert window.channel_combo.currentData() == "DevTest/ai0"

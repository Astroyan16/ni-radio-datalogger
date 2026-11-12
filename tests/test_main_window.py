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
        "DevTest", "USB-6009", ("DevTest/ai1", "DevTest/ai5"),
        terminal_modes_by_channel={
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

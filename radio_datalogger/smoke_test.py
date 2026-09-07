"""Contrôle de distribution : interface Qt et CSV, exclusivement en simulation."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
from time import monotonic
import traceback

import numpy as np
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtWidgets import QApplication

from . import __version__
from . import daq
from . import main_window as ui
from .models import SIMULATION_DEVICE


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        lines = [line for line in source if not line.startswith("#")]
    rows = list(csv.DictReader(lines))
    assert rows, f"CSV vide : {path.name}"
    indices = np.array([int(row["sample_index"]) for row in rows])
    times = np.array([float(row["elapsed_s"]) for row in rows])
    values = np.array([float(row["interferometer_voltage_v"]) for row in rows])
    assert np.all(np.diff(indices) == 1), "Indices CSV discontinus"
    assert np.allclose(times, indices / 1000, rtol=0, atol=1e-9)
    assert np.all(np.isfinite(values)), "Tensions CSV non finies"
    return rows


def run_smoke_test(app: QApplication, output_dir: Path) -> int:
    """Exerce les contrôles réels de la fenêtre et quitte avec un code vérifiable."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "status": "failed",
        "version": __version__,
        "frozen": bool(getattr(sys, "frozen", False)),
        "platform": platform.platform(),
        "hardware_accessed": False,
        "checks": [],
    }
    original_settings = ui.QSettings
    original_discovery = ui.discover_devices
    original_dialog = ui.QFileDialog.getSaveFileName
    original_critical = ui.QMessageBox.critical
    original_warning = ui.QMessageBox.warning
    original_excepthook = sys.excepthook
    window = None
    timer = QTimer()
    started = monotonic()
    state = "start"
    error: str | None = None

    def fail(message: str) -> None:
        nonlocal error
        if error is None:
            error = message
        app.exit(1)

    def exception_hook(kind, value, tb) -> None:
        fail("".join(traceback.format_exception(kind, value, tb)))

    def unexpected_dialog(parent, title, message, *args, **kwargs):
        fail(f"{title}: {message}")
        return ui.QMessageBox.StandardButton.Ok

    try:
        # L'import NI doit fonctionner même si le pilote système est absent.
        assert daq.NIDAQMX_IMPORT_ERROR is None, daq.NIDAQMX_IMPORT_ERROR
        assert daq.nidaqmx is not None
        report["nidaqmx_version"] = daq.nidaqmx.__version__
        report["checks"].append("nidaqmx_import_and_metadata")
        with TemporaryDirectory(prefix="ni-radio-smoke-settings-") as settings_dir:
            ui.QSettings = lambda: QSettings(
                str(Path(settings_dir) / "settings.ini"), QSettings.Format.IniFormat
            )
            ui.discover_devices = lambda: ([], None)
            paths = iter([output_dir / "live.csv", output_dir / "complete.csv"])
            ui.QFileDialog.getSaveFileName = lambda *args, **kwargs: (str(next(paths)), "CSV")
            ui.QMessageBox.critical = unexpected_dialog
            ui.QMessageBox.warning = unexpected_dialog
            sys.excepthook = exception_hook
            window = ui.MainWindow()
            window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
            window.show()

            def step() -> None:
                nonlocal state
                try:
                    if monotonic() - started > 15:
                        raise TimeoutError(f"Délai dépassé pendant : {state}")
                    if state == "start":
                        window.refresh_devices()
                        assert window.device_combo.currentData() == SIMULATION_DEVICE
                        window.rate_spin.setValue(1000)
                        window.display_samples_spin.setValue(100)
                        window.start_button.click()
                        state = "record"
                    elif state == "record" and window._total_samples >= 200:
                        assert window._worker is not None
                        assert not window.start_button.isEnabled()
                        assert window.record_button.isEnabled()
                        window.record_button.click()
                        assert window._recorder.is_recording
                        report["checks"].append("simulation_and_record_button")
                        state = "stop_recording"
                    elif state == "stop_recording" and window._total_samples >= 500:
                        assert window._buffer.size == 100
                        x_values, y_values = window.curve.getData()
                        assert len(x_values) == len(y_values) == 100
                        assert window.current_metric.text().endswith(" V")
                        assert window.grab().save(str(output_dir / "window.png"))
                        window.record_button.click()
                        assert not window._recorder.is_recording
                        report["checks"].append("bounded_plot_metrics_and_live_csv")
                        state = "stop"
                    elif state == "stop" and window._total_samples >= 700:
                        window.stop_button.click()
                        state = "export"
                    elif state == "export" and window._worker is None:
                        assert window.start_button.isEnabled()
                        assert window.record_button.isEnabled()
                        window.record_button.click()
                        complete = _read_csv(output_dir / "complete.csv")
                        live = _read_csv(output_dir / "live.csv")
                        assert len(complete) == window._total_samples
                        assert int(complete[0]["sample_index"]) == 0
                        assert 0 < len(live) < len(complete)
                        for row in live:
                            assert row == complete[int(row["sample_index"])]
                        report["samples"] = {"complete": len(complete), "live": len(live)}
                        report["checks"].append("complete_export_and_matching_samples")
                        window.start_button.click()
                        state = "restart"
                    elif state == "restart" and window._total_samples >= 100:
                        assert window._worker is not None
                        window.stop_button.click()
                        state = "finish"
                    elif state == "finish" and window._worker is None:
                        report["checks"].append("restart_and_clean_stop")
                        app.exit(0)
                except Exception:
                    fail(traceback.format_exc())

            timer.timeout.connect(step)
            timer.start(20)
            app.setQuitOnLastWindowClosed(False)
            result = app.exec()
            timer.stop()
            if error is not None:
                raise RuntimeError(error)
            assert result == 0 and state == "finish", "Fin de contrôle prématurée"
            window.close()
            window._settings.sync()
            report["status"] = "passed"
    except Exception:
        report["error"] = traceback.format_exc()
    finally:
        timer.stop()
        if window is not None:
            if window._worker is not None:
                window._worker.request_stop()
                window._worker.wait(5000)
            window.close()
        ui.QSettings = original_settings
        ui.discover_devices = original_discovery
        ui.QFileDialog.getSaveFileName = original_dialog
        ui.QMessageBox.critical = original_critical
        ui.QMessageBox.warning = original_warning
        sys.excepthook = original_excepthook
        report["duration_seconds"] = round(monotonic() - started, 3)
        (output_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return 0 if report["status"] == "passed" else 1

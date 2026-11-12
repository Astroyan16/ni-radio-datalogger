"""Fenêtre principale du datalogger."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtGui import QCloseEvent, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .buffer import RingBuffer
from .daq import AcquisitionWorker, TERMINAL_MODE_LABELS, discover_devices
from .models import AcquisitionConfig, DeviceInfo, SIMULATION_DEVICE
from .recording import AcquisitionSession, CsvRecorder
from . import __version__


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"NI Radio Datalogger {__version__}")
        self.resize(1320, 790)
        self.setMinimumSize(1050, 680)

        self._settings = QSettings()
        self._devices: dict[str, DeviceInfo] = {}
        self._initial_device_scan_done = False
        self._worker: AcquisitionWorker | None = None
        self._buffer = RingBuffer(10_000)
        self._recorder = CsvRecorder()
        self._session_capture = AcquisitionSession()
        self._active_config: AcquisitionConfig | None = None
        self._actual_rate = 0.0
        self._acquisition_started_utc: datetime | None = None
        self._total_samples = 0
        self._build_ui()
        self._restore_settings()

        self._device_timer = QTimer(self)
        self._device_timer.setInterval(4000)
        self._device_timer.timeout.connect(self.refresh_devices)
        self._device_timer.start()
        QTimer.singleShot(0, self.refresh_devices)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 14)
        root.setSpacing(14)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("NI Radio Datalogger")
        title.setObjectName("title")
        subtitle = QLabel("Acquisition analogique · visualisation temps réel · export CSV")
        subtitle.setObjectName("subtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()
        self.status_pill = QLabel("●  Prêt")
        self.status_pill.setObjectName("statusPill")
        header.addWidget(self.status_pill, alignment=Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        root.addLayout(body, stretch=1)

        side_panel = QWidget()
        side_panel.setFixedWidth(360)
        side = QVBoxLayout(side_panel)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(12)
        body.addWidget(side_panel)

        connection_card, connection_layout = self._card("SORTIE INTERFÉROMÈTRE")
        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._device_changed)
        refresh_button = QPushButton("Actualiser")
        refresh_button.setToolTip("Relancer immédiatement la détection des périphériques NI")
        refresh_button.clicked.connect(self.refresh_devices)
        device_row = QHBoxLayout()
        device_row.addWidget(self.device_combo, stretch=1)
        device_row.addWidget(refresh_button)
        connection_layout.addRow("Périphérique", device_row)

        self.channel_combo = QComboBox()
        self.channel_combo.currentIndexChanged.connect(self._channel_changed)
        connection_layout.addRow("Entrée analogique", self.channel_combo)
        self.terminal_combo = QComboBox()
        for key, label in TERMINAL_MODE_LABELS.items():
            self.terminal_combo.addItem(label, key)
        connection_layout.addRow("Connexion", self.terminal_combo)
        source_note = QLabel(
            "Une voie unique mesure le signal déjà combiné par l'interféromètre des deux antennes."
        )
        source_note.setObjectName("muted")
        source_note.setWordWrap(True)
        connection_layout.addRow(source_note)
        side.addWidget(connection_card)

        acquisition_card, acquisition_layout = self._card("ACQUISITION")
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0.1, 1_000_000.0)
        self.rate_spin.setDecimals(1)
        self.rate_spin.setValue(1_000.0)
        self.rate_spin.setSuffix(" éch/s")
        acquisition_layout.addRow("Fréquence", self.rate_spin)

        self.display_samples_spin = QSpinBox()
        self.display_samples_spin.setRange(100, 1_000_000)
        self.display_samples_spin.setSingleStep(1000)
        self.display_samples_spin.setValue(10_000)
        self.display_samples_spin.setSuffix(" points")
        self.display_samples_spin.valueChanged.connect(self._display_capacity_changed)
        acquisition_layout.addRow("Fenêtre affichée", self.display_samples_spin)

        range_row = QHBoxLayout()
        self.voltage_min_spin = QDoubleSpinBox()
        self.voltage_min_spin.setRange(-1000.0, 999.0)
        self.voltage_min_spin.setDecimals(2)
        self.voltage_min_spin.setValue(-10.0)
        self.voltage_min_spin.setSuffix(" V")
        self.voltage_max_spin = QDoubleSpinBox()
        self.voltage_max_spin.setRange(-999.0, 1000.0)
        self.voltage_max_spin.setDecimals(2)
        self.voltage_max_spin.setValue(10.0)
        self.voltage_max_spin.setSuffix(" V")
        range_row.addWidget(self.voltage_min_spin)
        range_row.addWidget(self.voltage_max_spin)
        acquisition_layout.addRow("Plage min / max", range_row)

        self.auto_y_checkbox = QCheckBox("Adapter en continu aux données affichées")
        self.auto_y_checkbox.setChecked(True)
        self.auto_y_checkbox.toggled.connect(self._vertical_autoscale_changed)
        acquisition_layout.addRow("Axe vertical", self.auto_y_checkbox)
        side.addWidget(acquisition_card)

        actions_card = QFrame()
        actions_card.setObjectName("card")
        actions = QVBoxLayout(actions_card)
        actions.setContentsMargins(14, 14, 14, 14)
        self.start_button = QPushButton("Démarrer l'acquisition")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.start_acquisition)
        self.stop_button = QPushButton("Arrêter")
        self.stop_button.setObjectName("dangerButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_acquisition)
        action_row = QHBoxLayout()
        action_row.addWidget(self.start_button, stretch=1)
        action_row.addWidget(self.stop_button)
        actions.addLayout(action_row)

        self.record_button = QPushButton("●  Enregistrer en CSV pendant l'acquisition")
        self.record_button.setObjectName("recordButton")
        self.record_button.setCheckable(True)
        self.record_button.setEnabled(False)
        self.record_button.clicked.connect(self._toggle_recording)
        actions.addWidget(self.record_button)
        recording_note = QLabel(
            "Après l'arrêt, l'acquisition complète pourra aussi être exportée en CSV."
        )
        recording_note.setObjectName("muted")
        recording_note.setWordWrap(True)
        actions.addWidget(recording_note)
        self.file_label = QLabel("Aucun fichier sélectionné")
        self.file_label.setObjectName("muted")
        self.file_label.setWordWrap(True)
        actions.addWidget(self.file_label)
        side.addWidget(actions_card)
        side.addStretch()

        content = QVBoxLayout()
        content.setSpacing(12)
        body.addLayout(content, stretch=1)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(10)
        self.current_metric = self._metric(metrics, 0, "—", "Valeur instantanée")
        self.minimum_metric = self._metric(metrics, 1, "—", "Minimum affiché")
        self.maximum_metric = self._metric(metrics, 2, "—", "Maximum affiché")
        self.samples_metric = self._metric(metrics, 3, "0", "Échantillons acquis")
        content.addLayout(metrics)

        plot_card = QFrame()
        plot_card.setObjectName("card")
        plot_layout = QVBoxLayout(plot_card)
        plot_layout.setContentsMargins(12, 12, 12, 12)
        self.plot = pg.PlotWidget(background="#0d1728")
        self.plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.plot.showGrid(x=True, y=True, alpha=0.18)
        self.plot.setLabel("bottom", "Temps écoulé", units="s")
        self.plot.setLabel("left", "Tension", units="V")
        self.plot.getAxis("bottom").setTextPen(QColor("#92a6c2"))
        self.plot.getAxis("left").setTextPen(QColor("#92a6c2"))
        self.plot.getAxis("bottom").setPen(QColor("#405675"))
        self.plot.getAxis("left").setPen(QColor("#405675"))
        self.plot.setDownsampling(auto=True, mode="peak")
        self.plot.setClipToView(True)
        self.curve = self.plot.plot([], [], pen=pg.mkPen("#43b5ff", width=1.6))
        self.voltage_min_spin.valueChanged.connect(self._apply_vertical_range)
        self.voltage_max_spin.valueChanged.connect(self._apply_vertical_range)
        plot_layout.addWidget(self.plot)
        content.addWidget(plot_card, stretch=1)

        self.statusBar().showMessage("Initialisation de la détection NI-DAQmx…")

    @staticmethod
    def _card(title_text: str) -> tuple[QFrame, QFormLayout]:
        card = QFrame()
        card.setObjectName("card")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(14, 13, 14, 14)
        outer.setSpacing(10)
        title = QLabel(title_text)
        title.setObjectName("sectionTitle")
        outer.addWidget(title)
        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        outer.addLayout(form)
        return card, form

    @staticmethod
    def _metric(layout: QGridLayout, column: int, value: str, caption: str) -> QLabel:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(13, 9, 13, 9)
        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        caption_label = QLabel(caption)
        caption_label.setObjectName("metricCaption")
        card_layout.addWidget(value_label)
        card_layout.addWidget(caption_label)
        layout.addWidget(card, 0, column)
        return value_label

    def _restore_settings(self) -> None:
        self.rate_spin.setValue(float(self._settings.value("sample_rate", 1000.0)))
        self.display_samples_spin.setValue(int(self._settings.value("display_samples", 10000)))
        self.voltage_min_spin.setValue(float(self._settings.value("voltage_min", -10.0)))
        self.voltage_max_spin.setValue(float(self._settings.value("voltage_max", 10.0)))
        self.auto_y_checkbox.setChecked(
            self._settings.value("auto_y_scale", True, type=bool)
        )
        self._vertical_autoscale_changed(self.auto_y_checkbox.isChecked())
        # Remplace aussi l'ancien choix implicite du pilote au prochain lancement.
        # Un mode explicite déjà mémorisé (RSE, etc.) reste un choix utilisateur.
        mode = str(self._settings.value("terminal_mode", "DIFFERENTIAL"))
        if mode == "DEFAULT":
            mode = "DIFFERENTIAL"
        mode_index = self.terminal_combo.findData(mode)
        if mode_index < 0:
            mode_index = self.terminal_combo.findData("DIFFERENTIAL")
        self.terminal_combo.setCurrentIndex(max(0, mode_index))

    def _save_settings(self) -> None:
        self._settings.setValue("sample_rate", self.rate_spin.value())
        self._settings.setValue("display_samples", self.display_samples_spin.value())
        self._settings.setValue("voltage_min", self.voltage_min_spin.value())
        self._settings.setValue("voltage_max", self.voltage_max_spin.value())
        self._settings.setValue("auto_y_scale", self.auto_y_checkbox.isChecked())
        self._settings.setValue("terminal_mode", self.terminal_combo.currentData())

    def _vertical_autoscale_changed(self, enabled: bool) -> None:
        if enabled:
            self.plot.enableAutoRange(axis="y", enable=True)
        else:
            self.plot.enableAutoRange(axis="y", enable=False)
            self._apply_vertical_range()

    def _apply_vertical_range(self, _value: float | None = None) -> None:
        if self.auto_y_checkbox.isChecked():
            return
        minimum = self.voltage_min_spin.value()
        maximum = self.voltage_max_spin.value()
        if minimum < maximum:
            self.plot.setYRange(minimum, maximum, padding=0.0)

    def refresh_devices(self) -> None:
        if self._worker is not None:
            return
        previous_device = self.device_combo.currentData()
        previous_channel = self.channel_combo.currentData()
        devices, error = discover_devices()
        self._devices = {device.name: device for device in devices}

        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device_combo.addItem("Simulation (sans matériel)", SIMULATION_DEVICE)
        for device in devices:
            self.device_combo.addItem(device.display_name, device.name)

        desired_device = previous_device
        if not self._initial_device_scan_done and devices:
            desired_device = devices[0].name
        selected_index = self.device_combo.findData(desired_device)
        self.device_combo.setCurrentIndex(max(0, selected_index))
        self.device_combo.blockSignals(False)
        self._initial_device_scan_done = True
        self._device_changed(preferred_channel=previous_channel)

        if devices:
            self.statusBar().showMessage(
                f"{len(devices)} périphérique(s) NI avec entrée analogique détecté(s)."
            )
        elif error:
            self.statusBar().showMessage(f"Mode simulation disponible — {error}")
        else:
            self.statusBar().showMessage("Aucun périphérique NI détecté — mode simulation disponible.")

    def _device_changed(self, _index: int = -1, preferred_channel: str | None = None) -> None:
        device_name = self.device_combo.currentData()
        self.channel_combo.blockSignals(True)
        self.channel_combo.clear()
        if device_name == SIMULATION_DEVICE or device_name is None:
            self.channel_combo.addItem("Sortie interféromètre simulée", "")
            self.channel_combo.setEnabled(False)
            self.rate_spin.setMaximum(1_000_000.0)
            self.channel_combo.blockSignals(False)
            self._channel_changed()
            return

        device = self._devices.get(str(device_name))
        if device is None:
            self.channel_combo.blockSignals(False)
            return
        self.channel_combo.setEnabled(True)
        for channel in device.channels:
            self.channel_combo.addItem(channel, channel)
        target = preferred_channel or self._settings.value("physical_channel", "")
        target_index = self.channel_combo.findData(target)
        if target_index < 0:
            target_index = next(
                (
                    index
                    for index, channel in enumerate(device.channels)
                    if channel.lower().endswith("/ai1")
                ),
                0,
            )
        self.channel_combo.setCurrentIndex(target_index)
        self.channel_combo.blockSignals(False)
        self._channel_changed()
        maximum = device.max_single_channel_rate or 1_000_000.0
        self.rate_spin.setMaximum(maximum)
        if device.max_single_channel_rate:
            self.rate_spin.setToolTip(
                f"Limite annoncée pour une voie : {device.max_single_channel_rate:g} éch/s"
            )

    def _channel_changed(self, _index: int = -1) -> None:
        selected_mode = self.terminal_combo.currentData()
        device = self._devices.get(str(self.device_combo.currentData()))
        channel = str(self.channel_combo.currentData() or "")
        if device is None:
            supported_modes = tuple(TERMINAL_MODE_LABELS)
        else:
            supported_modes = device.terminal_modes_by_channel.get(
                channel, tuple(TERMINAL_MODE_LABELS)
            )
        self.terminal_combo.blockSignals(True)
        self.terminal_combo.clear()
        for key in supported_modes:
            self.terminal_combo.addItem(TERMINAL_MODE_LABELS[key], key)
        selected_index = self.terminal_combo.findData(selected_mode)
        if selected_index < 0:
            selected_index = self.terminal_combo.findData("DIFFERENTIAL")
        self.terminal_combo.setCurrentIndex(max(0, selected_index))
        self.terminal_combo.blockSignals(False)

    def _display_capacity_changed(self, value: int) -> None:
        self._buffer.resize(value)
        self._refresh_plot()

    def _current_config(self) -> tuple[AcquisitionConfig, float | None]:
        device_name = str(self.device_combo.currentData())
        device = self._devices.get(device_name)
        config = AcquisitionConfig(
            device_name=device_name,
            physical_channel=str(self.channel_combo.currentData() or ""),
            terminal_mode=str(self.terminal_combo.currentData()),
            sample_rate=self.rate_spin.value(),
            display_samples=self.display_samples_spin.value(),
            voltage_min=self.voltage_min_spin.value(),
            voltage_max=self.voltage_max_spin.value(),
        )
        return config, device.max_single_channel_rate if device else None

    def start_acquisition(self) -> None:
        if self._worker is not None:
            return
        try:
            config, maximum_rate = self._current_config()
            config.validate(maximum_rate)
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(self, "Configuration invalide", str(exc))
            return

        self._save_settings()
        if config.physical_channel:
            self._settings.setValue("physical_channel", config.physical_channel)
        self._buffer.resize(config.display_samples)
        self._buffer.clear()
        self._session_capture.discard()
        self.curve.setData([], [])
        self._total_samples = 0
        self._actual_rate = config.sample_rate
        self._acquisition_started_utc = None
        self._active_config = config
        self._update_metrics(np.empty(0))

        worker = AcquisitionWorker(config, self)
        worker.chunk_ready.connect(self._receive_chunk)
        worker.acquisition_ready.connect(self._acquisition_ready)
        worker.acquisition_error.connect(self._acquisition_error)
        # QThread.finished garantit que run() a rendu la main avant deleteLater().
        worker.finished.connect(self._acquisition_stopped)
        self._worker = worker
        self._set_running_controls(True)
        self._set_status("●  Connexion…", "#eab54d")
        self.statusBar().showMessage("Configuration de la tâche d'acquisition…")
        worker.start()

    def stop_acquisition(self) -> None:
        if self._worker is None:
            return
        self.stop_button.setEnabled(False)
        self.statusBar().showMessage("Arrêt de l'acquisition…")
        self._worker.request_stop()

    def _acquisition_ready(self, actual_rate: float) -> None:
        self._actual_rate = actual_rate
        self._acquisition_started_utc = datetime.now(timezone.utc)
        if self._active_config is not None:
            self._session_capture.start(
                self._active_config,
                actual_rate,
                self._acquisition_started_utc,
            )
        self.record_button.setEnabled(True)
        self.record_button.setText("●  Enregistrer en CSV à partir de maintenant")
        source = "Simulation" if self._active_config and self._active_config.is_simulation else "NI-DAQmx"
        self._set_status("●  Acquisition", "#42d392")
        self.statusBar().showMessage(
            f"{source} actif à {actual_rate:g} éch/s — affichage des "
            f"{self.display_samples_spin.value():n} derniers points."
        )

    def _receive_chunk(self, first_index: int, times: object, values: object) -> None:
        time_values = np.asarray(times, dtype=np.float64)
        voltage_values = np.asarray(values, dtype=np.float64)
        self._buffer.append(time_values, voltage_values)
        self._session_capture.append(voltage_values)
        self._total_samples = first_index + voltage_values.size
        if self._recorder.is_recording:
            try:
                self._recorder.append(first_index, time_values, voltage_values)
            except Exception as exc:
                self._stop_recording()
                QMessageBox.critical(self, "Erreur d'enregistrement", str(exc))
        self._refresh_plot()
        self._update_metrics(voltage_values)

    def _refresh_plot(self) -> None:
        times, values = self._buffer.arrays()
        self.curve.setData(times, values)

    def _update_metrics(self, newest_values: np.ndarray) -> None:
        _, displayed = self._buffer.arrays()
        if displayed.size:
            current = newest_values[-1] if newest_values.size else displayed[-1]
            self.current_metric.setText(f"{current:+.4f} V")
            self.minimum_metric.setText(f"{np.min(displayed):+.4f} V")
            self.maximum_metric.setText(f"{np.max(displayed):+.4f} V")
        else:
            self.current_metric.setText("—")
            self.minimum_metric.setText("—")
            self.maximum_metric.setText("—")
        self.samples_metric.setText(f"{self._total_samples:n}")

    def _acquisition_error(self, message: str) -> None:
        self._set_status("●  Erreur", "#ff6577")
        QMessageBox.critical(
            self,
            "Erreur d'acquisition",
            f"L'acquisition n'a pas pu continuer.\n\n{message}",
        )

    def _acquisition_stopped(self) -> None:
        self._stop_recording()
        self._session_capture.finish()
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self._set_running_controls(False)
        if self._session_capture.is_available:
            self.record_button.setEnabled(True)
            self.record_button.setText("Enregistrer toute l'acquisition en CSV…")
        if "Erreur" not in self.status_pill.text():
            self._set_status("●  Prêt", "#9db0c9")
        self.statusBar().showMessage(
            f"Acquisition arrêtée — {self._total_samples:n} échantillon(s) reçu(s)."
        )
        QTimer.singleShot(0, self.refresh_devices)

    def _set_running_controls(self, running: bool) -> None:
        for widget in (
            self.device_combo,
            self.channel_combo,
            self.terminal_combo,
            self.rate_spin,
            self.display_samples_spin,
            self.voltage_min_spin,
            self.voltage_max_spin,
            self.start_button,
        ):
            widget.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.record_button.setEnabled(False)

    def _set_status(self, text: str, color: str) -> None:
        self.status_pill.setText(text)
        self.status_pill.setStyleSheet(
            f"color: {color}; background-color: #17243a; border: 1px solid #2a3b57; "
            "border-radius: 10px; padding: 5px 10px;"
        )

    def _toggle_recording(self, checked: bool) -> None:
        if self._worker is None:
            self.record_button.blockSignals(True)
            self.record_button.setChecked(False)
            self.record_button.blockSignals(False)
            if checked:
                self._export_completed_acquisition()
            return
        if not checked:
            self._stop_recording()
            return
        if (
            self._active_config is None
            or self._worker is None
            or self._acquisition_started_utc is None
        ):
            self.record_button.setChecked(False)
            return

        default_dir = Path.cwd() / "recordings"
        default_name = f"acquisition_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer les données",
            str(default_dir / default_name),
            "Fichier CSV (*.csv)",
        )
        if not path:
            self.record_button.setChecked(False)
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            self._recorder.start(
                path,
                self._active_config,
                self._actual_rate,
                self._acquisition_started_utc,
            )
        except Exception as exc:
            self.record_button.setChecked(False)
            QMessageBox.critical(self, "Enregistrement impossible", str(exc))
            return
        self.record_button.setText("■  Arrêter l'enregistrement")
        self.file_label.setText(str(Path(path)))
        self.statusBar().showMessage(f"Enregistrement en cours : {path}")

    def _export_completed_acquisition(self) -> None:
        if not self._session_capture.is_available:
            return
        default_dir = Path.cwd() / "recordings"
        default_name = f"acquisition_complete_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer toute l'acquisition",
            str(default_dir / default_name),
            "Fichier CSV (*.csv)",
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            destination = self._session_capture.export_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "Export impossible", str(exc))
            return
        self.file_label.setText(
            f"{destination} — {self._session_capture.samples_written:n} échantillon(s) exportés"
        )
        self.statusBar().showMessage(f"Acquisition complète enregistrée : {destination}")

    def _stop_recording(self) -> None:
        if self._recorder.is_recording:
            path = self._recorder.stop()
            if path is not None:
                self.file_label.setText(
                    f"{path} — {self._recorder.samples_written:n} échantillon(s) enregistrés"
                )
        self.record_button.blockSignals(True)
        self.record_button.setChecked(False)
        self.record_button.setText("●  Enregistrer en CSV pendant l'acquisition")
        self.record_button.blockSignals(False)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (nom imposé par Qt)
        self._device_timer.stop()
        self._save_settings()
        if self._worker is not None:
            self._worker.request_stop()
            if not self._worker.wait(3500):
                QMessageBox.warning(
                    self,
                    "Acquisition encore active",
                    "Le pilote NI-DAQmx n'a pas encore rendu la main. Réessayez dans un instant.",
                )
                event.ignore()
                return
        self._stop_recording()
        self._session_capture.discard()
        event.accept()

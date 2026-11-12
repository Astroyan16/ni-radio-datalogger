"""Détection NI-DAQmx et worker d'acquisition."""

from __future__ import annotations

import math
import threading
import time
from typing import Any

import numpy as np
from PySide6.QtCore import QThread, Signal

from .models import AcquisitionConfig, DeviceInfo

try:
    import nidaqmx
    from nidaqmx.constants import AcquisitionType, TerminalConfiguration

    NIDAQMX_IMPORT_ERROR: str | None = None
except Exception as exc:  # Le mode simulation doit rester disponible sans NI-DAQmx.
    nidaqmx = None  # type: ignore[assignment]
    AcquisitionType = None  # type: ignore[assignment]
    TerminalConfiguration = None  # type: ignore[assignment]
    NIDAQMX_IMPORT_ERROR = str(exc)


TERMINAL_MODE_LABELS: dict[str, str] = {
    "DEFAULT": "Default (choix NI-DAQmx)",
    "DIFFERENTIAL": "Différentiel (DIFF)",
    "RSE": "Référencé à la masse (RSE)",
    "NRSE": "Non référencé (NRSE)",
    "PSEUDODIFFERENTIAL": "Pseudo-différentiel",
}


def discover_devices() -> tuple[list[DeviceInfo], str | None]:
    """Retourne les périphériques avec au moins une entrée analogique."""

    if nidaqmx is None:
        detail = f" ({NIDAQMX_IMPORT_ERROR})" if NIDAQMX_IMPORT_ERROR else ""
        return [], f"Module nidaqmx indisponible{detail}"

    try:
        system = nidaqmx.system.System.local()
        found: list[DeviceInfo] = []
        for device in system.devices:
            physical_channels = tuple(device.ai_physical_chans)
            channels = tuple(channel.name for channel in physical_channels)
            if not channels:
                continue
            terminal_modes_by_channel: dict[str, tuple[str, ...]] = {}
            for channel in physical_channels:
                try:
                    supported = tuple(
                        "DIFFERENTIAL" if mode.name == "DIFF" else mode.name
                        for mode in channel.ai_term_cfgs
                        if mode.name == "DIFF"
                        or (mode.name in TERMINAL_MODE_LABELS and mode.name != "DEFAULT")
                    )
                    terminal_modes_by_channel[channel.name] = ("DEFAULT", *supported)
                except Exception:
                    terminal_modes_by_channel[channel.name] = tuple(TERMINAL_MODE_LABELS)
            try:
                maximum_rate = float(device.ai_max_single_chan_rate)
                if not math.isfinite(maximum_rate) or maximum_rate <= 0:
                    maximum_rate = None
            except Exception:
                maximum_rate = None
            try:
                serial_value = int(device.serial_num)
                serial = str(serial_value) if serial_value else None
            except Exception:
                serial = None
            try:
                product_type = str(device.product_type)
            except Exception:
                product_type = "Périphérique NI"
            found.append(
                DeviceInfo(
                    name=device.name,
                    product_type=product_type,
                    channels=channels,
                    max_single_channel_rate=maximum_rate,
                    serial_number=serial,
                    terminal_modes_by_channel=terminal_modes_by_channel,
                )
            )
        return found, None
    except Exception as exc:
        return [], f"Détection NI-DAQmx impossible : {exc}"


def _terminal_configuration(mode: str) -> Any:
    if TerminalConfiguration is None:
        raise RuntimeError("NI-DAQmx n'est pas installé.")
    try:
        return getattr(TerminalConfiguration, "DIFF" if mode == "DIFFERENTIAL" else mode)
    except AttributeError as exc:
        raise ValueError(f"Mode de connexion inconnu : {mode}") from exc


class AcquisitionWorker(QThread):
    """Lit le matériel dans un thread afin de ne jamais bloquer Qt."""

    chunk_ready = Signal(int, object, object)
    acquisition_ready = Signal(float)
    acquisition_error = Signal(str)
    acquisition_stopped = Signal()

    def __init__(self, config: AcquisitionConfig, parent: Any = None) -> None:
        super().__init__(parent)
        self.config = config
        self._stop_event = threading.Event()
        self._sample_index = 0

    def request_stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        try:
            if self.config.is_simulation:
                self._run_simulation()
            else:
                self._run_hardware()
        except Exception as exc:
            if not self._stop_event.is_set():
                self.acquisition_error.emit(str(exc))
        finally:
            self.acquisition_stopped.emit()

    def _emit_values(self, values: np.ndarray, rate: float) -> None:
        values = np.asarray(values, dtype=np.float64).reshape(-1)
        if values.size == 0:
            return
        start = self._sample_index
        times = (np.arange(values.size, dtype=np.float64) + start) / rate
        self._sample_index += values.size
        self.chunk_ready.emit(start, times, values)

    def _run_hardware(self) -> None:
        if nidaqmx is None or AcquisitionType is None:
            raise RuntimeError(
                "NI-DAQmx pour Python n'est pas disponible. Installez les dépendances "
                "et le pilote NI-DAQmx, ou utilisez la source Simulation."
            )

        chunk_size = max(1, min(4096, round(self.config.sample_rate / 20.0)))
        driver_buffer = max(1000, chunk_size * 10)
        timeout = max(0.5, chunk_size / self.config.sample_rate + 0.5)

        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                self.config.physical_channel,
                terminal_config=_terminal_configuration(self.config.terminal_mode),
                min_val=self.config.voltage_min,
                max_val=self.config.voltage_max,
            )
            task.timing.cfg_samp_clk_timing(
                rate=self.config.sample_rate,
                sample_mode=AcquisitionType.CONTINUOUS,
                samps_per_chan=driver_buffer,
            )
            task.start()
            try:
                actual_rate = float(task.timing.samp_clk_rate)
            except Exception:
                actual_rate = self.config.sample_rate
            self.acquisition_ready.emit(actual_rate)

            while not self._stop_event.is_set():
                data = task.read(
                    number_of_samples_per_channel=chunk_size,
                    timeout=timeout,
                )
                self._emit_values(np.asarray(data, dtype=np.float64), actual_rate)

    def _run_simulation(self) -> None:
        rate = self.config.sample_rate
        chunk_size = max(1, min(4096, round(rate / 20.0)))
        period = chunk_size / rate
        random_generator = np.random.default_rng()
        deadline = time.perf_counter()
        self.acquisition_ready.emit(rate)

        while not self._stop_event.is_set():
            times = (
                np.arange(chunk_size, dtype=np.float64) + self._sample_index
            ) / rate
            # Signal volontairement riche : fondamentale, ondulation et bruit blanc.
            values = (
                1.2 * np.sin(2.0 * np.pi * 2.0 * times)
                + 0.25 * np.sin(2.0 * np.pi * 17.0 * times)
                + 0.055 * random_generator.standard_normal(chunk_size)
            )
            self._emit_values(values, rate)
            deadline += period
            wait_time = deadline - time.perf_counter()
            if wait_time > 0:
                self._stop_event.wait(wait_time)
            else:
                deadline = time.perf_counter()

"""Enregistrement CSV progressif des échantillons."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from time import perf_counter
from typing import BinaryIO, TextIO

import numpy as np
from numpy.typing import NDArray

from .models import AcquisitionConfig


class AcquisitionSession:
    """Conserve temporairement toute une acquisition pour un export ultérieur."""

    def __init__(self) -> None:
        self._file: BinaryIO | None = None
        self._temporary_path: Path | None = None
        self.config: AcquisitionConfig | None = None
        self.actual_rate = 0.0
        self.acquisition_started_utc: datetime | None = None
        self.samples_written = 0

    @property
    def is_available(self) -> bool:
        return self._temporary_path is not None and self.samples_written > 0

    def start(
        self,
        config: AcquisitionConfig,
        actual_rate: float,
        acquisition_started_utc: datetime,
    ) -> None:
        self.discard()
        output = tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix="ni_radio_datalogger_",
            suffix=".bin",
            delete=False,
        )
        self._file = output
        self._temporary_path = Path(output.name)
        self.config = config
        self.actual_rate = actual_rate
        self.acquisition_started_utc = acquisition_started_utc
        self.samples_written = 0

    def append(self, voltages: NDArray[np.float64]) -> None:
        if self._file is None:
            return
        values = np.asarray(voltages, dtype="<f8").reshape(-1)
        self._file.write(values.tobytes())
        self.samples_written += values.size

    def finish(self) -> None:
        if self._file is not None:
            self._file.flush()
            self._file.close()
            self._file = None

    def export_csv(self, path: str | Path) -> Path:
        self.finish()
        if (
            not self.is_available
            or self.config is None
            or self.acquisition_started_utc is None
        ):
            raise RuntimeError("Aucune acquisition terminée n'est disponible.")

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        assert self._temporary_path is not None
        with destination.open("w", encoding="utf-8", newline="") as output:
            output.write(f"# created_utc,{datetime.now(timezone.utc).isoformat()}\n")
            output.write(
                f"# acquisition_started_utc,{self.acquisition_started_utc.isoformat()}\n"
            )
            output.write(f"# source,{self.config.device_name}\n")
            output.write(f"# channel,{self.config.physical_channel or 'simulation'}\n")
            output.write(f"# terminal_mode,{self.config.terminal_mode}\n")
            output.write(f"# sample_rate_hz,{self.actual_rate:.12g}\n")
            output.write(
                f"# voltage_range_v,{self.config.voltage_min:g},{self.config.voltage_max:g}\n"
            )
            writer = csv.writer(output)
            writer.writerow(("sample_index", "elapsed_s", "interferometer_voltage_v"))
            sample_index = 0
            with self._temporary_path.open("rb") as source:
                while block := source.read(65_536 * 8):
                    values = np.frombuffer(block, dtype="<f8")
                    writer.writerows(
                        (
                            sample_index + offset,
                            f"{(sample_index + offset) / self.actual_rate:.9f}",
                            f"{voltage:.9f}",
                        )
                        for offset, voltage in enumerate(values)
                    )
                    sample_index += values.size
        return destination

    def discard(self) -> None:
        self.finish()
        if self._temporary_path is not None:
            self._temporary_path.unlink(missing_ok=True)
        self._temporary_path = None
        self.config = None
        self.actual_rate = 0.0
        self.acquisition_started_utc = None
        self.samples_written = 0


class CsvRecorder:
    def __init__(self) -> None:
        self._file: TextIO | None = None
        self._writer: csv.writer | None = None
        self._last_flush = 0.0
        self.path: Path | None = None
        self.samples_written = 0

    @property
    def is_recording(self) -> bool:
        return self._file is not None

    def start(
        self,
        path: str | Path,
        config: AcquisitionConfig,
        actual_rate: float,
        acquisition_started_utc: datetime,
    ) -> None:
        if self.is_recording:
            raise RuntimeError("Un enregistrement est déjà en cours.")
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        output = destination.open("w", encoding="utf-8", newline="")
        try:
            output.write(f"# created_utc,{datetime.now(timezone.utc).isoformat()}\n")
            output.write(f"# acquisition_started_utc,{acquisition_started_utc.isoformat()}\n")
            output.write(f"# source,{config.device_name}\n")
            output.write(f"# channel,{config.physical_channel or 'simulation'}\n")
            output.write(f"# terminal_mode,{config.terminal_mode}\n")
            output.write(f"# sample_rate_hz,{actual_rate:.12g}\n")
            output.write(f"# voltage_range_v,{config.voltage_min:g},{config.voltage_max:g}\n")
            writer = csv.writer(output)
            writer.writerow(("sample_index", "elapsed_s", "interferometer_voltage_v"))
        except Exception:
            output.close()
            raise
        self._file = output
        self._writer = writer
        self._last_flush = perf_counter()
        self.path = destination
        self.samples_written = 0

    def append(
        self,
        first_sample_index: int,
        elapsed_seconds: NDArray[np.float64],
        voltages: NDArray[np.float64],
    ) -> None:
        if self._writer is None or self._file is None:
            return
        times = np.asarray(elapsed_seconds, dtype=np.float64).reshape(-1)
        values = np.asarray(voltages, dtype=np.float64).reshape(-1)
        if times.size != values.size:
            raise ValueError("Le bloc à enregistrer est incohérent.")
        self._writer.writerows(
            (first_sample_index + offset, f"{time_value:.9f}", f"{voltage:.9f}")
            for offset, (time_value, voltage) in enumerate(zip(times, values, strict=True))
        )
        self.samples_written += values.size
        now = perf_counter()
        if now - self._last_flush >= 1.0:
            self._file.flush()
            self._last_flush = now

    def stop(self) -> Path | None:
        result = self.path
        if self._file is not None:
            self._file.flush()
            self._file.close()
        self._file = None
        self._writer = None
        return result

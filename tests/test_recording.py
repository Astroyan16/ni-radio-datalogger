from datetime import datetime, timezone

import numpy as np

from radio_datalogger.models import AcquisitionConfig, SIMULATION_DEVICE
from radio_datalogger.recording import AcquisitionSession, CsvRecorder


def test_csv_records_metadata_and_samples(tmp_path) -> None:
    config = AcquisitionConfig(
        device_name=SIMULATION_DEVICE,
        physical_channel="",
        terminal_mode="DEFAULT",
        sample_rate=1000.0,
        display_samples=1000,
    )
    destination = tmp_path / "capture.csv"
    recorder = CsvRecorder()
    recorder.start(
        destination,
        config,
        actual_rate=1000.0,
        acquisition_started_utc=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    recorder.append(10, np.array([0.010, 0.011]), np.array([1.25, -0.5]))
    recorder.stop()

    contents = destination.read_text(encoding="utf-8")
    assert "# acquisition_started_utc,2026-01-02T00:00:00+00:00" in contents
    assert "sample_index,elapsed_s,interferometer_voltage_v" in contents
    assert "10,0.010000000,1.250000000" in contents
    assert "11,0.011000000,-0.500000000" in contents


def test_completed_session_can_be_exported_after_stop(tmp_path) -> None:
    config = AcquisitionConfig(
        device_name=SIMULATION_DEVICE,
        physical_channel="",
        terminal_mode="DEFAULT",
        sample_rate=1000.0,
        display_samples=100,
    )
    session = AcquisitionSession()
    session.start(
        config,
        actual_rate=1000.0,
        acquisition_started_utc=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    session.append(np.array([1.25, -0.5]))
    session.finish()

    destination = session.export_csv(tmp_path / "complete.csv")
    contents = destination.read_text(encoding="utf-8")

    assert session.samples_written == 2
    assert "0,0.000000000,1.250000000" in contents
    assert "1,0.001000000,-0.500000000" in contents
    session.discard()

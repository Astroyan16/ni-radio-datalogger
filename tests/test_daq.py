from contextlib import nullcontext
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from PySide6.QtCore import Qt

from radio_datalogger import daq
from radio_datalogger.models import AcquisitionConfig, SIMULATION_DEVICE


def config() -> AcquisitionConfig:
    return AcquisitionConfig(SIMULATION_DEVICE, "", "DEFAULT", 1000, 100)


def test_simulation_emits_contiguous_samples_and_stops() -> None:
    worker = daq.AcquisitionWorker(config())
    blocks = []
    ready = []
    stopped = []

    def receive(index, times, values):
        blocks.append((index, times, values))
        if len(blocks) == 3:
            worker.request_stop()

    worker.chunk_ready.connect(receive, Qt.ConnectionType.DirectConnection)
    worker.acquisition_ready.connect(ready.append, Qt.ConnectionType.DirectConnection)
    worker.acquisition_stopped.connect(lambda: stopped.append(True), Qt.ConnectionType.DirectConnection)
    worker.run()
    assert ready == [1000]
    assert stopped == [True]
    assert [block[0] for block in blocks] == [0, 50, 100]
    np.testing.assert_allclose(np.concatenate([block[1] for block in blocks]), np.arange(150) / 1000)
    assert np.isfinite(np.concatenate([block[2] for block in blocks])).all()


@pytest.mark.parametrize("mode", ["RSE", "DIFFERENTIAL"])
def test_hardware_configuration_uses_actual_rate_without_real_device(monkeypatch, mode) -> None:
    task = Mock()
    task.timing.samp_clk_rate = 800.0
    task.read.return_value = [1.0, 2.0, 3.0]
    monkeypatch.setattr(daq, "nidaqmx", SimpleNamespace(Task=lambda: nullcontext(task)))
    worker = daq.AcquisitionWorker(replace(config(), device_name="DevTest", physical_channel="DevTest/ai1", terminal_mode=mode))
    blocks = []
    ready = []

    def receive(index, times, values):
        blocks.append((index, times, values))
        worker.request_stop()

    worker.chunk_ready.connect(receive, Qt.ConnectionType.DirectConnection)
    worker.acquisition_ready.connect(ready.append, Qt.ConnectionType.DirectConnection)
    worker.run()
    task.ai_channels.add_ai_voltage_chan.assert_called_once_with(
        "DevTest/ai1",
        terminal_config=(daq.TerminalConfiguration.DIFF if mode == "DIFFERENTIAL" else daq.TerminalConfiguration.RSE),
        min_val=-10, max_val=10
    )
    task.timing.cfg_samp_clk_timing.assert_called_once_with(
        rate=1000, sample_mode=daq.AcquisitionType.CONTINUOUS, samps_per_chan=1000
    )
    task.start.assert_called_once()
    assert ready == [800]
    assert blocks[0][0] == 0
    np.testing.assert_allclose(blocks[0][1], np.arange(3) / 800)
    np.testing.assert_array_equal(blocks[0][2], [1, 2, 3])


def test_missing_ni_package_reports_error_and_stops(monkeypatch) -> None:
    monkeypatch.setattr(daq, "nidaqmx", None)
    worker = daq.AcquisitionWorker(replace(config(), device_name="DevTest", physical_channel="DevTest/ai1"))
    errors = []
    stopped = []
    worker.acquisition_error.connect(errors.append, Qt.ConnectionType.DirectConnection)
    worker.acquisition_stopped.connect(lambda: stopped.append(True), Qt.ConnectionType.DirectConnection)
    worker.run()
    assert len(errors) == 1
    assert "Simulation" in errors[0]
    assert stopped == [True]


def test_missing_driver_keeps_discovery_nonfatal(monkeypatch) -> None:
    local = Mock(side_effect=RuntimeError("Pilote absent"))
    monkeypatch.setattr(daq, "nidaqmx", SimpleNamespace(system=SimpleNamespace(System=SimpleNamespace(local=local))))
    devices, error = daq.discover_devices()
    assert devices == []
    assert "Pilote absent" in error


def test_discovery_includes_driver_diff_mode(monkeypatch) -> None:
    channel = SimpleNamespace(name="DevTest/ai1", ai_term_cfgs=[
        daq.TerminalConfiguration.DIFF, daq.TerminalConfiguration.RSE,
    ])
    device = SimpleNamespace(
        name="DevTest", product_type="USB-6009", serial_num=123,
        ai_max_single_chan_rate=48000, ai_physical_chans=[channel],
    )
    monkeypatch.setattr(daq, "nidaqmx", SimpleNamespace(system=SimpleNamespace(
        System=SimpleNamespace(local=lambda: SimpleNamespace(devices=[device]))
    )))
    devices, error = daq.discover_devices()
    assert error is None
    assert devices[0].terminal_modes_by_channel["DevTest/ai1"] == (
        "DEFAULT", "DIFFERENTIAL", "RSE",
    )

import pytest

from radio_datalogger.models import AcquisitionConfig, SIMULATION_DEVICE


def valid_config(**overrides: object) -> AcquisitionConfig:
    values = {
        "device_name": SIMULATION_DEVICE,
        "physical_channel": "",
        "terminal_mode": "DEFAULT",
        "sample_rate": 1000.0,
        "display_samples": 10_000,
        "voltage_min": -10.0,
        "voltage_max": 10.0,
    }
    values.update(overrides)
    return AcquisitionConfig(**values)  # type: ignore[arg-type]


def test_valid_simulation_config() -> None:
    valid_config().validate()


def test_hardware_requires_channel() -> None:
    with pytest.raises(ValueError, match="entrée analogique"):
        valid_config(device_name="Dev1").validate()


def test_rate_must_not_exceed_device_limit() -> None:
    with pytest.raises(ValueError, match="dépasse"):
        valid_config(sample_rate=48_001.0).validate(48_000.0)


def test_voltage_range_must_be_ordered() -> None:
    with pytest.raises(ValueError, match="minimale"):
        valid_config(voltage_min=10.0, voltage_max=-10.0).validate()

"""Modèles indépendants de l'interface graphique."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite


SIMULATION_DEVICE = "__simulation__"


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """Description minimale d'un périphérique NI détecté."""

    name: str
    product_type: str
    channels: tuple[str, ...]
    max_single_channel_rate: float | None = None
    serial_number: str | None = None
    terminal_modes_by_channel: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        serial = f" · S/N {self.serial_number}" if self.serial_number else ""
        return f"{self.name} — {self.product_type}{serial}"

@dataclass(frozen=True, slots=True)
class AcquisitionConfig:
    """Configuration figée au démarrage d'une acquisition."""

    device_name: str
    physical_channel: str
    terminal_mode: str
    sample_rate: float
    display_samples: int
    voltage_min: float = -10.0
    voltage_max: float = 10.0

    @property
    def is_simulation(self) -> bool:
        return self.device_name == SIMULATION_DEVICE

    def validate(self, maximum_rate: float | None = None) -> None:
        if not self.is_simulation and not self.physical_channel:
            raise ValueError("Sélectionnez l'entrée analogique de la sortie interféromètre.")
        if not isfinite(self.sample_rate) or self.sample_rate <= 0:
            raise ValueError("La fréquence d'échantillonnage doit être positive.")
        if maximum_rate is not None and self.sample_rate > maximum_rate:
            raise ValueError(
                f"La fréquence demandée dépasse la limite du périphérique "
                f"({maximum_rate:g} éch/s)."
            )
        if self.display_samples < 2:
            raise ValueError("Il faut afficher au moins deux échantillons.")
        if not isfinite(self.voltage_min) or not isfinite(self.voltage_max):
            raise ValueError("Les limites de tension doivent être finies.")
        if self.voltage_min >= self.voltage_max:
            raise ValueError("La tension minimale doit être inférieure à la maximale.")

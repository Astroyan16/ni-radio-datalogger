"""Tampon circulaire utilisé par l'affichage temps réel."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class RingBuffer:
    """Conserve les N derniers couples (temps, valeur) sans croissance mémoire."""

    def __init__(self, capacity: int) -> None:
        if capacity < 2:
            raise ValueError("capacity doit être supérieur ou égal à 2")
        self._capacity = int(capacity)
        self._x = np.empty(self._capacity, dtype=np.float64)
        self._y = np.empty(self._capacity, dtype=np.float64)
        self._start = 0
        self._size = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return self._size

    def clear(self) -> None:
        self._start = 0
        self._size = 0

    def resize(self, capacity: int) -> None:
        if capacity < 2:
            raise ValueError("capacity doit être supérieur ou égal à 2")
        old_x, old_y = self.arrays()
        self._capacity = int(capacity)
        self._x = np.empty(self._capacity, dtype=np.float64)
        self._y = np.empty(self._capacity, dtype=np.float64)
        self._start = 0
        self._size = 0
        self.append(old_x[-self._capacity :], old_y[-self._capacity :])

    def append(self, x: NDArray[np.float64], y: NDArray[np.float64]) -> None:
        x_values = np.asarray(x, dtype=np.float64).reshape(-1)
        y_values = np.asarray(y, dtype=np.float64).reshape(-1)
        if x_values.size != y_values.size:
            raise ValueError("x et y doivent avoir la même longueur")
        if x_values.size == 0:
            return

        if x_values.size >= self._capacity:
            self._x[:] = x_values[-self._capacity :]
            self._y[:] = y_values[-self._capacity :]
            self._start = 0
            self._size = self._capacity
            return

        end = (self._start + self._size) % self._capacity
        first_count = min(x_values.size, self._capacity - end)
        self._x[end : end + first_count] = x_values[:first_count]
        self._y[end : end + first_count] = y_values[:first_count]
        remaining = x_values.size - first_count
        if remaining:
            self._x[:remaining] = x_values[first_count:]
            self._y[:remaining] = y_values[first_count:]

        overflow = max(0, self._size + x_values.size - self._capacity)
        self._start = (self._start + overflow) % self._capacity
        self._size = min(self._capacity, self._size + x_values.size)

    def arrays(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        if self._size == 0:
            return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)
        end = self._start + self._size
        if end <= self._capacity:
            return self._x[self._start : end].copy(), self._y[self._start : end].copy()
        split = end % self._capacity
        return (
            np.concatenate((self._x[self._start :], self._x[:split])),
            np.concatenate((self._y[self._start :], self._y[:split])),
        )

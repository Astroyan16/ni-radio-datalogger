import numpy as np

from radio_datalogger.buffer import RingBuffer


def test_append_without_wrap() -> None:
    buffer = RingBuffer(5)
    buffer.append(np.array([0.0, 1.0]), np.array([10.0, 11.0]))
    x, y = buffer.arrays()
    np.testing.assert_array_equal(x, [0.0, 1.0])
    np.testing.assert_array_equal(y, [10.0, 11.0])


def test_wrap_keeps_newest_values_in_order() -> None:
    buffer = RingBuffer(5)
    buffer.append(np.arange(4.0), np.arange(10.0, 14.0))
    buffer.append(np.arange(4.0, 8.0), np.arange(14.0, 18.0))
    x, y = buffer.arrays()
    np.testing.assert_array_equal(x, [3.0, 4.0, 5.0, 6.0, 7.0])
    np.testing.assert_array_equal(y, [13.0, 14.0, 15.0, 16.0, 17.0])


def test_resize_preserves_most_recent_values() -> None:
    buffer = RingBuffer(6)
    buffer.append(np.arange(6.0), np.arange(6.0) * 2)
    buffer.resize(3)
    x, y = buffer.arrays()
    np.testing.assert_array_equal(x, [3.0, 4.0, 5.0])
    np.testing.assert_array_equal(y, [6.0, 8.0, 10.0])


def test_oversized_append_keeps_only_capacity() -> None:
    buffer = RingBuffer(3)
    buffer.append(np.arange(10.0), np.arange(20.0, 30.0))
    x, y = buffer.arrays()
    np.testing.assert_array_equal(x, [7.0, 8.0, 9.0])
    np.testing.assert_array_equal(y, [27.0, 28.0, 29.0])

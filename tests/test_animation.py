"""Animation und Abfragetakt ohne grafischen Desktop prüfen."""
import queue
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from cpu_monitor import Gauge, Monitor, UPDATE_INTERVAL


class AnimationTests(unittest.TestCase):
    def gauge(self):
        gauge = SimpleNamespace(
            animation=None, duration=UPDATE_INTERVAL, started=10.0,
            start_value=20.0, target_value=100.0,
            start_maximum=100.0, target_maximum=200.0,
            winfo_viewable=Mock(return_value=True), draw=Mock(),
            after=Mock(return_value='next-frame'), animate=Mock(),
        )
        return gauge

    def test_linear_motion_uses_full_interval(self):
        for progress in (0.0, 0.25, 0.5, 0.75, 0.99, 1.0, 1.2):
            with self.subTest(progress=progress):
                gauge = self.gauge()
                with patch('cpu_monitor.time.monotonic', return_value=10 + progress * UPDATE_INTERVAL):
                    Gauge.animate(gauge)
                fraction = min(progress, 1.0)
                self.assertAlmostEqual(gauge.value, 20 + 80 * fraction)
                self.assertAlmostEqual(gauge.maximum, 100 + 100 * fraction)
                self.assertEqual(gauge.after.call_count, int(progress < 1))

    def test_hidden_gauge_finishes_without_more_frames(self):
        gauge = self.gauge()
        gauge.winfo_viewable.return_value = False
        with patch('cpu_monitor.time.monotonic', return_value=10.25):
            Gauge.animate(gauge)
        self.assertEqual(gauge.value, 100)
        gauge.after.assert_not_called()

    def test_collection_time_counts_towards_interval(self):
        for elapsed in (0.2, 1.5):
            with self.subTest(elapsed=elapsed):
                stopping = Mock()
                stopping.is_set.side_effect = (False, True)
                monitor = SimpleNamespace(stopping=stopping, mailbox=queue.Queue())
                with patch('cpu_monitor.time.monotonic', side_effect=(10.0, 10.0 + elapsed)), \
                     patch('cpu_monitor.read_sensors', return_value={}), \
                     patch('cpu_monitor.frequencies', return_value={}), \
                     patch('cpu_monitor.temperatures', return_value={}):
                    Monitor.collect(monitor)
                self.assertAlmostEqual(stopping.wait.call_args.args[0], max(0, UPDATE_INTERVAL - elapsed))
                self.assertEqual(monitor.mailbox.qsize(), 1)


if __name__ == '__main__':
    unittest.main()

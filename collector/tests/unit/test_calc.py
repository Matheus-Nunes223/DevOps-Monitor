import unittest

from monitor.calc import calculate_web_metrics, parse_access_log, percentile


class WebCalculationTests(unittest.TestCase):
    def test_parses_json_log_and_converts_seconds_to_ms(self):
        entry = parse_access_log(
            '{"remote_addr":"192.0.2.10","status":200,"request_time":0.125,'
            '"request_uri":"/","request_method":"GET","user":""}'
        )
        self.assertEqual(entry.remote_addr, "192.0.2.10")
        self.assertEqual(entry.request_time_ms, 125.0)

    def test_rejects_invalid_schema_and_status(self):
        with self.assertRaises(ValueError):
            parse_access_log('{"remote_addr":"192.0.2.1","status":99,"request_time":0}')
        with self.assertRaises(ValueError):
            parse_access_log("not json")

    def test_calculates_rps_percentiles_counts_and_error_rates(self):
        entries = [
            parse_access_log('{"remote_addr":"192.0.2.1","status":200,"request_time":0.01}'),
            parse_access_log('{"remote_addr":"192.0.2.2","status":404,"request_time":0.03}'),
            parse_access_log('{"remote_addr":"192.0.2.3","status":500,"request_time":0.05}'),
            parse_access_log('{"remote_addr":"192.0.2.4","status":503,"request_time":0.07}'),
        ]
        metrics = calculate_web_metrics(entries, duration_seconds=2)
        self.assertEqual(metrics.rps, 2.0)
        self.assertEqual(metrics.latency_p50_ms, 40.0)
        self.assertAlmostEqual(metrics.latency_p95_ms, 67.0)
        self.assertEqual(metrics.status_counts, {200: 1, 404: 1, 500: 1, 503: 1})
        self.assertEqual(metrics.error_4xx_rate, 0.25)
        self.assertEqual(metrics.error_5xx_rate, 0.5)

    def test_empty_window_has_zero_rps_but_undefined_rates_and_latency(self):
        metrics = calculate_web_metrics([], duration_seconds=15)
        self.assertEqual(metrics.rps, 0.0)
        self.assertIsNone(metrics.latency_p50_ms)
        self.assertIsNone(metrics.latency_p95_ms)
        self.assertIsNone(metrics.error_4xx_rate)
        self.assertIsNone(metrics.error_5xx_rate)
        self.assertEqual(metrics.status_counts, {})

    def test_percentile_interpolates_between_samples(self):
        self.assertEqual(percentile([10.0, 20.0, 30.0, 40.0], 0.5), 25.0)
        self.assertIsNone(percentile([], 0.95))


if __name__ == "__main__":
    unittest.main()

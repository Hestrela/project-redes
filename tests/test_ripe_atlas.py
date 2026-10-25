import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, call, patch

from fastapi.testclient import TestClient

from api.main import app
from api.ripe_atlas import (
    fetch_measurement_results,
    normalize_measurement_results,
    split_calibration_and_recent,
)


class RipeAtlasAdapterTests(unittest.TestCase):
    @patch("api.ripe_atlas.requests.get")
    def test_fetch_splits_fourteen_day_window_into_ripe_chunks(self, mock_get) -> None:
        mock_response = Mock(ok=True, status_code=200)
        mock_response.json.return_value = [{"timestamp": 1}]
        mock_get.return_value = mock_response
        start = datetime(2026, 10, 1, tzinfo=timezone.utc)
        stop = start + timedelta(days=14)

        results = fetch_measurement_results(12345, start, stop, probe_id=987)

        self.assertEqual(len(results), 3)
        self.assertEqual(mock_get.call_count, 3)
        calls = [item.kwargs["params"] for item in mock_get.call_args_list]
        self.assertEqual(
            [(item["stop"] - item["start"]) for item in calls],
            [6 * 24 * 60 * 60, 6 * 24 * 60 * 60, 2 * 24 * 60 * 60],
        )
        self.assertTrue(all(item["probe_ids"] == 987 for item in calls))

    def test_normalizes_results_by_probe_and_destination(self) -> None:
        records = [
            {
                "prb_id": 123,
                "dst_addr": "203.0.113.10",
                "timestamp": 1790812966,
                "sent": 3,
                "rcvd": 2,
                "result": [{"rtt": 20.0}, {"rtt": 22.0}, {"x": "timeout"}],
            },
            {
                "prb_id": 456,
                "dst_addr": "203.0.113.10",
                "timestamp": 1790812966,
                "sent": 3,
                "rcvd": 0,
                "result": [],
            },
        ]

        flows = normalize_measurement_results(records)

        self.assertEqual(set(flows), {"123|203.0.113.10", "456|203.0.113.10"})
        self.assertEqual(flows["123|203.0.113.10"][0].rtts_ms, (20.0, 22.0))
        self.assertEqual(flows["123|203.0.113.10"][0].enviados, 3)
        self.assertEqual(flows["456|203.0.113.10"][0].rtts_ms, ())
        self.assertEqual(
            flows["123|203.0.113.10"][0].timestamp_utc.tzinfo,
            timezone.utc,
        )

    def test_splits_first_seven_days_as_calibration(self) -> None:
        start = datetime(2026, 10, 1, tzinfo=timezone.utc)
        measurements = [
            type("Sample", (), {"timestamp_utc": start + timedelta(days=day)})()
            for day in range(9)
        ]

        calibration, recent = split_calibration_and_recent(measurements)

        self.assertEqual(len(calibration), 7)
        self.assertEqual([item.timestamp_utc for item in recent], [
            start + timedelta(days=7),
            start + timedelta(days=8),
        ])

    def test_predicts_from_measurement_id_and_probe_id(self) -> None:
        start = datetime(2026, 10, 1, tzinfo=timezone.utc)
        start_epoch = int(start.timestamp())
        raw_records = [
            {
                "prb_id": 123,
                "dst_addr": "203.0.113.10",
                "timestamp": start_epoch + 240 * index,
                "sent": 4,
                "rcvd": 4,
                "result": [
                    {"rtt": 21.2},
                    {"rtt": 20.9},
                    {"rtt": 21.5},
                    {"rtt": 21.1},
                ],
            }
            for index in range(2525)
        ]

        class FakeModel:
            def predict(self, features):
                return [0]

            def predict_proba(self, features):
                return [[0.9, 0.05, 0.05]]

        client = TestClient(app)
        with (
            patch("api.main.fetch_measurement_results", return_value=raw_records),
            patch("api.main._load_model", return_value=FakeModel()),
            patch("api.main._model_sha256", return_value="test-sha"),
        ):
            response = client.post(
                "/api/v1/previsoes/ripe-atlas",
                json={
                    "measurement_id": 109069241,
                    "probe_id": 123,
                    "inicio_utc": "2026-10-01T00:00:00Z",
                    "fim_utc": "2026-10-15T00:00:00Z",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["measurement_id"], 109069241)
        self.assertEqual(body["fluxos_encontrados"], 1)
        self.assertEqual(len(body["previsoes"]), 1)
        self.assertEqual(body["previsoes"][0]["fluxo_id"], "123|203.0.113.10")
        self.assertEqual(body["previsoes"][0]["classe_prevista"], "OK")

    def test_rejects_ripe_atlas_window_over_fourteen_days(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/api/v1/previsoes/ripe-atlas",
            json={
                "measurement_id": 109069241,
                "inicio_utc": "2026-10-01T00:00:00Z",
                "fim_utc": "2026-10-16T00:00:00Z",
            },
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
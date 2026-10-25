import unittest
from datetime import datetime, timedelta, timezone

from api.features import (
    FEATURES,
    FeatureInputError,
    Measurement,
    build_features,
)


class FeatureEngineeringTests(unittest.TestCase):
    def setUp(self) -> None:
        start = datetime(2026, 10, 1, tzinfo=timezone.utc)
        self.calibration = [
            Measurement(
                timestamp_utc=start + timedelta(minutes=index),
                enviados=2,
                rtts_ms=(10.0, 12.0),
            )
            for index in range(1500)
        ]
        recent_start = start + timedelta(days=2)
        self.recent = [
            Measurement(recent_start + timedelta(minutes=offset), 2, rtts)
            for offset, rtts in enumerate(
                ((11.0, 11.0), (15.0, 15.0), (22.0, 22.0), (), (11.0, 11.0))
            )
        ]

    def test_builds_official_t12_feature_order_and_window_counts(self) -> None:
        features = build_features(self.calibration, self.recent)

        self.assertEqual(tuple(features), FEATURES)
        self.assertEqual(features["z_robusto"], 0.0)
        self.assertEqual(features["aumento_pct"], 0.0)
        self.assertEqual(features["perda_pct"], 0.0)
        self.assertEqual(features["timeout_atual"], 0)
        self.assertEqual(features["n5_timeout"], 1)
        self.assertEqual(features["n5_aumento80"], 1)
        self.assertEqual(features["n5_risco"], 1)

    def test_rejects_calibration_below_project_minimum(self) -> None:
        with self.assertRaises(FeatureInputError):
            build_features(self.calibration[:-1], self.recent)


if __name__ == "__main__":
    unittest.main()
"""
Tests for operations services and ML components.
"""
from unittest.mock import patch, MagicMock

from django.test import TestCase

from apps.operations.ml.anomaly_detector import AnomalyDetector
from apps.operations.ml.demand_forecaster import DemandForecaster


class AnomalyDetectorTest(TestCase):
    """Tests for the AnomalyDetector class."""

    def test_detector_initialization(self):
        detector = AnomalyDetector()
        self.assertEqual(detector.contamination, 0.05)

    def test_detector_custom_contamination(self):
        detector = AnomalyDetector(contamination=0.1)
        self.assertEqual(detector.contamination, 0.1)

    def test_detect_anomalies_insufficient_data(self):
        detector = AnomalyDetector()
        result = detector.detect_anomalies(turbine_id=99999, lookback_hours=168)
        self.assertEqual(result['anomaly_count'], 0)
        self.assertEqual(result['risk_level'], 'low')
        self.assertIn('Insufficient', result['details'])

    def test_predict_failure_no_data(self):
        detector = AnomalyDetector()
        result = detector.predict_failure(turbine_id=99999)
        self.assertFalse(result['has_risk'])
        self.assertIsNone(result['predicted_failure_date'])
        self.assertEqual(result['confidence'], 0.0)
        self.assertEqual(result['severity'], 'low')

    def test_classify_failure_type_empty(self):
        detector = AnomalyDetector()
        result = detector._classify_failure_type(anomalies=[])
        self.assertEqual(result, 'other')


class DemandForecasterTest(TestCase):
    """Tests for the DemandForecaster class."""

    def test_forecaster_initialization(self):
        forecaster = DemandForecaster()
        self.assertIsNotNone(forecaster)

    def test_generate_forecast_insufficient_data(self):
        forecaster = DemandForecaster()
        result = forecaster.generate_forecast(hours_ahead=24)
        self.assertEqual(result, [])

    def test_timestamp_to_features_shape(self):
        import numpy as np
        from django.utils import timezone

        forecaster = DemandForecaster()
        now = timezone.now()
        features = forecaster._timestamp_to_features(now)
        self.assertEqual(features.shape, (7,))
        self.assertIsInstance(features, np.ndarray)

    def test_timestamp_to_features_weekend(self):
        import numpy as np
        from datetime import datetime
        from django.utils import timezone

        forecaster = DemandForecaster()
        # Create a Saturday (weekday() == 5)
        saturday = timezone.make_aware(datetime(2024, 1, 6, 12, 0))
        features = forecaster._timestamp_to_features(saturday)
        self.assertEqual(features[6], 1.0)  # is_weekend flag

    def test_timestamp_to_features_weekday(self):
        import numpy as np
        from datetime import datetime
        from django.utils import timezone

        forecaster = DemandForecaster()
        # Create a Monday (weekday() == 0)
        monday = timezone.make_aware(datetime(2024, 1, 1, 12, 0))
        features = forecaster._timestamp_to_features(monday)
        self.assertEqual(features[6], 0.0)  # is_weekend flag

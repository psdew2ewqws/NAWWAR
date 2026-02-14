"""
Anomaly detection for turbine sensor data using Isolation Forest.

Uses sklearn's IsolationForest to detect anomalous sensor readings
and predict potential turbine failures.
"""
import logging
from collections import defaultdict
from datetime import timedelta

import numpy as np
from django.utils import timezone
from sklearn.ensemble import IsolationForest

from apps.operations.models import SensorReading

logger = logging.getLogger(__name__)

# Mapping from dominant anomalous sensor to failure type
_FAILURE_TYPE_MAP = {
    'vibration': 'bearing',
    'temperature': 'blade',
    'exhaust_temp': 'gearbox',
    'pressure': 'seal',
    'rpm': 'other',
}

_SEVERITY_THRESHOLDS = {
    'low': 0.15,
    'medium': 0.30,
    'high': 0.50,
    'critical': 0.70,
}

_RECOMMENDED_ACTIONS = {
    'bearing': 'Schedule bearing inspection and lubrication check. Monitor vibration trend closely.',
    'blade': 'Inspect blade surfaces for erosion or fouling. Check inlet filters.',
    'seal': 'Check seal integrity and pressure differential. Inspect for leaks.',
    'gearbox': 'Inspect gearbox oil quality and temperature. Schedule vibration analysis.',
    'other': 'Schedule general inspection. Review operational parameters.',
}


class AnomalyDetector:
    """Detects anomalies in turbine sensor data using Isolation Forest."""

    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination

    def detect_anomalies(self, *, turbine_id: int, lookback_hours: int = 168) -> dict:
        """
        Run anomaly detection on sensor readings for a turbine.

        Args:
            turbine_id: ID of the turbine to analyze.
            lookback_hours: Hours of historical data to use.

        Returns:
            Dict with anomalies list, anomaly_count, risk_level, details.
        """
        cutoff = timezone.now() - timedelta(hours=lookback_hours)

        readings = SensorReading.objects.filter(
            turbine_id=turbine_id,
            timestamp__gte=cutoff,
        ).order_by('timestamp')

        # Group readings by timestamp to build feature matrix
        readings_by_ts = defaultdict(dict)
        for r in readings:
            readings_by_ts[r.timestamp][r.reading_type] = float(r.value)

        feature_names = ['vibration', 'temperature', 'pressure', 'rpm', 'exhaust_temp']
        timestamps = []
        features = []

        for ts in sorted(readings_by_ts.keys()):
            row = readings_by_ts[ts]
            if len(row) >= 4:  # Need most sensor types present
                feature_row = [
                    row.get('vibration', 0.0),
                    row.get('temperature', 0.0),
                    row.get('pressure', 0.0),
                    row.get('rpm', 0.0),
                    row.get('exhaust_temp', 0.0),
                ]
                features.append(feature_row)
                timestamps.append(ts)

        if len(features) < 10:
            return {
                'anomalies': [],
                'anomaly_count': 0,
                'risk_level': 'low',
                'details': 'Insufficient data for analysis.',
            }

        X = np.array(features)

        model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100,
        )
        model.fit(X)

        predictions = model.predict(X)
        scores = model.decision_function(X)

        anomalies = []
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:  # Anomaly
                anomaly_score = max(0.0, min(1.0, -score))
                anomalies.append({
                    'timestamp': timestamps[i].isoformat(),
                    'anomaly_score': round(anomaly_score, 4),
                    'features': {
                        name: round(X[i, j], 4)
                        for j, name in enumerate(feature_names)
                    },
                })

        anomaly_count = len(anomalies)
        total = len(features)
        anomaly_ratio = anomaly_count / total if total > 0 else 0.0

        if anomaly_ratio > 0.15:
            risk_level = 'critical'
        elif anomaly_ratio > 0.08:
            risk_level = 'high'
        elif anomaly_ratio > 0.03:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        return {
            'anomalies': anomalies,
            'anomaly_count': anomaly_count,
            'total_readings': total,
            'risk_level': risk_level,
            'details': f'Detected {anomaly_count}/{total} anomalous readings.',
        }

    def predict_failure(self, *, turbine_id: int) -> dict:
        """
        Analyze anomaly trends to predict potential failure.

        Looks at the recent window of sensor data, detects anomalies,
        and if the anomaly score trend is increasing, estimates time to failure.

        Args:
            turbine_id: ID of the turbine to analyze.

        Returns:
            Dict with failure prediction details.
        """
        result = self.detect_anomalies(turbine_id=turbine_id, lookback_hours=336)  # 2 weeks

        if result['anomaly_count'] == 0:
            return {
                'has_risk': False,
                'predicted_failure_date': None,
                'confidence': 0.0,
                'failure_type': None,
                'severity': 'low',
                'description': 'No anomalies detected. Turbine operating normally.',
                'recommended_action': 'Continue routine monitoring.',
            }

        anomalies = result['anomalies']

        # Analyze trend: split into first half and second half
        mid = len(anomalies) // 2
        if mid == 0:
            mid = 1
        first_half_scores = [a['anomaly_score'] for a in anomalies[:mid]]
        second_half_scores = [a['anomaly_score'] for a in anomalies[mid:]]

        avg_first = np.mean(first_half_scores) if first_half_scores else 0
        avg_second = np.mean(second_half_scores) if second_half_scores else 0

        increasing_trend = avg_second > avg_first * 1.1

        # Determine dominant failure type from latest anomalies
        latest_anomalies = anomalies[-5:] if len(anomalies) >= 5 else anomalies
        dominant_feature = self._classify_failure_type(anomalies=latest_anomalies)
        failure_type = _FAILURE_TYPE_MAP.get(dominant_feature, 'other')

        # Determine severity from risk level
        risk_level = result['risk_level']
        severity = risk_level

        if not increasing_trend and risk_level in ('low', 'medium'):
            return {
                'has_risk': False,
                'predicted_failure_date': None,
                'confidence': round(avg_second, 2),
                'failure_type': failure_type,
                'severity': severity,
                'description': f'Some anomalies detected but no increasing trend. Risk level: {risk_level}.',
                'recommended_action': _RECOMMENDED_ACTIONS.get(failure_type, _RECOMMENDED_ACTIONS['other']),
            }

        # Estimate time to failure based on anomaly progression rate
        if avg_second > 0.7:
            days_to_failure = 3
        elif avg_second > 0.5:
            days_to_failure = 7
        elif avg_second > 0.3:
            days_to_failure = 14
        else:
            days_to_failure = 30

        predicted_date = (timezone.now() + timedelta(days=days_to_failure)).date()
        confidence = min(0.95, avg_second + 0.2) if increasing_trend else min(0.7, avg_second)

        return {
            'has_risk': True,
            'predicted_failure_date': predicted_date.isoformat(),
            'confidence': round(confidence, 2),
            'failure_type': failure_type,
            'severity': severity,
            'description': (
                f'Increasing anomaly trend detected. '
                f'Potential {failure_type} failure predicted within {days_to_failure} days.'
            ),
            'recommended_action': _RECOMMENDED_ACTIONS.get(failure_type, _RECOMMENDED_ACTIONS['other']),
        }

    def _classify_failure_type(self, *, anomalies: list[dict]) -> str:
        """
        Classify the most likely failure type based on which sensor
        shows the highest deviation in anomalous readings.
        """
        if not anomalies:
            return 'other'

        # Aggregate feature values across anomalies (normalized deviation)
        feature_sums = defaultdict(float)
        for anomaly in anomalies:
            features = anomaly.get('features', {})
            for name, value in features.items():
                feature_sums[name] += abs(value)

        if not feature_sums:
            return 'other'

        # The feature with highest aggregate value relative to its normal range
        # is the most likely cause
        # Normalize by typical ranges
        ranges = {
            'vibration': 5.0,
            'temperature': 500.0,
            'pressure': 15.0,
            'rpm': 3600.0,
            'exhaust_temp': 600.0,
        }

        normalized = {}
        for name, total in feature_sums.items():
            range_val = ranges.get(name, 1.0)
            normalized[name] = total / (range_val * len(anomalies))

        return max(normalized, key=normalized.get)

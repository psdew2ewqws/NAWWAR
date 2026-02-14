"""
Demand forecasting using sklearn linear models with time-based features.

Uses Ridge regression with cyclical time features (hour, day-of-week, month)
to forecast grid electricity demand.
"""
import logging
from datetime import timedelta

import numpy as np
from django.utils import timezone
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from apps.operations.models import DemandForecast

logger = logging.getLogger(__name__)


class DemandForecaster:
    """Forecasts electricity demand using Ridge regression with time features."""

    def generate_forecast(self, *, hours_ahead: int = 24) -> list[dict]:
        """
        Generate demand forecast for the next N hours.

        Uses historical DemandForecast data to train a model and predict
        future demand based on time-of-day, day-of-week, and seasonal patterns.

        Args:
            hours_ahead: Number of hours to forecast into the future.

        Returns:
            List of dicts with timestamp, predicted_mw, confidence bounds.
        """
        historical = DemandForecast.objects.order_by('forecast_hour').values_list(
            'forecast_hour', 'predicted_mw',
        )

        hist_list = list(historical)
        if len(hist_list) < 48:
            logger.warning('Insufficient historical data for forecasting (%d records)', len(hist_list))
            return []

        timestamps, values = zip(*hist_list)
        X, y = self._prepare_features(timestamps=timestamps, values=values)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = Ridge(alpha=1.0)
        model.fit(X_scaled, y)

        # Calculate residual std for confidence intervals
        y_pred_train = model.predict(X_scaled)
        residuals = y - y_pred_train
        residual_std = float(np.std(residuals))

        # Generate future timestamps and predict
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        forecasts = []

        for i in range(1, hours_ahead + 1):
            future_ts = now + timedelta(hours=i)
            X_future = self._timestamp_to_features(future_ts)
            X_future_scaled = scaler.transform(X_future.reshape(1, -1))
            predicted = float(model.predict(X_future_scaled)[0])

            # Confidence widens with forecast horizon
            horizon_factor = 1.0 + (i / hours_ahead) * 0.5
            margin = residual_std * 1.96 * horizon_factor

            forecasts.append({
                'timestamp': future_ts.isoformat(),
                'predicted_mw': round(max(0, predicted), 2),
                'confidence_lower': round(max(0, predicted - margin), 2),
                'confidence_upper': round(predicted + margin, 2),
            })

        return forecasts

    def _prepare_features(self, *, timestamps: tuple, values: tuple) -> tuple:
        """
        Extract time-based features from timestamps.

        Features: hour_sin, hour_cos, dow_sin, dow_cos, month_sin, month_cos,
                  is_weekend (binary).

        Returns:
            Tuple of (X, y) numpy arrays.
        """
        X_list = []
        for ts in timestamps:
            X_list.append(self._timestamp_to_features(ts))

        X = np.array(X_list)
        y = np.array([float(v) for v in values])
        return X, y

    def _timestamp_to_features(self, ts) -> np.ndarray:
        """Convert a single timestamp to feature vector."""
        hour = ts.hour
        dow = ts.weekday()
        month = ts.month

        return np.array([
            np.sin(2 * np.pi * hour / 24),
            np.cos(2 * np.pi * hour / 24),
            np.sin(2 * np.pi * dow / 7),
            np.cos(2 * np.pi * dow / 7),
            np.sin(2 * np.pi * month / 12),
            np.cos(2 * np.pi * month / 12),
            1.0 if dow >= 5 else 0.0,
        ])

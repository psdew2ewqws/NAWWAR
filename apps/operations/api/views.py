"""
Operations API views.

Includes CRUD viewsets for models and action endpoints for
anomaly detection, demand forecasting, and plant overview.
"""
import logging

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.operations.models import (
    Plant,
    Turbine,
    SensorReading,
    MaintenancePrediction,
    EmissionsRecord,
    HeatRateRecord,
    DemandForecast,
)
from apps.operations import selectors, services
from .serializers import (
    PlantSerializer,
    TurbineSerializer,
    SensorReadingSerializer,
    MaintenancePredictionSerializer,
    EmissionsRecordSerializer,
    HeatRateRecordSerializer,
    DemandForecastSerializer,
)

logger = logging.getLogger(__name__)


class PlantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Plant.objects.filter(is_active=True)
    serializer_class = PlantSerializer
    permission_classes = [IsAuthenticated]


class PlantDetailApi(APIView):
    """Get detailed plant information by code."""
    permission_classes = [IsAuthenticated]

    def get(self, request, plant_code):
        plant = selectors.plant_get_by_code(code=plant_code)
        if not plant:
            return Response(
                {'error': f'Plant {plant_code} not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PlantSerializer(plant)
        return Response(serializer.data)


class TurbineViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Turbine.objects.select_related('plant').all()
    serializer_class = TurbineSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['plant', 'status']


class TurbineListApi(APIView):
    """List turbines for a specific plant."""
    permission_classes = [IsAuthenticated]

    def get(self, request, plant_code):
        turbines = selectors.turbine_list(plant_code=plant_code)
        serializer = TurbineSerializer(turbines, many=True)
        return Response(serializer.data)


class SensorReadingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SensorReading.objects.select_related('turbine', 'turbine__plant').all()
    serializer_class = SensorReadingSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['turbine', 'reading_type', 'is_anomaly']


class MaintenancePredictionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MaintenancePrediction.objects.select_related('turbine', 'turbine__plant').all()
    serializer_class = MaintenancePredictionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['turbine', 'severity', 'is_acknowledged']


class EmissionsRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EmissionsRecord.objects.select_related('plant').all()
    serializer_class = EmissionsRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['plant', 'is_compliant']


class HeatRateRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HeatRateRecord.objects.select_related('plant').all()
    serializer_class = HeatRateRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['plant']


class DemandForecastViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DemandForecast.objects.all()
    serializer_class = DemandForecastSerializer
    permission_classes = [IsAuthenticated]


class AnomalyDetectionApi(APIView):
    """
    POST: Trigger anomaly detection for a plant or all plants.
    GET: Get active maintenance predictions.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plant_code = request.query_params.get('plant_code')
        predictions = selectors.maintenance_predictions_active(plant_code=plant_code)
        serializer = MaintenancePredictionSerializer(predictions, many=True)
        return Response(serializer.data)

    def post(self, request):
        plant_code = request.data.get('plant_code')
        try:
            results = services.run_anomaly_detection(plant_code=plant_code)
            return Response({
                'status': 'success',
                'predictions': results,
                'count': len(results),
            })
        except Exception:
            logger.exception('Anomaly detection failed')
            return Response(
                {'error': 'Anomaly detection failed. Check server logs.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DemandForecastApi(APIView):
    """
    POST: Generate new demand forecast.
    GET: Get upcoming demand forecasts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        hours = int(request.query_params.get('hours', 24))
        forecasts = selectors.demand_forecast_upcoming(hours=hours)
        serializer = DemandForecastSerializer(forecasts, many=True)
        return Response(serializer.data)

    def post(self, request):
        hours_ahead = int(request.data.get('hours_ahead', 24))
        try:
            results = services.generate_demand_forecast(hours_ahead=hours_ahead)
            return Response({
                'status': 'success',
                'forecasts': results,
                'count': len(results),
            })
        except Exception:
            logger.exception('Demand forecast generation failed')
            return Response(
                {'error': 'Forecast generation failed. Check server logs.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EmissionsStatusApi(APIView):
    """Get emissions compliance status for a plant."""
    permission_classes = [IsAuthenticated]

    def get(self, request, plant_code):
        result = services.calculate_emissions_status(plant_code=plant_code)
        if 'error' in result:
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        return Response(result)


class PlantOverviewApi(APIView):
    """Get comprehensive plant overview including turbines, alerts, emissions."""
    permission_classes = [IsAuthenticated]

    def get(self, request, plant_code):
        result = services.get_plant_overview(plant_code=plant_code)
        if 'error' in result:
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        return Response(result)

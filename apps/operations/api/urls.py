"""
Operations API URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'plants', views.PlantViewSet, basename='plant')
router.register(r'turbines', views.TurbineViewSet, basename='turbine')
router.register(r'sensor-readings', views.SensorReadingViewSet, basename='sensor-reading')
router.register(r'maintenance', views.MaintenancePredictionViewSet, basename='maintenance')
router.register(r'emissions', views.EmissionsRecordViewSet, basename='emissions')
router.register(r'heat-rate', views.HeatRateRecordViewSet, basename='heat-rate')
router.register(r'forecasts', views.DemandForecastViewSet, basename='forecast')

app_name = 'operations'

urlpatterns = [
    path('', include(router.urls)),
    # Action endpoints
    path('anomaly-detection/', views.AnomalyDetectionApi.as_view(), name='anomaly-detection'),
    path('demand-forecast/', views.DemandForecastApi.as_view(), name='demand-forecast'),
    path('emissions-status/<str:plant_code>/', views.EmissionsStatusApi.as_view(), name='emissions-status'),
    path('plant-overview/<str:plant_code>/', views.PlantOverviewApi.as_view(), name='plant-overview'),
    path('plant-detail/<str:plant_code>/', views.PlantDetailApi.as_view(), name='plant-detail'),
    path('plant-turbines/<str:plant_code>/', views.TurbineListApi.as_view(), name='plant-turbines'),
]

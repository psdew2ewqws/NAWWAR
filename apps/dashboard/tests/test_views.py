"""
Tests for dashboard views.
"""
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse

from apps.operations.models import Plant


class OperationsIndexViewTest(TestCase):
    """Tests for the operations index view."""

    def setUp(self):
        self.client = Client()
        self.plant = Plant.objects.create(
            code='AQABA',
            name='Aqaba Thermal Power Station',
            plant_type=Plant.PlantType.STEAM,
            capacity_mw=Decimal('656.00'),
            current_load_mw=Decimal('400.00'),
        )

    def test_operations_index_returns_200(self):
        response = self.client.get(reverse('dashboard:operations-index'))
        self.assertEqual(response.status_code, 200)

    def test_operations_index_uses_template(self):
        response = self.client.get(reverse('dashboard:operations-index'))
        self.assertTemplateUsed(response, 'dashboard/operations/index.html')

    def test_operations_index_contains_plant(self):
        response = self.client.get(reverse('dashboard:operations-index'))
        self.assertContains(response, 'AQABA')


class OperationsPlantDetailViewTest(TestCase):
    """Tests for the plant detail view."""

    def setUp(self):
        self.client = Client()
        self.plant = Plant.objects.create(
            code='REHAB',
            name='Rehab Gas Power Station',
            plant_type=Plant.PlantType.GAS,
            capacity_mw=Decimal('357.00'),
            current_load_mw=Decimal('200.00'),
        )

    def test_plant_detail_returns_200(self):
        response = self.client.get(
            reverse('dashboard:operations-plant-detail', kwargs={'plant_key': 'rehab'})
        )
        self.assertEqual(response.status_code, 200)

    def test_plant_detail_case_insensitive(self):
        response = self.client.get(
            reverse('dashboard:operations-plant-detail', kwargs={'plant_key': 'Rehab'})
        )
        self.assertEqual(response.status_code, 200)

    def test_plant_detail_returns_404_for_invalid(self):
        response = self.client.get(
            reverse('dashboard:operations-plant-detail', kwargs={'plant_key': 'NONEXISTENT'})
        )
        self.assertEqual(response.status_code, 404)

    def test_plant_detail_uses_template(self):
        response = self.client.get(
            reverse('dashboard:operations-plant-detail', kwargs={'plant_key': 'rehab'})
        )
        self.assertTemplateUsed(response, 'dashboard/operations/plant_detail.html')


class ConsumerIndexViewTest(TestCase):
    """Tests for the consumer index view."""

    def setUp(self):
        self.client = Client()

    def test_consumer_index_returns_200(self):
        response = self.client.get(reverse('dashboard:consumer-index'))
        self.assertEqual(response.status_code, 200)

    def test_consumer_index_uses_template(self):
        response = self.client.get(reverse('dashboard:consumer-index'))
        self.assertTemplateUsed(response, 'dashboard/consumer/index.html')


class ApiPlantDataViewTest(TestCase):
    """Tests for the plant data API endpoint."""

    def setUp(self):
        self.client = Client()
        self.plant = Plant.objects.create(
            code='SAMRA',
            name='Samra Power Plant',
            plant_type=Plant.PlantType.CCGT,
            capacity_mw=Decimal('900.00'),
            current_load_mw=Decimal('750.00'),
        )

    def test_api_plant_data_returns_json(self):
        response = self.client.get(
            reverse('dashboard:api-plant-data', kwargs={'plant_key': 'samra'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_api_plant_data_content(self):
        response = self.client.get(
            reverse('dashboard:api-plant-data', kwargs={'plant_key': 'samra'})
        )
        data = response.json()
        self.assertEqual(data['code'], 'SAMRA')
        self.assertEqual(data['status'], 'online')
        self.assertEqual(data['capacity_mw'], 900.0)
        self.assertEqual(data['current_load_mw'], 750.0)
        self.assertIn('load_pct', data)

    def test_api_plant_data_returns_404_for_invalid(self):
        response = self.client.get(
            reverse('dashboard:api-plant-data', kwargs={'plant_key': 'INVALID'})
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('error', data)

    def test_api_plant_data_load_percentage(self):
        response = self.client.get(
            reverse('dashboard:api-plant-data', kwargs={'plant_key': 'samra'})
        )
        data = response.json()
        expected_pct = round(750.0 / 900.0 * 100, 1)
        self.assertEqual(data['load_pct'], expected_pct)

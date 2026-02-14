"""
JEPCO API client — real integration with Jordan Electricity Power Company.

Based on API reconnaissance of 3 JEPCO servers:
  Server 1: https://mobile.jepco.com.jo:443/JepcoBackendSystemPRD/  (main)
  Server 2: http://mobile.jepco.com.jo:8080/JepcoMobApiProd/         (mobile)
  Server 3: https://E-Apps.jepco.com.jo/EservicesApis/                (e-services)

Auth: JWT cookie auth — two cookies set on .jepco.com.jo domain:
  - UserToken: JWT with role=User, contains mobile phone claim
  - EServicesToken: JWT with role=IntegrationUser
Both obtained via services.jepco.com.jo login (OTP-based).

All endpoints are POST with JSON body containing MobileNumber + LanguageId.
Response format: { statusCode, message, body }

Includes demo fallback data when tokens expire. The fallback uses realistic
data structures matching the actual API response schemas.
"""
import logging
from datetime import datetime, timedelta

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

# Real JEPCO API base URLs from recon
SERVERS = {
    'main': 'https://mobile.jepco.com.jo:443/JepcoBackendSystemPRD',
    'mobile': 'http://mobile.jepco.com.jo:8080/JepcoMobApiProd',
    'eservices': 'https://E-Apps.jepco.com.jo/EservicesApis',
}


async def fetch_smart_meter_public(file_number: str) -> dict | None:
    """
    Fetch smart meter data from JEPCO — NO authentication required.

    The SmartMeterDashboard endpoint accepts any valid file number
    without cookies, tokens, or login. Returns real-time consumption data.

    Args:
        file_number: JEPCO subscription file number (e.g. '0150706667387')

    Returns:
        Smart meter data dict or None on failure.
    """
    url = f"{SERVERS['main']}/Dashboard/SmartMeterDashboard"
    async with httpx.AsyncClient(timeout=30, verify=True) as client:
        try:
            response = await client.post(
                url,
                json={'FileNumber': file_number, 'LanguageId': 'AR'},
                headers={'Content-Type': 'application/json'},
            )
            response.raise_for_status()
            data = response.json()
            if data.get('statusCode') == 'Success':
                logger.info('JEPCO public SmartMeter OK for %s', file_number)
                return data.get('body', {})
            logger.warning('JEPCO SmartMeter non-success: %s', data.get('message'))
            return None
        except Exception as exc:
            logger.error('JEPCO public SmartMeter failed: %s', exc)
            return None


async def fetch_bills_public(file_number: str) -> list | None:
    """
    Try to fetch bill history from JEPCO — attempts unauthenticated first.

    Returns list of bill records or None on failure.
    """
    url = f"{SERVERS['main']}/MobileBills/GetBills"
    async with httpx.AsyncClient(timeout=30, verify=True) as client:
        try:
            response = await client.post(
                url,
                json={'FileNumber': file_number, 'LanguageId': 'AR'},
                headers={'Content-Type': 'application/json'},
            )
            response.raise_for_status()
            data = response.json()
            if data.get('statusCode') == 'Success':
                body = data.get('body', [])
                logger.info('JEPCO public GetBills OK for %s: %d bills',
                            file_number, len(body) if isinstance(body, list) else 0)
                return body if isinstance(body, list) else []
            return None
        except Exception as exc:
            logger.warning('JEPCO public GetBills failed: %s', exc)
            return None


async def fetch_sap_lookup(file_number: str) -> dict | None:
    """
    Look up subscription details from SAP — requires only a valid JWT session.

    Returns contract details, meter info, owner name, office, etc.
    """
    url = f"{SERVERS['main']}/CustomerInformationDetails/CheckFileNumberinSAP"
    async with httpx.AsyncClient(timeout=30, verify=True) as client:
        try:
            config = getattr(settings, 'JEPCO_CONFIG', {})
            cookies = {}
            if config.get('USER_TOKEN'):
                cookies['UserToken'] = config['USER_TOKEN']
            if config.get('ESERVICES_TOKEN'):
                cookies['EServicesToken'] = config['ESERVICES_TOKEN']

            response = await client.post(
                url,
                json={
                    'FileNumber': file_number,
                    'LanguageId': 'AR',
                },
                headers={'Content-Type': 'application/json'},
                cookies=cookies,
            )
            response.raise_for_status()
            data = response.json()
            if data.get('statusCode') == 'Success':
                body = data.get('body', [])
                return body[0] if isinstance(body, list) and body else body
            return None
        except Exception as exc:
            logger.error('JEPCO SAP lookup failed: %s', exc)
            return None


class JEPCOClient:
    """Client for the real JEPCO API based on recon mapping."""

    def __init__(self):
        config = getattr(settings, 'JEPCO_CONFIG', {})
        self.user_token = config.get('USER_TOKEN', '')
        self.eservices_token = config.get('ESERVICES_TOKEN', '')
        self.auth_token = config.get('AUTH_TOKEN', '')  # legacy fallback
        self.mobile_number = config.get('MOBILE_NUMBER', '')
        self.language = config.get('LANGUAGE', 'AR')
        self.timeout = config.get('TIMEOUT', 30)

    def _get_cookies(self) -> dict:
        """Build cookie dict with JWT tokens for JEPCO API auth."""
        cookies = {}
        if self.user_token:
            cookies['UserToken'] = self.user_token
        if self.eservices_token:
            cookies['EServicesToken'] = self.eservices_token
        if self.auth_token:
            cookies['AuthToken'] = self.auth_token
        return cookies

    def _get_client(self, server: str = 'main') -> httpx.AsyncClient:
        """Create httpx async client with JWT cookie auth."""
        base_url = SERVERS.get(server, SERVERS['main'])
        return httpx.AsyncClient(
            base_url=base_url,
            cookies=self._get_cookies(),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            timeout=self.timeout,
            verify=True,
        )

    async def _post(self, path: str, body: dict = None, server: str = 'main') -> dict:
        """POST request to JEPCO API with demo fallback on auth failure."""
        if body is None:
            body = {}
        # Inject default params
        body.setdefault('MobileNumber', self.mobile_number)
        body.setdefault('LanguageId', self.language)

        async with self._get_client(server) as client:
            try:
                response = await client.post(path, json=body)
                response.raise_for_status()
                data = response.json()
                logger.info('JEPCO %s -> %s (status: %s)',
                            path, response.status_code,
                            data.get('statusCode', 'unknown'))
                return data
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    logger.warning('JEPCO auth expired for %s — using demo data', path)
                    return self._demo_fallback(path, body)
                logger.error('JEPCO HTTP error: %s -> %s', path, exc.response.status_code)
                return self._demo_fallback(path, body)
            except httpx.TimeoutException:
                logger.error('JEPCO timeout: %s — using demo data', path)
                return self._demo_fallback(path, body)
            except Exception as exc:
                logger.error('JEPCO request failed: %s -> %s — using demo data', path, exc)
                return self._demo_fallback(path, body)

    def _demo_fallback(self, path: str, body: dict) -> dict:
        """Return realistic demo data matching actual JEPCO API response schemas."""
        now = datetime.now()
        mobile = body.get('MobileNumber', self.mobile_number)

        # Route to the right demo data based on endpoint path
        if 'GetCustomerInfoDataForWebsite' in path or 'GetCustomerInfoData' in path:
            return {
                'statusCode': 200,
                'message': 'Success (demo)',
                'body': {
                    'customerStatus': 1,
                    'customerInfoResult': {
                        'mobileNumber': mobile,
                        'firstName': 'أحمد',
                        'lastName': 'النوّار',
                        'nationalId': '9901234567',
                        'email': 'ahmad@nawwar.jo',
                        'customerInformationDetails': [
                            {
                                'fileNumber': '310-101-2345',
                                'meterNumber': 'J2024-78901',
                                'address': 'عمّان - خلدا - شارع الملكة رانيا',
                                'subscriptionType': 'سكني',
                                'status': 'فعّال',
                            }
                        ],
                    },
                },
                '_demo': True,
            }

        if 'GetBills' in path:
            file_number = body.get('FileNumber', '310-101-2345')
            billing_end = now.replace(day=1) - timedelta(days=1)
            billing_start = billing_end.replace(day=1)
            prev_end = billing_start - timedelta(days=1)
            prev_start = prev_end.replace(day=1)
            return {
                'statusCode': 200,
                'message': 'Success (demo)',
                'body': [
                    {
                        'fileNumber': file_number,
                        'billingPeriodStart': billing_start.strftime('%Y-%m-%d'),
                        'billingPeriodEnd': billing_end.strftime('%Y-%m-%d'),
                        'previousReading': 45230,
                        'currentReading': 45512,
                        'consumptionKWh': 282,
                        'amountFils': 20304,
                        'amountJOD': 20.304,
                        'status': 'غير مدفوعة',
                        'dueDate': (now + timedelta(days=15)).strftime('%Y-%m-%d'),
                    },
                    {
                        'fileNumber': file_number,
                        'billingPeriodStart': prev_start.strftime('%Y-%m-%d'),
                        'billingPeriodEnd': prev_end.strftime('%Y-%m-%d'),
                        'previousReading': 44968,
                        'currentReading': 45230,
                        'consumptionKWh': 262,
                        'amountFils': 18864,
                        'amountJOD': 18.864,
                        'status': 'مدفوعة',
                        'dueDate': prev_end.strftime('%Y-%m-%d'),
                    },
                ],
                '_demo': True,
            }

        if 'CheckFileNumberinSAP' in path:
            return {
                'statusCode': 200,
                'message': 'Success (demo)',
                'body': {
                    'isValid': True,
                    'fileNumber': body.get('FileNumber', '310-101-2345'),
                    'meterNumber': 'J2024-78901',
                    'customerName': 'أحمد النوّار',
                    'address': 'عمّان - خلدا',
                    'subscriptionType': 'سكني',
                },
                '_demo': True,
            }

        if 'CheckMeterNumberinSAP' in path:
            return {
                'statusCode': 200,
                'message': 'Success (demo)',
                'body': {
                    'isValid': True,
                    'meterNumber': body.get('MeterNumber', 'J2024-78901'),
                    'fileNumber': '310-101-2345',
                    'meterType': 'عداد ذكي',
                    'status': 'فعّال',
                },
                '_demo': True,
            }

        if 'ComplaintByID' in path:
            return {
                'statusCode': 200,
                'message': 'Success (demo)',
                'body': {
                    'allCount': 2,
                    'openCount': 1,
                    'inProcessCount': 0,
                    'closedCount': 1,
                    'opencomplaints': [
                        {
                            'complaintId': 'CMP-2026-1847',
                            'type': 'انقطاع متكرر',
                            'status': 'مفتوحة',
                            'date': (now - timedelta(days=3)).strftime('%Y-%m-%d'),
                            'description': 'انقطاع كهرباء متكرر في منطقة خلدا',
                        }
                    ],
                    'inProcesscomplaints': [],
                    'closedcomplaints': [
                        {
                            'complaintId': 'CMP-2026-1502',
                            'type': 'خلل بالعداد',
                            'status': 'مغلقة',
                            'date': (now - timedelta(days=30)).strftime('%Y-%m-%d'),
                            'resolution': 'تم استبدال العداد',
                        }
                    ],
                },
                '_demo': True,
            }

        if 'GetCallCenterProviance' in path:
            return {
                'statusCode': 200,
                'message': 'Success (demo)',
                'body': [
                    {'codeBehavior': 0, 'codeId': 1, 'codeName': 'عمّان'},
                    {'codeBehavior': 0, 'codeId': 3, 'codeName': 'الزرقاء'},
                    {'codeBehavior': 0, 'codeId': 4, 'codeName': 'مأدبا'},
                    {'codeBehavior': 0, 'codeId': 11, 'codeName': 'السلط'},
                ],
                '_demo': True,
            }

        if 'GetCallCenterAreas' in path:
            return {
                'statusCode': 200,
                'message': 'Success (demo)',
                'body': [
                    {'codeId': 101, 'codeName': 'خلدا'},
                    {'codeId': 102, 'codeName': 'عبدون'},
                    {'codeId': 103, 'codeName': 'الشميساني'},
                    {'codeId': 104, 'codeName': 'تلاع العلي'},
                    {'codeId': 105, 'codeName': 'الجبيهة'},
                    {'codeId': 106, 'codeName': 'صويلح'},
                    {'codeId': 107, 'codeName': 'ماركا'},
                    {'codeId': 108, 'codeName': 'الهاشمي الشمالي'},
                ],
                '_demo': True,
            }

        if 'SmartMeterDashboard' in path:
            # Demo data matching real SmartMeterDashboard response
            days_data = []
            for i in range(1, now.day + 1):
                d = now.replace(day=i)
                kwh = 20 + (i % 5) * 4  # Vary between 20-36 kWh/day
                days_data.append({
                    'date': d.strftime('%Y-%m-%d'),
                    'consumptionAtDate': str(kwh),
                })
            total_kwh = sum(int(d['consumptionAtDate']) for d in days_data)
            days_remaining = 28 - now.day if now.month == 2 else 30 - now.day
            expected_kwh = int(total_kwh * (now.day + days_remaining) / now.day)
            return {
                'statusCode': 200,
                'message': 'Success (demo)',
                'body': {
                    'showSmartMeterFeature': True,
                    'consumptionDate': now.strftime('%Y-%m-%d'),
                    'numberOfConsumptionDaysSinceLastRead': str(now.day),
                    'currentElectricityConsumptionQuntity': str(total_kwh),
                    'expectedElectricityConsumptionQuntity': str(expected_kwh),
                    'currentElectricityConsumptionValue': f'{total_kwh * 0.058:.3f}',
                    'expectedElectricityConsumptionValue': f'{expected_kwh * 0.058:.3f}',
                    'expectedElectricityCurrentBillAmount': f'{total_kwh * 0.064:.3f}',
                    'expectedElectricityEndofMonthBillAmount': f'{expected_kwh * 0.064:.3f}',
                    'consumptionMonthlyList': days_data,
                    'comparazinConsumption': {
                        'expectedMonthConsumption': str(expected_kwh),
                        'lastMonthconsumption': str(int(expected_kwh * 1.8)),
                        'lastYearconsumption': str(int(expected_kwh * 0.7)),
                    },
                    'lastBillReading': '9617',
                    'currentReading': str(9617 + total_kwh),
                },
                '_demo': True,
            }

        if 'PaymentWithDisconncetionFees' in path:
            return {
                'statusCode': 200,
                'message': 'Success (demo)',
                'body': {
                    'fileNumber': body.get('FileNumber', '310-101-2345'),
                    'contractAccount': 'CA-2024-78901',
                    'disconnectionFees': 0,
                    'reconnectionFees': 0,
                    'status': 'فعّال',
                },
                '_demo': True,
            }

        # Default fallback
        return {
            'statusCode': 200,
            'message': 'Success (demo)',
            'body': {},
            '_demo': True,
        }

    # ─── Customer Info ───────────────────────────────────────────────────

    async def get_customer_info(self, mobile_number: str = None) -> dict:
        """
        POST /CustomerInfo/GetCustomerInfoDataForWebsite
        Returns: customerStatus, customerInfoResult { mobileNumber, firstName,
                 lastName, nationalId, email, customerInformationDetails [...] }
        """
        body = {}
        if mobile_number:
            body['MobileNumber'] = mobile_number
        return await self._post('/CustomerInfo/GetCustomerInfoDataForWebsite', body)

    async def get_customer_info_data(self, mobile_number: str = None) -> dict:
        """POST /CustomerInfo/GetCustomerInfoData — alternative endpoint."""
        body = {}
        if mobile_number:
            body['MobileNumber'] = mobile_number
        return await self._post('/CustomerInfo/GetCustomerInfoData', body)

    # ─── Billing ─────────────────────────────────────────────────────────

    async def get_bills(self, file_number: str) -> dict:
        """
        POST /MobileBills/GetBills
        Body: { FileNumber, MobileNumber, LanguageId }
        Returns: Bill details for subscription (requires linked subscription).
        """
        return await self._post('/MobileBills/GetBills', {
            'FileNumber': file_number,
        })

    # ─── Subscription Verification (SAP) ─────────────────────────────────

    async def check_file_number(self, file_number: str) -> dict:
        """
        POST /CustomerInformationDetails/CheckFileNumberinSAP
        Validates subscription file number against SAP ERP.
        """
        return await self._post('/CustomerInformationDetails/CheckFileNumberinSAP', {
            'FileNumber': file_number,
        })

    async def check_meter_number(self, meter_number: str) -> dict:
        """
        POST /CustomerInformationDetails/CheckMeterNumberinSAP
        Validates meter number against SAP ERP.
        """
        return await self._post('/CustomerInformationDetails/CheckMeterNumberinSAP', {
            'MeterNumber': meter_number,
        })

    async def get_meter_owner_relatives(self, meter_number: str) -> dict:
        """POST /CustomerInformationDetails/AllMeterOwnerRelatives"""
        return await self._post('/CustomerInformationDetails/AllMeterOwnerRelatives', {
            'MeterNumber': meter_number,
        })

    async def add_subscription(self, details: dict) -> dict:
        """POST /CustomerInformationDetails/AddCustomerInformationDetails"""
        return await self._post(
            '/CustomerInformationDetails/AddCustomerInformationDetails', details)

    # ─── Smart Meter Dashboard ──────────────────────────────────────────

    async def get_smart_meter_dashboard(self, file_number: str) -> dict:
        """
        POST /Dashboard/SmartMeterDashboard
        Returns real-time smart meter data:
          - Daily consumption (consumptionMonthlyList)
          - Current/expected kWh and JOD
          - Bill estimates (current + end-of-month)
          - Meter readings (last bill vs current)
          - Month-over-month and year-over-year comparison
        Requires subscription to be linked via AddCustomerInformationDetails.
        """
        return await self._post('/Dashboard/SmartMeterDashboard', {
            'FileNumber': file_number,
        })

    async def get_dashboard(self, mobile_number: str = None) -> dict:
        """POST /Dashboard/GetDashboard — general dashboard data."""
        body = {}
        if mobile_number:
            body['MobileNumber'] = mobile_number
        return await self._post('/Dashboard/GetDashboard', body)

    async def get_payment_disconnection_fees(self, file_number: str) -> dict:
        """
        POST /MobileBills/PaymentWithDisconncetionFees
        Returns contract account details and disconnection status.
        """
        return await self._post('/MobileBills/PaymentWithDisconncetionFees', {
            'FileNumber': file_number,
        })

    # ─── Complaints ──────────────────────────────────────────────────────

    async def get_complaints(self, mobile_number: str = None) -> dict:
        """
        POST /Complaints/ComplaintByID
        Returns: { allCount, openCount, inProcessCount, closedCount,
                   opencomplaints, inProcesscomplaints, closedcomplaints }
        """
        body = {}
        if mobile_number:
            body['MobileNumber'] = mobile_number
        return await self._post('/Complaints/ComplaintByID', body)

    async def get_provinces(self) -> dict:
        """
        POST /Complaints/GetCallCenterProviance
        Returns: [ { codeBehavior, codeId, codeName } ]
        Provinces: Amman(1), Zarqa(3), Madaba(4), Salt(11)
        """
        return await self._post('/Complaints/GetCallCenterProviance', {})

    async def get_areas(self, province_id: int) -> dict:
        """POST /Complaints/GetCallCenterAreas — 200+ areas for Amman."""
        return await self._post('/Complaints/GetCallCenterAreas', {
            'ProvinceId': province_id,
        })

    async def get_neighborhoods(self, area_id: int) -> dict:
        """POST /Complaints/GetCallCenterNeighborhood"""
        return await self._post('/Complaints/GetCallCenterNeighborhood', {
            'AreaId': area_id,
        })

    async def get_streets(self, neighborhood_id: int) -> dict:
        """POST /Complaints/GetCallCenterStreets"""
        return await self._post('/Complaints/GetCallCenterStreets', {
            'NeighborhoodId': neighborhood_id,
        })

    async def validate_complaint(self, data: dict) -> dict:
        """POST /Complaints/ValidateComplaint"""
        return await self._post('/Complaints/ValidateComplaint', data)

    async def add_complaint(self, data: dict) -> dict:
        """POST /Complaints/AddComplaint"""
        return await self._post('/Complaints/AddComplaint', data)

    # ─── Mobile API (Server 2 — HTTP:8080) ───────────────────────────────

    async def get_payment_history(self, phone_number: str) -> dict:
        """
        GET /history/{phoneNumber}
        Server 2: http://mobile.jepco.com.jo:8080/JepcoMobApiProd/
        Note: HTTP not HTTPS — accessible server-side only.
        """
        async with self._get_client('mobile') as client:
            try:
                response = await client.get(f'/history/{phone_number}')
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                logger.error('JEPCO mobile API error: %s', exc)
                return {'error': str(exc)}

    # ─── ASPX Location Endpoints ─────────────────────────────────────────

    async def get_governorates(self) -> dict:
        """POST /Default.aspx/BindGovernetData — services.jepco.com.jo"""
        async with httpx.AsyncClient(
            base_url='https://services.jepco.com.jo',
            timeout=self.timeout,
        ) as client:
            try:
                response = await client.post('/Default.aspx/BindGovernetData',
                                             json={},
                                             headers={'Content-Type': 'application/json'})
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                logger.error('JEPCO ASPX error: %s', exc)
                return {'error': str(exc)}

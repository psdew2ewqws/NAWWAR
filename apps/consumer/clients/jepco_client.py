"""
JEPCO client — fetches consumer data via automated JWT authentication.

Auth flow:
  1. POST LoginController/Login with app credentials → JWT token (9h validity)
  2. Use JWT as AuthToken cookie + Bearer header on all subsequent calls

The token is cached in-memory and auto-refreshed when expired.
"""
import logging
import time
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

_BASE = 'https://mobile.jepco.com.jo:443/JepcoBackendSystemPRD'

_LOGIN_BODY = {
    'username': 'JepcoMobileApp',
    'password': 'Mobile@jepco@123',
}

_COMMON_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Origin': 'https://services.jepco.com.jo',
    'Referer': 'https://services.jepco.com.jo/',
}

# Token cache: (token_string, expiry_timestamp)
_token_cache: dict[str, Any] = {'token': None, 'expires_at': 0}

# Token lifetime: refresh 30 min before the 9h expiry
_TOKEN_TTL = 8 * 3600 + 30 * 60  # 8h30m


def _cfg() -> dict:
    return getattr(settings, 'JEPCO_CONFIG', {})


def _client(timeout: int = 20) -> httpx.AsyncClient:
    cfg = _cfg()
    proxy = cfg.get('PROXY_URL', '')
    kwargs: dict = {'timeout': timeout, 'verify': True}
    if proxy:
        kwargs['proxy'] = proxy
    return httpx.AsyncClient(**kwargs)


# ── JWT Authentication ────────────────────────────────────────────────────────

async def _get_token(client: httpx.AsyncClient) -> str | None:
    """Get a valid JWT token, using cache if still fresh."""
    now = time.time()
    if _token_cache['token'] and now < _token_cache['expires_at']:
        return _token_cache['token']

    # Fetch fresh token
    url = f"{_BASE}/LoginController/Login"
    try:
        r = await client.post(url, json=_LOGIN_BODY, headers=_COMMON_HEADERS, timeout=15)
        if r.status_code != 200:
            logger.error('JEPCO login failed: %s %s', r.status_code, r.text[:200])
            return None

        data = r.json()
        token = None

        if isinstance(data, dict):
            token = (
                data.get('token') or data.get('Token')
                or data.get('authToken') or data.get('AuthToken')
                or data.get('access_token')
            )
            body = data.get('body', {})
            if isinstance(body, dict) and not token:
                token = (
                    body.get('token') or body.get('Token')
                    or body.get('authToken') or body.get('AuthToken')
                )
            # Check if the whole body is the token string
            if not token and isinstance(body, str) and len(body) > 20:
                token = body
        elif isinstance(data, str) and len(data) > 20:
            token = data

        # Check cookies
        if not token:
            for name in ('AuthToken', 'authToken'):
                if name in r.cookies:
                    token = r.cookies[name]
                    break

        if token:
            _token_cache['token'] = token
            _token_cache['expires_at'] = now + _TOKEN_TTL
            logger.info('JEPCO JWT obtained (expires in ~8.5h)')
            return token

        logger.error('JEPCO login: no token in response: %s', str(data)[:300])
        return None

    except Exception as exc:
        logger.error('JEPCO login error: %s', exc)
        return None


async def _authed_post(
    client: httpx.AsyncClient,
    endpoint: str,
    body: dict,
    timeout: int = 20,
) -> dict | None:
    """Make an authenticated POST call to a JEPCO endpoint."""
    token = await _get_token(client)
    url = f"{_BASE}/{endpoint}"

    headers = dict(_COMMON_HEADERS)
    cookies = {}
    if token:
        cookies['AuthToken'] = token
        headers['Authorization'] = f'Bearer {token}'

    try:
        r = await client.post(
            url, json=body, headers=headers, cookies=cookies, timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
        if data.get('statusCode') == 'Success':
            return data.get('body')
        logger.warning('JEPCO %s non-success: %s', endpoint, data.get('message', ''))
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning('JEPCO %s HTTP %s: %s', endpoint, exc.response.status_code,
                        exc.response.text[:200])
        return None
    except Exception as exc:
        logger.warning('JEPCO %s failed: %s', endpoint, exc)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

async def fetch_smart_meter(file_number: str) -> dict | None:
    """Fetch real-time smart meter dashboard data (daily consumption, projections)."""
    async with _client() as client:
        data = await _authed_post(
            client,
            'Dashboard/SmartMeterDashboard',
            {'FileNumber': file_number, 'LanguageId': 'AR'},
        )
        if data:
            logger.info('Smart meter OK for %s', file_number)
        return data


async def fetch_bills(file_number: str) -> dict | None:
    """Fetch billing history with full bill details and meter readings."""
    async with _client() as client:
        return await _authed_post(
            client,
            'MobileBills/GetBills',
            {'FileNumber': file_number, 'LanguageId': 'AR', 'MobileNumber': ''},
        )


async def fetch_sap_info(file_number: str) -> dict | None:
    """Validate file number in SAP — returns subscriber name, meter, tariff, office."""
    async with _client() as client:
        data = await _authed_post(
            client,
            'CustomerInformationDetails/CheckFileNumberinSAP',
            {'FileNumber': file_number, 'LanguageId': 'AR', 'MobileNumber': ''},
        )
        # Returns a list; take first entry
        if isinstance(data, list) and data:
            return data[0]
        return data


async def fetch_account_statement(file_number: str) -> dict | None:
    """Fetch account statement with payment history."""
    async with _client() as client:
        return await _authed_post(
            client,
            'MobileBills/AccountStatement',
            {'FileNumber': file_number, 'LanguageId': 'AR', 'MobileNumber': ''},
        )


async def fetch_consumption_comparison(file_number: str) -> dict | None:
    """Compare current month vs last month vs same month last year."""
    async with _client() as client:
        return await _authed_post(
            client,
            'Dashboard/ComparazinConsumption',
            {'FileNumber': file_number, 'LanguageId': 'AR'},
        )


async def fetch_subsidy_simulation(file_number: str) -> list | None:
    """Get subsidy simulation data — old tariff vs new tariff comparison."""
    async with _client() as client:
        data = await _authed_post(
            client,
            'SimulateConsumptionCalculation/GetSimulateConsumptionCalculationByFileNumber',
            {'FileNumber': file_number, 'LanguageId': 'AR'},
        )
        return data if isinstance(data, list) else None


async def fetch_bill_header(file_number: str) -> dict | None:
    """Fetch bill header info (subscription, meter, readings, next read date)."""
    async with _client() as client:
        data = await _authed_post(
            client,
            'CalculateBills/GetHeaderBills',
            {'FileNumber': file_number, 'LanguageId': 'AR'},
        )
        if isinstance(data, dict):
            return data.get('billsHeader', data)
        return data


async def fetch_all_data(file_number: str) -> dict:
    """
    Fetch ALL available data for a file number in parallel.

    Returns a dict with keys: smart_meter, sap_info, bills, account_statement,
    consumption_comparison, subsidy_simulation, bill_header.
    """
    import asyncio

    async with _client() as client:
        # Ensure token is ready before parallel calls
        await _get_token(client)

        results = await asyncio.gather(
            _authed_post(client, 'Dashboard/SmartMeterDashboard',
                         {'FileNumber': file_number, 'LanguageId': 'AR'}),
            _authed_post(client, 'CustomerInformationDetails/CheckFileNumberinSAP',
                         {'FileNumber': file_number, 'LanguageId': 'AR', 'MobileNumber': ''}),
            _authed_post(client, 'MobileBills/GetBills',
                         {'FileNumber': file_number, 'LanguageId': 'AR', 'MobileNumber': ''}),
            _authed_post(client, 'MobileBills/AccountStatement',
                         {'FileNumber': file_number, 'LanguageId': 'AR', 'MobileNumber': ''}),
            _authed_post(client, 'Dashboard/ComparazinConsumption',
                         {'FileNumber': file_number, 'LanguageId': 'AR'}),
            _authed_post(client, 'SimulateConsumptionCalculation/GetSimulateConsumptionCalculationByFileNumber',
                         {'FileNumber': file_number, 'LanguageId': 'AR'}),
            _authed_post(client, 'CalculateBills/GetHeaderBills',
                         {'FileNumber': file_number, 'LanguageId': 'AR'}),
            return_exceptions=True,
        )

    keys = [
        'smart_meter', 'sap_info', 'bills', 'account_statement',
        'consumption_comparison', 'subsidy_simulation', 'bill_header',
    ]

    data = {}
    for key, result in zip(keys, results):
        if isinstance(result, Exception):
            logger.warning('JEPCO %s error: %s', key, result)
            data[key] = None
        else:
            data[key] = result

    # Normalize sap_info (returns list)
    sap = data.get('sap_info')
    if isinstance(sap, list) and sap:
        data['sap_info'] = sap[0]

    # Normalize bill_header
    bh = data.get('bill_header')
    if isinstance(bh, dict) and 'billsHeader' in bh:
        data['bill_header'] = bh['billsHeader']

    logger.info('JEPCO fetch_all_data for %s: %d/%d succeeded',
                file_number,
                sum(1 for v in data.values() if v),
                len(data))
    return data

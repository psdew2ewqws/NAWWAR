"""
JEPCO client — fetches consumer smart meter data for AI analysis.
"""
import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

_BASE = getattr(settings, 'JEPCO_CONFIG', {}).get(
    'BASE_URL', 'https://mobile.jepco.com.jo:443/JepcoBackendSystemPRD',
)


def _client(timeout: int = 20) -> httpx.AsyncClient:
    proxy = getattr(settings, 'JEPCO_CONFIG', {}).get('PROXY_URL', '')
    if proxy:
        return httpx.AsyncClient(timeout=timeout, proxy=proxy)
    return httpx.AsyncClient(timeout=timeout, verify=True)


async def fetch_smart_meter(file_number: str) -> dict | None:
    """Fetch smart meter consumption data for a given file number."""
    body = {'FileNumber': file_number, 'LanguageId': 'AR'}
    url = f"{_BASE}/Dashboard/SmartMeterDashboard"

    async with _client(timeout=20) as client:
        try:
            response = await client.post(
                url, json=body,
                headers={'Content-Type': 'application/json'},
            )
            response.raise_for_status()
            data = response.json()
            if data.get('statusCode') == 'Success':
                logger.info('Smart meter fetch OK for %s', file_number)
                return data.get('body', {})
            logger.warning('Smart meter non-success: %s', data.get('message'))
            return None
        except Exception as exc:
            logger.warning('Smart meter fetch failed: %s', exc)
            return None

"""
WhatsApp client for 4whats.net API.
"""
import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """
    Client for the 4whats.net WhatsApp API.

    All endpoints use GET requests with query-string authentication.
    """

    def __init__(self):
        config = settings.WHATSAPP_CONFIG
        self.api_url = config['API_URL']
        self.auth_params = {
            'instanceid': config['INSTANCE_ID'],
            'token': config['TOKEN'],
        }

    async def send_text(self, to: str, body: str) -> dict:
        """Send a text message."""
        params = {**self.auth_params, 'phone': to, 'body': body}
        return await self._request('/sendMessage', params)

    async def send_image(self, to: str, image_url: str, caption: str = '') -> dict:
        """Send an image/file message."""
        params = {
            **self.auth_params,
            'phone': to,
            'body': image_url,
            'filename': 'image.jpg',
            'caption': caption,
        }
        return await self._request('/sendFile', params)

    async def send_audio(self, to: str, audio_url: str) -> dict:
        """Send a voice note (PTT)."""
        params = {**self.auth_params, 'phone': to, 'body': audio_url}
        return await self._request('/sendPTT', params)

    async def download_media(self, media_url: str) -> bytes:
        """
        Download media from a direct URL.

        4whats provides direct URLs for media (no media-ID lookup needed).
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(media_url, timeout=30)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as e:
            logger.error("Failed to download media from %s: %s", media_url, e)
            raise

    async def set_webhook(self, url: str) -> dict:
        """Register a webhook URL with 4whats."""
        params = {**self.auth_params, 'webhookUrl': url}
        return await self._request('/webhook', params)

    async def get_status(self) -> dict:
        """Check instance status."""
        return await self._request('/status', self.auth_params)

    async def _request(self, endpoint: str, params: dict) -> dict:
        """Make a GET request to the 4whats API."""
        url = f"{self.api_url}{endpoint}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=30)
                response.raise_for_status()
                result = response.json()
                logger.info("4whats %s → %s", endpoint, response.status_code)
                return result
        except httpx.HTTPError as e:
            logger.error("4whats API error on %s: %s", endpoint, e)
            raise

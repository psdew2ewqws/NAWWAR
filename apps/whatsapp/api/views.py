"""
WhatsApp webhook view for 4whats.net.

Receives incoming messages POSTed by 4whats.net and routes them
through the MessageRouter for AI processing.
"""
import asyncio
import hashlib
import hmac
import json
import logging
import threading

from django.conf import settings
from django.core.cache import cache

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from apps.consumer.models import Message as MessageModel
from apps.consumer.selectors import conversation_get_active
from apps.consumer.services import conversation_create, message_create
from apps.core.utils import sanitise_text, mask_phone
from apps.whatsapp.clients.whatsapp_client import WhatsAppClient
from apps.whatsapp.services.message_router import MessageRouter

from django.http import JsonResponse as DjangoJsonResponse

logger = logging.getLogger(__name__)


def webhook_debug(request):
    """Debug view: shows last 5 webhook payloads received + recent sessions."""
    payloads = cache.get('wa_debug_payloads', [])
    # Also pull recent sessions from DB as fallback (cache may not be shared)
    from apps.consumer.models import ConversationSession, Message as Msg
    recent_sessions = []
    for s in ConversationSession.objects.filter(platform='whatsapp').order_by('-created_at')[:5]:
        msgs = list(Msg.objects.filter(session=s).order_by('-created_at')[:3].values('role', 'content', 'created_at'))
        recent_sessions.append({
            'phone': s.phone_number,
            'created': str(s.created_at),
            'messages': [{'role': m['role'], 'content': m['content'][:100], 'at': str(m['created_at'])} for m in msgs],
        })
    return DjangoJsonResponse({
        'payloads_captured': len(payloads),
        'payloads': payloads,
        'recent_whatsapp_sessions': recent_sessions,
    })

# Per-phone rate limit: max messages per minute
PHONE_RATE_LIMIT = 20
PHONE_RATE_WINDOW = 60  # seconds


def _run_async_in_thread(coro):
    """Run an async coroutine in a daemon thread with its own event loop.

    This is necessary because Gunicorn/WSGI doesn't have a running
    asyncio event loop, so asyncio.ensure_future() would fail.
    """
    def _target():
        asyncio.run(coro)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()


class WhatsAppWebhookView(APIView):
    """
    4whats.net webhook endpoint.

    POST — Incoming messages forwarded by 4whats.net.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'whatsapp_webhook'

    def post(self, request):
        """
        Process incoming 4whats.net webhook payload.

        Validates HMAC signature (if secret configured), normalizes
        the payload, and dispatches async processing.
        """
        # Kill switch: disable all webhook processing
        if not getattr(settings, 'WHATSAPP_ENABLED', False):
            return Response({'status': 'disabled'}, status=status.HTTP_200_OK)

        # HMAC signature verification
        webhook_secret = getattr(settings, 'WHATSAPP_WEBHOOK_SECRET', '')
        if webhook_secret:
            signature = request.headers.get('X-Signature', '')
            if not signature:
                logger.warning(
                    "Webhook rejected: missing X-Signature from %s",
                    request.META.get('REMOTE_ADDR', '?'),
                )
                return Response(
                    {'error': 'Missing signature'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            expected = hmac.new(
                webhook_secret.encode(),
                request.body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                logger.warning(
                    "Webhook rejected: invalid signature from %s",
                    request.META.get('REMOTE_ADDR', '?'),
                )
                return Response(
                    {'error': 'Invalid signature'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        body = request.data

        # Store raw payload for debugging (last 5 payloads)
        try:
            raw_json = json.dumps(body, ensure_ascii=False, default=str)
            debug_payloads = cache.get('wa_debug_payloads', [])
            debug_payloads.append(raw_json[:2000])  # Truncate large payloads
            cache.set('wa_debug_payloads', debug_payloads[-5:], 3600)  # Keep 1 hour
        except Exception:
            pass

        logger.info(
            "4whats webhook: type=%s, keys=%s, raw=%s",
            body.get('type', '?'),
            ','.join(body.keys()) if isinstance(body, dict) else '?',
            json.dumps(body, ensure_ascii=False, default=str)[:500],
        )

        try:
            # 4whats sends message data — extract key fields
            # Common 4whats payload fields:
            #   body/message, from/phone/sender/chatId, type/messageType, media/file
            message_data = self._normalize_payload(body)

            if message_data:
                sender = message_data.get('from', '')
                msg_type = message_data.get('type', 'text')
                logger.info(
                    "Received message from %s: type=%s",
                    mask_phone(sender), msg_type,
                )

                # Per-phone rate limit
                phone_key = f'wa_rate:{sender}'
                phone_count = cache.get(phone_key, 0)
                if phone_count >= PHONE_RATE_LIMIT:
                    logger.warning(
                        "Phone rate limit exceeded for %s (%d/%d)",
                        mask_phone(sender), phone_count, PHONE_RATE_LIMIT,
                    )
                    return Response({'status': 'rate_limited'}, status=status.HTTP_200_OK)
                cache.set(phone_key, phone_count + 1, PHONE_RATE_WINDOW)

                # Run async processing in a background thread with its
                # own event loop.  asyncio.ensure_future() requires a
                # running loop, which doesn't exist under Gunicorn/WSGI.
                _run_async_in_thread(
                    self._process_message(
                        message=message_data,
                        sender=sender,
                    )
                )

        except Exception as e:
            logger.error("Error processing 4whats webhook: %s", e, exc_info=True)

        return Response({'status': 'ok'}, status=status.HTTP_200_OK)

    def _normalize_payload(self, body: dict) -> dict | None:
        """
        Normalize a 4whats.net webhook payload into the format
        expected by MessageRouter.

        4whats payloads can arrive in several shapes:
        1. Flat: {from, body, type, ...}
        2. Nested under 'data': {instanceId, data: {from, body, type, ...}}
        3. Nested under 'messages': {instanceId, messages: [{from, body, ...}]}
        4. ACK/status: {instanceId, ack: [...]}

        Returns None for status updates or unrecognizable payloads.
        """
        # Skip delivery receipts / ack payloads
        if 'ack' in body and 'from' not in body and 'body' not in body:
            logger.debug("Skipping ack/delivery receipt payload")
            return None
        if body.get('event') in ('ack', 'seen', 'delivered', 'read'):
            logger.debug("Skipping status event: %s", body.get('event'))
            return None

        # --- Unwrap nested payloads ---
        # 4whats may nest message data under 'data' or 'messages'
        msg = body
        if 'data' in body and isinstance(body['data'], dict):
            msg = body['data']
            logger.info("Unwrapped 'data' key from payload")
        elif 'messages' in body and isinstance(body['messages'], list) and body['messages']:
            msg = body['messages'][0]
            logger.info("Unwrapped 'messages[0]' from payload")

        # Skip outgoing messages (fromMe)
        if msg.get('fromMe') is True:
            logger.debug("Skipping outgoing message (fromMe=true)")
            return None

        # Skip group messages — only respond to direct/private chats
        chat_id = msg.get('chatId', '') or msg.get('from', '') or ''
        if '@g.us' in str(chat_id):
            logger.debug("Skipping group message from %s", chat_id)
            return None

        # Extract sender phone — try common field names
        sender = (
            msg.get('from')
            or msg.get('phone')
            or msg.get('sender')
            or msg.get('chatId', '')
            or msg.get('author', '')
        )
        # Clean phone: remove @c.us suffix and non-digit chars
        if isinstance(sender, str):
            sender = sender.replace('@c.us', '').replace('@s.whatsapp.net', '')

        if not sender:
            logger.warning("No sender found in 4whats payload: keys=%s",
                           list(msg.keys())[:10])
            return None

        # Determine message type
        # 4whats uses 'chat' for text messages, normalize it
        msg_type = (
            msg.get('type')
            or msg.get('messageType')
            or 'text'
        ).lower()
        if msg_type == 'chat':
            msg_type = 'text'

        # Normalize into MessageRouter format
        if msg_type in ('image', 'photo'):
            media_url = (
                msg.get('media')
                or msg.get('file')
                or msg.get('image')
                or msg.get('body')
                or ''
            )
            caption = msg.get('caption', '')
            mime_type = msg.get('mimetype') or msg.get('mime_type') or 'image/jpeg'
            return {
                'type': 'image',
                'from': sender,
                'image': {
                    'id': media_url,
                    'mime_type': mime_type,
                    'caption': caption,
                },
            }

        elif msg_type in ('audio', 'voice', 'ptt'):
            media_url = (
                msg.get('media')
                or msg.get('file')
                or msg.get('audio')
                or msg.get('body')
                or ''
            )
            return {
                'type': 'audio',
                'from': sender,
                'audio': {
                    'id': media_url,
                },
            }

        elif msg_type == 'location':
            lat = msg.get('lat') or msg.get('latitude') or 0
            lng = msg.get('lng') or msg.get('longitude') or 0
            return {
                'type': 'location',
                'from': sender,
                'location': {
                    'latitude': float(lat),
                    'longitude': float(lng),
                },
            }

        else:
            # Default: treat as text
            text = (
                msg.get('body')
                or msg.get('message')
                or msg.get('text')
                or ''
            )
            if not text:
                logger.warning("Empty text message from %s, keys=%s",
                               mask_phone(sender), list(msg.keys())[:10])
                return None

            return {
                'type': 'text',
                'from': sender,
                'text': {'body': text},
            }

    @staticmethod
    async def _process_message(*, message: dict, sender: str):
        """
        Process a single message asynchronously.

        1. Get or create a ConversationSession for the sender
        2. Save the incoming user message
        3. Route through MessageRouter for AI processing
        4. Save the assistant response
        5. On first contact, send a welcome message with a web dashboard link
        6. Send the reply back via WhatsApp
        """
        router = MessageRouter()
        client = WhatsAppClient()

        try:
            # --- Session tracking ---
            session = await asyncio.to_thread(
                conversation_get_active, phone_number=sender,
            )
            is_new_session = session is None
            if is_new_session:
                session = await asyncio.to_thread(
                    conversation_create,
                    phone_number=sender,
                    platform='whatsapp',
                )
                logger.info("Created new session %s for %s", session.session_key, mask_phone(sender))

            # Determine message type for the DB record
            msg_type = message.get('type', 'text')
            MESSAGE_TYPE_MAP = {
                'text': MessageModel.MessageType.TEXT,
                'location': MessageModel.MessageType.TEXT,
                'image': MessageModel.MessageType.IMAGE,
                'audio': MessageModel.MessageType.VOICE,
            }
            db_message_type = MESSAGE_TYPE_MAP.get(msg_type, MessageModel.MessageType.TEXT)

            # Extract user-facing content for the DB record
            if msg_type == 'text':
                user_content = message.get('text', {}).get('body', '')
            elif msg_type == 'image':
                user_content = message.get('image', {}).get('caption', '') or '[image]'
            elif msg_type == 'audio':
                user_content = '[audio]'
            elif msg_type == 'location':
                loc = message.get('location', {})
                user_content = f"[location: {loc.get('latitude')}, {loc.get('longitude')}]"
            else:
                user_content = str(message)

            # Sanitise before storage
            user_content = sanitise_text(user_content)

            # Save incoming user message
            await asyncio.to_thread(
                message_create,
                session=session,
                role='user',
                content=user_content,
                message_type=db_message_type,
            )

            # --- AI processing (unchanged) ---
            result = await router.route_message(message)
            response_type = result.get('response_type', 'text')
            content = result.get('content', '')

            # Sanitise AI output before storage and sending
            content = sanitise_text(content)

            # Save assistant response
            if content:
                await asyncio.to_thread(
                    message_create,
                    session=session,
                    role='assistant',
                    content=content,
                    message_type=MessageModel.MessageType.TEXT,
                )

            # --- Send reply ---
            if response_type == 'audio' and result.get('audio_url'):
                await client.send_audio(to=sender, audio_url=result['audio_url'])
                if content:
                    await client.send_text(to=sender, body=content)
            elif response_type == 'image' and result.get('image_url'):
                await client.send_image(
                    to=sender,
                    image_url=result['image_url'],
                    caption=content,
                )
            else:
                if content:
                    await client.send_text(to=sender, body=content)

            # --- Welcome message on first contact ---
            if is_new_session and settings.SITE_URL:
                chat_url = f"{settings.SITE_URL.rstrip('/')}/nawwar/consumer/chat/{session.session_key}/"
                welcome = (
                    f"لمشاهدة التحليل الكامل ومتابعة المحادثة عبر الويب:\n{chat_url}"
                )
                await client.send_text(to=sender, body=welcome)

            logger.info(
                "Response sent to %s: type=%s, length=%d",
                mask_phone(sender), response_type, len(content),
            )

        except Exception as e:
            logger.error(
                "Failed to process message from %s: %s", mask_phone(sender), e, exc_info=True,
            )
            try:
                await client.send_text(
                    to=sender,
                    body="عذراً، حدث خطأ أثناء معالجة رسالتك. يرجى المحاولة مرة أخرى.",
                )
            except Exception:
                logger.error("Failed to send error message to %s", mask_phone(sender))

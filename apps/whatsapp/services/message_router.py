"""
WhatsApp message router — classifies intent and dispatches to AI services.

Routes incoming WhatsApp messages to the appropriate handler based on
message type (text, image, audio, location) and detected intent.

All message types are context-aware: the router loads the conversation
session (by phone number) and passes file_number + session_context to
LLMService, ensuring continuity across text, voice, and image messages.
"""
import logging

from asgiref.sync import sync_to_async

from apps.ai_engine.services.llm_service import LLMService
from apps.ai_engine.services.voice_service import VoiceService
from apps.consumer.models.conversation import ConversationSession, Message
from apps.whatsapp.clients.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


class MessageRouter:
    """
    Routes incoming WhatsApp messages to the appropriate service handler
    based on message type and detected intent.

    All handlers load session context (file_number, appliances, etc.) from
    the ConversationSession so the AI remembers previous conversation turns.
    """

    def __init__(self):
        self.llm = LLMService()
        self.voice = VoiceService()
        self.wa_client = WhatsAppClient()

    async def _get_session(self, phone: str) -> ConversationSession | None:
        """Load or create a WhatsApp conversation session."""
        if not phone:
            return None
        session = await sync_to_async(
            ConversationSession.objects.filter(
                phone_number=phone, platform='whatsapp', is_active=True,
            ).first
        )()
        if not session:
            session = await sync_to_async(ConversationSession.objects.create)(
                phone_number=phone, platform='whatsapp',
            )
        return session

    async def _save_and_update_ctx(
        self, session, user_content: str, result: dict,
        msg_type: str = 'text',
    ):
        """Save user + assistant messages and persist context updates."""
        if not session:
            return
        await sync_to_async(Message.objects.create)(
            session=session, role='user', content=user_content,
            message_type=msg_type,
        )
        await sync_to_async(Message.objects.create)(
            session=session, role='assistant',
            content=result.get('response_text', ''),
            processing_time_ms=result.get('metadata', {}).get('processing_ms', 0),
        )
        # Persist file_number, appliances, projected_kwh in session context
        meta = result.get('metadata', {})
        ctx = session.context or {}
        changed = False
        for key in ('file_number', 'appliances', 'expected_kwh', 'projected_kwh'):
            if meta.get(key):
                ctx[key] = meta[key]
                changed = True
        if meta.get('awaiting'):
            ctx['awaiting'] = meta['awaiting']
            changed = True
        elif 'awaiting' in ctx:
            ctx.pop('awaiting')
            changed = True
        if changed:
            session.context = ctx
            await sync_to_async(session.save)(update_fields=['context'])

    async def route_message(self, message_data: dict) -> dict:
        """
        Route an incoming message to the appropriate handler.

        Args:
            message_data: Parsed WhatsApp message dict containing at least
                          'type', 'from', and the type-specific payload.

        Returns:
            Dict with 'response_type' (text/audio/image) and 'content'.
        """
        msg_type = message_data.get('type', 'text')
        sender = message_data.get('from', 'unknown')

        logger.info("Routing message from %s, type=%s", sender, msg_type)

        if msg_type == 'image':
            return await self._handle_image(message_data)
        elif msg_type == 'audio':
            return await self._handle_audio(message_data)
        elif msg_type == 'location':
            return await self._handle_location(message_data)
        else:
            return await self._handle_text(message_data)

    async def _handle_text(self, message_data: dict) -> dict:
        """Route text through LLMService with full session context."""
        text = message_data.get('text', {}).get('body', '')
        phone = message_data.get('from', '')

        session = await self._get_session(phone)
        ctx = (session.context or {}) if session else {}
        file_number = ctx.get('file_number')

        result = await self.llm.route_request(
            message_type='text',
            content=text,
            file_number=file_number,
            session_context=ctx,
        )

        await self._save_and_update_ctx(session, text, result)

        return {
            'response_type': 'text',
            'content': result.get('response_text', ''),
        }

    async def _handle_image(self, message_data: dict) -> dict:
        """Route image through LLMService bill scan with session context."""
        image_info = message_data.get('image', {})
        media_id = image_info.get('id', '')
        phone = message_data.get('from', '')

        if not media_id:
            return {
                'response_type': 'text',
                'content': 'لم يتم استلام الصورة بشكل صحيح. يرجى إعادة إرسالها.',
            }

        try:
            image_data = await self.wa_client.download_media(media_id)

            session = await self._get_session(phone)
            ctx = (session.context or {}) if session else {}
            file_number = ctx.get('file_number')

            # Route through LLMService (extracts file number + fetches JEPCO)
            result = await self.llm.route_request(
                message_type='image',
                content=image_data,
                file_number=file_number,
                session_context=ctx,
            )

            await self._save_and_update_ctx(
                session, '[صورة فاتورة]', result, msg_type='image',
            )

            return {
                'response_type': 'text',
                'content': result.get('response_text', ''),
            }

        except Exception as e:
            logger.error("Bill scanning failed: %s", e, exc_info=True)
            return {
                'response_type': 'text',
                'content': 'عذراً، لم نتمكن من تحليل صورة الفاتورة. تأكد من وضوح الصورة وأعد المحاولة.',
            }

    async def _handle_audio(self, message_data: dict) -> dict:
        """Route audio through transcription then LLMService with context."""
        audio_info = message_data.get('audio', {})
        media_id = audio_info.get('id', '')
        phone = message_data.get('from', '')

        if not media_id:
            return {
                'response_type': 'text',
                'content': 'لم يتم استلام الرسالة الصوتية بشكل صحيح. يرجى إعادة إرسالها.',
            }

        try:
            audio_data = await self.wa_client.download_media(media_id)

            session = await self._get_session(phone)
            ctx = (session.context or {}) if session else {}
            file_number = ctx.get('file_number')

            # Route through LLMService audio handler (transcribe → text pipeline)
            # WhatsApp voice notes are OGG/opus format
            result = await self.llm.route_request(
                message_type='audio',
                content=audio_data,
                file_number=file_number,
                session_context=ctx,
                audio_filename='voice_note.ogg',
            )

            transcript = result.get('metadata', {}).get('transcript', '')
            response_text = result.get('response_text', '')

            await self._save_and_update_ctx(
                session, transcript or '[رسالة صوتية]', result, msg_type='voice',
            )

            # Prepend transcript so user sees what was understood
            content = f"فهمت: \"{transcript}\"\n\n{response_text}" if transcript else response_text

            return {
                'response_type': 'text',
                'content': content,
            }

        except Exception as e:
            logger.error("Voice processing failed: %s", e, exc_info=True)
            return {
                'response_type': 'text',
                'content': 'عذراً، لم نتمكن من معالجة الرسالة الصوتية. يرجى إرسال رسالة نصية.',
            }

    async def _handle_location(self, message_data: dict) -> dict:
        """Handle location messages — suggest nearest JEPCO office."""
        location = message_data.get('location', {})
        lat = location.get('latitude', 0)
        lng = location.get('longitude', 0)

        logger.info("Location received: lat=%s, lng=%s", lat, lng)

        return {
            'response_type': 'text',
            'content': (
                'شكراً لمشاركة موقعك. يمكنك زيارة أقرب فرع لشركة الكهرباء.\n\n'
                'للاستفسارات العاجلة:\n'
                'هاتف الطوارئ: 1111\n'
                'خدمة العملاء: 06-5300-666'
            ),
        }

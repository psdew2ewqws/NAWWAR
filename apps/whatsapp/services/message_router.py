"""
WhatsApp message router — classifies intent and dispatches to AI services.

Routes incoming WhatsApp messages to the appropriate handler based on
message type (text, image, audio, location) and detected intent.

Text messages are routed through LLMService (same as web chat) which
provides live JEPCO data lookup, file number detection, and multi-model
analysis — not just RAG knowledge base Q&A.
"""
import logging

from apps.ai_engine.services.llm_service import LLMService
from apps.ai_engine.services.voice_service import VoiceService
from apps.ai_engine.services import vision_service
from apps.whatsapp.clients.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


class MessageRouter:
    """
    Routes incoming WhatsApp messages to the appropriate service handler
    based on message type and detected intent.

    Message types handled:
    - text: LLMService (file number detection, JEPCO live data, RAG).
    - image: Route to VisionService for bill scanning.
    - audio: Route to VoiceService for transcription, then re-route the text.
    - location: Acknowledge and suggest nearest JEPCO office.
    """

    def __init__(self):
        self.llm = LLMService()
        self.voice = VoiceService()
        self.wa_client = WhatsAppClient()

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
        """
        Route text through LLMService — same pipeline as the web chat.

        LLMService handles:
        - File number detection (13-digit JEPCO numbers)
        - Live JEPCO smart meter data lookup
        - Multi-model analysis (GPT-4o + Claude)
        - CrewAI for complex queries
        - RAG for general knowledge Q&A
        """
        text = message_data.get('text', {}).get('body', '')

        logger.info("Routing text to LLMService: %s", text[:80])

        result = await self.llm.route_request(
            message_type='text',
            content=text,
        )

        return {
            'response_type': 'text',
            'content': result.get('response_text', ''),
        }

    async def _handle_image(self, message_data: dict) -> dict:
        """
        Route image messages to the bill scanning pipeline.

        Downloads the image from WhatsApp, passes to VisionService,
        and returns the structured analysis.
        """
        image_info = message_data.get('image', {})
        media_id = image_info.get('id', '')

        if not media_id:
            return {
                'response_type': 'text',
                'content': 'لم يتم استلام الصورة بشكل صحيح. يرجى إعادة إرسالها.',
            }

        try:
            # Download image from WhatsApp
            image_data = await self.wa_client.download_media(media_id)

            # Scan the bill image
            mime_type = image_info.get('mime_type', 'image/jpeg')
            scan_result = await vision_service.scan_bill(
                image_data=image_data,
                mime_type=mime_type,
            )

            # Build a user-friendly Arabic response
            parts = ["تم تحليل الفاتورة بنجاح ✅\n"]

            if scan_result.get('subscriber_number'):
                parts.append(f"رقم الاشتراك: {scan_result['subscriber_number']}")
            if scan_result.get('billing_period_start') and scan_result.get('billing_period_end'):
                parts.append(
                    f"فترة الفاتورة: {scan_result['billing_period_start']} - {scan_result['billing_period_end']}"
                )
            if scan_result.get('total_kwh'):
                parts.append(f"الاستهلاك: {scan_result['total_kwh']} ك.و.س")
            if scan_result.get('total_amount_fils'):
                jod = scan_result['total_amount_fils'] / 1000
                parts.append(f"المبلغ الإجمالي: {jod:.3f} دينار")
            if scan_result.get('previous_reading') and scan_result.get('current_reading'):
                parts.append(
                    f"القراءة: {scan_result['previous_reading']} → {scan_result['current_reading']}"
                )

            # Add line items if available
            line_items = scan_result.get('line_items', [])
            if line_items:
                parts.append("\nتفاصيل الشرائح:")
                for item in line_items:
                    parts.append(f"  {item.get('description_ar', item.get('description', ''))}")

            return {
                'response_type': 'text',
                'content': '\n'.join(parts),
            }

        except Exception as e:
            logger.error("Bill scanning failed: %s", e, exc_info=True)
            return {
                'response_type': 'text',
                'content': 'عذراً، لم نتمكن من تحليل صورة الفاتورة. تأكد من وضوح الصورة وأعد المحاولة.',
            }

    async def _handle_audio(self, message_data: dict) -> dict:
        """
        Route audio messages through the full voice pipeline.

        Downloads audio from WhatsApp -> Whisper transcription ->
        intent classification -> RAG answer -> TTS synthesis.
        """
        audio_info = message_data.get('audio', {})
        media_id = audio_info.get('id', '')

        if not media_id:
            return {
                'response_type': 'text',
                'content': 'لم يتم استلام الرسالة الصوتية بشكل صحيح. يرجى إعادة إرسالها.',
            }

        try:
            # Download audio from WhatsApp
            audio_data = await self.wa_client.download_media(media_id)

            # Run the full voice pipeline: transcribe -> classify -> answer -> synthesize
            result = await self.voice.process_voice_message(audio_data=audio_data)

            transcript = result.get('transcript', '')
            response_text = result.get('response_text', '')

            # Prepend the transcript so the user sees what was understood
            content = f"📝 فهمت: \"{transcript}\"\n\n{response_text}"

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
                '📞 هاتف الطوارئ: 1111\n'
                '📞 خدمة العملاء: 06-5300-666'
            ),
        }


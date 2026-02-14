"""
WhatsApp message router — classifies intent and dispatches to AI services.

Routes incoming WhatsApp messages to the appropriate handler based on
message type (text, image, audio, location) and detected intent.
"""
import logging

from apps.ai_engine.services.rag_service import RAGService
from apps.ai_engine.services.voice_service import VoiceService
from apps.ai_engine.services import vision_service
from apps.whatsapp.clients.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)

# Intents that benefit from CrewAI multi-agent analysis
CREW_INTENTS = {'billing', 'savings', 'operations'}


class MessageRouter:
    """
    Routes incoming WhatsApp messages to the appropriate service handler
    based on message type and detected intent.

    Message types handled:
    - text: Detect intent -> RAG (simple Q&A) or CrewAI (complex analysis).
    - image: Route to VisionService for bill scanning.
    - audio: Route to VoiceService for transcription, then re-route the text.
    - location: Acknowledge and suggest nearest JEPCO office.
    """

    def __init__(self):
        self.rag = RAGService()
        self.voice = VoiceService()
        self.wa_client = WhatsAppClient()
        self.intent_keywords = {
            'billing': ['فاتورة', 'bill', 'مبلغ', 'amount', 'دفع', 'pay', 'رصيد', 'balance', 'حساب'],
            'tariff': ['تعرفة', 'شريحة', 'سعر', 'tariff', 'rate', 'tier', 'كيلوواط'],
            'savings': ['توفير', 'تخفيض', 'save', 'reduce', 'savings', 'نصائح', 'tips'],
            'outage': ['انقطاع', 'عطل', 'outage', 'power cut', 'كهرباء مقطوعة'],
            'complaint': ['شكوى', 'complaint', 'مشكلة', 'problem', 'عداد', 'meter'],
            'operations': ['محطة', 'plant', 'توربين', 'turbine', 'صيانة', 'maintenance', 'توليد'],
        }

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
        Classify text intent and dispatch to the right AI service.

        Simple queries (tariff, outage, complaint, general) go to RAG.
        Complex queries (billing analysis, savings) can invoke CrewAI.
        """
        text = message_data.get('text', {}).get('body', '')
        intent = self._detect_intent(text)

        logger.info("Detected intent: %s for text: %s", intent, text[:80])

        if intent in CREW_INTENTS:
            return await self._handle_crew_intent(text=text, intent=intent)

        # Default: RAG-grounded Q&A
        context_type = 'operations' if intent == 'operations' else 'consumer'
        answer = await self.rag.answer(query=text, context_type=context_type)

        return {
            'response_type': 'text',
            'content': answer,
        }

    async def _handle_crew_intent(self, *, text: str, intent: str) -> dict:
        """
        Handle intents that benefit from multi-agent CrewAI analysis.

        Falls back to RAG if CrewAI is unavailable or the query doesn't
        contain enough info (e.g., no subscriber number).
        """
        from apps.consumer.selectors import subscription_get_by_phone
        import re

        # Try to extract a subscriber number from the text
        subscriber_number = None
        numbers = re.findall(r'\b\d{6,12}\b', text)
        if numbers:
            subscriber_number = numbers[0]

        if not subscriber_number:
            # Fall back to RAG for queries without a specific account
            context_type = 'operations' if intent == 'operations' else 'consumer'
            answer = await self.rag.answer(query=text, context_type=context_type)
            return {'response_type': 'text', 'content': answer}

        # Run CrewAI analysis in a thread to avoid blocking
        try:
            import asyncio
            from apps.ai_engine.crew.crews import run_consumer_analysis

            result = await asyncio.to_thread(
                run_consumer_analysis,
                subscriber_number=subscriber_number,
            )

            if result.get('status') == 'success':
                output = result.get('raw_output', '')
                return {'response_type': 'text', 'content': output}

        except Exception as e:
            logger.error("CrewAI analysis failed, falling back to RAG: %s", e)

        # Fallback to RAG
        answer = await self.rag.answer(query=text, context_type='consumer')
        return {'response_type': 'text', 'content': answer}

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

    def _detect_intent(self, text: str) -> str:
        """Classify intent using keyword matching with scoring."""
        text_lower = text.lower()
        scores: dict[str, int] = {}

        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[intent] = score

        if not scores:
            return 'general_qa'

        return max(scores, key=scores.get)

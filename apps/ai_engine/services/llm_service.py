"""
LLM service — unified interface for all language-model interactions.

Routes requests to the appropriate AI client based on message type:
- text → intent detection → JEPCO live data / CrewAI / RAG
- image → Vision service (bill scanning)
- audio → OpenAI Whisper (transcription) → text routing

When a JEPCO file number is detected in billing/savings queries,
fetches real-time smart meter data (no auth needed) and feeds it
to Claude for personalized analysis.
"""
import asyncio
import json
import logging
import re
import time

from django.conf import settings as django_settings
from django.core.cache import cache

from apps.ai_engine.clients.anthropic_client import AnthropicClient
from apps.ai_engine.clients.openai_client import OpenAIClient
from apps.ai_engine.services.rag_service import RAGService
from apps.ai_engine.services import vision_service
from apps.core.utils import check_prompt_injection, INJECTION_SAFE_RESPONSE, mask_content

logger = logging.getLogger(__name__)

# Intents that trigger CrewAI multi-agent analysis
CREW_INTENTS = {'billing', 'savings', 'operations'}

# Regex for JEPCO file numbers (13 digits starting with 0)
FILE_NUMBER_RE = re.compile(r'\b(0\d{12})\b')

# Fastest models per provider (benchmarked)
FAST_CLAUDE = 'claude-haiku-4-5-20251001'     # ~2.5s
FAST_GPT = 'gpt-4.1-mini'                      # ~1.5s

# Approximate cost per 1K tokens (USD) for budget estimation
MODEL_COST_PER_1K = {
    FAST_CLAUDE: 0.00025,
    FAST_GPT: 0.00015,
    'gpt-4o': 0.005,
    'claude-sonnet-4-6': 0.003,
}

BUDGET_EXCEEDED_AR = "الخدمة مشغولة حالياً، يرجى المحاولة لاحقاً."
DAILY_COST_CACHE_KEY = 'ai_daily_cost_usd'

# Typical appliance monthly kWh for Jordanian households
APPLIANCE_KWH = {
    # Cooling & Heating (highest consumers)
    'مكيف': {'name_ar': 'مكيف', 'name_en': 'AC', 'kwh_per_month': 180, 'note': '1.5 طن، 8 ساعات/يوم'},
    'تكييف': {'name_ar': 'مكيف', 'name_en': 'AC', 'kwh_per_month': 180, 'note': '1.5 طن، 8 ساعات/يوم'},
    'دفاية': {'name_ar': 'دفاية كهربائية', 'name_en': 'Space Heater', 'kwh_per_month': 200, 'note': '2000 واط'},
    'هيتر': {'name_ar': 'دفاية كهربائية', 'name_en': 'Space Heater', 'kwh_per_month': 200, 'note': '2000 واط'},
    'صوبة': {'name_ar': 'دفاية كهربائية', 'name_en': 'Space Heater', 'kwh_per_month': 200, 'note': '2000 واط'},
    # Water heating
    'سخان': {'name_ar': 'سخان ماء', 'name_en': 'Water Heater', 'kwh_per_month': 120, 'note': '80 لتر، ساعتين/يوم'},
    'بويلر': {'name_ar': 'سخان ماء', 'name_en': 'Water Heater', 'kwh_per_month': 120, 'note': '80 لتر'},
    # Kitchen
    'ثلاجة': {'name_ar': 'ثلاجة', 'name_en': 'Refrigerator', 'kwh_per_month': 45, 'note': '24/7'},
    'براد': {'name_ar': 'ثلاجة', 'name_en': 'Refrigerator', 'kwh_per_month': 45, 'note': '24/7'},
    'فريزر': {'name_ar': 'فريزر', 'name_en': 'Freezer', 'kwh_per_month': 40, 'note': '24/7'},
    'فرن': {'name_ar': 'فرن كهربائي', 'name_en': 'Electric Oven', 'kwh_per_month': 60, 'note': 'ساعة/يوم'},
    'ميكروويف': {'name_ar': 'ميكروويف', 'name_en': 'Microwave', 'kwh_per_month': 10, 'note': '20 دقيقة/يوم'},
    'غلاية': {'name_ar': 'غلاية ماء', 'name_en': 'Electric Kettle', 'kwh_per_month': 12, 'note': '3 مرات/يوم'},
    'كتل': {'name_ar': 'غلاية ماء', 'name_en': 'Electric Kettle', 'kwh_per_month': 12, 'note': '3 مرات/يوم'},
    'جلاية': {'name_ar': 'جلاية صحون', 'name_en': 'Dishwasher', 'kwh_per_month': 30, 'note': 'دورة/يوم'},
    # Laundry
    'غسالة': {'name_ar': 'غسالة ملابس', 'name_en': 'Washing Machine', 'kwh_per_month': 20, 'note': '5 دورات/أسبوع'},
    'مجفف': {'name_ar': 'مجفف ملابس', 'name_en': 'Dryer', 'kwh_per_month': 75, 'note': 'استهلاك عالي'},
    'نشافة': {'name_ar': 'نشافة ملابس', 'name_en': 'Dryer', 'kwh_per_month': 75, 'note': 'استهلاك عالي'},
    'مكواة': {'name_ar': 'مكواة', 'name_en': 'Iron', 'kwh_per_month': 15, 'note': '3 ساعات/أسبوع'},
    # Entertainment & Electronics
    'تلفزيون': {'name_ar': 'تلفزيون', 'name_en': 'TV', 'kwh_per_month': 15, 'note': '6 ساعات/يوم'},
    'تلفاز': {'name_ar': 'تلفزيون', 'name_en': 'TV', 'kwh_per_month': 15, 'note': '6 ساعات/يوم'},
    'شاشة': {'name_ar': 'تلفزيون', 'name_en': 'TV', 'kwh_per_month': 15, 'note': '6 ساعات/يوم'},
    'كمبيوتر': {'name_ar': 'كمبيوتر', 'name_en': 'Desktop PC', 'kwh_per_month': 25, 'note': '8 ساعات/يوم'},
    'لابتوب': {'name_ar': 'لابتوب', 'name_en': 'Laptop', 'kwh_per_month': 8, 'note': '8 ساعات/يوم'},
    'بلايستيشن': {'name_ar': 'بلايستيشن', 'name_en': 'PlayStation', 'kwh_per_month': 15, 'note': '4 ساعات/يوم'},
    # Lighting
    'إضاءة': {'name_ar': 'إضاءة LED', 'name_en': 'LED Lighting', 'kwh_per_month': 10, 'note': '10 لمبات'},
    'لمبات': {'name_ar': 'إضاءة LED', 'name_en': 'LED Lighting', 'kwh_per_month': 10, 'note': '10 لمبات'},
    # Other
    'مضخة': {'name_ar': 'مضخة ماء', 'name_en': 'Water Pump', 'kwh_per_month': 30, 'note': 'حسب الاستخدام'},
    'مروحة': {'name_ar': 'مروحة', 'name_en': 'Fan', 'kwh_per_month': 8, 'note': '8 ساعات/يوم'},
    'مكنسة': {'name_ar': 'مكنسة كهربائية', 'name_en': 'Vacuum', 'kwh_per_month': 8, 'note': 'ساعة/يوم'},
    'راوتر': {'name_ar': 'راوتر إنترنت', 'name_en': 'Router', 'kwh_per_month': 5, 'note': '24/7'},
}


def check_ai_budget() -> bool:
    """Return True if daily AI budget is still available."""
    daily_limit = getattr(django_settings, 'AI_DAILY_BUDGET_USD', 5.0)
    spent = cache.get(DAILY_COST_CACHE_KEY, 0.0)
    return spent < daily_limit


def record_ai_cost(model: str, tokens: int):
    """Accumulate estimated cost for budget tracking."""
    cost_per_1k = MODEL_COST_PER_1K.get(model, 0.003)
    cost = (tokens / 1000) * cost_per_1k
    current = cache.get(DAILY_COST_CACHE_KEY, 0.0)
    # TTL = seconds until midnight (rough: 24h rolling window)
    cache.set(DAILY_COST_CACHE_KEY, current + cost, 86400)


class LLMService:
    """Unified entry point for all AI interactions in the Nawwar platform."""

    def __init__(self):
        self.openai = OpenAIClient()
        self.rag = RAGService()
        self.claude = AnthropicClient()

    async def route_request(
        self,
        *,
        message_type: str,
        content,
        session_id: str = None,
        file_number: str = None,
        jepco_data: dict = None,
        session_context: dict | None = None,
    ) -> dict:
        """
        Route a request to the appropriate AI service.

        Args:
            message_type: One of 'text', 'image', 'audio'.
            content: Text string, image bytes, or audio bytes.
            session_id: Optional conversation session ID for context.
            file_number: Optional file number from previous conversation turn.
            jepco_data: Optional dict with client-fetched JEPCO data
                        (keys: 'smart_meter', 'bills', 'sap').
            session_context: Optional dict with conversation state
                             (e.g. awaiting, appliances, expected_kwh).

        Returns:
            Dict with:
                response_text: The AI's text response.
                response_type: 'text', 'bill_scan', 'transcription'.
                metadata: Extra data (scan result, intent, etc.).
        """
        # Budget enforcement
        if not check_ai_budget():
            logger.warning("AI daily budget exceeded, rejecting request")
            return {
                'response_text': BUDGET_EXCEEDED_AR,
                'response_type': 'text',
                'metadata': {'intent': 'budget_exceeded'},
            }

        start = time.monotonic()

        if message_type == 'image':
            result = await self._handle_image(content)
        elif message_type == 'audio':
            result = await self._handle_audio(content)
        else:
            result = await self._handle_text(
                content, file_number=file_number, jepco_data=jepco_data,
                session_context=session_context,
            )

        elapsed = int((time.monotonic() - start) * 1000)
        result['metadata']['processing_ms'] = elapsed

        logger.info(
            "LLM request completed: type=%s, response_type=%s, %dms",
            message_type, result['response_type'], elapsed,
        )

        return result

    async def _handle_text(
        self, text: str, *, file_number: str = None, jepco_data: dict = None,
        session_context: dict | None = None,
    ) -> dict:
        """Route text to JEPCO live analysis, CrewAI, or RAG."""
        # Prompt injection pre-screening
        injection_match = check_prompt_injection(text)
        if injection_match:
            logger.warning(
                "Prompt injection detected: pattern='%s', input='%s'",
                injection_match, mask_content(text),
            )
            return {
                'response_text': INJECTION_SAFE_RESPONSE,
                'response_type': 'text',
                'metadata': {'intent': 'blocked', 'reason': 'injection_detected'},
            }

        # Check if we're in an appliance conversation flow
        if file_number and session_context and session_context.get('awaiting') == 'appliance_list':
            # Try appliance matching first
            result = await self._analyze_appliances(text, file_number, session_context)
            # If appliances were found, return the analysis
            if result['metadata'].get('appliances'):
                return result
            # Otherwise, the user is asking a follow-up question — use AI
            # with their consumption context instead of re-running full analysis
            return await self._followup_with_context(text, file_number, session_context)

        intent = await self.rag.classify_intent(text=text)

        # Check for JEPCO file number in message text
        file_match = FILE_NUMBER_RE.search(text)
        # Trigger if: billing/savings/general intent OR the message is just the number
        is_bare_number = file_match and text.strip() == file_match.group(1)

        # Use file number from message, or fall back to one from previous turn
        detected_file = file_match.group(1) if file_match else None
        effective_file = detected_file or file_number

        # Only run full JEPCO analysis for NEW file numbers (first time).
        # For follow-up questions when we already have data, use contextual AI.
        already_analyzed = (
            session_context
            and session_context.get('projected_kwh')
            and not detected_file  # user didn't type a new file number
        )

        if effective_file and (intent in ('billing', 'savings', 'general') or is_bare_number):
            if already_analyzed and not is_bare_number:
                # User already has analysis — answer follow-up with context
                return await self._followup_with_context(text, effective_file, session_context)

            jepco_result = await self._analyze_jepco(
                text=text, file_number=effective_file, intent=intent,
                jepco_data=jepco_data,
            )
            if jepco_result:
                return jepco_result

            # File number detected but no smart meter data → invalid number
            reply = await self._handle_invalid_file_number(effective_file)
            return {
                'response_text': reply,
                'response_type': 'text',
                'metadata': {
                    'intent': intent,
                    'awaiting': 'file_number',
                    'invalid_file_number': effective_file,
                },
            }

        # Billing/savings question WITHOUT any file number → conversational response
        if intent in ('billing', 'savings') and not effective_file:
            reply = await self._ask_for_file_number(text)
            return {
                'response_text': reply,
                'response_type': 'text',
                'metadata': {
                    'intent': intent,
                    'awaiting': 'file_number',
                },
            }

        # Try CrewAI for operations intents (only for operations — billing/savings handled above)
        if intent in CREW_INTENTS:
            crew_result = await self._try_crew(text=text, intent=intent)
            if crew_result:
                return crew_result

        # Default: RAG-grounded Q&A
        context_type = 'operations' if intent == 'operations' else 'consumer'
        answer = await self.rag.answer(query=text, context_type=context_type)

        # For tariff/billing-related intents, append offer to look up their bill
        if intent in ('tariff', 'billing', 'savings', 'general') and not effective_file:
            answer += (
                "\n\n"
                "لتحليل فاتورتك الفعلية ومعرفة استهلاكك الحقيقي وشريحتك، "
                "أرسل لي رقم الملف (13 خانة يبدأ بـ 015) وراح أعطيك تحليل مفصّل."
            )

        return {
            'response_text': answer,
            'response_type': 'text',
            'metadata': {'intent': intent},
        }

    async def _ask_for_file_number(self, user_text: str) -> str:
        """
        Conversational response when user asks about billing but hasn't
        provided a file number. Guides them to find it or take a photo.
        """
        # Check if user is saying they don't know their number
        dont_know_phrases = [
            'ما بعرف', 'مش عارف', 'ما اعرف', 'لا اعرف', 'مو عارف',
            'وين', 'كيف', 'ما عندي', 'مش لاقي', 'مش ملاقي',
            'ما لقيت', 'شو هو', 'اي رقم', 'ايش رقم', 'وين الرقم',
            "don't know", "where", "how", "can't find", "what number",
            'ما بلاقي', 'مش فاهم', 'مش محدد',
        ]
        user_lower = user_text.lower().strip()
        is_confused = any(phrase in user_lower for phrase in dont_know_phrases)

        if is_confused:
            return (
                "لا تشيل هم! رقم الملف موجود على فاتورة الكهرباء الورقية.\n\n"
                "مكانه بالتحديد:\n"
                "في نص الفاتورة، بعد جدول قراءات العداد، مكتوب:\n"
                "\"رقم المرجع : 01/XXXXX/XXXXXX\"\n\n"
                "هو رقم من 13 خانة يبدأ بـ 015.\n\n"
                "الأسهل: صوّر الفاتورة بالكاميرا وابعثها هون وأنا بطلّع الرقم لحالي.\n"
                "اضغط زر الكاميرا أو ابعثلي الصورة مباشرة."
            )

        try:
            reply = await self.openai.chat(
                messages=[{'role': 'user', 'content': user_text}],
                system_prompt=(
                    "أنت نوّار، مساعد كهرباء ذكي أردني. المستخدم يسأل عن فاتورته لكنه لم يعطِ رقم الملف.\n"
                    "القواعد:\n"
                    "- أجب بتعاطف ثم اطلب رقم الملف (13 خانة يبدأ بـ 015)\n"
                    "- أخبره أنه يقدر يصوّر الفاتورة الورقية ويبعثها صورة وأنا بطلّع الرقم\n"
                    "- الرقم مكتوب في نص الفاتورة بجانب كلمة 'رقم المرجع'\n"
                    "- التنسيق: 01/XXXXX/XXXXXX (مثال: 01/50706/667387)\n"
                    "- 3 جمل فقط. بدون Markdown أو إيموجي. عربي فقط."
                ),
                max_tokens=200,
                model=FAST_GPT,
            )
            return reply
        except Exception as e:
            logger.warning("_ask_for_file_number AI failed: %s", e)
            return (
                "لتحليل فاتورتك، أحتاج رقم الملف — 13 خانة يبدأ بـ 015.\n"
                "تلاقيه في نص الفاتورة الورقية بجانب كلمة 'رقم المرجع'.\n\n"
                "أو صوّر الفاتورة الورقية وابعثها هون وأنا بطلّع الرقم تلقائياً."
            )

    async def _handle_invalid_file_number(self, file_number: str) -> str:
        """AI-powered response when the file number is invalid / has no smart meter."""
        try:
            reply = await self.openai.chat(
                messages=[{
                    'role': 'user',
                    'content': f'أدخلت رقم الملف {file_number} لكنه غير صحيح أو لا يوجد له عداد ذكي',
                }],
                system_prompt=(
                    "أنت نوّار، مساعد كهرباء. المستخدم أدخل رقم ملف غير صحيح أو بدون عداد ذكي.\n"
                    "أخبره بلطف، اطلب التأكد من الرقم (015XXXXXXXXXX — 13 خانة)، أو مسح صورة الفاتورة.\n"
                    "3 جمل فقط. بدون Markdown أو إيموجي. عربي فقط."
                ),
                max_tokens=150,
                model=FAST_GPT,
            )
            return reply
        except Exception as e:
            logger.warning("_handle_invalid_file_number AI failed: %s", e)
            return (
                f"عذراً، الرقم {file_number} غير صحيح أو لا تتوفر له بيانات عداد ذكي. "
                "تأكد من رقم الملف (015XXXXXXXXXX — 13 خانة) الموجود في أعلى فاتورتك، وحاول مرة أخرى."
            )

    async def _followup_with_context(
        self, text: str, file_number: str, session_context: dict,
    ) -> dict:
        """
        Answer a follow-up question using existing consumption context.

        Called when the user already has their smart meter data loaded and
        asks about their consumption, appliances, savings, etc. Uses a fast
        LLM call with the session data as context instead of re-running
        the full JEPCO analysis pipeline.
        """
        projected_kwh = session_context.get('projected_kwh', '?')
        expected_kwh = session_context.get('expected_kwh', '?')
        appliances = session_context.get('appliances', [])
        fn = file_number

        context_block = (
            f"بيانات المستخدم (رقم الملف: {fn}):\n"
            f"- الاستهلاك المتوقع نهاية الشهر: {projected_kwh} kWh\n"
        )
        if appliances:
            context_block += f"- الأجهزة المعروفة: {', '.join(appliances)}\n"
        else:
            context_block += "- لم يذكر أجهزته بعد\n"

        # Add appliance reference table
        context_block += (
            "\nمرجع الأجهزة (kWh/شهر تقريبي):\n"
            "مكيف: 180, سخان: 120, مجفف: 60, ثلاجة: 45, فرن: 40, "
            "إضاءة: 30, كمبيوتر: 25, غسالة: 20, تلفزيون: 15, مكواة: 15\n"
        )
        context_block += (
            "\nتعرفة الأردن السكنية:\n"
            "الشريحة 1: 0-300 kWh × 0.050 JOD\n"
            "الشريحة 2: 301-600 kWh × 0.100 JOD\n"
            "الشريحة 3: 600+ kWh × 0.200 JOD\n"
        )

        try:
            reply = await self.openai.chat(
                messages=[{'role': 'user', 'content': text}],
                system_prompt=(
                    "أنت نوّار، مساعد كهرباء ذكي في الأردن.\n"
                    f"{context_block}\n"
                    "القواعد:\n"
                    "- أجب على سؤال المستخدم بناءً على بياناته الفعلية\n"
                    "- إذا سأل 'ايش أكثر شي بستهلك' ولم يذكر أجهزته: اعطِه تقدير "
                    "بناءً على مستوى استهلاكه واسأله عن أجهزته\n"
                    "- إذا سأل عن نصائح توفير: أعطِ نصائح محددة بناءً على استهلاكه\n"
                    "- كلّمه كأنك جاره — بسيط وواضح\n"
                    "- 3-5 جمل فقط. بدون Markdown أو إيموجي. عربي فقط.\n"
                    "- لا تبدأ بتحية"
                ),
                max_tokens=300,
                model=FAST_GPT,
            )
            return {
                'response_text': reply,
                'response_type': 'text',
                'metadata': {
                    'intent': 'followup',
                    'file_number': file_number,
                    'awaiting': 'appliance_list' if not appliances else None,
                },
            }
        except Exception as e:
            logger.warning("_followup_with_context AI failed: %s", e)
            return {
                'response_text': (
                    f"استهلاكك المتوقع {projected_kwh} kWh هذا الشهر. "
                    "عشان أعرف أكثر شي بستهلك عندك، قولي شو الأجهزة الكهربائية اللي عندك "
                    "(مكيف، سخان، ثلاجة، غسالة...) وراح أحللّك بالتفصيل."
                ),
                'response_type': 'text',
                'metadata': {
                    'intent': 'followup',
                    'file_number': file_number,
                    'awaiting': 'appliance_list',
                },
            }

    async def _analyze_jepco(
        self, *, text: str, file_number: str, intent: str,
        jepco_data: dict = None,
    ) -> dict | None:
        """
        Full JEPCO analysis pipeline with JWT auto-auth:

        1. Use client-provided data if available, OR fetch ALL data server-side
           (smart meter + SAP subscriber + bills + consumption comparison)
        2. Build structured data template with anomaly detection
        3. Claude: Bill & tariff analysis, numerical precision
        4. Combine into personalized Arabic response with appliance questions
        """
        from apps.consumer.clients.jepco_client import fetch_all_data, fetch_smart_meter

        try:
            smart_data = None
            bills_data = None
            sap_data = None
            comparison_data = None
            subsidy_data = None
            bill_header = None

            # Use client-provided data if available (browser → JEPCO direct)
            if jepco_data and jepco_data.get('smart_meter'):
                logger.info("Using client-provided JEPCO data for %s", file_number)
                smart_data = jepco_data['smart_meter']
                bills_data = jepco_data.get('bills')
                sap_data = jepco_data.get('sap')
            else:
                # Server-side: fetch ALL data via JWT auto-auth (parallel)
                all_data = await fetch_all_data(file_number)
                smart_data = all_data.get('smart_meter')
                sap_data = all_data.get('sap_info')
                bills_data = all_data.get('bills')
                comparison_data = all_data.get('consumption_comparison')
                subsidy_data = all_data.get('subsidy_simulation')
                bill_header = all_data.get('bill_header')

            if not smart_data or not smart_data.get('showSmartMeterFeature'):
                # Even without smart meter, if we have SAP data, return basic info
                if sap_data:
                    return self._build_non_smart_response(sap_data, file_number, intent)
                return None

            # Build structured template with all data (instant)
            template_text = self._build_jepco_analysis(
                smart_data, file_number, bills_data, sap_data,
                comparison=comparison_data, subsidy=subsidy_data,
                bill_header=bill_header,
            )

            # Claude bill analysis (enhanced with real bill data)
            sonnet_result = None
            try:
                sonnet_result = await self._sonnet_bill_analysis(
                    smart_data, file_number, bills_data,
                )
            except Exception as e:
                logger.warning("Sonnet analysis error: %s", e)

            # Combine: structured template + Claude analysis
            response_text = template_text
            if sonnet_result:
                response_text += f"\n\n{sonnet_result}"

            # Build subscriber info from SAP data
            subscriber_info = None
            if sap_data and isinstance(sap_data, dict):
                subscriber_info = {
                    'name': sap_data.get('firstName', ''),
                    'file_number': sap_data.get('fileNumber', file_number),
                    'meter_number': sap_data.get('meterNumber', ''),
                    'meter_type': sap_data.get('deviceCategoryAdditionalType', ''),
                    'subscription_type': sap_data.get('subscriptionDescription', ''),
                    'subscription_code': sap_data.get('subscriptionCode', ''),
                    'office': sap_data.get('officeDescription', ''),
                    'balance_due': sap_data.get('receivableAmount', '0'),
                    'insurance_balance': sap_data.get('insuranceBalance', '0'),
                    'subsidy_flag': sap_data.get('subsidy_Flag', ''),
                    'rate_group': sap_data.get('rateFactorGroup', ''),
                    'contract_account': sap_data.get('contractAccount', ''),
                }

            return {
                'response_text': response_text,
                'response_type': 'jepco_analysis',
                'metadata': {
                    'intent': intent,
                    'file_number': file_number,
                    'source': 'jepco_live',
                    'awaiting': 'appliance_list',
                    'subscriber': subscriber_info,
                    'models_used': {
                        'data': 'jepco_full_api',
                        'bill_analysis': 'claude-sonnet' if sonnet_result else None,
                    },
                    'bills_found': (
                        len(bills_data.get('allBillsDetails', []))
                        if isinstance(bills_data, dict) else 0
                    ),
                    'current_kwh': smart_data.get('currentElectricityConsumptionQuntity'),
                    'bill_estimate': smart_data.get('expectedElectricityCurrentBillAmount'),
                    'projected_bill': smart_data.get('expectedElectricityEndofMonthBillAmount'),
                    'projected_kwh': smart_data.get('expectedElectricityConsumptionQuntity'),
                },
            }

        except Exception as e:
            logger.warning("JEPCO live analysis failed: %s", e)
            return None

    def _build_non_smart_response(
        self, sap: dict, file_number: str, intent: str,
    ) -> dict:
        """Build response for meters without smart meter but with SAP data."""
        name = sap.get('firstName', '')
        meter = sap.get('meterNumber', '')
        sub_desc = sap.get('subscriptionDescription', '')
        office = sap.get('officeDescription', '')
        subsidy = 'نعم' if sap.get('subsidy_Flag') == 'X' else 'لا'

        lines = [
            f"بيانات المشترك — {name}",
            f"رقم الملف: {file_number}",
            f"رقم العداد: {meter}",
            f"نوع الاشتراك: {sub_desc}",
            f"المكتب: {office}",
            f"الدعم الحكومي: {subsidy}",
            "",
            "عدادك ليس عداداً ذكياً، لذلك لا تتوفر بيانات الاستهلاك اللحظية.",
            "لكن يمكنك إرسال صورة فاتورتك الورقية وسأحللها لك بالتفصيل.",
        ]
        return {
            'response_text': '\n'.join(lines),
            'response_type': 'jepco_analysis',
            'metadata': {
                'intent': intent,
                'file_number': file_number,
                'source': 'jepco_sap_only',
                'subscriber': {
                    'name': name,
                    'file_number': file_number,
                    'meter_number': meter,
                    'subscription_type': sub_desc,
                    'office': office,
                },
            },
        }

    async def _gpt4o_deep_analysis(
        self, smart_data: dict, file_number: str,
    ) -> str | None:
        """
        GPT-4o reasoning: analyze daily consumption patterns, identify
        probable appliance usage, ask targeted questions about peak days.
        """
        try:
            daily = smart_data.get('consumptionMonthlyList', [])
            cur_kwh = smart_data.get('currentElectricityConsumptionQuntity', '0')
            days = smart_data.get('numberOfConsumptionDaysSinceLastRead', '0')
            comp = smart_data.get('comparazinConsumption', {})

            # Build daily log with day names
            day_names_ar = {
                0: 'الاثنين', 1: 'الثلاثاء', 2: 'الأربعاء',
                3: 'الخميس', 4: 'الجمعة', 5: 'السبت', 6: 'الأحد',
            }
            daily_log = []
            for d in daily:
                date_str = d.get('date', '')
                kwh = d.get('consumptionAtDate', '0')
                try:
                    from datetime import datetime
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                    day_name = day_names_ar.get(dt.weekday(), '')
                    daily_log.append(f"  {date_str} ({day_name}): {kwh} kWh")
                except (ValueError, TypeError):
                    daily_log.append(f"  {date_str}: {kwh} kWh")

            daily_text = '\n'.join(daily_log) if daily_log else 'لا تتوفر بيانات يومية'

            data_prompt = (
                f"بيانات العداد الذكي — رقم الملف: {file_number}\n"
                f"إجمالي الاستهلاك: {cur_kwh} kWh خلال {days} يوم\n"
                f"الشهر الماضي: {comp.get('lastMonthconsumption', '?')} kWh\n"
                f"نفس الشهر العام الماضي: {comp.get('lastYearconsumption', '?')} kWh\n\n"
                f"الاستهلاك اليومي المفصّل:\n{daily_text}"
            )

            result = await self.openai.chat(
                messages=[{'role': 'user', 'content': data_prompt}],
                system_prompt=(
                    "أنت خبير تحليل استهلاك الطاقة في الأردن ضمن منصة نوّر.\n"
                    "حلّل بيانات الاستهلاك اليومي المقدمة وقدّم:\n\n"
                    "1. تحليل النمط اليومي: حدد أيام الذروة واسأل المستخدم ماذا استخدم فيها\n"
                    "2. نمط أيام الأسبوع vs عطلة نهاية الأسبوع\n"
                    "3. تقدير الأجهزة المحتملة بناءً على مستوى الاستهلاك\n"
                    "4. اسأل المستخدم عن أجهزته الكهربائية لتحليل أعمق\n\n"
                    "قواعد التنسيق الصارمة:\n"
                    "- لا تستخدم Markdown أبداً (ممنوع: # ## ** ``` - 1️⃣ أو أي رموز تنسيق)\n"
                    "- اكتب نصاً عادياً فقط مع أسطر جديدة للفصل\n"
                    "- لا تبدأ بتحية أو مرحباً — ادخل بالتحليل مباشرة\n"
                    "- كن مختصراً وواضحاً\n"
                    "- أجب دائماً بالعربية"
                ),
                max_tokens=500,
                model=FAST_GPT,
            )
            return result

        except Exception as e:
            logger.warning("GPT-4o deep analysis failed: %s", e)
            return None

    async def _sonnet_bill_analysis(
        self, smart_data: dict, file_number: str, bills_data: list | None,
    ) -> str | None:
        """
        Claude Sonnet: precise bill/tariff analysis with numerical reasoning.
        Analyzes current bill breakdown and historical trend if available.
        """
        try:
            cur_kwh = smart_data.get('currentElectricityConsumptionQuntity', '0')
            exp_kwh = smart_data.get('expectedElectricityConsumptionQuntity', '0')
            cur_bill = smart_data.get('expectedElectricityCurrentBillAmount', '0')
            end_bill = smart_data.get('expectedElectricityEndofMonthBillAmount', '0')
            comp = smart_data.get('comparazinConsumption', {})

            # Build bill history section
            bill_history = ''
            if bills_data and isinstance(bills_data, list):
                bill_lines = []
                for b in bills_data[:6]:
                    period = b.get('billingPeriodEnd', b.get('billDate', ''))
                    kwh = b.get('consumptionKWh', b.get('consumption', '?'))
                    amount = b.get('amountJOD', b.get('billAmount', '?'))
                    status = b.get('status', '')
                    bill_lines.append(
                        f"  {period}: {kwh} kWh — {amount} دينار ({status})"
                    )
                if bill_lines:
                    bill_history = (
                        "\n\nسجل الفواتير (آخر 6 أشهر):\n"
                        + '\n'.join(bill_lines)
                    )

            data_prompt = (
                f"بيانات الفاتورة لرقم الملف {file_number}:\n"
                f"- الاستهلاك الحالي: {cur_kwh} kWh\n"
                f"- المتوقع نهاية الشهر: {exp_kwh} kWh\n"
                f"- الفاتورة الحالية: {cur_bill} دينار\n"
                f"- المتوقع نهاية الشهر: {end_bill} دينار\n"
                f"- الشهر الماضي: {comp.get('lastMonthconsumption', '?')} kWh\n"
                f"- نفس الشهر العام الماضي: {comp.get('lastYearconsumption', '?')} kWh"
                f"{bill_history}"
            )

            result = await self.claude.chat(
                messages=[{'role': 'user', 'content': data_prompt}],
                system_prompt=(
                    "أنت محلل فواتير كهرباء متخصص في نظام التعرفة الأردني.\n"
                    "مرجع الحساب الإلزامي (كل الأسعار بالدينار):\n"
                    "  الشريحة 1: أول 300 kWh × 0.050 دينار = 15.000 دينار\n"
                    "  الشريحة 2: من 301 لـ 600 kWh × 0.100 دينار (مثال: 300 × 0.100 = 30.000 دينار)\n"
                    "  الشريحة 3: فوق 600 kWh × 0.200 دينار\n"
                    "اعرض كل المبالغ بالدينار فقط. لا تستخدم فلس نهائياً.\n\n"
                    "أعطِ نصيحة توفير واحدة محددة بناءً على البيانات.\n"
                    "اذكر أوقات الذروة: شغّل الأجهزة الثقيلة بعد 9 مساءً.\n"
                    "اكتب كأنك تكلم جارك — بسيط وواضح.\n"
                    "احسب بدقة ولا تترك الحساب ناقصاً.\n\n"
                    "قواعد التنسيق الصارمة:\n"
                    "- لا تستخدم Markdown أبداً (ممنوع: # ## ** ``` - 1️⃣ أو أي رموز تنسيق)\n"
                    "- اكتب نصاً عادياً فقط مع أسطر جديدة للفصل\n"
                    "- لا تبدأ بتحية أو مرحباً — ادخل بالتحليل مباشرة\n"
                    "- أجب بـ3-4 جمل فقط. لا أكثر. كل جملة تضيف معلومة جديدة.\n"
                    "- أجب دائماً بالعربية"
                ),
                max_tokens=250,
                model=FAST_CLAUDE,
            )
            return result

        except Exception as e:
            logger.warning("Sonnet bill analysis failed: %s", e)
            return None

    @staticmethod
    def _build_jepco_analysis(
        sm: dict, file_number: str, bills=None,
        sap: dict | None = None,
        comparison: dict | None = None,
        subsidy: list | None = None,
        bill_header: dict | None = None,
    ) -> str:
        """Build instant structured analysis from smart meter + SAP + bill data."""
        days = sm.get('numberOfConsumptionDaysSinceLastRead', '?')
        cur_kwh = sm.get('currentElectricityConsumptionQuntity', '0')
        exp_kwh = sm.get('expectedElectricityConsumptionQuntity', '0')
        cur_bill = sm.get('expectedElectricityCurrentBillAmount', '0')
        end_bill = sm.get('expectedElectricityEndofMonthBillAmount', '0')
        last_read = sm.get('lastBillReading', '?')
        cur_read = sm.get('currentReading', '?')
        read_date = sm.get('lastBillReadingDate', '?')
        comp = sm.get('comparazinConsumption', {})
        daily = sm.get('consumptionMonthlyList', [])

        # Daily average
        try:
            avg = round(float(cur_kwh) / max(int(days), 1), 1)
        except (ValueError, ZeroDivisionError):
            avg = 0

        # Day names for Arabic
        day_names_ar = {
            0: 'الاثنين', 1: 'الثلاثاء', 2: 'الأربعاء',
            3: 'الخميس', 4: 'الجمعة', 5: 'السبت', 6: 'الأحد',
        }

        # Sort days by consumption
        sorted_days = sorted(
            daily,
            key=lambda d: float(d.get('consumptionAtDate', 0)),
            reverse=True,
        )
        peak_days = sorted_days[:3] if sorted_days else []
        low_days = sorted_days[-2:] if len(sorted_days) >= 2 else []

        # Comparison percentages
        last_month = comp.get('lastMonthconsumption', '0')
        last_year = comp.get('lastYearconsumption', '0')
        try:
            exp_f = float(exp_kwh)
            lm_f = float(last_month)
            ly_f = float(last_year)
            lm_pct = round((exp_f - lm_f) / lm_f * 100, 1) if lm_f else 0
            ly_pct = round((exp_f - ly_f) / ly_f * 100, 1) if ly_f else 0
        except ValueError:
            lm_pct = ly_pct = 0

        lm_dir = 'انخفاض' if lm_pct < 0 else 'زيادة'
        ly_dir = 'انخفاض' if ly_pct < 0 else 'زيادة'

        # Tariff tier estimation + bill breakdown (Jordan residential)
        # 1 JOD = 1000 fils. Tiers: 0-300@0.050JOD, 301-600@0.100JOD, 600+@0.200JOD
        tier = '—'
        bill_breakdown_lines = []
        savings_advice = ''
        try:
            exp_f = float(exp_kwh)
            if exp_f <= 300:
                tier = 'الشريحة 1 (0.050 JOD/kWh)'
                cost_jod = exp_f * 0.050
                bill_breakdown_lines = [
                    "تفصيل الفاتورة المتوقعة:",
                    f"  {exp_f:.0f} kWh × 0.050 = {cost_jod:.3f} دينار",
                    f"  الإجمالي: {cost_jod:.3f} دينار (+ رسوم وضرائب)",
                ]
            elif exp_f <= 600:
                tier = 'الشريحة 2 (0.100 JOD/kWh)'
                t1_jod = 300 * 0.050  # 15.000
                t2_kwh = exp_f - 300
                t2_jod = t2_kwh * 0.100
                cost_jod = t1_jod + t2_jod
                bill_breakdown_lines = [
                    "تفصيل الفاتورة المتوقعة:",
                    f"  300 kWh × 0.050 = {t1_jod:.3f} دينار",
                    f"  {t2_kwh:.0f} kWh × 0.100 = {t2_jod:.3f} دينار",
                    f"  الإجمالي: {cost_jod:.3f} دينار (+ رسوم وضرائب)",
                ]
                # Savings advice: how much to cut to stay in Tier 1
                savings_advice = (
                    f"\nنصيحة التوفير:\n"
                    f"لو خفّضت استهلاكك {t2_kwh:.0f} kWh وبقيت تحت 300 kWh/شهر، "
                    f"بتوفّر {t2_jod:.3f} دينار لأنك بتتجنب الشريحة الثانية الأغلى."
                )
            else:
                tier = 'الشريحة 3 (0.200 JOD/kWh)'
                t1_jod = 300 * 0.050   # 15.000
                t2_jod = 300 * 0.100   # 30.000
                t3_kwh = exp_f - 600
                t3_jod = t3_kwh * 0.200
                cost_jod = t1_jod + t2_jod + t3_jod
                bill_breakdown_lines = [
                    "تفصيل الفاتورة المتوقعة:",
                    f"  300 kWh × 0.050 = {t1_jod:.3f} دينار",
                    f"  300 kWh × 0.100 = {t2_jod:.3f} دينار",
                    f"  {t3_kwh:.0f} kWh × 0.200 = {t3_jod:.3f} دينار",
                    f"  الإجمالي: {cost_jod:.3f} دينار (+ رسوم وضرائب)",
                ]
                # Savings advice: how much to cut to drop a tier
                over_600 = exp_f - 600
                savings_advice = (
                    f"\nنصيحة التوفير:\n"
                    f"لو خفّضت استهلاكك {over_600:.0f} kWh وبقيت تحت 600 kWh/شهر، "
                    f"بتوفّر {t3_jod:.3f} دينار لأنك بتتجنب الشريحة الثالثة الأغلى."
                )
        except ValueError:
            pass

        # Build structured response
        lines = []

        # Subscriber info from SAP lookup (if available)
        if sap and isinstance(sap, dict):
            name = sap.get('firstName', '')
            meter = sap.get('meterNumber', '')
            meter_type = sap.get('deviceCategoryAdditionalType', '')
            sub_desc = sap.get('subscriptionDescription', '')
            office = sap.get('officeDescription', '')
            balance = sap.get('receivableAmount', '0')
            subsidy = 'نعم' if sap.get('subsidy_Flag') == 'X' else 'لا'

            lines.append(f"بيانات المشترك — {name}")
            lines.append(f"رقم الملف: {file_number}")
            if meter:
                lines.append(f"رقم العداد: {meter} ({meter_type})")
            if sub_desc:
                lines.append(f"نوع الاشتراك: {sub_desc}")
            if office:
                lines.append(f"المكتب: {office}")
            if float(balance) > 0:
                lines.append(f"الرصيد المستحق: {balance} دينار")
            else:
                lines.append("الرصيد المستحق: لا يوجد مبالغ مستحقة")
            lines.append(f"الدعم الحكومي: {subsidy}")
            lines.append("")
        else:
            lines.append(f"تحليل العداد الذكي — رقم الملف: {file_number}")
            lines.append("")

        lines.extend([
            f"الاستهلاك الحالي: {cur_kwh} kWh خلال {days} يوم",
            f"المعدل اليومي: {avg} kWh/يوم",
            f"الفاتورة الحالية: {cur_bill} دينار",
            f"الفاتورة المتوقعة نهاية الشهر: {end_bill} دينار",
            f"شريحتك: {tier}",
        ])
        if bill_breakdown_lines:
            lines.append("")
            lines.extend(bill_breakdown_lines)
        if savings_advice:
            lines.append(savings_advice)
        # Peak hours advice
        lines.append("")
        lines.append("أوقات الذروة (الأغلى): 7 صباحاً - 5 عصراً")
        lines.append("شغّل الغسالة والسخان بعد 9 مساءً وقبل 7 صباحاً للتوفير.")
        lines.extend([
            "",
            "المقارنة:",
            f"  الشهر الماضي: {last_month} kWh ({lm_dir} {abs(lm_pct)}%)",
            f"  نفس الشهر العام الماضي: {last_year} kWh ({ly_dir} {abs(ly_pct)}%)",
            "",
            f"قراءة العداد: {last_read} ← {cur_read} ({read_date})",
        ])

        # Top 3 peak days only (full daily breakdown shown in sidebar chart)
        if peak_days:
            lines.append("")
            lines.append("أعلى 3 أيام استهلاكاً:")
            for d in peak_days:
                date_str = d.get('date', '')
                kwh = d.get('consumptionAtDate', '0')
                try:
                    from datetime import datetime as _dt
                    dt = _dt.strptime(date_str, '%Y-%m-%d')
                    day_name = day_names_ar.get(dt.weekday(), '')
                    lines.append(f"  {date_str} ({day_name}): {kwh} kWh")
                except (ValueError, TypeError):
                    lines.append(f"  {date_str}: {kwh} kWh")

        # Bill history section — from real JEPCO API
        bill_details = []
        if isinstance(bills, dict):
            bill_details = bills.get('allBillsDetails', [])
        elif isinstance(bills, list):
            bill_details = bills

        if bill_details:
            lines.append("")
            lines.append("سجل الفواتير السابقة:")
            # Detect anomalies in billing history
            amounts = []
            for b in bill_details[:13]:
                period = b.get('billPeriod', '?')
                kwh = b.get('ibillingQuantity', b.get('consumptionKWh', '?'))
                amount = b.get('totalBillAmount', b.get('amountJOD', '?'))
                status = 'مدفوعة' if b.get('clearingStatus') == 'X' else 'غير مدفوعة'
                lines.append(f"  {period}: {kwh} kWh — {amount} دينار ({status})")
                try:
                    amounts.append((period, float(kwh)))
                except (ValueError, TypeError):
                    pass

            # Anomaly detection: flag bills that are 2x the average
            if len(amounts) >= 3:
                avg_kwh = sum(a[1] for a in amounts) / len(amounts)
                anomalies = [(p, k) for p, k in amounts if k > avg_kwh * 1.8]
                if anomalies:
                    lines.append("")
                    lines.append("تنبيه — فواتير مرتفعة بشكل غير عادي:")
                    for period, kwh in anomalies:
                        pct = round((kwh / avg_kwh - 1) * 100)
                        lines.append(
                            f"  {period}: {kwh:.0f} kWh — أعلى من معدلك بـ {pct}%"
                        )
                    lines.append(
                        "هل تغير شي بهالفترة؟ (ضيوف، أجهزة جديدة، تدفئة كهربائية؟)"
                    )

        # Cautionary note from JEPCO
        caution = sm.get('cautionaryNoteForSmartMeterConsumption', '')
        if caution:
            lines.append("")
            lines.append(f"ملاحظة: {caution}")

        # Appliance conversation prompt
        lines.append("")
        lines.append(
            "عشان أساعدك أكثر، قولي شو الأجهزة الكهربائية اللي عندك بالبيت؟ "
            "(مكيف، سخان، غسالة، ثلاجة...)"
        )

        return '\n'.join(lines)

    async def _analyze_appliances(
        self, text: str, file_number: str, session_context: dict,
    ) -> dict:
        """
        Analyze user-listed appliances against actual JEPCO consumption.

        Matches appliance keywords from user text against APPLIANCE_KWH,
        sums expected monthly kWh, and compares with actual consumption.
        """
        # Parse appliance keywords from user text
        matched = {}
        text_lower = text
        for key, info in APPLIANCE_KWH.items():
            if key in text_lower or info['name_en'].lower() in text_lower.lower():
                matched[key] = info

        if not matched:
            # No appliance keywords found — return without re-setting awaiting
            # so the caller can fall through to normal routing
            return {
                'response_text': '',
                'response_type': 'text',
                'metadata': {
                    'intent': 'appliance_analysis',
                    'file_number': file_number,
                },
            }

        # Calculate expected total
        total_expected = sum(info['kwh_per_month'] for info in matched.values())

        # Get actual consumption from session context or metadata
        actual_kwh = 0
        try:
            actual_kwh = float(session_context.get('projected_kwh', 0))
        except (ValueError, TypeError):
            pass

        # Build appliance breakdown
        lines = ["بناءً على أجهزتك:"]
        for info in matched.values():
            lines.append(f"  {info['name_ar']}: ~{info['kwh_per_month']} kWh/شهر")
        lines.append(f"  المجموع المتوقع: ~{total_expected} kWh/شهر")

        if actual_kwh > 0:
            lines.append("")
            lines.append(f"استهلاكك الفعلي المتوقع: {actual_kwh:.0f} kWh/شهر")
            diff = abs(actual_kwh - total_expected)
            diff_pct = (diff / actual_kwh * 100) if actual_kwh else 0

            if diff_pct <= 30:
                lines.append(
                    f"الفرق: {diff:.0f} kWh فقط — استهلاكك متطابق مع أجهزتك تقريباً. وضعك ممتاز."
                )
            elif diff_pct <= 50:
                direction = "أعلى" if actual_kwh > total_expected else "أقل"
                lines.append(
                    f"فرق متوسط: استهلاكك الفعلي ({actual_kwh:.0f} kWh) {direction} من المتوقع "
                    f"({total_expected} kWh) بنسبة {diff_pct:.0f}%."
                )
                lines.extend([
                    "",
                    "الأسباب المحتملة:",
                    "  - جهاز نسيت تذكره (سخان ماء، فرن كهربائي، نشافة)",
                    "  - جهاز قديم يستهلك أكثر من الطبيعي",
                    "  - إضاءة عادية بدل LED",
                    "",
                    "حاول تتذكر إذا في جهاز ثاني ما ذكرته.",
                ])
            else:
                lines.append(
                    f"تنبيه مهم: فرق كبير جداً ({diff_pct:.0f}%) بين المتوقع "
                    f"({total_expected} kWh) والفعلي ({actual_kwh:.0f} kWh)!"
                )
                lines.extend([
                    "",
                    "هذا الفرق غير طبيعي. الأسباب المحتملة:",
                    "  1. جهاز يشتغل بدون ما تحس (سخان منسي، مضخة ماء)",
                    "  2. تسريب كهربائي في التمديدات",
                    "  3. سرقة كهرباء من خطك — شخص موصّل على عدادك",
                    "  4. مشكلة في العداد نفسه",
                    "",
                    "ننصحك بشدة:",
                    "  - افحص التمديدات مع كهربائي معتمد",
                    "  - أطفئ كل الأجهزة وراقب العداد — إذا بقي يعد في سرقة",
                    "  - تواصل مع جيبكو: اتصل 116 (مجاني) أو زر أقرب فرع",
                ])

        # Find top consumers and give specific advice
        sorted_appliances = sorted(
            matched.values(), key=lambda x: x['kwh_per_month'], reverse=True,
        )
        if len(sorted_appliances) >= 2 and total_expected > 0:
            top_two = sorted_appliances[:2]
            top_pct = sum(a['kwh_per_month'] for a in top_two) / total_expected * 100
            names = ' و'.join(a['name_ar'] for a in top_two)
            lines.append("")
            lines.append(f"{names} هم {top_pct:.0f}% من استهلاكك. ركّز عليهم:")
            if any(a['name_en'] == 'Water Heater' for a in sorted_appliances):
                lines.append("  شغّل السخان ساعة وحدة بدل ساعتين — توفّر ~60 kWh = 6.000 دينار/شهر")
            if any(a['name_en'] == 'AC' for a in sorted_appliances):
                lines.append("  ارفع حرارة المكيف لـ 24 درجة — توفّر ~30 kWh")

        return {
            'response_text': '\n'.join(lines),
            'response_type': 'appliance_analysis',
            'metadata': {
                'intent': 'appliance_analysis',
                'file_number': file_number,
                'appliances': list(matched.keys()),
                'expected_kwh': total_expected,
                'actual_kwh': actual_kwh,
            },
        }

    async def _try_crew(self, *, text: str, intent: str) -> dict | None:
        """
        Attempt CrewAI multi-agent analysis for complex queries.

        Returns result dict on success, None to fall back to RAG.
        """
        # Extract subscriber number from text (6-12 digit number)
        numbers = re.findall(r'\b\d{6,12}\b', text)
        subscriber_number = numbers[0] if numbers else None

        if intent == 'operations':
            # Extract plant code from text
            plant_code = None
            for code in ('AQABA', 'RISHA', 'REHAB'):
                if code.lower() in text.lower() or code in text:
                    plant_code = code
                    break
            # Also check Arabic names
            arabic_map = {'عقبة': 'AQABA', 'ريشة': 'RISHA', 'رحاب': 'REHAB'}
            for ar_name, code in arabic_map.items():
                if ar_name in text:
                    plant_code = code
                    break

            if not plant_code:
                return None  # Fall back to RAG

            try:
                from apps.ai_engine.crew.crews import run_operations_monitoring
                result = await asyncio.to_thread(
                    run_operations_monitoring,
                    plant_code=plant_code,
                )
                if result.get('status') == 'success':
                    return {
                        'response_text': result.get('raw_output', ''),
                        'response_type': 'crew_analysis',
                        'metadata': {
                            'intent': intent,
                            'crew': 'operations_monitoring',
                            'plant_code': plant_code,
                            'task_results': result.get('task_results', []),
                        },
                    }
            except Exception as e:
                logger.warning("CrewAI operations failed, falling back to RAG: %s", e)
            return None

        # Consumer intents (billing, savings)
        if not subscriber_number:
            return None  # Need a subscriber number for CrewAI, fall back to RAG

        try:
            from apps.ai_engine.crew.crews import run_consumer_analysis
            result = await asyncio.to_thread(
                run_consumer_analysis,
                subscriber_number=subscriber_number,
            )
            if result.get('status') == 'success':
                return {
                    'response_text': result.get('raw_output', ''),
                    'response_type': 'crew_analysis',
                    'metadata': {
                        'intent': intent,
                        'crew': 'consumer_analysis',
                        'subscriber_number': subscriber_number,
                        'task_results': result.get('task_results', []),
                    },
                }
        except Exception as e:
            logger.warning("CrewAI consumer analysis failed, falling back to RAG: %s", e)

        return None

    async def _handle_image(self, image_data: bytes) -> dict:
        """
        Route image through bill scanning → extract file number → fetch all JEPCO data.

        The primary goal is extracting the 13-digit file number (رقم المرجع).
        Once we have it, we fetch real-time data from JEPCO and return a full
        personalized analysis — much richer than what's printed on the paper.
        """
        scan_result = await vision_service.scan_bill(image_data=image_data)

        # Try to extract the file number from the OCR result
        file_number = None
        raw_ocr = scan_result.get('raw_ocr', {})

        # Check multiple possible fields where file number might appear
        for field in ('account_number', 'file_number', 'reference_number', 'subscriber_number'):
            candidate = raw_ocr.get(field, '') or scan_result.get(field, '')
            if candidate:
                # Normalize: remove slashes, spaces, dashes
                cleaned = re.sub(r'[/\s\-]', '', str(candidate))
                # Check if it matches JEPCO file number pattern
                match = re.search(r'(0\d{12})', cleaned)
                if match:
                    file_number = match.group(1)
                    break

        # Also search the full OCR text for any 13-digit number starting with 0
        if not file_number:
            all_text = json.dumps(raw_ocr, ensure_ascii=False) if raw_ocr else ''
            match = FILE_NUMBER_RE.search(all_text)
            if match:
                file_number = match.group(1)

        # If we found a file number, fetch ALL live data from JEPCO
        if file_number:
            logger.info("Bill photo: extracted file number %s, fetching live data", file_number)
            jepco_result = await self._analyze_jepco(
                text=f'حلل فاتورتي رقم {file_number}',
                file_number=file_number,
                intent='billing',
                jepco_data=None,  # Force fresh fetch from API
            )
            if jepco_result:
                # Prepend a note that we extracted the number from the photo
                jepco_result['response_text'] = (
                    f"تم التعرف على رقم الملف من صورة الفاتورة: {file_number}\n\n"
                    + jepco_result['response_text']
                )
                jepco_result['metadata']['source'] = 'bill_photo_scan'
                jepco_result['metadata']['scan_result'] = scan_result
                return jepco_result

        # Fallback: return basic OCR scan result if no file number or API failed
        summary_parts = []
        if scan_result.get('subscriber_number'):
            summary_parts.append(f"رقم الاشتراك: {scan_result['subscriber_number']}")
        if scan_result.get('total_kwh'):
            summary_parts.append(f"الاستهلاك: {scan_result['total_kwh']} ك.و.س")
        if scan_result.get('total_amount_fils'):
            jod = scan_result['total_amount_fils'] / 1000
            summary_parts.append(f"المبلغ: {jod:.3f} دينار")

        response_text = "تم تحليل الفاتورة.\n" + "\n".join(summary_parts)
        if not file_number:
            response_text += (
                "\n\nلم أتمكن من قراءة رقم المرجع من الصورة.\n"
                "حاول تصوير الفاتورة بوضوح أكثر، أو اكتب رقم المرجع يدوياً "
                "(13 رقم يبدأ بـ 015 — موجود في وسط الفاتورة بجانب كلمة 'رقم المرجع')."
            )

        return {
            'response_text': response_text,
            'response_type': 'bill_scan',
            'metadata': {
                'scan_result': scan_result,
                'file_number': file_number,
                'awaiting': 'file_number' if not file_number else None,
            },
        }

    async def _handle_audio(self, audio_data: bytes) -> dict:
        """Transcribe audio, then route the text through RAG."""
        transcript = await self.openai.transcribe_audio(audio_data)

        logger.info("Audio transcribed: length=%d", len(transcript))

        # Now route the transcribed text
        text_result = await self._handle_text(transcript)

        text_result['response_type'] = 'transcription'
        text_result['metadata']['transcript'] = transcript

        return text_result

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
    'claude-sonnet-4-20250514': 0.003,
}

BUDGET_EXCEEDED_AR = "الخدمة مشغولة حالياً، يرجى المحاولة لاحقاً."
DAILY_COST_CACHE_KEY = 'ai_daily_cost_usd'


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
    ) -> dict:
        """
        Route a request to the appropriate AI service.

        Args:
            message_type: One of 'text', 'image', 'audio'.
            content: Text string, image bytes, or audio bytes.
            session_id: Optional conversation session ID for context.
            file_number: Optional file number from previous conversation turn.

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
            result = await self._handle_text(content, file_number=file_number)

        elapsed = int((time.monotonic() - start) * 1000)
        result['metadata']['processing_ms'] = elapsed

        logger.info(
            "LLM request completed: type=%s, response_type=%s, %dms",
            message_type, result['response_type'], elapsed,
        )

        return result

    async def _handle_text(self, text: str, *, file_number: str = None) -> dict:
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

        intent = await self.rag.classify_intent(text=text)

        # Check for JEPCO file number in message text
        file_match = FILE_NUMBER_RE.search(text)
        # Trigger if: billing/savings/general intent OR the message is just the number
        is_bare_number = file_match and text.strip() == file_match.group(1)

        # Use file number from message, or fall back to one from previous turn
        detected_file = file_match.group(1) if file_match else None
        effective_file = detected_file or file_number

        if effective_file and (intent in ('billing', 'savings', 'general') or is_bare_number):
            jepco_result = await self._analyze_jepco(
                text=text, file_number=effective_file, intent=intent,
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

        return {
            'response_text': answer,
            'response_type': 'text',
            'metadata': {'intent': intent},
        }

    async def _ask_for_file_number(self, user_text: str) -> str:
        """
        Conversational response when user asks about billing but hasn't
        provided a file number. Uses fast GPT to understand context and
        respond naturally — handles image upload requests, panicking users, etc.
        """
        try:
            reply = await self.openai.chat(
                messages=[{'role': 'user', 'content': user_text}],
                system_prompt=(
                    "أنت نوّار، مساعد كهرباء ذكي. المستخدم يسأل عن فاتورته لكنه لم يعطِ رقم الملف بعد.\n\n"
                    "القواعد:\n"
                    "- أجب على ما يقوله المستخدم بشكل طبيعي ومتعاطف أولاً\n"
                    "- إذا ذكر صورة/مسح/scan/image/photo: أخبره أنه يمكنه استخدام زر 'مسح فاتورة' (SCAN) "
                    "في أسفل المحادثة لتصوير الفاتورة واستخراج البيانات تلقائياً\n"
                    "- إذا كان قلقاً أو خائفاً: طمئنه أولاً ثم ساعده\n"
                    "- في كل الحالات، اعرض مثال واضح لرقم الملف بهذا الشكل:\n"
                    "  رقم الملف يتكون من 13 خانة ويبدأ بـ 015، مثال: 015XXXXXXXXXX\n"
                    "- أخبره أين يجد رقم الملف: مكتوب في أعلى يمين فاتورة الكهرباء بجانب كلمة 'رقم الملف'\n"
                    "- أخبره كيف يرسله: يكتب الرقم مباشرة في المحادثة، أو يستخدم زر 'مسح فاتورة' (SCAN) "
                    "لتصوير الفاتورة واستخراج الرقم تلقائياً\n"
                    "- لا تكرر نفس الرد — كن طبيعياً ومحادثاتياً\n"
                    "- أجب بـ3-5 جمل فقط، لا تطوّل\n"
                    "- أجب دائماً بالعربية حتى لو كتب المستخدم بالإنجليزية"
                ),
                max_tokens=300,
                model=FAST_GPT,
            )
            return reply
        except Exception as e:
            logger.warning("_ask_for_file_number AI failed: %s", e)
            # Fallback to static response
            return (
                "لتحليل فاتورتك، أحتاج رقم الملف — وهو رقم مكوّن من 13 خانة يبدأ بـ 015، "
                "مثال: 015XXXXXXXXXX\n\n"
                "📌 تجده في أعلى يمين فاتورة الكهرباء بجانب كلمة 'رقم الملف'.\n\n"
                "يمكنك كتابة الرقم هنا مباشرة، أو استخدام زر 'مسح فاتورة' (SCAN) لتصوير الفاتورة."
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
                    "أنت نوّار، مساعد كهرباء ذكي. المستخدم أدخل رقم ملف لكنه غير صحيح "
                    "أو لا تتوفر بيانات عداد ذكي لهذا الرقم.\n\n"
                    "القواعد:\n"
                    "- أخبره بلطف أن الرقم الذي أدخله غير صحيح أو لا تتوفر له بيانات\n"
                    "- اطلب منه التأكد من رقم الملف (015XXXXXXXXXX — 13 خانة)\n"
                    "- أخبره أن الرقم موجود في أعلى فاتورة الكهرباء\n"
                    "- أو يمكنه مسح صورة الفاتورة باستخدام زر 'مسح فاتورة'\n"
                    "- أجب بـ3-4 جمل فقط\n"
                    "- أجب دائماً بالعربية"
                ),
                max_tokens=250,
                model=FAST_GPT,
            )
            return reply
        except Exception as e:
            logger.warning("_handle_invalid_file_number AI failed: %s", e)
            return (
                f"عذراً، الرقم {file_number} غير صحيح أو لا تتوفر له بيانات عداد ذكي. "
                "تأكد من رقم الملف (015XXXXXXXXXX — 13 خانة) الموجود في أعلى فاتورتك، وحاول مرة أخرى."
            )

    async def _analyze_jepco(
        self, *, text: str, file_number: str, intent: str,
    ) -> dict | None:
        """
        Multi-model JEPCO analysis pipeline:

        1. Fetch live smart meter data (unauthenticated, ~500ms)
        2. Fetch bill history if available (~500ms, concurrent)
        3. Build structured data template (instant)
        4. GPT-4o: Deep reasoning — appliance pattern analysis, peak day
           investigation, daily usage profiling (reasoning engine)
        5. Claude Sonnet: Bill & tariff analysis, numerical precision
        6. Combine into comprehensive response with appliance questions
        """
        from apps.consumer.clients.jepco_client import (
            fetch_smart_meter_public, fetch_bills_public, fetch_sap_lookup,
        )

        try:
            # Fetch smart meter + bill history + SAP subscriber info concurrently
            smart_task = fetch_smart_meter_public(file_number)
            bills_task = fetch_bills_public(file_number)
            sap_task = fetch_sap_lookup(file_number)
            smart_data, bills_data, sap_data = await asyncio.gather(
                smart_task, bills_task, sap_task, return_exceptions=True,
            )

            # Handle exceptions from gather
            if isinstance(smart_data, Exception):
                logger.warning("Smart meter fetch error: %s", smart_data)
                smart_data = None
            if isinstance(bills_data, Exception):
                logger.warning("Bills fetch error: %s", bills_data)
                bills_data = None
            if isinstance(sap_data, Exception):
                logger.warning("SAP lookup error: %s", sap_data)
                sap_data = None

            if not smart_data or not smart_data.get('showSmartMeterFeature'):
                return None

            # Build structured template (instant)
            template_text = self._build_jepco_analysis(
                smart_data, file_number, bills_data, sap_data,
            )

            # GPT-4o deep analysis + Claude bill analysis — concurrently
            gpt4o_task = self._gpt4o_deep_analysis(smart_data, file_number)
            sonnet_task = self._sonnet_bill_analysis(
                smart_data, file_number, bills_data,
            )
            gpt4o_result, sonnet_result = await asyncio.gather(
                gpt4o_task, sonnet_task, return_exceptions=True,
            )

            # Handle exceptions
            if isinstance(gpt4o_result, Exception):
                logger.warning("GPT-4o analysis error: %s", gpt4o_result)
                gpt4o_result = None
            if isinstance(sonnet_result, Exception):
                logger.warning("Sonnet analysis error: %s", sonnet_result)
                sonnet_result = None

            # Combine all parts — no model names exposed to user
            parts = [template_text]

            if sonnet_result:
                parts.append(f"\n\nتحليل الفاتورة:\n{sonnet_result}")

            if gpt4o_result:
                parts.append(f"\n\nتحليل الاستهلاك الذكي:\n{gpt4o_result}")

            response_text = ''.join(parts)

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
                    'subscriber': subscriber_info,
                    'models_used': {
                        'data': 'jepco_smart_meter',
                        'reasoning': 'gpt-4o' if gpt4o_result else None,
                        'bill_analysis': 'claude-sonnet' if sonnet_result else None,
                    },
                    'bills_found': len(bills_data) if isinstance(bills_data, list) else 0,
                    'current_kwh': smart_data.get('currentElectricityConsumptionQuntity'),
                    'bill_estimate': smart_data.get('expectedElectricityCurrentBillAmount'),
                    'projected_bill': smart_data.get('expectedElectricityEndofMonthBillAmount'),
                },
            }

        except Exception as e:
            logger.warning("JEPCO live analysis failed: %s", e)
            return None

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
                max_tokens=800,
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
                    "حلّل بيانات الفاتورة وقدّم:\n"
                    "1. تفصيل الفاتورة حسب الشرائح السبع "
                    "(33/72/86/114/158/188/265 فلس/kWh)\n"
                    "2. كم ستوفر لو خفضت استهلاكك لشريحة أقل (بالدينار)\n"
                    "3. اتجاه الاستهلاك (تصاعدي/تنازلي) مع السبب المحتمل\n\n"
                    "قواعد التنسيق الصارمة:\n"
                    "- لا تستخدم Markdown أبداً (ممنوع: # ## ** ``` - 1️⃣ أو أي رموز تنسيق)\n"
                    "- اكتب نصاً عادياً فقط مع أسطر جديدة للفصل\n"
                    "- لا تبدأ بتحية أو مرحباً — ادخل بالتحليل مباشرة\n"
                    "- كن دقيقاً بالأرقام ومختصراً. 4-5 جمل كافية.\n"
                    "- أجب دائماً بالعربية"
                ),
                max_tokens=400,
                model=FAST_CLAUDE,
            )
            return result

        except Exception as e:
            logger.warning("Sonnet bill analysis failed: %s", e)
            return None

    @staticmethod
    def _build_jepco_analysis(
        sm: dict, file_number: str, bills: list | None = None,
        sap: dict | None = None,
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

        # Tariff tier estimation (Jordan residential)
        try:
            exp_f = float(exp_kwh)
            if exp_f <= 160:
                tier = 'الشريحة 1 (33 فلس/kWh)'
            elif exp_f <= 300:
                tier = 'الشريحة 2 (72 فلس/kWh)'
            elif exp_f <= 500:
                tier = 'الشريحة 3 (86 فلس/kWh)'
            elif exp_f <= 600:
                tier = 'الشريحة 4 (114 فلس/kWh)'
            elif exp_f <= 750:
                tier = 'الشريحة 5 (158 فلس/kWh)'
            elif exp_f <= 1000:
                tier = 'الشريحة 6 (188 فلس/kWh)'
            else:
                tier = 'الشريحة 7 (265 فلس/kWh)'
        except ValueError:
            tier = '—'

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
            f"شريحة التعرفة: {tier}",
            "",
            "المقارنة:",
            f"  الشهر الماضي: {last_month} kWh ({lm_dir} {abs(lm_pct)}%)",
            f"  نفس الشهر العام الماضي: {last_year} kWh ({ly_dir} {abs(ly_pct)}%)",
            "",
            f"قراءة العداد: {last_read} ← {cur_read} ({read_date})",
        ])

        # Full daily breakdown with day names
        if daily:
            lines.append("")
            lines.append("الاستهلاك اليومي المفصّل:")
            for d in daily:
                date_str = d.get('date', '')
                kwh = d.get('consumptionAtDate', '0')
                try:
                    from datetime import datetime as _dt
                    dt = _dt.strptime(date_str, '%Y-%m-%d')
                    day_name = day_names_ar.get(dt.weekday(), '')
                    marker = ' ⚡' if d in peak_days else ''
                    lines.append(f"  {date_str} ({day_name}): {kwh} kWh{marker}")
                except (ValueError, TypeError):
                    lines.append(f"  {date_str}: {kwh} kWh")

        # Bill history section
        if bills and isinstance(bills, list) and len(bills) > 0:
            lines.append("")
            lines.append("سجل الفواتير السابقة:")
            for b in bills[:6]:
                period = b.get('billingPeriodEnd', b.get('billDate', '?'))
                kwh = b.get('consumptionKWh', b.get('consumption', '?'))
                amount = b.get('amountJOD', b.get('billAmount', '?'))
                status = b.get('status', '')
                lines.append(f"  {period}: {kwh} kWh — {amount} دينار ({status})")

        # Cautionary note from JEPCO
        caution = sm.get('cautionaryNoteForSmartMeterConsumption', '')
        if caution:
            lines.append("")
            lines.append(f"ملاحظة: {caution}")

        return '\n'.join(lines)

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
        """Route image through the bill scanning pipeline."""
        scan_result = await vision_service.scan_bill(image_data=image_data)

        summary_parts = []
        if scan_result.get('subscriber_number'):
            summary_parts.append(f"رقم الاشتراك: {scan_result['subscriber_number']}")
        if scan_result.get('total_kwh'):
            summary_parts.append(f"الاستهلاك: {scan_result['total_kwh']} ك.و.س")
        if scan_result.get('total_amount_fils'):
            jod = scan_result['total_amount_fils'] / 1000
            summary_parts.append(f"المبلغ: {jod:.3f} دينار")

        response_text = "تم تحليل الفاتورة بنجاح.\n" + "\n".join(summary_parts)

        return {
            'response_text': response_text,
            'response_type': 'bill_scan',
            'metadata': {'scan_result': scan_result},
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

"""
RAG service — retrieval-augmented generation over the knowledge base.

Retrieves relevant knowledge chunks from ChromaDB, injects them as
context into Claude prompts, and returns grounded answers.
"""
import logging

from django.core.cache import cache

from apps.ai_engine.clients.anthropic_client import AnthropicClient
from apps.ai_engine.knowledge.loader import KnowledgeBaseLoader
from apps.ai_engine.prompts.rag_prompts import (
    SYSTEM_PROMPT_AR,
    CONSUMER_QA_PROMPT,
    OPERATIONS_QA_PROMPT,
)
from apps.ai_engine.validators.output_validator import validate_ai_response
from apps.core.utils import normalise_and_hash

logger = logging.getLogger(__name__)

# Cache TTLs (seconds)
RAG_CACHE_TTL = 3600       # 1 hour for full RAG responses
INTENT_CACHE_TTL = 1800    # 30 minutes for intent classification
CACHE_BYPASS_KEYWORDS = {'تحديث', '/refresh', 'refresh'}

# Intent keywords for classification
# Arabic stems used to handle morphological variants (فاتورة/فاتورتي/فواتير)
INTENT_KEYWORDS = {
    'billing': ['فاتور', 'فواتير', 'bill', 'مبلغ', 'amount', 'دفع', 'pay', 'رصيد', 'balance', 'حساب', 'اشتراك'],
    'tariff': ['تعرفة', 'tariff', 'شريحة', 'tier', 'سعر', 'rate', 'كيلوواط'],
    'outage': ['انقطاع', 'outage', 'عطل', 'fault', 'كهرباء مقطوعة', 'power cut'],
    'complaint': ['شكوى', 'complaint', 'مشكلة', 'problem', 'عداد', 'meter'],
    'savings': ['توفير', 'وفر', 'save', 'تخفيض', 'reduce', 'نصائح', 'tips', 'ترشيد'],
    'operations': ['محطة', 'plant', 'توربين', 'turbine', 'توليد', 'generation', 'صيانة', 'maintenance', 'عقبة', 'ريشة', 'رحاب'],
}


class RAGService:
    """Retrieval-augmented generation service for Nawwar."""

    def __init__(self):
        self.kb = KnowledgeBaseLoader()
        self.claude = AnthropicClient()

    async def answer(
        self,
        *,
        query: str,
        language: str = 'ar',
        context_type: str = 'consumer',
        n_results: int = 5,
    ) -> str:
        """
        Answer a user query using knowledge base retrieval + Claude.

        Args:
            query: The user's question (Arabic or English).
            language: Desired response language (ar/en).
            context_type: 'consumer' or 'operations' — selects the prompt template.
            n_results: Number of knowledge chunks to retrieve.

        Returns:
            Grounded text answer from Claude.
        """
        logger.info("RAG query: type=%s, length=%d", context_type, len(query))

        # Check cache (bypass if user requests refresh)
        bypass_cache = any(kw in query for kw in CACHE_BYPASS_KEYWORDS)
        cache_key = normalise_and_hash(f"{context_type}:{query}", prefix='rag')

        if not bypass_cache:
            cached = cache.get(cache_key)
            if cached:
                logger.info("RAG cache HIT for key=%s", cache_key)
                return cached
            logger.info("RAG cache MISS for key=%s", cache_key)

        # Retrieve relevant chunks
        hits = self.kb.search(query=query, n_results=n_results)

        if not hits:
            logger.warning("No knowledge base hits for query (len=%d)", len(query))
            return "لا تتوفر لدي هذه المعلومة حالياً. يرجى التواصل مع الجهة المختصة."

        # Build context string from retrieved chunks
        context = self._format_context(hits)

        # Select prompt template
        if context_type == 'operations':
            prompt_template = OPERATIONS_QA_PROMPT
        else:
            prompt_template = CONSUMER_QA_PROMPT

        user_message = prompt_template.format(context=context, query=query)

        # Call Claude with the RAG prompt
        response = await self.claude.chat(
            messages=[{'role': 'user', 'content': user_message}],
            system_prompt=SYSTEM_PROMPT_AR,
        )

        result = validate_ai_response(response)

        # Store in cache
        cache.set(cache_key, result, RAG_CACHE_TTL)

        return result

    async def classify_intent(self, *, text: str) -> str:
        """
        Classify the intent of a user message using keyword matching.

        Results are cached for 30 minutes.
        """
        cache_key = normalise_and_hash(text, prefix='intent')
        cached = cache.get(cache_key)
        if cached:
            return cached

        text_lower = text.lower()

        scores: dict[str, int] = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[intent] = score

        result = max(scores, key=scores.get) if scores else 'general'
        cache.set(cache_key, result, INTENT_CACHE_TTL)
        return result

    @staticmethod
    def _format_context(hits: list[dict]) -> str:
        """Format retrieved knowledge chunks into a single context string."""
        parts = []
        for i, hit in enumerate(hits, 1):
            source = hit.get('source', 'unknown')
            section = hit.get('section', '')
            text = hit.get('text', '')
            parts.append(f"[{i}] ({source} — {section})\n{text}")

        return '\n\n'.join(parts)

"""
Anthropic API client for chat and RAG tasks via Claude.
"""
import logging
import time

from django.conf import settings
from anthropic import AsyncAnthropic

from apps.ai_engine.models import AILog

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Wrapper around the Anthropic API for Nawwar platform chat tasks."""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.config = settings.AI_CONFIG

    async def chat(
        self,
        messages: list,
        system_prompt: str = '',
        max_tokens: int = 4096,
        model: str | None = None,
    ) -> str:
        """
        Send a chat completion request to Claude.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            system_prompt: Optional system-level instructions.
            max_tokens: Maximum tokens in the response.
            model: Override model (e.g. 'claude-haiku-4-5-20251001' for speed).

        Returns:
            The assistant's text response.
        """
        start = time.monotonic()
        model_name = model or self.config['CLAUDE_MODEL']

        try:
            kwargs = {
                'model': model_name,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': self.config['TEMPERATURE'],
            }
            if system_prompt:
                kwargs['system'] = system_prompt

            response = await self.client.messages.create(**kwargs)

            latency = int((time.monotonic() - start) * 1000)
            content = response.content[0].text

            await AILog.objects.acreate(
                model_name=model_name,
                provider=AILog.Provider.ANTHROPIC,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cost_usd=self._estimate_cost(
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                ),
                latency_ms=latency,
                task_type=AILog.TaskType.CHAT,
                success=True,
            )

            return content

        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            logger.error("Anthropic chat failed: %s", e)
            await AILog.objects.acreate(
                model_name=model_name,
                provider=AILog.Provider.ANTHROPIC,
                latency_ms=latency,
                task_type=AILog.TaskType.CHAT,
                success=False,
                error_message=str(e),
            )
            raise

    async def chat_with_context(
        self,
        query: str,
        context: str,
        system_prompt: str = '',
    ) -> str:
        """
        RAG-style chat: inject retrieved context into the user message.

        Args:
            query: The user's question.
            context: Retrieved documents / knowledge base text.
            system_prompt: Optional system-level instructions.

        Returns:
            The assistant's text response grounded in the provided context.
        """
        messages = [
            {
                'role': 'user',
                'content': (
                    f"السياق المرجعي (Reference Context):\n"
                    f"---\n{context}\n---\n\n"
                    f"السؤال (Question): {query}"
                ),
            }
        ]
        return await self.chat(
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=self.config['MAX_TOKENS'],
        )

    @staticmethod
    def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
        """Rough cost estimation for Claude Sonnet."""
        return (input_tokens / 1000 * 0.003) + (output_tokens / 1000 * 0.015)

"""
OpenAI API client for vision, transcription, and embedding tasks.
"""
import base64
import logging
import time

from django.conf import settings
from openai import AsyncOpenAI

from apps.ai_engine.models import AILog

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Wrapper around the OpenAI API for Nawwar platform tasks."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.config = settings.AI_CONFIG

    async def chat(
        self,
        messages: list,
        system_prompt: str = '',
        max_tokens: int = 2048,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """
        Send a text chat completion to GPT-4o (or specified model).

        Used for reasoning tasks like appliance analysis and pattern detection.
        """
        start = time.monotonic()
        model_name = model or self.config['VISION_MODEL']  # gpt-4o
        temp = temperature if temperature is not None else self.config['TEMPERATURE']

        try:
            kwargs = {
                'model': model_name,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temp,
            }
            if system_prompt:
                kwargs['messages'] = [
                    {'role': 'system', 'content': system_prompt},
                    *messages,
                ]

            response = await self.client.chat.completions.create(**kwargs)

            latency = int((time.monotonic() - start) * 1000)
            content = response.choices[0].message.content
            usage = response.usage

            await AILog.objects.acreate(
                model_name=model_name,
                provider=AILog.Provider.OPENAI,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cost_usd=self._estimate_cost(usage.prompt_tokens, usage.completion_tokens, 'chat'),
                latency_ms=latency,
                task_type=AILog.TaskType.CHAT,
                success=True,
            )

            return content

        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            logger.error("OpenAI chat failed: %s", e)
            await AILog.objects.acreate(
                model_name=model_name,
                provider=AILog.Provider.OPENAI,
                latency_ms=latency,
                task_type=AILog.TaskType.CHAT,
                success=False,
                error_message=str(e),
            )
            raise

    async def vision_extract(self, image_data: bytes, prompt: str) -> dict:
        """
        Extract structured data from an image using GPT-4o vision.

        Args:
            image_data: Raw image bytes (JPEG/PNG).
            prompt: Extraction instructions for the model.

        Returns:
            Parsed JSON dict from the model response.
        """
        import json

        b64_image = base64.b64encode(image_data).decode('utf-8')
        start = time.monotonic()

        try:
            response = await self.client.chat.completions.create(
                model=self.config['VISION_MODEL'],
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/jpeg;base64,{b64_image}',
                                    'detail': 'high',
                                },
                            },
                        ],
                    }
                ],
                max_tokens=self.config['MAX_TOKENS'],
                temperature=self.config['TEMPERATURE'],
                response_format={'type': 'json_object'},
            )

            latency = int((time.monotonic() - start) * 1000)
            content = response.choices[0].message.content
            usage = response.usage

            await AILog.objects.acreate(
                model_name=self.config['VISION_MODEL'],
                provider=AILog.Provider.OPENAI,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cost_usd=self._estimate_cost(usage.prompt_tokens, usage.completion_tokens, 'vision'),
                latency_ms=latency,
                task_type=AILog.TaskType.VISION,
                success=True,
            )

            return json.loads(content)

        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            logger.error("OpenAI vision_extract failed: %s", e)
            await AILog.objects.acreate(
                model_name=self.config['VISION_MODEL'],
                provider=AILog.Provider.OPENAI,
                latency_ms=latency,
                task_type=AILog.TaskType.VISION,
                success=False,
                error_message=str(e),
            )
            raise

    async def transcribe_audio(self, audio_data: bytes, *, filename: str = 'audio.webm') -> str:
        """
        Transcribe audio to text using Whisper / gpt-4o-transcribe.

        Args:
            audio_data: Raw audio bytes.
            filename: Original filename with correct extension (e.g. 'recording.webm').
                      gpt-4o-transcribe is strict about format detection from the extension.

        Returns:
            Transcribed text string.
        """
        import io

        start = time.monotonic()

        try:
            audio_file = io.BytesIO(audio_data)
            audio_file.name = filename

            model = self.config['WHISPER_MODEL']
            kwargs = {
                'model': model,
                'file': audio_file,
            }
            # Only whisper-1 supports the language hint; gpt-4o-transcribe auto-detects
            if model.startswith('whisper'):
                kwargs['language'] = 'ar'

            response = await self.client.audio.transcriptions.create(**kwargs)

            latency = int((time.monotonic() - start) * 1000)

            await AILog.objects.acreate(
                model_name=self.config['WHISPER_MODEL'],
                provider=AILog.Provider.OPENAI,
                latency_ms=latency,
                task_type=AILog.TaskType.STT,
                success=True,
            )

            return response.text

        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            logger.error("OpenAI transcribe_audio failed: %s", e)
            await AILog.objects.acreate(
                model_name=self.config['WHISPER_MODEL'],
                provider=AILog.Provider.OPENAI,
                latency_ms=latency,
                task_type=AILog.TaskType.STT,
                success=False,
                error_message=str(e),
            )
            raise

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate a vector embedding for the given text.

        Args:
            text: Input text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        start = time.monotonic()

        try:
            response = await self.client.embeddings.create(
                model=self.config['EMBEDDING_MODEL'],
                input=text,
            )

            latency = int((time.monotonic() - start) * 1000)

            await AILog.objects.acreate(
                model_name=self.config['EMBEDDING_MODEL'],
                provider=AILog.Provider.OPENAI,
                input_tokens=response.usage.prompt_tokens,
                latency_ms=latency,
                task_type=AILog.TaskType.RAG,
                success=True,
            )

            return response.data[0].embedding

        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            logger.error("OpenAI get_embedding failed: %s", e)
            await AILog.objects.acreate(
                model_name=self.config['EMBEDDING_MODEL'],
                provider=AILog.Provider.OPENAI,
                latency_ms=latency,
                task_type=AILog.TaskType.RAG,
                success=False,
                error_message=str(e),
            )
            raise

    @staticmethod
    def _estimate_cost(input_tokens: int, output_tokens: int, task: str) -> float:
        """Rough cost estimation for logging purposes."""
        rates = {
            'vision': (0.005, 0.015),      # per 1K tokens
            'embedding': (0.00002, 0.0),
            'chat': (0.005, 0.015),
        }
        input_rate, output_rate = rates.get(task, (0.005, 0.015))
        return (input_tokens / 1000 * input_rate) + (output_tokens / 1000 * output_rate)

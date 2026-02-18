"""
Voice service — speech-to-text and text-to-speech.

Handles the full voice pipeline:
- STT: Accept audio bytes (OGG from WhatsApp), call OpenAI Whisper,
  return Arabic transcript text.
- TTS: Accept Arabic text, generate speech audio via edge-tts,
  return audio bytes ready for WhatsApp delivery.

Configuration lives in settings.TTS_CONFIG (voice selection).
"""
import logging
import time

import edge_tts
from django.conf import settings

from apps.ai_engine.clients.openai_client import OpenAIClient
from apps.ai_engine.models import AILog
from apps.ai_engine.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class VoiceService:
    """Arabic voice processing: transcription, synthesis, and full pipeline."""

    def __init__(self):
        self.openai = OpenAIClient()
        self.rag = RAGService()
        self.tts_config = settings.TTS_CONFIG

    async def transcribe(self, *, audio_data: bytes, language: str = 'ar') -> str:
        """
        Transcribe audio to text using OpenAI Whisper.

        Args:
            audio_data: Raw audio bytes (OGG/WAV/MP3).
            language: Language code for transcription (default: Arabic).

        Returns:
            Transcribed text string.
        """
        logger.info("VoiceService.transcribe: %d bytes, lang=%s", len(audio_data), language)

        transcript = await self.openai.transcribe_audio(audio_data)

        logger.info("VoiceService.transcribe result: %s", transcript[:80] if transcript else "")
        return transcript

    async def synthesize(self, *, text: str, voice: str = None) -> bytes:
        """
        Synthesize Arabic text to speech audio.

        Tries edge-tts first (free), falls back to OpenAI TTS.

        Returns:
            Audio bytes in MP3 format.
        """
        if not voice:
            voice = self.tts_config['DEFAULT_VOICE']

        logger.info("VoiceService.synthesize: %d chars, voice=%s", len(text), voice)
        start = time.monotonic()

        # Try edge-tts first (free)
        try:
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if audio_data:
                latency = int((time.monotonic() - start) * 1000)
                await AILog.objects.acreate(
                    model_name=f'edge-tts:{voice}',
                    provider=AILog.Provider.LOCAL,
                    latency_ms=latency,
                    task_type=AILog.TaskType.TTS,
                    success=True,
                )
                logger.info("VoiceService.synthesize (edge-tts): %d bytes, %dms", len(audio_data), latency)
                return audio_data
        except Exception as e:
            logger.warning("edge-tts failed, falling back to OpenAI TTS: %s", e)

        # Fallback: OpenAI TTS
        try:
            response = await self.openai.client.audio.speech.create(
                model='tts-1',
                voice='onyx',
                input=text[:4096],
                response_format='mp3',
            )
            audio_data = response.content

            latency = int((time.monotonic() - start) * 1000)
            await AILog.objects.acreate(
                model_name='tts-1:onyx',
                provider=AILog.Provider.OPENAI,
                latency_ms=latency,
                task_type=AILog.TaskType.TTS,
                success=True,
            )
            logger.info("VoiceService.synthesize (openai): %d bytes, %dms", len(audio_data), latency)
            return audio_data

        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            logger.error("VoiceService.synthesize failed (both providers): %s", e)
            await AILog.objects.acreate(
                model_name='tts-1:onyx',
                provider=AILog.Provider.OPENAI,
                latency_ms=latency,
                task_type=AILog.TaskType.TTS,
                success=False,
                error_message=str(e),
            )
            raise

    async def process_voice_message(self, *, audio_data: bytes) -> dict:
        """
        Full voice pipeline: transcribe -> classify intent -> RAG answer -> synthesize.

        Args:
            audio_data: Raw audio bytes from the user.

        Returns:
            Dict with:
                transcript: The transcribed Arabic text.
                response_text: The AI's text response.
                audio_data: Synthesized audio bytes (MP3).
                intent: Classified intent string.
        """
        logger.info("VoiceService.process_voice_message: %d bytes", len(audio_data))
        start = time.monotonic()

        # Step 1: Transcribe audio to text
        transcript = await self.transcribe(audio_data=audio_data)

        # Step 2: Classify intent
        intent = await self.rag.classify_intent(text=transcript)

        # Step 3: Generate RAG-grounded answer
        context_type = 'operations' if intent == 'operations' else 'consumer'
        response_text = await self.rag.answer(
            query=transcript,
            context_type=context_type,
        )

        # Step 4: Synthesize response to audio (non-fatal if it fails)
        response_audio = None
        try:
            response_audio = await self.synthesize(text=response_text)
        except Exception as e:
            logger.warning("TTS synthesis failed (non-fatal): %s", e)

        elapsed = int((time.monotonic() - start) * 1000)
        logger.info(
            "VoiceService.process_voice_message complete: intent=%s, %dms",
            intent, elapsed,
        )

        return {
            'transcript': transcript,
            'response_text': response_text,
            'audio_data': response_audio,
            'intent': intent,
        }

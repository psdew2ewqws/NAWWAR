"""
Consumer API views.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle

from apps.consumer import services, selectors
from apps.consumer.api.serializers import (
    SubscriptionSerializer,
    SubscriptionCreateSerializer,
    BillSerializer,
    BillCreateSerializer,
    BillScanSerializer,
    ComplaintSerializer,
    ComplaintCreateSerializer,
    TariffTierSerializer,
    TariffPeriodSerializer,
    ConversationSessionSerializer,
    ConversationCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    BillImageScanSerializer,
    BillAnalysisRequestSerializer,
    ConsumerQuerySerializer,
    VoiceQuerySerializer,
    SavingsAnalysisSerializer,
    SavingsResponseSerializer,
)


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

class SubscriptionCreateApi(APIView):
    """Create a new subscription."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription = services.subscription_create(**serializer.validated_data)

        return Response(
            SubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED,
        )


class SubscriptionDetailApi(APIView):
    """Get subscription by subscriber number."""

    permission_classes = [IsAuthenticated]

    def get(self, request, subscriber_number):
        subscription = selectors.subscription_get_by_number(
            subscriber_number=subscriber_number,
        )
        if subscription is None:
            return Response(
                {'detail': 'Subscription not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(SubscriptionSerializer(subscription).data)


# ---------------------------------------------------------------------------
# Bill
# ---------------------------------------------------------------------------

class BillListApi(APIView):
    """List bills for a subscription."""

    permission_classes = [IsAuthenticated]

    def get(self, request, subscriber_number):
        subscription = selectors.subscription_get_by_number(
            subscriber_number=subscriber_number,
        )
        if subscription is None:
            return Response(
                {'detail': 'Subscription not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        bills = selectors.bill_list(subscription=subscription)
        return Response(BillSerializer(bills, many=True).data)


class BillCreateApi(APIView):
    """Create a new bill."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BillCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        subscriber_number = data.pop('subscriber_number')

        subscription = selectors.subscription_get_by_number(
            subscriber_number=subscriber_number,
        )
        if subscription is None:
            return Response(
                {'detail': 'Subscription not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        bill = services.bill_create(subscription=subscription, **data)

        return Response(
            BillSerializer(bill).data,
            status=status.HTTP_201_CREATED,
        )


class BillScanApi(APIView):
    """Create a bill from scanned/OCR data."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BillScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscriber_number = serializer.validated_data['subscriber_number']
        scan_data = serializer.validated_data['scan_data']

        subscription = selectors.subscription_get_by_number(
            subscriber_number=subscriber_number,
        )
        if subscription is None:
            return Response(
                {'detail': 'Subscription not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        bill = services.bill_create_from_scan(
            subscription=subscription,
            scan_data=scan_data,
        )

        return Response(
            BillSerializer(bill).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Complaint
# ---------------------------------------------------------------------------

class ComplaintCreateApi(APIView):
    """Create a new complaint."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ComplaintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        subscriber_number = data.pop('subscriber_number')

        subscription = selectors.subscription_get_by_number(
            subscriber_number=subscriber_number,
        )
        if subscription is None:
            return Response(
                {'detail': 'Subscription not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        complaint = services.complaint_create(subscription=subscription, **data)

        return Response(
            ComplaintSerializer(complaint).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Tariff
# ---------------------------------------------------------------------------

class TariffTierListApi(APIView):
    """List active tariff tiers for a sector."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        sector = request.query_params.get('sector', 'residential')
        tiers = selectors.tariff_get_active(sector=sector)
        return Response(TariffTierSerializer(tiers, many=True).data)


class TariffPeriodListApi(APIView):
    """List all tariff periods."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        periods = selectors.tariff_periods_list()
        return Response(TariffPeriodSerializer(periods, many=True).data)


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

class ConversationCreateApi(APIView):
    """Create a new conversation session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = services.conversation_create(**serializer.validated_data)

        return Response(
            ConversationSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class ConversationDetailApi(APIView):
    """Get active conversation for a phone number."""

    permission_classes = [IsAuthenticated]

    def get(self, request, phone_number):
        session = selectors.conversation_get_active(phone_number=phone_number)
        if session is None:
            return Response(
                {'detail': 'No active conversation found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(ConversationSessionSerializer(session).data)


class MessageListApi(APIView):
    """List messages for a conversation session."""

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            from apps.consumer.models import ConversationSession
            session = ConversationSession.objects.get(id=session_id)
        except ConversationSession.DoesNotExist:
            return Response(
                {'detail': 'Session not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        messages = selectors.message_list(session=session)
        return Response(MessageSerializer(messages, many=True).data)


class MessageCreateApi(APIView):
    """Create a new message in a conversation."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        session_id = data.pop('session_id')

        try:
            from apps.consumer.models import ConversationSession
            session = ConversationSession.objects.get(id=session_id)
        except ConversationSession.DoesNotExist:
            return Response(
                {'detail': 'Session not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        message = services.message_create(session=session, **data)

        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# AI-powered endpoints
# ---------------------------------------------------------------------------

class BillImageScanApi(APIView):
    """Scan a bill image using GPT-4o vision and return structured data."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai_endpoint'

    def post(self, request):
        import asyncio
        from apps.ai_engine.services import vision_service

        serializer = BillImageScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_file = serializer.validated_data['image']
        image_data = image_file.read()
        subscriber_number = serializer.validated_data.get('subscriber_number', '')

        try:
            scan_result = asyncio.run(vision_service.scan_bill(image_data=image_data))
        except Exception as e:
            return Response(
                {'detail': f'Bill scan failed: {e}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # If subscriber_number provided, create a Bill from the scan
        if subscriber_number:
            subscription = selectors.subscription_get_by_number(
                subscriber_number=subscriber_number,
            )
            if subscription:
                try:
                    bill = services.bill_create_from_scan(
                        subscription=subscription,
                        scan_data={**scan_result},
                    )
                    scan_result['bill_id'] = bill.id
                except Exception as e:
                    scan_result['bill_creation_error'] = str(e)

        return Response(scan_result, status=status.HTTP_200_OK)


class BillAnalysisApi(APIView):
    """Analyze an existing bill using AI and return consumer-friendly insights."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai_endpoint'

    def post(self, request):
        import asyncio
        from apps.ai_engine.services import vision_service
        from apps.consumer.models import Bill

        serializer = BillAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bill_id = serializer.validated_data['bill_id']

        try:
            bill = Bill.objects.select_related('subscription').get(id=bill_id)
        except Bill.DoesNotExist:
            return Response(
                {'detail': 'Bill not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        bill_data = {
            'account_number': bill.subscription.subscriber_number,
            'consumption_kwh': int(bill.total_kwh),
            'total_amount_fils': bill.total_amount_fils,
            'billing_period_start': str(bill.billing_period_start),
            'billing_period_end': str(bill.billing_period_end),
            'previous_reading': bill.previous_reading,
            'current_reading': bill.current_reading,
        }

        try:
            analysis = asyncio.run(vision_service.analyze_bill(bill_data=bill_data))
        except Exception as e:
            return Response(
                {'detail': f'Analysis failed: {e}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(analysis, status=status.HTTP_200_OK)


class ConsumerQueryApi(APIView):
    """Answer consumer questions using RAG over the knowledge base."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai_endpoint'

    def post(self, request):
        import asyncio
        from apps.ai_engine.services.rag_service import RAGService

        serializer = ConsumerQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data['query']
        language = serializer.validated_data['language']

        rag = RAGService()

        try:
            answer = asyncio.run(
                rag.answer(query=query, language=language, context_type='consumer')
            )
        except Exception as e:
            return Response(
                {'detail': f'Query failed: {e}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {'query': query, 'answer': answer, 'language': language},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------

class VoiceQueryApi(APIView):
    """Process a voice message: transcribe, answer via RAG, synthesize response."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai_endpoint'

    def post(self, request):
        import asyncio
        import base64
        from apps.ai_engine.services.voice_service import VoiceService

        serializer = VoiceQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        audio_file = serializer.validated_data['audio']
        audio_data = audio_file.read()

        voice_svc = VoiceService()

        try:
            result = asyncio.run(
                voice_svc.process_voice_message(audio_data=audio_data)
            )
        except Exception as e:
            return Response(
                {'detail': f'Voice processing failed: {e}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Encode audio response as base64 data URI for JSON transport
        response_audio_b64 = base64.b64encode(result['audio_data']).decode('utf-8')
        audio_url = f'data:audio/mpeg;base64,{response_audio_b64}'

        return Response(
            {
                'transcript': result['transcript'],
                'response_text': result['response_text'],
                'intent': result['intent'],
                'audio_url': audio_url,
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Savings
# ---------------------------------------------------------------------------

class SavingsAnalysisApi(APIView):
    """Run full savings analysis for a subscription."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'ai_endpoint'

    def post(self, request):
        import asyncio
        from apps.ai_engine.services.optimizer_service import SavingsOptimizer
        from apps.consumer.models import Subscription

        serializer = SavingsAnalysisSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription_id = serializer.validated_data['subscription_id']

        try:
            Subscription.objects.get(id=subscription_id)
        except Subscription.DoesNotExist:
            return Response(
                {'detail': 'Subscription not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        optimizer = SavingsOptimizer()

        try:
            result = asyncio.run(
                optimizer.full_analysis(subscription_id=subscription_id)
            )
        except Exception as e:
            return Response(
                {'detail': f'Savings analysis failed: {e}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        response_serializer = SavingsResponseSerializer(data=result)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(result, status=status.HTTP_200_OK)

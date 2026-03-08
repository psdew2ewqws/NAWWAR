"""
Dashboard views for the Nawwar platform.

Provides server-rendered pages for both operations staff and consumers.
"""
import base64
import json
import logging
from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.utils import sanitise_text
from apps.operations.models import (
    Plant, Turbine, SensorReading, MaintenancePrediction,
    EmissionsRecord, DemandForecast, HeatRateRecord,
)

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def operations_index(request):
    """Operations dashboard — overview of all CEGCO plants."""
    plants = Plant.objects.filter(is_active=True).prefetch_related('turbines')

    plant_data = []
    for plant in plants:
        turbines = plant.turbines.all()
        online_turbines = turbines.filter(status='online').count()
        total_turbines = turbines.count()

        # Latest emissions
        latest_emission = EmissionsRecord.objects.filter(
            plant=plant
        ).order_by('-timestamp').first()

        # Active maintenance predictions
        active_predictions = MaintenancePrediction.objects.filter(
            turbine__plant=plant,
            is_acknowledged=False,
        ).select_related('turbine').order_by('predicted_failure_date')[:3]

        # Calculate load percentage
        load_pct = 0
        if plant.capacity_mw > 0:
            load_pct = round(float(plant.current_load_mw) / float(plant.capacity_mw) * 100, 1)

        plant_data.append({
            'plant': plant,
            'online_turbines': online_turbines,
            'total_turbines': total_turbines,
            'load_pct': load_pct,
            'latest_emission': latest_emission,
            'predictions': active_predictions,
        })

    # Demand forecast for chart
    now = timezone.now()
    forecasts = DemandForecast.objects.filter(
        forecast_hour__gte=now,
    ).order_by('forecast_hour')[:24]

    forecast_labels = [f.forecast_hour.strftime('%H:%M') for f in forecasts]
    forecast_values = [float(f.predicted_mw) for f in forecasts]
    forecast_lower = [float(f.confidence_lower) for f in forecasts]
    forecast_upper = [float(f.confidence_upper) for f in forecasts]

    # If no future forecasts, show the most recent 24
    if not forecast_labels:
        forecasts = DemandForecast.objects.all().order_by('-forecast_hour')[:24]
        forecasts = list(reversed(list(forecasts)))
        forecast_labels = [f.forecast_hour.strftime('%m/%d %H:%M') for f in forecasts]
        forecast_values = [float(f.predicted_mw) for f in forecasts]
        forecast_lower = [float(f.confidence_lower) for f in forecasts]
        forecast_upper = [float(f.confidence_upper) for f in forecasts]

    # Total generation
    total_capacity = sum(float(p.capacity_mw) for p in plants)
    total_load = sum(float(p.current_load_mw) for p in plants)

    # All active alerts
    all_predictions = MaintenancePrediction.objects.filter(
        is_acknowledged=False,
    ).select_related('turbine', 'turbine__plant').order_by('severity', 'predicted_failure_date')[:10]

    context = {
        'page_title': 'مركز عمليات نوّر — CEGCO Operations',
        'plant_data': plant_data,
        'total_capacity': total_capacity,
        'total_load': total_load,
        'total_load_pct': round(total_load / total_capacity * 100, 1) if total_capacity else 0,
        'forecast_labels_json': json.dumps(forecast_labels),
        'forecast_values_json': json.dumps(forecast_values),
        'forecast_lower_json': json.dumps(forecast_lower),
        'forecast_upper_json': json.dumps(forecast_upper),
        'all_predictions': all_predictions,
        'plant_count': plants.count(),
        'turbine_count': Turbine.objects.filter(plant__is_active=True).count(),
    }
    return render(request, 'dashboard/operations/index.html', context)


def operations_plant_detail(request, plant_key):
    """Operations dashboard — single plant detail view."""
    plant = get_object_or_404(Plant, code=plant_key.upper(), is_active=True)
    turbines = plant.turbines.all()

    # Sensor data for each turbine (last 24 hours)
    hours_24_ago = timezone.now() - timezone.timedelta(hours=24)
    turbine_data = []
    for turbine in turbines:
        readings = SensorReading.objects.filter(
            turbine=turbine,
            timestamp__gte=hours_24_ago,
        ).order_by('timestamp')

        # Get latest readings by type
        latest = {}
        for rtype in ['vibration', 'temperature', 'pressure', 'rpm', 'exhaust_temp']:
            reading = readings.filter(reading_type=rtype).order_by('-timestamp').first()
            if reading:
                latest[rtype] = float(reading.value)

        # Get anomaly count
        anomaly_count = readings.filter(is_anomaly=True).count()

        # Time series for vibration (for chart)
        vib_readings = readings.filter(reading_type='vibration').order_by('timestamp')
        vib_times = [r.timestamp.strftime('%H:%M') for r in vib_readings]
        vib_values = [float(r.value) for r in vib_readings]

        # Time series for temperature
        temp_readings = readings.filter(reading_type='temperature').order_by('timestamp')
        temp_times = [r.timestamp.strftime('%H:%M') for r in temp_readings]
        temp_values = [float(r.value) for r in temp_readings]

        turbine_data.append({
            'turbine': turbine,
            'latest': latest,
            'anomaly_count': anomaly_count,
            'vib_times_json': json.dumps(vib_times),
            'vib_values_json': json.dumps(vib_values),
            'temp_times_json': json.dumps(temp_times),
            'temp_values_json': json.dumps(temp_values),
        })

    # Maintenance predictions
    predictions = MaintenancePrediction.objects.filter(
        turbine__plant=plant,
    ).select_related('turbine').order_by('-created_at')[:10]

    # Emissions history (last 7 days)
    days_7_ago = timezone.now() - timezone.timedelta(days=7)
    emissions = EmissionsRecord.objects.filter(
        plant=plant,
        timestamp__gte=days_7_ago,
    ).order_by('timestamp')

    latest_emission = emissions.order_by('-timestamp').first()

    # Emissions for gauges
    emission_data = {}
    if latest_emission:
        emission_data = {
            'nox': {'value': float(latest_emission.nox_ppm), 'limit': float(latest_emission.nox_limit)},
            'co2': {'value': float(latest_emission.co2_tonnes), 'limit': float(latest_emission.co2_limit)},
            'sox': {'value': float(latest_emission.sox_ppm), 'limit': float(latest_emission.sox_limit)},
            'compliant': latest_emission.is_compliant,
        }

    # Heat rate history
    heat_rates = HeatRateRecord.objects.filter(
        plant=plant,
        timestamp__gte=days_7_ago,
    ).order_by('timestamp')

    hr_times = [hr.timestamp.strftime('%m/%d %H:%M') for hr in heat_rates[:48]]
    hr_values = [float(hr.heat_rate_btu_kwh) for hr in heat_rates[:48]]

    context = {
        'page_title': f'{plant.name_ar} — نوّر',
        'plant': plant,
        'turbine_data': turbine_data,
        'predictions': predictions,
        'emission_data_json': json.dumps(emission_data, cls=DecimalEncoder),
        'emission_data': emission_data,
        'hr_times_json': json.dumps(hr_times),
        'hr_values_json': json.dumps(hr_values),
        'load_pct': round(float(plant.current_load_mw) / float(plant.capacity_mw) * 100, 1) if plant.capacity_mw else 0,
    }
    return render(request, 'dashboard/operations/plant_detail.html', context)


def consumer_index(request):
    """Create a new chat session and redirect to its unique URL."""
    from apps.consumer.models.conversation import ConversationSession
    session = ConversationSession.objects.create(platform='web')
    return redirect('dashboard:consumer-chat', session_key=session.session_key)


def consumer_chat(request, session_key):
    """Load an existing chat session and render the chat UI."""
    from apps.consumer.models.conversation import ConversationSession
    session = get_object_or_404(ConversationSession, session_key=session_key)
    messages = session.messages.order_by('created_at')
    file_number = session.context.get('file_number', '') if session.context else ''
    context = {
        'page_title': 'لوحة المستهلك — نوّر',
        'session_key': session.session_key,
        'file_number': file_number,
        'messages': messages,
    }
    return render(request, 'dashboard/consumer/index.html', context)


def api_plant_data(request, plant_key):
    """API endpoint for real-time plant data updates."""
    try:
        plant = Plant.objects.get(code=plant_key.upper(), is_active=True)
    except Plant.DoesNotExist:
        return JsonResponse({'error': 'Plant not found'}, status=404)

    data = {
        'code': plant.code,
        'status': plant.status,
        'current_load_mw': float(plant.current_load_mw),
        'capacity_mw': float(plant.capacity_mw),
        'load_pct': round(float(plant.current_load_mw) / float(plant.capacity_mw) * 100, 1) if plant.capacity_mw else 0,
    }
    return JsonResponse(data)


# ─── Consumer Chat API ─────────────────────────────────────────────────────

@csrf_exempt
@require_POST
async def api_chat(request):
    """Text chat endpoint — routes user message through RAG pipeline."""
    try:
        body = json.loads(request.body)
        message = sanitise_text(body.get('message', ''))
        if not message:
            return JsonResponse({'error': 'Empty message'}, status=400)

        file_number = body.get('file_number', '').strip() or None

        # Load session if session_key provided
        from apps.consumer.models.conversation import ConversationSession, Message
        session = None
        session_key = body.get('session_key', '').strip()
        if session_key:
            from asgiref.sync import sync_to_async
            session = await sync_to_async(
                ConversationSession.objects.filter(session_key=session_key).first
            )()

        # Fall back to file_number stored in session context
        if not file_number and session and session.context:
            file_number = session.context.get('file_number') or None

        # Save user message
        if session:
            from asgiref.sync import sync_to_async
            await sync_to_async(Message.objects.create)(
                session=session, role='user', content=message,
            )

        # Accept client-provided JEPCO data (browser calls JEPCO directly
        # to bypass geo-blocking on the Railway server)
        jepco_data = body.get('jepco_data')

        # Build session context for conversation flow (appliance analysis, etc.)
        session_ctx = {}
        if session and session.context:
            session_ctx = session.context

        from apps.ai_engine.services.llm_service import LLMService
        svc = LLMService()
        result = await svc.route_request(
            message_type='text', content=message, file_number=file_number,
            jepco_data=jepco_data,
            session_context=session_ctx,
        )

        response = {
            'reply': result['response_text'],
            'intent': result['metadata'].get('intent', 'general'),
            'processing_ms': result['metadata'].get('processing_ms', 0),
        }
        # Include file_number so frontend can trigger sidebar update
        if result['metadata'].get('file_number'):
            response['file_number'] = result['metadata']['file_number']
        # Include subscriber info from SAP lookup
        if result['metadata'].get('subscriber'):
            response['subscriber'] = result['metadata']['subscriber']

        # TTS: synthesize voice reply (non-blocking, non-fatal)
        if body.get('tts', False):
            try:
                from apps.ai_engine.services.voice_service import VoiceService
                voice_svc = VoiceService()
                audio_bytes = await voice_svc.synthesize(text=result['response_text'])
                if audio_bytes:
                    response['audio_b64'] = base64.b64encode(audio_bytes).decode('utf-8')
            except Exception as tts_err:
                logger.warning("TTS synthesis failed (non-fatal): %s", tts_err)

        # Save assistant message and persist file_number in session context
        if session:
            from asgiref.sync import sync_to_async
            await sync_to_async(Message.objects.create)(
                session=session, role='assistant', content=result['response_text'],
                processing_time_ms=result['metadata'].get('processing_ms', 0),
            )
            returned_file = result['metadata'].get('file_number')
            if returned_file or result['metadata'].get('awaiting'):
                ctx = session.context or {}
                if returned_file:
                    ctx['file_number'] = returned_file
                # Persist conversation flow state
                awaiting = result['metadata'].get('awaiting')
                if awaiting:
                    ctx['awaiting'] = awaiting
                else:
                    ctx.pop('awaiting', None)
                if result['metadata'].get('appliances'):
                    ctx['appliances'] = result['metadata']['appliances']
                if result['metadata'].get('expected_kwh'):
                    ctx['expected_kwh'] = result['metadata']['expected_kwh']
                if result['metadata'].get('projected_kwh'):
                    ctx['projected_kwh'] = result['metadata']['projected_kwh']
                session.context = ctx
                await sync_to_async(session.save)(update_fields=['context'])

        return JsonResponse(response)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception("api_chat error: %s", e)
        return JsonResponse({
            'reply': 'عذراً، حدث خطأ في المعالجة. يرجى المحاولة مرة أخرى.',
            'error': str(e),
        }, status=500)


@csrf_exempt
@require_POST
async def api_chat_scan(request):
    """Bill scanning endpoint — sends image through GPT-4o Vision pipeline."""
    try:
        if request.content_type and 'multipart' in request.content_type:
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'error': 'No image file provided'}, status=400)
            image_data = image_file.read()
        else:
            body = json.loads(request.body)
            b64_image = body.get('image', '')
            if not b64_image:
                return JsonResponse({'error': 'No image data provided'}, status=400)
            image_data = base64.b64decode(b64_image)

        from apps.ai_engine.services.llm_service import LLMService
        svc = LLMService()
        result = await svc.route_request(message_type='image', content=image_data)

        return JsonResponse({
            'reply': result['response_text'],
            'scan_result': result['metadata'].get('scan_result', {}),
            'processing_ms': result['metadata'].get('processing_ms', 0),
        })

    except Exception as e:
        logger.exception("api_chat_scan error: %s", e)
        return JsonResponse({
            'reply': 'عذراً، فشل تحليل الفاتورة. تأكد من جودة الصورة وحاول مرة أخرى.',
            'error': str(e),
        }, status=500)


@csrf_exempt
@require_POST
async def api_chat_voice(request):
    """Voice chat endpoint — Whisper STT → LLMService (full pipeline) → Edge-TTS."""
    try:
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return JsonResponse({'error': 'No audio file provided'}, status=400)

        audio_data = audio_file.read()

        # Read session/file context from FormData (sent by frontend)
        session_key = request.POST.get('session_key', '').strip()
        file_number = request.POST.get('file_number', '').strip() or None

        # Step 1: Transcribe audio → text
        from apps.ai_engine.services.voice_service import VoiceService
        voice_svc = VoiceService()
        transcript = await voice_svc.transcribe(audio_data=audio_data)

        if not transcript or not transcript.strip():
            return JsonResponse({
                'transcript': '',
                'reply': 'لم أتمكن من فهم الرسالة الصوتية. حاول مرة أخرى بوضوح.',
                'audio_b64': '',
                'intent': 'general',
            })

        # Step 2: Load session context (same as text chat)
        from apps.consumer.models.conversation import ConversationSession, Message
        from asgiref.sync import sync_to_async
        session = None
        if session_key:
            session = await sync_to_async(
                ConversationSession.objects.filter(session_key=session_key).first
            )()

        if not file_number and session and session.context:
            file_number = session.context.get('file_number') or None

        session_ctx = {}
        if session and session.context:
            session_ctx = session.context

        # Save user message (the transcript)
        if session:
            await sync_to_async(Message.objects.create)(
                session=session, role='user', content=transcript,
            )

        # Step 3: Route through full LLM pipeline (with JEPCO, appliances, etc.)
        from apps.ai_engine.services.llm_service import LLMService
        svc = LLMService()
        result = await svc.route_request(
            message_type='text', content=transcript, file_number=file_number,
            session_context=session_ctx,
        )

        response = {
            'transcript': transcript,
            'reply': result['response_text'],
            'intent': result['metadata'].get('intent', 'general'),
            'processing_ms': result['metadata'].get('processing_ms', 0),
        }

        if result['metadata'].get('file_number'):
            response['file_number'] = result['metadata']['file_number']

        # Step 4: Synthesize TTS audio (non-fatal)
        try:
            audio_bytes = await voice_svc.synthesize(text=result['response_text'])
            if audio_bytes:
                response['audio_b64'] = base64.b64encode(audio_bytes).decode('utf-8')
        except Exception as tts_err:
            logger.warning("Voice TTS synthesis failed (non-fatal): %s", tts_err)
            response['audio_b64'] = ''

        # Save assistant message and persist context
        if session:
            await sync_to_async(Message.objects.create)(
                session=session, role='assistant', content=result['response_text'],
                processing_time_ms=result['metadata'].get('processing_ms', 0),
            )
            returned_file = result['metadata'].get('file_number')
            if returned_file or result['metadata'].get('awaiting'):
                ctx = session.context or {}
                if returned_file:
                    ctx['file_number'] = returned_file
                awaiting = result['metadata'].get('awaiting')
                if awaiting:
                    ctx['awaiting'] = awaiting
                else:
                    ctx.pop('awaiting', None)
                if result['metadata'].get('appliances'):
                    ctx['appliances'] = result['metadata']['appliances']
                if result['metadata'].get('expected_kwh'):
                    ctx['expected_kwh'] = result['metadata']['expected_kwh']
                if result['metadata'].get('projected_kwh'):
                    ctx['projected_kwh'] = result['metadata']['projected_kwh']
                session.context = ctx
                await sync_to_async(session.save)(update_fields=['context'])

        return JsonResponse(response)

    except Exception as e:
        logger.exception("api_chat_voice error: %s", e)
        return JsonResponse({
            'reply': 'عذراً، فشلت معالجة الرسالة الصوتية. حاول مرة أخرى.',
            'error': str(e),
        }, status=500)


# ─── JEPCO API Endpoints ──────────────────────────────────────────────────────

async def api_jepco_customer(request):
    """Get JEPCO SAP subscriber info for a file number."""
    from apps.consumer.clients.jepco_client import fetch_sap_info
    file_number = request.GET.get('file_number', '')
    if not file_number:
        return JsonResponse({'error': 'file_number required'}, status=400)
    data = await fetch_sap_info(file_number)
    if data:
        return JsonResponse({'statusCode': 'Success', 'body': data})
    return JsonResponse({'error': 'Customer not found'}, status=404)


async def api_jepco_bills(request, file_number):
    """Get full billing history for a file number."""
    from apps.consumer.clients.jepco_client import fetch_bills
    data = await fetch_bills(file_number)
    if data:
        return JsonResponse({'statusCode': 'Success', 'body': data})
    return JsonResponse({'error': 'Bills not available'}, status=404)


async def api_jepco_complaints(request):
    """Get complaints — requires mobile number linkage."""
    return JsonResponse({'error': 'Endpoint requires linked mobile number'}, status=501)


async def api_jepco_provinces(request):
    """Get JEPCO coverage provinces."""
    from apps.consumer.clients.jepco_client import _client, _authed_post, _get_token
    async with _client() as client:
        await _get_token(client)
        data = await _authed_post(client, 'Complaints/GetCallCenterProviance', {})
    if data:
        return JsonResponse({'statusCode': 'Success', 'body': data})
    return JsonResponse({'error': 'Provinces not available'}, status=404)


async def api_jepco_verify_meter(request, meter_number):
    """Validate a meter number against JEPCO SAP."""
    from apps.consumer.clients.jepco_client import _client, _authed_post, _get_token
    async with _client() as client:
        await _get_token(client)
        data = await _authed_post(
            client,
            'CustomerInformationDetails/CheckMeterNumberinSAP',
            {'MeterNumber': meter_number, 'LanguageId': 'AR', 'MobileNumber': ''},
        )
    if data:
        return JsonResponse({'statusCode': 'Success', 'body': data})
    return JsonResponse({'error': 'Meter not found in SAP'}, status=404)


async def api_jepco_smart_meter(request, file_number):
    """Get real-time smart meter dashboard data from JEPCO (JWT auto-auth)."""
    from apps.consumer.clients.jepco_client import fetch_smart_meter
    data = await fetch_smart_meter(file_number)
    if data:
        return JsonResponse({'statusCode': 'Success', 'body': data})
    return JsonResponse({'error': 'Smart meter data not available'}, status=404)


async def api_jepco_analyze(request, file_number):
    """
    Fetch real-time smart meter data and return AI analysis.

    No auth needed — calls JEPCO's unauthenticated SmartMeterDashboard,
    then feeds the data to Claude for personalized analysis.
    """
    from apps.consumer.clients.jepco_client import fetch_smart_meter

    smart_data = await fetch_smart_meter(file_number)
    if not smart_data or not smart_data.get('showSmartMeterFeature'):
        return JsonResponse({
            'error': 'Smart meter data not available for this file number',
            'file_number': file_number,
        }, status=404)

    # Return raw data + AI analysis
    from apps.ai_engine.services.llm_service import LLMService
    svc = LLMService()
    result = await svc.route_request(
        message_type='text',
        content=f'حلل استهلاك الكهرباء لرقم الاشتراك {file_number}',
    )

    return JsonResponse({
        'file_number': file_number,
        'smart_meter': smart_data,
        'analysis': result['response_text'],
        'metadata': result['metadata'],
    })


async def api_jepco_account_summary(request):
    """
    Combined account summary — all JEPCO data via JWT auto-auth.

    Fetches smart meter, SAP info, bills, consumption comparison,
    and subsidy simulation in parallel.
    """
    from apps.consumer.clients.jepco_client import fetch_all_data

    file_number = request.GET.get('file_number', '')
    if not file_number:
        config = getattr(settings, 'JEPCO_CONFIG', {})
        file_number = config.get('DEFAULT_FILE_NUMBER', '')

    if not file_number:
        return JsonResponse({'error': 'No file number provided'}, status=400)

    data = await fetch_all_data(file_number)

    return JsonResponse({
        'fileNumber': file_number,
        'smartMeter': data.get('smart_meter'),
        'subscriber': data.get('sap_info'),
        'bills': data.get('bills'),
        'accountStatement': data.get('account_statement'),
        'consumptionComparison': data.get('consumption_comparison'),
        'subsidySimulation': data.get('subsidy_simulation'),
        'billHeader': data.get('bill_header'),
    })

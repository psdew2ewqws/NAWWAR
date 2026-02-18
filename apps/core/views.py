import base64

import httpx
from django.http import HttpResponse, JsonResponse
from django.conf import settings


def hello_world(request):
    return HttpResponse("Hello World")


async def server_ip(request):
    """Return this server's outbound IP (for proxy whitelisting)."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get('https://api.ipify.org?format=json')
        return JsonResponse(r.json())


async def tts_test(request):
    """Test TTS synthesis."""
    try:
        from apps.ai_engine.services.voice_service import VoiceService
        svc = VoiceService()
        audio = await svc.synthesize(text='مرحباً، أنا نوّار')
        return JsonResponse({
            'ok': True,
            'audio_bytes': len(audio) if audio else 0,
            'audio_b64_preview': base64.b64encode(audio[:100]).decode() if audio else '',
        })
    except Exception as e:
        import traceback
        return JsonResponse({'ok': False, 'error': f'{type(e).__name__}: {e}', 'traceback': traceback.format_exc()})


async def proxy_test(request):
    """Test SOCKS5 proxy connectivity — step by step."""
    config = getattr(settings, 'JEPCO_CONFIG', {})
    proxy_url = config.get('PROXY_URL', '')
    result = {'proxy_configured': bool(proxy_url), 'proxy_url_prefix': proxy_url[:20] + '...' if proxy_url else ''}

    if not proxy_url:
        return JsonResponse(result)

    # Step 1: Test proxy with ipify (simple HTTPS)
    try:
        async with httpx.AsyncClient(timeout=15, proxy=proxy_url) as client:
            r = await client.get('https://api.ipify.org?format=json')
            result['proxy_exit_ip'] = r.json().get('ip')
    except Exception as exc:
        result['ipify_error'] = f'{type(exc).__name__}: {exc}'
        return JsonResponse(result)

    # Step 2: Test provider through proxy
    try:
        async with httpx.AsyncClient(timeout=20, proxy=proxy_url) as client:
            r = await client.post(
                'https://mobile.j****.com.jo:443/J****BackendSystemPRD/Dashboard/SmartMeterDashboard',
                json={'FileNumber': '015070████387', 'LanguageId': 'AR'},
                headers={'Content-Type': 'application/json'},
            )
            result['status_code'] = r.status_code
            data = r.json()
            result['provider_status'] = data.get('statusCode')
            if data.get('statusCode') == 'Success':
                body = data.get('body', {})
                result['kwh'] = body.get('currentElectricityConsumptionQuntity')
                result['bill'] = body.get('expectedElectricityCurrentBillAmount')
            else:
                result['message'] = data.get('message', '')
    except Exception as exc:
        result['provider_error'] = f'{type(exc).__name__}: {exc}'

    return JsonResponse(result)

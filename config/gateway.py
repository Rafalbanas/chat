"""Loopback-only Ollama policy: bounded context, one generation, CV priority.

No prompt/response logging. Raw Ollama NDJSON keeps content/thinking separate.
Only read-only model metadata and chat generation are permitted.
"""
import asyncio
import contextlib
import json
import os
import time
from collections import deque
from pathlib import Path

import aiohttp
from aiohttp import web

UPSTREAM = os.getenv('OLLAMA_UPSTREAM', 'http://127.0.0.1:11434').rstrip('/')
STATUS = Path(os.getenv('GPU_STATUS_FILE', '/run/private-chat/gpu.json'))
ALLOWED = {'qwen3.5:9b', 'qwen3.8-27b-iq2s:latest'}
BUSY = 'GPU jest zajęte przez CV Tailor lub trwa inne generowanie. Spróbuj ponownie za chwilę.'
THINKING_LIMIT = 'Model wykorzystał limit wyjścia na myślenie. Wyłącz think (Ollama) i ponów odpowiedź, aby otrzymać wynik w bezpiecznym budżecie GPU.'


def cv_busy():
    try:
        state = json.loads(STATUS.read_text())
        return state['busy'] or abs(time.time() - state['at']) > 4
    except (OSError, ValueError, KeyError, TypeError):
        return True  # fail closed when the read-only status monitor is unavailable


def prepare(body):
    model = body.get('model', '')
    if model == 'qwen3.8-27b-iq2s':
        model += ':latest'
    if model not in ALLOWED:
        raise web.HTTPBadRequest(text='Model niedostępny w prywatnym czacie.')
    messages = body.get('messages')
    if not isinstance(messages, list) or not messages:
        raise web.HTTPBadRequest(text='Brak wiadomości.')
    # Conservative UTF-8 byte upper bound, plus template reserve per turn.
    # Images/tools are excluded for this text-only deployment.
    size = 0
    clean = []
    for m in messages:
        if not isinstance(m, dict) or m.get('role') not in {'user', 'assistant', 'system'} or not isinstance(m.get('content'), str):
            raise web.HTTPBadRequest(text='Obsługiwane są wiadomości tekstowe.')
        if m.get('images') or m.get('tool_calls'):
            raise web.HTTPBadRequest(text='Obrazy i narzędzia nie są włączone.')
        size += len(m['content'].encode('utf-8')) + 64
        clean.append({'role': m['role'], 'content': m['content']})
    if size > 5632:
        raise web.HTTPRequestEntityTooLarge(max_size=5632, actual_size=size,
            text='Przekroczono bezpieczny kontekst. Rozpocznij nową rozmowę lub skróć wiadomości. Historia pozostaje zapisana.')
    requested = body.get('options') or {}
    if not isinstance(requested, dict):
        raise web.HTTPBadRequest(text='Nieprawidłowe parametry.')
    options = {k: requested[k] for k in ('temperature', 'top_p', 'top_k', 'repeat_penalty', 'seed') if k in requested}
    try:
        predicted = int(requested.get('num_predict', 1536))
    except (ValueError, TypeError):
        raise web.HTTPBadRequest(text='Nieprawidłowy limit odpowiedzi.')
    options.update(num_ctx=8192, num_predict=min(1536, predicted) if predicted > 0 else 1536)
    result = dict(model=model, messages=clean, stream=bool(body.get('stream', True)), options=options, keep_alive=0)
    if 'think' in body:
        if not isinstance(body['think'], bool):
            raise web.HTTPBadRequest(text='Tryb myślenia musi być włączony lub wyłączony.')
        result['think'] = body['think']
    else:
        result['think'] = False
    return result


@web.middleware
async def errors(request, handler):
    try:
        return await handler(request)
    except web.HTTPException as e:
        return web.json_response({'error': e.text}, status=e.status, headers={'Retry-After': '10'} if e.status in (429, 503) else None)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return web.json_response({'error': 'Brak połączenia z Ollamą. Sprawdź stacjonarkę i tunel SSH.'}, status=503)


async def metadata(request):
    path = request.path
    if path == '/health':
        return web.json_response({'status': 'ok', 'gpu_busy': cv_busy()})
    payload = None
    if path == '/api/show':
        payload = await request.json()
        model = payload.get('model', payload.get('name', ''))
        if model == 'qwen3.8-27b-iq2s':
            model += ':latest'
        if model not in ALLOWED:
            raise web.HTTPBadRequest(text='Model niedostępny.')
        payload = {'model': model}
    async with request.app['client'].request(request.method, UPSTREAM + path, json=payload) as upstream:
        data = await upstream.json()
        if path in ('/api/tags', '/api/ps'):
            data['models'] = [m for m in data.get('models', []) if m.get('name', m.get('model')) in ALLOWED]
        return web.json_response(data, status=upstream.status)


async def chat(request):
    body = await request.json()
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(text='Nieprawidłowe żądanie.')
    payload = prepare(body)
    if cv_busy() or request.app['active']:
        raise web.HTTPServiceUnavailable(text=BUSY)
    now = time.monotonic()
    starts = request.app['starts']
    while starts and starts[0] < now - 60:
        starts.popleft()
    if len(starts) >= 12:
        raise web.HTTPTooManyRequests(text='Limit 12 generowań na minutę. Zaczekaj chwilę.')
    # No awaits between check and acquisition: single event loop owns the gate.
    request.app['active'] = True
    starts.append(now)
    task = asyncio.current_task()

    async def interrupt():
        while True:
            await asyncio.sleep(0.25)
            if cv_busy():
                task.cancel('CV Tailor priority')
                return

    watchdog = asyncio.create_task(interrupt())
    response = None
    try:
        async with request.app['client'].post(UPSTREAM + '/api/chat', json=payload) as upstream:
            if upstream.status != 200:
                # Do not echo provider diagnostics that may contain request text.
                raise web.HTTPServiceUnavailable(text='Ollama nie może teraz uruchomić modelu. Spróbuj ponownie.')
            if not payload['stream']:
                result = await upstream.json()
                message = result.get('message') or {}
                if message.get('thinking') and not message.get('content'):
                    return web.json_response({'error': THINKING_LIMIT}, status=422)
                return web.json_response(result)
            response = web.StreamResponse(headers={'Content-Type': 'application/x-ndjson', 'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})
            await response.prepare(request)
            has_answer, has_thinking = False, False
            async for line in upstream.content:
                event = json.loads(line)
                message = event.get('message') or {}
                has_answer = has_answer or bool(message.get('content'))
                has_thinking = has_thinking or bool(message.get('thinking'))
                if event.get('done') and has_thinking and not has_answer:
                    event['error'] = THINKING_LIMIT
                    line = (json.dumps(event, ensure_ascii=False) + '\n').encode()
                await response.write(line)
            await response.write_eof()
            return response
    except asyncio.CancelledError:
        if cv_busy():
            if response is not None:
                with contextlib.suppress(ConnectionError, RuntimeError):
                    await response.write((json.dumps({'error': BUSY, 'done': True}) + '\n').encode())
                    await response.write_eof()
                return response
            raise web.HTTPServiceUnavailable(text=BUSY)
        raise
    finally:
        watchdog.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watchdog
        request.app['active'] = False


async def lifecycle(app):
    app['client'] = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=240, connect=5, sock_read=120))
    yield
    await app['client'].close()


def make_app():
    app = web.Application(middlewares=[errors], client_max_size=128 * 1024)
    app['active'] = False
    app['starts'] = deque()
    app.cleanup_ctx.append(lifecycle)
    app.router.add_get('/health', metadata)
    for path in ('/api/version', '/api/tags', '/api/ps'):
        app.router.add_get(path, metadata)
    app.router.add_post('/api/show', metadata)
    app.router.add_post('/api/chat', chat)
    return app


if __name__ == '__main__':
    web.run_app(make_app(), host='127.0.0.1', port=18085, access_log=None, print=None, handler_cancellation=True)

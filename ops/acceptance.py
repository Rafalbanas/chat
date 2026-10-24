#!/usr/bin/python3
"""Run origin acceptance checks. Never print credentials, tokens or prompts."""
import json
from pathlib import Path
import time
import uuid

from client import Client

c = Client()
report = {'at': time.time(), 'target': 'local HTTPS origin, TLS validated with Cloudflare Origin CA', 'checks': []}


def check(name, condition, detail=None):
    report['checks'].append({'name': name, 'passed': bool(condition), 'detail': detail})
    print(('PASS ' if condition else 'FAIL ') + name + (': ' + str(detail) if detail is not None else ''), flush=True)
    Path('/etc/private-chat/acceptance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    if not condition:
        raise SystemExit('Acceptance stopped after failure: ' + name)


status, _, _ = c.json('GET', '/', authenticated=False)
check('HTTPS origin serves application', status == 200, status)
for path in ['/api/v1/chats/', '/api/models', '/ollama/api/tags']:
    status, _, _ = c.json('GET', path, authenticated=False)
    check('Anonymous denied ' + path, status in (401, 403), status)
status, _, _ = c.json('POST', '/api/chat/completions', {'model': 'qwen3.5:9b', 'messages': [{'role': 'user', 'content': 'Test'}]}, authenticated=False)
check('Anonymous generation denied', status in (401, 403), status)
status, _, _ = c.json('POST', '/api/v1/auths/signup', {}, authenticated=False)
check('Registration closed', status == 403, status)
status, _, _ = c.json('POST', '/api/v1/auths/signin', {}, authenticated=False, origin='https://attacker.invalid')
check('Cross-origin mutation denied', status == 403, status)
user, headers = c.login()
check('Administrator login', user.get('role') == 'admin')
cookies = [v.lower() for k, v in headers if k.lower() == 'set-cookie']
check('Session cookie Secure HttpOnly SameSite=Strict', any(all(x in cookie for x in ['secure', 'httponly', 'samesite=strict']) for cookie in cookies))
status, models, _ = c.json('GET', '/api/models')
ids = [m['id'] for m in models.get('data', [])]
check('Required models discovered', status == 200 and {'qwen3.5:9b', 'qwen3.8-27b-iq2s:latest'}.issubset(ids), ids)

uid, aid = str(uuid.uuid4()), str(uuid.uuid4())
chat = {'title': 'Test trwałości wdrożenia', 'models': ['qwen3.5:9b'], 'messages': [], 'history': {'messages': {}, 'currentId': None}, 'params': {}}
status, saved, _ = c.json('POST', '/api/v1/chats/new', {'chat': chat})
check('New chat saved', status == 200 and bool(saved.get('id')))
chat_id = saved['id']
Path('/etc/private-chat/test-chat-id').write_text(chat_id)
chat['title'] = 'Test wdrożenia — zmieniona nazwa'
status, _, _ = c.json('POST', '/api/v1/chats/' + chat_id, {'chat': chat})
check('Rename chat', status == 200)
status, found, _ = c.json('GET', '/api/v1/chats/search?text=zmieniona')
check('Search chat', status == 200 and any(x.get('id') == chat_id for x in found))

for model in ['qwen3.5:9b', 'qwen3.8-27b-iq2s:latest']:
    start = time.monotonic()
    connection, response = c.request('POST', '/ollama/api/chat', {'model': model, 'messages': [{'role': 'user', 'content': 'Odpowiedz po polsku jednym zdaniem: dlaczego niebo jest niebieskie?'}], 'stream': True, 'think': False, 'options': {'num_ctx': 8192, 'num_predict': 128}})
    check('Generation accepted ' + model, response.status == 200, response.status)
    chunks, answer, thinking, first = 0, '', '', None
    while True:
        raw = response.readline()
        if not raw:
            break
        event = json.loads(raw)
        if event.get('error'):
            check('No provider error ' + model, False, event['error'])
        message = event.get('message') or {}
        if message.get('content') or message.get('thinking'):
            chunks += 1
            first = first if first is not None else round(time.monotonic() - start, 2)
        answer += message.get('content', '')
        thinking += message.get('thinking', '')
    connection.close()
    check('Streaming tokens ' + model, chunks > 1, {'chunks': chunks, 'first_chunk_seconds': first, 'total_seconds': round(time.monotonic() - start, 2)})
    check('Nonempty Polish answer ' + model, len(answer) > 10, answer)
    if model == 'qwen3.5:9b':
        messages = {
            uid: {'id': uid, 'parentId': None, 'childrenIds': [aid], 'role': 'user', 'content': 'Dlaczego niebo jest niebieskie?', 'models': [model], 'timestamp': int(time.time())},
            aid: {'id': aid, 'parentId': uid, 'childrenIds': [], 'role': 'assistant', 'content': answer, 'model': model, 'done': True, 'timestamp': int(time.time())},
        }
        chat['history'] = {'messages': messages, 'currentId': aid}
        chat['messages'] = list(messages.values())
        status, _, _ = c.json('POST', '/api/v1/chats/' + chat_id, {'chat': chat})
        check('Real generated answer persisted', status == 200)

status, loaded, _ = c.json('GET', '/api/v1/chats/' + chat_id)
check('History survives fresh HTTP request', status == 200 and loaded['chat']['history']['currentId'] == aid)
status, exported, _ = c.json('GET', '/api/v1/chats/all')
if isinstance(exported, str):
    exported = [json.loads(line) for line in exported.splitlines() if line.strip()]
elif isinstance(exported, dict):
    exported = [exported]
check('JSON export available', status == 200 and any(x.get('id') == chat_id for x in exported))
print('Origin checks complete; retained test conversation for restart verification.', flush=True)

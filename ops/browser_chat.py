#!/usr/bin/python3
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

OUT = Path('/root/chat/private-chat/docs/screenshots')
password = next(x.removeprefix('Hasło: ') for x in Path('/etc/private-chat/initial-login.txt').read_text().splitlines() if x.startswith('Hasło: '))
ids = []
report = {'checks': [], 'page_errors': []}


def record(name, result, detail=None):
    report['checks'].append({'name': name, 'passed': bool(result), 'detail': detail})
    print(('PASS ' if result else 'FAIL ') + name + ': ' + str(detail), flush=True)
    Path('/etc/private-chat/browser-chat.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/root/.cache/ms-playwright/chromium-1187/chrome-linux/chrome', headless=True, args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'])
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    page.set_default_timeout(12000)
    page.on('pageerror', lambda error: report['page_errors'].append(str(error)[:500]))
    page.on('framenavigated', lambda frame: print('NAV', frame.url, flush=True) if frame == page.main_frame else None)

    def onresponse(response):
        path = urlsplit(response.url).path
        if '/api/v1/chats' in path or response.status >= 400:
            print('HTTP', response.status, path, flush=True)
        if response.url.rstrip('/').endswith('/api/v1/chats/new') and response.status == 200:
            ids.append(response.json()['id'])
            Path('/etc/private-chat/browser-test-chat-ids').write_text(json.dumps(ids))
        if '/api/chat/completions' in response.url:
            print('UI generation HTTP', response.status, flush=True)

    page.on('response', onresponse)
    page.goto('https://chat.banas.dev/auth', wait_until='domcontentloaded')
    page.locator('input[type=email]').fill('admin@banas.dev')
    page.locator('input[type=password]').fill(password)
    page.locator('button[type=submit]').click()
    page.wait_for_url(lambda url: '/auth' not in str(url), timeout=30000)
    page.wait_for_selector('#chat-input')
    welcome = page.get_by_role('button', name='OK, Jedziemy!')
    if welcome.count():
        welcome.click()
    page.locator('#chat-input').fill('Zwróć wyłącznie blok kodu Python z instrukcją print(2 + 2).')
    page.locator('#chat-input').press('Enter')
    page.wait_for_timeout(6000)
    print('AFTER SEND URL', page.url, 'CHAT IDS', ids, flush=True)
    if ids and '/c/' not in page.url:
        page.goto('https://chat.banas.dev/c/' + ids[-1], wait_until='domcontentloaded')
    try:
        page.wait_for_selector('.cm-editor, pre code', timeout=20000)
    except Exception:
        print('PAGE ERRORS', report['page_errors'], flush=True)
        print('FAILED BODY', page.locator('body').inner_text()[-1800:], flush=True)
        page.screenshot(path=str(OUT / 'diagnostic.png'))
        raise
    record('Markdown code rendered from actual UI generation', page.locator('.cm-editor, pre code').count() > 0)
    record('Code syntax highlighting', page.locator('.cm-line span, pre code span').count() > 0)
    print('BODY', page.locator('body').inner_text()[-1800:], flush=True)
    print('BUTTONS', page.get_by_role('button').evaluate_all('(nodes)=>nodes.map(n=>({id:n.id,text:n.innerText,aria:n.getAttribute("aria-label"),title:n.title})).slice(-35)'), flush=True)
    print('ERR', report['page_errors'], flush=True)
    page.screenshot(path=str(OUT / 'desktop-conversation.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(500)
    record('Mobile conversation has no horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
    page.screenshot(path=str(OUT / 'mobile-conversation.png'), full_page=True)
    browser.close()

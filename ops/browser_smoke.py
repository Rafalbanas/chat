#!/usr/bin/python3
"""Public browser QA; never persist the session, password or authentication token."""
import json
from pathlib import Path
import re
import time

from playwright.sync_api import sync_playwright

OUT = Path('/root/chat/private-chat/docs/screenshots')
OUT.mkdir(parents=True, exist_ok=True)
password = next(x.removeprefix('Hasło: ') for x in Path('/etc/private-chat/initial-login.txt').read_text().splitlines() if x.startswith('Hasło: '))
report = {'checks': [], 'csp_errors': []}


def record(name, success, detail=None):
    report['checks'].append({'name': name, 'passed': success, 'detail': detail})
    print(('PASS ' if success else 'FAIL ') + name + (': ' + str(detail) if detail is not None else ''), flush=True)
    Path('/etc/private-chat/browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/root/.cache/ms-playwright/chromium-1187/chrome-linux/chrome', headless=True, args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'])
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    page.on('console', lambda message: report['csp_errors'].append(message.text[:250]) if message.type == 'error' and 'Content Security Policy' in message.text else None)
    response = page.goto('https://chat.banas.dev', wait_until='domcontentloaded', timeout=30000)
    page.wait_for_selector('input[type=email]', timeout=45000)
    record('Public login page', response.status == 200)
    page.screenshot(path=str(OUT / 'desktop-login.png'), full_page=True)
    page.locator('input[type=email]').fill('admin@banas.dev')
    page.locator('input[type=password]').fill(password)
    page.locator('button[type=submit]').click()
    page.wait_for_url(lambda url: '/auth' not in str(url), timeout=45000)
    page.wait_for_timeout(2500)
    record('Browser login works', '/auth' not in page.url)
    welcome = page.get_by_role('button', name='OK, Jedziemy!')
    if welcome.count():
        welcome.click()
        page.wait_for_timeout(500)
    print('Visible buttons:', json.dumps(page.get_by_role('button').all_text_contents()[:30], ensure_ascii=False), flush=True)
    print('Inputs:', json.dumps(page.locator('textarea,input,[contenteditable=true]').evaluate_all('(nodes)=>nodes.map(n=>({tag:n.tagName,id:n.id,placeholder:n.getAttribute("placeholder"),role:n.getAttribute("role")}))'), ensure_ascii=False), flush=True)
    page.screenshot(path=str(OUT / 'desktop-chat.png'), full_page=True)
    record('No desktop horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
    # Exercise the actual composer and token delivery through the UI.
    page.locator('#chat-input').fill('Odpowiedz po polsku. Napisz krótką listę dwóch zastosowań Pythona i blok kodu python zawierający print(2 + 2).')
    page.locator('#chat-input').press('Enter')
    page.wait_for_timeout(12000)
    print('After browser generation:', page.locator('body').inner_text()[-1800:], flush=True)
    print('Message nodes:', page.locator('[id*="message"],[id*="response"]').evaluate_all('(nodes)=>nodes.map(n=>({id:n.id,tag:n.tagName})).slice(-25)'), flush=True)
    record('Code block rendered after UI generation', page.locator('pre code').count() > 0)
    record('Python syntax highlighting', page.locator('pre code span').count() > 0)
    page.screenshot(path=str(OUT / 'desktop-conversation.png'), full_page=True)
    # A new chat uses a separate selection, so switching does not rewrite history.
    page.goto('https://chat.banas.dev/', wait_until='domcontentloaded')
    page.get_by_role('button', name=re.compile('Qwen 3.5 · codzienny')).first.click()
    page.get_by_text('Qwen 3.8 · wymagające zadania (27B)', exact=True).first.click()
    record('27B selectable in UI', page.get_by_role('button', name=re.compile('Qwen 3.8 · wymagające')).count() > 0)
    page.locator('#chat-input').fill('Odpowiedz po polsku jednym zdaniem: do czego służy procesor graficzny?')
    page.locator('#chat-input').press('Enter')
    page.wait_for_timeout(14000)
    print('27B browser response:', page.locator('body').inner_text()[-1600:], flush=True)
    record('27B response rendered in UI', page.locator('#response-content-container').count() > 0)
    page.screenshot(path=str(OUT / 'desktop-27b.png'), full_page=True)
    context.set_default_timeout(15000)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(1000)
    page.screenshot(path=str(OUT / 'mobile-chat.png'), full_page=True)
    record('No mobile horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
    record('Composer present on mobile', page.locator('#chat-input').count() > 0)
    print('Page text excerpt:', page.locator('body').inner_text()[:1400], flush=True)
    telemetry = [x for x in report['csp_errors'] if 'static.cloudflareinsights.com' in x]
    application_errors = [x for x in report['csp_errors'] if 'static.cloudflareinsights.com' not in x]
    record('No application CSP violations', not application_errors, application_errors)
    record('Optional Cloudflare analytics blocked by privacy CSP', bool(telemetry))
    context.close()
    browser.close()

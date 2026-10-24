#!/usr/bin/python3
import json
from pathlib import Path
import re
from playwright.sync_api import sync_playwright
from client import Client

c = Client()
c.login()
report = {'checks': []}
out = Path('/root/chat/private-chat/docs/screenshots')


def record(name, value, detail=None):
    report['checks'].append({'name': name, 'passed': bool(value), 'detail': detail})
    print(('PASS ' if value else 'FAIL ') + name + ': ' + str(detail), flush=True)
    Path('/etc/private-chat/browser-27b.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/root/.cache/ms-playwright/chromium-1187/chrome-linux/chrome', args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
    context = browser.new_context(viewport={'width':1440,'height':1000}, permissions=['clipboard-read','clipboard-write'])
    context.add_init_script('localStorage.setItem("token",'+json.dumps(c.token)+');localStorage.setItem("version","0.12.3");')
    page = context.new_page()
    page.set_default_timeout(15000)
    page.goto('https://chat.banas.dev/',wait_until='domcontentloaded')
    page.wait_for_selector('#chat-input',timeout=30000)
    if page.get_by_role('button',name='OK, Jedziemy!').count():
        page.get_by_role('button',name='OK, Jedziemy!').click()
    page.get_by_role('button',name=re.compile('Qwen 3.5 · codzienny')).first.click()
    page.get_by_text('Qwen 3.8 · wymagające zadania (27B)',exact=True).first.click()
    record('27B selected through model switcher',page.get_by_role('button',name=re.compile('Qwen 3.8 · wymagające')).count()>0)
    page.locator('#chat-input').fill('Odpowiedz po polsku jednym zdaniem: do czego służy procesor graficzny?')
    page.locator('#chat-input').press('Enter')
    page.wait_for_url('**/c/**',timeout=30000)
    page.wait_for_timeout(14000)
    print('URL',page.url,flush=True)
    print('BODY',page.locator('body').inner_text()[-1700:],flush=True)
    print('BUTTONS',page.get_by_role('button').evaluate_all('(nodes)=>nodes.map(n=>({id:n.id,text:n.innerText,aria:n.getAttribute("aria-label"),title:n.title})).slice(-30)'),flush=True)
    response_text=page.locator('body').inner_text()
    record('27B answer rendered in conversation', '/c/' in page.url and ('graficzn' in response_text or 'oblicze' in response_text))
    Path('/etc/private-chat/test-27b-chat-id').write_text(page.url.rsplit('/',1)[-1])
    page.screenshot(path=str(out/'desktop-27b.png'))
    page.reload(wait_until='domcontentloaded')
    page.wait_for_selector('#chat-input',timeout=30000)
    record('27B conversation survives browser refresh','procesor' in page.locator('body').inner_text().lower())
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_timeout(500)
    record('Mobile layout has no horizontal overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
    page.screenshot(path=str(out/'mobile-conversation.png'))
    browser.close()

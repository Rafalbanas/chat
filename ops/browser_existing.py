#!/usr/bin/python3
import json
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from client import Client

c = Client()
c.login()
chat_id = Path('/etc/private-chat/test-chat-id').read_text()
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/root/.cache/ms-playwright/chromium-1187/chrome-linux/chrome', args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
    context = browser.new_context(viewport={'width':1440,'height':1000})
    context.add_init_script('localStorage.setItem("token",'+json.dumps(c.token)+');localStorage.setItem("version","0.12.3");')
    page = context.new_page()
    page.on('response', lambda r: print('HTTP',r.status,urlsplit(r.url).path,flush=True) if '/api/' in r.url else None)
    page.on('pageerror',lambda error:print('PAGE ERROR',str(error)[:500],flush=True))
    page.on('framenavigated',lambda f:print('NAV',f.url,flush=True) if f==page.main_frame else None)
    page.goto('https://chat.banas.dev/c/'+chat_id,wait_until='domcontentloaded',timeout=30000)
    page.wait_for_selector('#chat-input',timeout=30000)
    page.wait_for_timeout(2000)
    print('FINAL URL',page.url,flush=True)
    print('BODY',page.locator('body').inner_text()[-2000:],flush=True)
    page.screenshot(path='/root/chat/private-chat/docs/screenshots/existing-diagnostic.png')
    browser.close()

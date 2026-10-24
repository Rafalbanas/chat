#!/usr/bin/python3
import json
from pathlib import Path
import re
import time
import uuid
from playwright.sync_api import sync_playwright
from client import Client

c=Client(); c.login()
u,a=str(uuid.uuid4()),str(uuid.uuid4())
markdown='## Test renderowania\n\n- Pierwszy element\n- Drugi element\n\n| Model | Kontekst |\n| --- | --- |\n| Qwen | 8192 |\n\n```python\nprint(2 + 2)\n```\n\n<script>window.__chat_xss_test=1</script><img src=x onerror="window.__chat_xss_test=1">'
messages={u:{'id':u,'parentId':None,'childrenIds':[a],'role':'user','content':'Test renderowania Markdown','models':['qwen3.5:9b'],'timestamp':int(time.time())},a:{'id':a,'parentId':u,'childrenIds':[],'role':'assistant','content':markdown,'model':'qwen3.5:9b','done':True,'timestamp':int(time.time())}}
chat={'title':'Test renderowania Markdown','models':['qwen3.5:9b'],'messages':list(messages.values()),'history':{'messages':messages,'currentId':a},'params':{}}
status,saved,_=c.json('POST','/api/v1/chats/new',{'chat':chat})
assert status==200
Path('/etc/private-chat/test-render-chat-id').write_text(saved['id'])
report={'checks':[]}
out=Path('/root/chat/private-chat/docs/screenshots')


def record(name,result,detail=None):
    report['checks'].append({'name':name,'passed':bool(result),'detail':detail})
    print(('PASS ' if result else 'FAIL ')+name+': '+str(detail),flush=True)
    Path('/etc/private-chat/browser-features.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))


with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/root/.cache/ms-playwright/chromium-1187/chrome-linux/chrome',args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
    context=browser.new_context(viewport={'width':1440,'height':1000},timezone_id='Europe/Warsaw',permissions=['clipboard-read','clipboard-write'])
    context.add_init_script('localStorage.setItem("token",'+json.dumps(c.token)+');localStorage.setItem("version","0.12.3");')
    page=context.new_page();page.set_default_timeout(12000)
    page.goto('https://chat.banas.dev/c/'+saved['id'],wait_until='domcontentloaded')
    page.wait_for_selector('.cm-editor',timeout=30000)
    if page.get_by_role('button',name='OK, Jedziemy!').count():page.get_by_role('button',name='OK, Jedziemy!').click()
    record('Markdown table renders',page.locator('table').count()>0)
    record('Markdown list renders',page.locator('ul li').count()>=2)
    record('Highlighted Python code renders',page.locator('.cm-line span').count()>0)
    record('Injected script and handler do not execute',page.evaluate('window.__chat_xss_test === undefined'))
    page.get_by_role('button',name='Kopiuj',exact=True).filter(has_text='Kopiuj').first.click()
    clipboard=page.evaluate('navigator.clipboard.readText()')
    record('Code copy button writes correct clipboard',clipboard.strip()=='print(2 + 2)')
    opener=page.get_by_role('button',name='Otwórz pasek boczny',exact=True)
    if opener.count():opener.click()
    page.screenshot(path=str(out/'desktop-markdown.png'))
    page.get_by_role('button',name='Sterowanie',exact=True).click()
    print('CONTROLS',page.locator('body').inner_text()[-3000:],flush=True)
    page.screenshot(path=str(out/'controls.png'))
    page.keyboard.press('Escape')
    # Actual cancellation of a long response, then retry the same user turn.
    page.locator('#chat-input').fill('Napisz długą listę 300 różnych zastosowań Pythona, każde w osobnym zdaniu.')
    page.locator('#chat-input').press('Enter')
    page.wait_for_timeout(1000)
    print('RUNNING BUTTONS',page.get_by_role('button').evaluate_all('(nodes)=>nodes.map(n=>({id:n.id,aria:n.getAttribute("aria-label"),text:n.innerText})).slice(-20)'),flush=True)
    stop=page.locator('#stop-response-button,button[aria-label*="Zatrzymaj"]')
    record('Stop generation control available',stop.count()>0)
    if stop.count():
        stop.first.click()
        page.wait_for_timeout(1500)
        record('Generation stops after click',stop.count()==0)
        retry=page.get_by_role('button',name='Wygeneruj ponownie',exact=True)
        record('Regenerate control available',retry.count()>0)
        if retry.count():
            retry.last.click()
            page.wait_for_timeout(1000)
            record('Regenerate starts a new generation',stop.count()>0)
            if stop.count():stop.first.click()
    page.screenshot(path=str(out/'desktop-stopped.png'))
    browser.close()

#!/usr/bin/python3
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from client import Client

c=Client();c.login()
report={'checks':[]}


def record(name,value,detail=None):
    report['checks'].append({'name':name,'passed':bool(value),'detail':detail})
    print(('PASS ' if value else 'FAIL ')+name+': '+str(detail),flush=True)
    Path('/etc/private-chat/browser-stop.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))


with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/root/.cache/ms-playwright/chromium-1187/chrome-linux/chrome',args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
    context=browser.new_context(viewport={'width':1280,'height':900},timezone_id='Europe/Warsaw')
    context.add_init_script('localStorage.setItem("token",'+json.dumps(c.token)+');localStorage.setItem("version","0.12.3");')
    page=context.new_page();page.set_default_timeout(15000)
    page.goto('https://chat.banas.dev/',wait_until='domcontentloaded')
    page.wait_for_selector('#chat-input',timeout=30000)
    if page.get_by_role('button',name='OK, Jedziemy!').count():page.get_by_role('button',name='OK, Jedziemy!').click()
    page.locator('#chat-input').fill('Napisz obszerną powieść przygodową, co najmniej 10000 słów.')
    page.locator('#chat-input').press('Enter')
    page.wait_for_url('**/c/**',timeout=30000)
    Path('/etc/private-chat/test-stop-chat-id').write_text(page.url.rsplit('/',1)[-1])
    page.wait_for_timeout(2000)
    stop=page.locator('#message-input-container button:visible').last
    print('COMPOSER LAST BUTTON',stop.evaluate('(node)=>node.outerHTML.slice(0,1000)'),flush=True)
    is_stop=lambda r:'/api/tasks/' in r.url and ('/stop/' in r.url or r.url.endswith('/stop'))
    with page.expect_response(is_stop,timeout=15000) as stopped:
        stop.click()
    record('Stop generation sends successful cancellation',stopped.value.status==200,stopped.value.status)
    retry=page.get_by_role('button',name='Wygeneruj ponownie',exact=True)
    retry.last.wait_for(timeout=15000)
    record('Regenerate button available after stop',retry.count()>0)
    retry.last.click()
    page.wait_for_timeout(300)
    print('RETRY MENU',page.locator('body').inner_text()[-1500:],flush=True)
    again=page.get_by_text('Spróbuj ponownie',exact=True)
    with page.expect_response(lambda r:'/api/chat/completions' in r.url,timeout=15000) as regenerated:
        if again.count():again.last.click()
        else:page.get_by_role('menuitem').filter(has_text='ponownie').first.click()
    record('Regenerate starts a new request',regenerated.value.status==200,regenerated.value.status)
    page.wait_for_timeout(1000)
    with page.expect_response(is_stop,timeout=15000) as stopped_again:
        page.locator('#message-input-container button:visible').last.click()
    record('Regenerated response can also be stopped',stopped_again.value.status==200,stopped_again.value.status)
    browser.close()

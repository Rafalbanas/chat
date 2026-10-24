#!/usr/bin/python3
"""Enable MFA without enrolling the owner's authenticator on their behalf."""
import json
from http.cookies import SimpleCookie
from pathlib import Path
from client import Client

c=Client(); user,_=c.login()
status,config,_=c.json('GET','/api/v1/auths/admin/config')
assert status==200
config={k:v for k,v in config.items() if v is not None}
config.update(ENABLE_MFA=True,MFA_ALLOW_OAUTH_BYPASS=False,MFA_ALLOW_TRUSTED_HEADER_BYPASS=False,
    ENABLE_SIGNUP=False,ENABLE_API_KEYS=False,ENABLE_COMMUNITY_SHARING=False,
    ENABLE_USER_WEBHOOKS=False,ENABLE_CHANNELS=False,ENABLE_ENCRYPTED_CHANNELS=False,
    ENABLE_APPS=False,ENABLE_CALENDAR=False,ENABLE_MEMORIES=False,ENABLE_NOTES=False,
    ENABLE_AUTOMATIONS=False)
status,_,_=c.json('POST','/api/v1/auths/admin/config',config)
if status!=200:raise SystemExit('Mandatory MFA enable failed with HTTP '+str(status))
status,_,_=c.json('GET','/api/v1/chats/')
if status not in (401,403):raise SystemExit('Enabling MFA did not revoke the previous session')
password=next(s.removeprefix('Hasło: ') for s in Path('/etc/private-chat/initial-login.txt').read_text().splitlines() if s.startswith('Hasło: '))
status,result,headers=c.json('POST','/api/v1/auths/signin',{'email':'admin@banas.dev','password':password},authenticated=False)
# Challenge response must never contain a full session token/cookie.
session_cookie=False
for name,value in headers:
    if name.lower()=='set-cookie':
        cookie=SimpleCookie(); cookie.load(value)
        session_cookie=session_cookie or bool(cookie.get('token') and cookie['token'].value)
report={'enabled':True,'old_session_revoked':True,'password_step_http':status,'next_step':result.get('next_step') if isinstance(result,dict) else None,'response_fields':list(result) if isinstance(result,dict) else [],'session_token_issued':bool(result.get('token')) if isinstance(result,dict) else None,'session_cookie_issued':session_cookie}
Path('/etc/private-chat/mfa-checks.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
if status!=200 or report['session_token_issued'] or report['session_cookie_issued']:
    raise SystemExit('Unexpected MFA password-step behavior; inspect without exposing challenge secrets.')
if not result.get('challenge_token') or report['next_step'] not in ('enroll','verify','recover'):
    raise SystemExit('MFA challenge missing')
c.token=result['challenge_token']
limited,_,_=c.json('GET','/api/v1/chats/')
report['challenge_cannot_read_history']=limited in (401,403)
Path('/etc/private-chat/mfa-checks.json').write_text(json.dumps(report,indent=2))
if not report['challenge_cannot_read_history']:raise SystemExit('MFA challenge must not grant access')
print('Mandatory MFA is enabled. Owner must enroll their own authenticator and retain recovery codes.',flush=True)

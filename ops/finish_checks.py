#!/usr/bin/python3
import json
from pathlib import Path
import subprocess
import time
from client import Client

c=Client(); user,_=c.login()
report={'checks':[]}


def check(name,value,detail=None):
    report['checks'].append({'name':name,'passed':bool(value),'detail':detail})
    print(('PASS ' if value else 'FAIL ')+name+': '+str(detail),flush=True)
    Path('/etc/private-chat/final-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if not value:raise SystemExit(name)


chat_id=Path('/etc/private-chat/test-chat-id').read_text()
status,before,_=c.json('GET','/api/v1/chats/'+chat_id)
check('Baseline history present before restart',status==200 and len(before['chat']['history']['messages'])==2)
status,data,_=c.json('GET','/api/v1/chats/all')
if isinstance(data,str):rows=[json.loads(line) for line in data.splitlines() if line.strip()]
elif isinstance(data,dict):rows=[data]
else:rows=data
check('Conversation JSON export',status==200 and any(r.get('id')==chat_id for r in rows))
status,_,_=c.json('POST','/ollama/api/chat',{'model':'qwen3.5:9b','messages':[{'role':'user','content':'a'*6000}],'stream':False})
check('Oversized context rejected before GPU generation',status in (400,413),status)
connection,response=c.request('POST','/ollama/api/chat',{'model':'qwen3.5:9b','messages':[{'role':'user','content':'Ile to 2+2? Odpowiedz krótko.'}],'think':True,'stream':True,'options':{'num_predict':256}})
content,thinking=0,0
for line in iter(response.readline,b''):
    event=json.loads(line)
    if event.get('error'):raise SystemExit('Thinking provider error')
    message=event.get('message') or {}
    content+=len(message.get('content',''))
    thinking+=len(message.get('thinking',''))
connection.close()
check('Thinking returned separately from content',response.status==200 and thinking>0,{'thinking_characters':thinking,'answer_characters':content})
subprocess.run(['docker','compose','--project-directory','/opt/private-chat','--env-file','/etc/private-chat/app.env','up','-d','--force-recreate','--no-deps','--wait','--wait-timeout','240','webui'],check=True)
status,after,_=c.json('GET','/api/v1/chats/'+chat_id)
check('History survives recreation of application container',status==200 and before['chat']['history']==after['chat']['history'])
check('Existing session survives app restart with stable secret',status==200)
status,_,_=c.json('POST','/api/v1/users/'+user['id']+'/sessions/revoke',{})
check('Revoke all sessions accepted',status==200,status)
status,_,_=c.json('GET','/api/v1/chats/')
check('Revoked bearer token cannot read private history',status in (401,403),status)
c.login()
status,_,_=c.json('GET','/api/v1/chats/')
check('Login works after session revocation',status==200)
status,_,_=c.json('DELETE','/api/v1/chats/'+chat_id)
check('Delete conversation',status==200)
status,_,_=c.json('GET','/api/v1/chats/'+chat_id)
check('Deleted conversation inaccessible',status in (401,403,404),status)
print('Final authenticated checks finished before enabling mandatory MFA.',flush=True)

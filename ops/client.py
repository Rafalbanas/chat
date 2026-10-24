"""Local origin test client: valid TLS hostname, official Cloudflare Origin CA."""
import http.client
import json
from pathlib import Path
import socket
import ssl


class Client:
    def __init__(self):
        self.context = ssl.create_default_context(cafile='/tmp/private-chat-origin-ca.pem')
        self.token = None

    def request(self, method, path, body=None, authenticated=True, origin='https://chat.banas.dev'):
        connection = http.client.HTTPSConnection('chat.banas.dev', context=self.context, timeout=240)
        connection._create_connection = lambda address, *args, **kwargs: socket.create_connection(('127.0.0.1', 443), *args, **kwargs)
        headers = {'Origin': origin, 'Content-Type': 'application/json'}
        if authenticated and self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        connection.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers=headers)
        return connection, connection.getresponse()

    def json(self, method, path, body=None, **kwargs):
        connection, response = self.request(method, path, body, **kwargs)
        raw = response.read()
        status, headers = response.status, response.getheaders()
        connection.close()
        try:
            result = json.loads(raw)
        except ValueError:
            result = raw.decode(errors='replace')
        return status, result, headers

    def login(self):
        lines = Path('/etc/private-chat/initial-login.txt').read_text().splitlines()
        password = next(line.removeprefix('Hasło: ') for line in lines if line.startswith('Hasło: '))
        status, data, headers = self.json('POST', '/api/v1/auths/signin', {'email': 'admin@banas.dev', 'password': password}, authenticated=False)
        if status != 200 or not data.get('token'):
            raise RuntimeError('Login failed with HTTP ' + str(status))
        self.token = data['token']
        return data, headers

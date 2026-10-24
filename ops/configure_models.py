#!/usr/bin/python3
from client import Client

c = Client()
c.login()
for model, name, description in [
    ('qwen3.5:9b', 'Qwen 3.5 · codzienny (9B)', 'Szybki model codzienny. Bezpieczny kontekst 8192; tryb myślenia można zmienić w ustawieniach rozmowy.'),
    ('qwen3.8-27b-iq2s:latest', 'Qwen 3.8 · wymagające zadania (27B)', 'Większy model do trudniejszych zadań. Kontekst ograniczony do 8192; CV Tailor ma pierwszeństwo.'),
]:
    form = {
        'id': model, 'base_model_id': None, 'name': name,
        'meta': {'description': description, 'profile_image_url': '/static/favicon.svg', 'capabilities': {'vision': False, 'file_upload': False, 'web_search': False, 'image_generation': False, 'code_interpreter': False}},
        'params': {'num_ctx': 8192, 'num_predict': 1536},
        'access_grants': [], 'is_active': True,
    }
    from urllib.parse import quote
    status, _, _ = c.json('GET', '/api/v1/models/model?id=' + quote(model, safe=''))
    if status == 200:
        status, _, _ = c.json('POST', '/api/v1/models/model/update?id=' + quote(model, safe=''), form)
    else:
        status, _, _ = c.json('POST', '/api/v1/models/create', form)
    if status != 200:
        raise SystemExit('Model preset configuration failed: HTTP ' + str(status))
    print('PASS model preset ' + model)

import asyncio
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

spec = importlib.util.spec_from_file_location('gateway', Path(__file__).parents[1] / 'config/gateway.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class Policy(unittest.TestCase):
    def body(self):
        return {'model': 'qwen3.8-27b-iq2s', 'messages': [{'role': 'user', 'content': 'Cześć'}]}

    def test_clamps_context_and_output(self):
        body = self.body()
        body['options'] = {'num_ctx': 262144, 'num_predict': -1, 'num_gpu': 999}
        result = g.prepare(body)
        self.assertEqual(result['model'], 'qwen3.8-27b-iq2s:latest')
        self.assertEqual(result['options'], {'num_ctx': 8192, 'num_predict': 1536})

    def test_rejects_oversize_without_truncating_history(self):
        body = self.body()
        body['messages'][0]['content'] = 'ą' * 3000
        with self.assertRaises(web.HTTPRequestEntityTooLarge):
            g.prepare(body)
        self.assertEqual(len(body['messages'][0]['content']), 3000)

    def test_rejects_other_models_and_images(self):
        body = self.body()
        body['model'] = 'gpt-oss:20b'
        with self.assertRaises(web.HTTPBadRequest):
            g.prepare(body)
        body = self.body()
        body['messages'][0]['images'] = ['abc']
        with self.assertRaises(web.HTTPBadRequest):
            g.prepare(body)


class Integration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = g.STATUS
        g.STATUS = Path(self.temp.name) / 'gpu.json'
        self.state(False)
        self.hold = asyncio.Event()
        self.arrived = asyncio.Event()

        async def fake(request):
            data = await request.json()
            self.arrived.set()
            await self.hold.wait()
            if data['messages'][0]['content']=='thinking-only':
                return web.json_response({'message': {'thinking': 'Test'}, 'done': True, 'done_reason': 'length'})
            return web.json_response({'message': {'content': 'Odpowiedź', 'thinking': 'Test'}, 'done': True})

        upstream = web.Application()
        upstream.router.add_post('/api/chat', fake)
        self.upstream = TestServer(upstream)
        await self.upstream.start_server()
        g.UPSTREAM = str(self.upstream.make_url('')).rstrip('/')
        self.client = TestClient(TestServer(g.make_app()))
        await self.client.start_server()

    def state(self, busy):
        g.STATUS.write_text(json.dumps({'at': time.time(), 'busy': busy}))

    def payload(self):
        return {'model': 'qwen3.5:9b', 'messages': [{'role': 'user', 'content': 'Cześć'}], 'stream': False}

    async def asyncTearDown(self):
        self.hold.set()
        await self.client.close()
        await self.upstream.close()
        g.STATUS = self.previous
        self.temp.cleanup()

    async def test_cv_busy_refuses_generation(self):
        self.state(True)
        response = await self.client.post('/api/chat', json=self.payload())
        self.assertEqual(response.status, 503)
        self.assertFalse(self.arrived.is_set())

    async def test_single_generation_and_separate_thinking(self):
        first = asyncio.create_task(self.client.post('/api/chat', json=self.payload()))
        await asyncio.wait_for(self.arrived.wait(), 3)
        second = await self.client.post('/api/chat', json=self.payload())
        self.assertEqual(second.status, 503)
        self.hold.set()
        response = await first
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())['message'], {'content': 'Odpowiedź', 'thinking': 'Test'})

    async def test_cv_priority_interrupts_pending_request(self):
        first = asyncio.create_task(self.client.post('/api/chat', json=self.payload()))
        await asyncio.wait_for(self.arrived.wait(), 3)
        self.state(True)
        response = await asyncio.wait_for(first, 3)
        self.assertEqual(response.status, 503)
        self.assertFalse(self.client.server.app['active'])

    async def test_stale_monitor_fails_closed_and_mutations_denied(self):
        g.STATUS.write_text(json.dumps({'at': time.time() - 10, 'busy': False}))
        response = await self.client.post('/api/chat', json=self.payload())
        self.assertEqual(response.status, 503)
        for path in ('/api/pull', '/api/delete', '/api/create', '/api/generate'):
            response = await self.client.post(path, json={})
            self.assertEqual(response.status, 404)

    async def test_thinking_budget_error_preserves_separate_field(self):
        self.hold.set()
        payload=self.payload()
        payload['stream']=True
        payload['messages'][0]['content']='thinking-only'
        response=await self.client.post('/api/chat',json=payload)
        event=json.loads(await response.text())
        self.assertEqual(event['message'],{'thinking':'Test'})
        self.assertEqual(event['error'],g.THINKING_LIMIT)

"""Test ASGI app"""
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
import django
django.setup()

import json, asyncio
from channels.testing import HttpCommunicator
from core.asgi import application

async def test():
    comm = HttpCommunicator(application, 'GET', '/api/health', headers=[
        (b'host', b'test.ikavisite.com'),
        (b'x-forwarded-proto', b'https'),
    ])
    response = await comm.get_response()
    print(f"Status: {response['status']}")
    print(f"Body: {response['body'].decode()}")

asyncio.run(test())

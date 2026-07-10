"""Debug the actual 500 error by catching it before the handler"""
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
os.environ['DJANGO_DEBUG'] = 'True'

from django.conf import settings
settings.DEBUG = True

import django
django.setup()

from django.test import RequestFactory
from django.urls import resolve
from core import urls as urlconf

# Also reset the handler500
from django.views import debug

factory = RequestFactory()
request = factory.get('/api/health', HTTP_HOST='test.ikavisite.com', HTTP_X_FORWARDED_PROTO='https')

match = resolve('/api/health', urlconf)
print(f"Handler: {match.func}")

try:
    response = match.func(request, **match.kwargs)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.content}")
except Exception as e:
    import traceback, sys
    print(f"Exception: {e}")
    traceback.print_exc(file=sys.stdout)

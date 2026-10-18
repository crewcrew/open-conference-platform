import subprocess
import sys
from unittest import TestCase


class HostingProbeTests(TestCase):
    def test_production_internal_probe_and_https_boundary(self):
        from .test_production import ProductionConfigTests

        environment = ProductionConfigTests().environment(
            OCP_ALLOWED_HOSTS="api.example.com,healthcheck.railway.app",
        )
        script = '''
import django
django.setup()
from django.test import Client
client = Client()
response = client.get('/health/live/', HTTP_HOST='healthcheck.railway.app')
assert response.status_code == 200, response.status_code
assert response.json() == {'status': 'ok'}
for path in ['/api/v1/session/', '/accounts/login/', '/health/live/extra/']:
    response = client.get(path, HTTP_HOST='api.example.com')
    assert response.status_code == 301, (path, response.status_code)
    assert response['Location'] == 'https://api.example.com' + path
'''
        result = subprocess.run([sys.executable, "-c", script], env=environment,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

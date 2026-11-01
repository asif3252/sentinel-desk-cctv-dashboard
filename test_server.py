import json
import io
from http.client import HTTPResponse
from types import SimpleNamespace
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import server


class DashboardTests(unittest.TestCase):
    def request(self, path, data=None, token=server.TOKEN, origin=None, host='127.0.0.1:8765'):
        headers = {'Host':host, 'X-Session-Token':token}
        if origin:
            headers['Origin'] = origin
        payload = json.dumps(data).encode() if data is not None else b''
        headers['Content-Length'] = str(len(payload))
        raw = (('POST' if data is not None else 'GET')+' '+path+' HTTP/1.0\r\n'+''.join(f'{k}: {v}\r\n' for k,v in headers.items())+'\r\n').encode()+payload
        class MemorySocket:
            def __init__(self, content):
                self.content, self.output = content, bytearray()
            def makefile(self, *args, **kwargs):
                return io.BytesIO(self.content)
            def sendall(self, data):
                self.output.extend(data)
        transport = MemorySocket(raw)
        server.Handler(transport, ('127.0.0.1',12345), SimpleNamespace(server_name='localhost',server_port=8765))
        response = HTTPResponse(MemorySocket(bytes(transport.output)))
        response.begin()
        if response.status >= 400:
            raise HTTPError(path,response.status,response.reason,response.headers,response)
        return response

    def test_config_does_not_expose_credentials(self):
        self.request('/api/config', {'host':'192.168.1.100','port':554,'channels':25,'username':'test-user','password':'test-secret'}).close()
        with self.request('/api/state') as response:
            result = response.read().decode()
        self.assertNotIn('test-secret',result)
        self.assertNotIn('test-user',result)
        self.assertEqual(json.loads(result)['recorder']['channels'],25)

    def test_cross_origin_and_invalid_token_rejected(self):
        for kwargs in [{'token':'wrong'}, {'origin':'https://example.org'}]:
            with self.assertRaises(HTTPError) as caught:
                self.request('/api/stop',{},**kwargs)
            self.assertEqual(caught.exception.code,403)

    def test_rebinding_and_file_traversal_rejected(self):
        with self.assertRaises(HTTPError) as caught:
            self.request('/api/state',host='evil.example:8765')
        self.assertEqual(caught.exception.code,403)
        with self.assertRaises(HTTPError) as caught:
            self.request('/../server.py')
        self.assertEqual(caught.exception.code,404)

    def test_configuration_validation(self):
        for host in ['http://192.168.1.100','127.0.0.1','0.0.0.0','224.0.0.1','not-an-ip']:
            with self.assertRaises(ValueError):
                server.validate_config({'host':host,'username':'u','password':'p'})

    def test_rules_continuity_cooldown_and_identity(self):
        rules = server.Rules(2,10)
        self.assertEqual(rules.update(0,{1}),[])
        self.assertEqual([e[1] for e in rules.update(2,{1})],['intrusion'])
        self.assertEqual([e[1] for e in rules.update(10,{1})],['loitering'])
        self.assertEqual(rules.update(11,{1}),[])
        self.assertEqual(rules.update(12,{2}),[])
        rules.update(13,set())
        self.assertEqual(rules.update(14,{1}),[])

    def test_dashboard_serves_without_detection_packages(self):
        with self.request('/') as response:
            self.assertIn(b'SENTINEL',response.read())
        with self.request('/api/export') as response:
            self.assertIn(b'acknowledged',response.read())


if __name__ == '__main__':
    unittest.main()

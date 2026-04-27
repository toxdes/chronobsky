import json
import urllib.request
import urllib.error
import urllib.parse


class Client:
    def __init__(self, pds_url):
        self.pds_url = pds_url.rstrip('/')
        self.token = None

    def set_token(self, token):
        self.token = token

    def _headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def _request(self, method, endpoint, data=None, params=None):
        url = f'{self.pds_url}/xrpc/{endpoint}'
        if params:
            url += '?' + urllib.parse.urlencode(params)
        body = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=body, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            raise HTTPError(e.code, e.read().decode('utf-8'))

    def get(self, endpoint, params=None):
        return self._request('GET', endpoint, params=params)

    def post(self, endpoint, data):
        return self._request('POST', endpoint, data=data)


class HTTPError(Exception):
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body
        super().__init__(f'HTTP {status_code}: {body}')

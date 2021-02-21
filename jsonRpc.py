import base64
import json
import random

import requests


class JsonRpc:
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password

    def call(self, method: str, **kwargs):
        data = {
            'jsonrpc': '2.0',
            'method': method,
            'id': random.randint(0, 1000000000000),
            'params': kwargs
        }

        headers = {
            'X-API-Auth': base64.b64encode(bytes(self.username+':'+self.password, 'utf-8'))
        }

        r = requests.post(url=self.url, json=data, headers=headers)

        # print(r.text)

        response = json.loads(r.text)

        if 'error' in response:
            raise BaseException(r.text)

        return response['result']

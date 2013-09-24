import json
import requests

r = requests.post(
    "http://127.0.0.1:5000/login/",
    headers={'content-type': 'application/json'},
    data=json.dumps({"username": "agent", "password": "agent"}))
print r.text

r = requests.post(
     "http://127.0.0.1:5000/login/",
     headers={'content-type': 'application/json'},
     data=json.dumps({"login": "test", "password": "test"}))
print r.text
print r.cookies

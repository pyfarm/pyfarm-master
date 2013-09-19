import json
import requests

print "logging in.."
r = requests.post(
    "http://127.0.0.1:5000/login",
    headers={'content-type': 'application/json'},
    data=json.dumps({"email": "test", "password": "test"}))

authentication_token = r.json()["response"]["user"]["authentication_token"]
print "Authentication-Token: %s" % authentication_token

# try with the token
print "testing WITH auth token..."
r = requests.get(
    "http://127.0.0.1:5000/test",
    headers={"Authentication-Token": authentication_token})
print r.text

# and try without
print "testing WITHOUT auth token..."
r = requests.get("http://127.0.0.1:5000/test")
print r.text
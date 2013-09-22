import json
import requests


r = requests.post(
    "http://127.0.0.1:5000/login/",
    headers={'content-type': 'application/json'},
    data=json.dumps({"username": "agent", "password": "agent"}))
print r.text

# r = requests.post(
#     "http://127.0.0.1:5000/login/",
#     headers={'content-type': 'application/json'},
#     data=json.dumps({"login": "test", "password": "test"}))
print r.text
print r.cookies

print "==========="

None
# r = requests.get(
#     "http://127.0.0.1:5000/login",
#     headers={'content-type': 'application/json'},
#     data=json.dumps({"username": "agent", "password": "agent"}))
# print r.text
#
# cookie = r.headers["set-cookie"]
# headers = {"set-cookie": cookie}
# r = requests.get("http://127.0.0.1:5000/", cookies=r.cookies)
# print r.text
# print "==========="
# # r = requests.get("http://127.0.0.1:5000/admin/", cookies=r.cookies)
# # print r.text
# # # print r.text
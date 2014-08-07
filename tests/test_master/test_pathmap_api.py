# No shebang line, this module is meant to be imported
#
# Copyright 2013 Oliver Palmer
# Copyright 2014 Ambient Entertainment GmbH & Co. KG
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from json import dumps


# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.master.application import get_api_blueprint
from pyfarm.master.entrypoints import load_api
from pyfarm.models.pathmap import PathMap


class TestPathMapAPI(BaseTestCase):
    def setup_app(self):
        super(TestPathMapAPI, self).setup_app()
        self.api = get_api_blueprint()
        self.app.register_blueprint(self.api)
        load_api(self.app, self.api)

    def test_pathmap_schema(self):
        response = self.client.get("/api/v1/pathmaps/schema")
        self.assert_ok(response)
        schema = PathMap.to_schema()
        schema["tag"] = "VARCHAR(64)"
        del schema["tag_id"]
        self.assertEqual(response.json, schema)

    def test_pathmap_post(self):
        response1 = self.client.post(
            "/api/v1/pathmaps/",
            content_type="application/json",
            data=dumps({"path_linux": "/test",
                        "path_windows": "c:\\test",
                        "path_osx": "/test",
                        "tag": "testtag"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.get("/api/v1/pathmaps/%s" % id)
        self.assert_ok(response2)
        self.assertEqual(
            response2.json, {
                "id": id,
                "path_linux": "/test",
                "path_windows": "c:\\test",
                "path_osx": "/test",
                "tag": "testtag"})

    def test_pathmap_post_bad_tag(self):
        response1 = self.client.post(
            "/api/v1/pathmaps/",
            content_type="application/json",
            data=dumps({"path_linux": "/test",
                        "path_windows": "c:\\test",
                        "path_osx": "/test",
                        "tag": 1.0}))
        self.assert_bad_request(response1)

    def test_pathmap_list(self):
        response1 = self.client.post(
            "/api/v1/pathmaps/",
            content_type="application/json",
            data=dumps({"path_linux": "/test",
                        "path_windows": "c:\\test",
                        "path_osx": "/test",
                        "tag": "testtag1"}))
        self.assert_created(response1)
        id1 = response1.json['id']
        response2 = self.client.post(
            "/api/v1/pathmaps/",
            content_type="application/json",
            data=dumps({"path_linux": "/test2",
                        "path_windows": "c:\\test2",
                        "path_osx": "/test2",
                        "tag": "testtag2"}))
        self.assert_created(response2)
        id2 = response2.json['id']
        response3 = self.client.post(
            "/api/v1/pathmaps/",
            content_type="application/json",
            data=dumps({"path_linux": "/test3",
                        "path_windows": "c:\\test3",
                        "path_osx": "/test3"}))
        self.assert_created(response3)
        id3 = response3.json['id']

        response4 = self.client.post(
            "/api/v1/agents/",
            content_type="application/json",
            data=dumps({
                "systemid": 42,
                "cpus": 16,
                "free_ram": 133,
                "hostname": "testagent1",
                "remote_ip": "10.0.200.1",
                "port": 64994,
                "ram": 2048}))
        self.assert_created(response4)
        agent_id = response4.json["id"]

        response5 = self.client.post(
            "/api/v1/tags/testtag1/agents/",
            content_type="application/json",
            data=dumps({"agent_id": agent_id}))
        self.assert_created(response5)

        response6 = self.client.get("/api/v1/pathmaps/?for_agent=%s" % agent_id)
        self.assert_ok(response6)
        self.assertEqual(
            response6.json,
                [
                    {
                        "id": id1,
                        "path_linux": "/test",
                        "path_windows": "c:\\test",
                        "path_osx": "/test",
                        "tag": "testtag1"
                    },
                    {
                        "id": id3,
                        "path_linux": "/test3",
                        "path_windows": "c:\\test3",
                        "path_osx": "/test3"
                    }
                ])

    def test_pathmap_get_unknown(self):
        response1 = self.client.get("/api/v1/pathmaps/10")
        self.assert_not_found(response1)

    def test_pathmap_edit(self):
        response1 = self.client.post(
            "/api/v1/pathmaps/",
            content_type="application/json",
            data=dumps({"path_linux": "/test",
                        "path_windows": "c:\\test",
                        "path_osx": "/test",
                        "tag": "testtag"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.post(
            "/api/v1/pathmaps/%s" % id,
            content_type="application/json",
            data=dumps({"path_linux": "/test2",
                        "tag": "newtag"}))
        self.assert_ok(response2)
        self.assertEqual(response2.json,
                         {"id": id,
                          "path_linux": "/test2",
                          "path_windows": "c:\\test",
                          "path_osx": "/test",
                          "tag": "newtag"})

    def test_pathmap_edit_id(self):
        response1 = self.client.post(
            "/api/v1/pathmaps/",
            content_type="application/json",
            data=dumps({"path_linux": "/test",
                        "path_windows": "c:\\test",
                        "path_osx": "/test",
                        "tag": "testtag"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.post(
            "/api/v1/pathmaps/%s" % id,
            content_type="application/json",
            data=dumps({"id": 42}))
        self.assert_bad_request(response2)

    def test_pathmap_edit_unknown(self):
        response1 = self.client.post(
            "/api/v1/pathmaps/42",
            content_type="application/json",
            data=dumps({"path_linux": "/test2"}))
        self.assert_not_found(response1)

    def test_pathmap_edit_bad_col_type(self):
        response1 = self.client.post(
            "/api/v1/pathmaps/",
            content_type="application/json",
            data=dumps({"path_linux": "/test",
                        "path_windows": "c:\\test",
                        "path_osx": "/test",
                        "tag": "testtag"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.post(
            "/api/v1/pathmaps/%s" % id,
            content_type="application/json",
            data=dumps({"path_linux": 1.0}))
        self.assert_bad_request(response2)

    def test_pathmap_edit_bad_col(self):
        response1 = self.client.post(
            "/api/v1/pathmaps/",
            content_type="application/json",
            data=dumps({"path_linux": "/test",
                        "path_windows": "c:\\test",
                        "path_osx": "/test",
                        "tag": "testtag"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.post(
            "/api/v1/pathmaps/%s" % id,
            content_type="application/json",
            data=dumps({"unknown_key": 1.0}))
        self.assert_bad_request(response2)

    def test_pathmap_delete(self):
        response1 = self.client.post(
            "/api/v1/pathmaps/",
            content_type="application/json",
            data=dumps({"path_linux": "/test",
                        "path_windows": "c:\\test",
                        "path_osx": "/test",
                        "tag": "testtag"}))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.delete("/api/v1/pathmaps/%s" % id)
        self.assert_no_content(response2)

        response3 = self.client.get("/api/v1/pathmaps/%s" % id)
        self.assert_not_found(response3)

    def test_pathmap_delete_unknown(self):
        response1 = self.client.delete("/api/v1/pathmaps/42")
        self.assert_no_content(response1)

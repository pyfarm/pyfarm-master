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


try:
    from httplib import CREATED, NO_CONTENT
except ImportError:
    from http.client import CREATED, NO_CONTENT

# test class must be loaded first
from pyfarm.master.testutil import BaseTestCase
BaseTestCase.build_environment()

from pyfarm.master.application import get_api_blueprint
from pyfarm.master.entrypoints import load_api
from pyfarm.models.software import Software


class TestSoftwareAPI(BaseTestCase):
    def setup_app(self):
        super(TestSoftwareAPI, self).setup_app()
        self.api = get_api_blueprint()
        self.app.register_blueprint(self.api)
        load_api(self.app, self.api)

    def test_software_schema(self):
        response = self.client.get("/api/v1/software/schema")
        self.assert_ok(response)
        self.assertEqual(response.json, Software.to_schema())

    def test_software_post(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {"version": "1.0"}
                            ]
                       }))
        self.assert_created(response1)
        id = response1.json['id']
        version_id = response1.json["versions"][0]["id"]

        response2 = self.client.get("/api/v1/software/%d" % id)
        self.assert_ok(response2)
        self.assertEqual(
            response2.json, {
                            "id": id,
                            "software": "foo", 
                            "versions": [
                                    {
                                    "id": version_id,
                                    "rank": 100,
                                    "version": "1.0"
                                    }
                                ]
                            })

    def test_software_post_bad_version(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {
                                        "version": 1,
                                        "bad_key": "bla"
                                    }
                            ]
                       }))
        self.assert_bad_request(response1)

    def test_software_post_duplicate_version_rank(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {
                                        "version": "1.0",
                                        "rank": 100
                                    },
                                    {
                                        "version": "1.1",
                                        "rank": 100
                                    }
                            ]
                       }))
        # Note, this should ideally return BAD_REQUEST, but SQLAlchemy does not
        # allow us to reliably tell a unique constraint violation from any other
        # database error.
        self.assert_internal_server_error(response1)

    def test_software_post_not_json(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="something/else",
            data="software=foo")
        self.assert_unsupported_media_type(response1)

    def test_software_post_existing(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                "software": "foo"}))
        self.assert_created(response1)

        response2 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                            {"version": "1.0"}
                        ]
                       }))
        self.assert_conflict(response2)

    def test_software_put(self):
        response1 = self.client.put(
            "/api/v1/software/foo",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                {"version": "1.0"}
                            ]
                       }))
        self.assert_created(response1)

        # Must be idempotent
        response2 = self.client.put(
            "/api/v1/software/foo",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                {"version": "1.0"}
                            ]
                       }))
        self.assert_ok(response2)
        id = response2.json['id']
        version_id = response2.json["versions"][0]["id"]

        response3 = self.client.get("/api/v1/software/foo")
        self.assert_ok(response3)
        self.assertEqual(
            response3.json, {
                            "id": id,
                            "software": "foo", 
                            "versions": [
                                    {
                                    "id": version_id,
                                    "rank": 100,
                                    "version": "1.0"
                                    }
                                ]
                            })

    def test_software_delete(self):
        response1 = self.client.put(
            "/api/v1/software/foo",
            content_type="application/json",
            data=dumps({
                "software": "foo"}))
        self.assert_created(response1)

        response2 = self.client.delete("/api/v1/software/foo")
        self.assert_no_content(response2)

        response3 = self.client.get("/api/v1/software/foo")
        self.assert_not_found(response3)

        # Must be idempotent
        response4 = self.client.delete("/api/v1/software/foo")
        self.assert_no_content(response4)

        response5 = self.client.get("/api/v1/software/foo")
        self.assert_not_found(response5)

    def test_software_update(self):
        response1 = self.client.put(
            "/api/v1/software/foo",
            content_type="application/json",
            data=dumps({
                "software": "foo"}))
        self.assert_created(response1)

    def test_software_post_version(self):
        response1 = self.client.put(
            "/api/v1/software/foo",
            content_type="application/json",
            data=dumps({
                "software": "foo"}))
        self.assert_created(response1)
        id = response1.json["id"]

        response2 = self.client.post(
            "/api/v1/software/foo/versions/",
            content_type="application/json",
            data=dumps({"version": "1.0"}))
        self.assert_created(response2)
        version_id = response2.json["id"]

        response3 = self.client.get("/api/v1/software/foo")
        self.assert_ok(response3)
        self.assertEqual(
            response3.json, {
                            "id": id,
                            "software": "foo", 
                            "versions": [
                                {
                                    "id": version_id,
                                    "rank": 100,
                                    "version": "1.0"
                                }
                            ]
                            })

    def test_software_get_versions(self):
        response1 = self.client.put(
            "/api/v1/software/foo",
            content_type="application/json",
            data=dumps({
                "software": "foo",
                            "versions": [
                                {"version": "1.0"},
                                {"version": "1.1"}
                            ]
                       }))
        self.assert_created(response1)
        version1_id = response1.json["versions"][0]["id"]
        version2_id = response1.json["versions"][1]["id"]

        response2 = self.client.get("/api/v1/software/foo/versions/")
        self.assert_ok(response2)
        self.assertEqual(
            response2.json, [
                                {
                                    "version": "1.0",
                                    "id": version1_id,
                                    "rank": 100
                                },
                                {
                                    "version": "1.1",
                                    "id": version2_id,
                                    "rank": 200
                                }
                            ])

    def test_software_delete_version(self):
        response1 = self.client.put(
            "/api/v1/software/foo",
            content_type="application/json",
            data=dumps({
                "software": "foo",
                "versions": [
                        {"version": "1.0"}
                    ]
                }))
        self.assert_created(response1)

        response2 = self.client.delete("/api/v1/software/foo/versions/1.0")
        self.assert_no_content(response2)

        response3 = self.client.get("/api/v1/software/foo/versions/1.0")
        self.assert_not_found(response3)

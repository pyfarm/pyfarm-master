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
from pyfarm.master.entrypoints.main import load_api
from pyfarm.models.jobtype import JobType, JobTypeVersion

code = """from pyfarm.jobtypes.core.jobtype import JobType

class TestJobType(JobType):
    def get_command(self):
        return "/usr/bin/touch"
    def get_arguments(self):
        return [os.path.join(
            self.assignment_data["job"]["data"]["path"],
            "%04d" % self.assignment_data[\"tasks\"][0][\"frame\"])]
"""

class TestJobTypeAPI(BaseTestCase):
    def setup_app(self):
        super(TestJobTypeAPI, self).setup_app()
        self.api = get_api_blueprint()
        self.app.register_blueprint(self.api)
        load_api(self.app, self.api)

    def test_jobtype_schema(self):
        response = self.client.get("/api/v1/jobtypes/schema")
        self.assert_ok(response)
        schema = JobType.to_schema()
        schema.update(JobTypeVersion.to_schema())
        self.assertEqual(response.json, schema)

    def test_jobtype_post(self):
        response1 = self.client.post(
            "/api/v1/jobtypes/",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.get("/api/v1/jobtypes/TestJobType")
        self.assert_ok(response2)
        self.assertEqual(
            response2.json, {
                "batch_contiguous": True,
                "classname": None,
                "code": code,
                "description": "Jobtype for testing inserts and queries",
                "id": id,
                "max_batch": 1,
                "name": "TestJobType",
                "software_requirements": [],
                "version": 1
                })

        response3 = self.client.get("/api/v1/jobtypes/%s" % id)
        self.assert_ok(response3)
        self.assertEqual(
            response3.json, {
                "batch_contiguous": True,
                "classname": None,
                "code": code,
                "description": "Jobtype for testing inserts and queries",
                "id": id,
                "max_batch": 1,
                "name": "TestJobType",
                "software_requirements": [],
                "version": 1
                })

    def test_jobtype_post_conflict(self):
        response1 = self.client.post(
            "/api/v1/jobtypes/",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)

        response2 = self.client.post(
            "/api/v1/jobtypes/",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_conflict(response2)

    def test_jobtypes_list(self):
        response1 = self.client.post(
            "/api/v1/jobtypes/",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "code": code
                    }))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.get("/api/v1/jobtypes/")
        self.assert_ok(response2)
        self.assertEqual(
            response2.json, [
                    {
                    "id": id,
                    "name": "TestJobType"
                    }
                ])

    def test_jobtype_post_with_no_name(self):
        response1 = self.client.post(
            "/api/v1/jobtypes/",
            content_type="application/json",
            data=dumps({
                    "description": "Jobtype for testing inserts and queries",
                    "code": code
                    }))
        self.assert_bad_request(response1)

    def test_jobtype_post_with_no_code(self):
        response1 = self.client.post(
            "/api/v1/jobtypes/",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries"
                    }))
        self.assert_bad_request(response1)

    def test_jobtype_post_with_additional_keys(self):
        response1 = self.client.post(
            "/api/v1/jobtypes/",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "code": code,
                    "unknown_key": 42
                    }))
        self.assert_bad_request(response1)

    def test_jobtype_get_unknown(self):
        response1 = self.client.get("/api/v1/jobtypes/unknown_jobtype")
        self.assert_not_found(response1)

    def test_jobtype_put(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.get("/api/v1/jobtypes/TestJobType")
        self.assert_ok(response2)
        self.assertEqual(
            response2.json, {
                "batch_contiguous": True,
                "classname": None,
                "code": code,
                "description": "Jobtype for testing inserts and queries",
                "id": id,
                "max_batch": 1,
                "name": "TestJobType",
                "software_requirements": [],
                "version": 1
                })

    def test_jobtype_put_overwrite(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.put(
            "/api/v1/jobtypes/%s" % id,
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing (updated)",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response2)

        response3 = self.client.get("/api/v1/jobtypes/%s" % id)
        self.assert_ok(response3)
        self.assertEqual(
            response3.json, {
                "batch_contiguous": True,
                "classname": None,
                "code": code,
                "description": "Jobtype for testing (updated)",
                "id": id,
                "max_batch": 1,
                "name": "TestJobType",
                "software_requirements": [],
                "version": 2
                })

    def test_jobtype_put_unknown_keys(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "unknown_key": 42
                    }))
        self.assert_bad_request(response1)

    def test_jobtype_put_with_no_name(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "unknown_key": 42
                    }))
        self.assert_bad_request(response1)

    def test_jobtype_put_with_requirements(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {"version": "1.0"},
                                    {"version": "1.1"}
                            ]
                       }))
        self.assert_created(response1)
        software_id = response1.json['id']
        software_min_version_id = response1.json["versions"][0]["id"]
        software_max_version_id = response1.json["versions"][1]["id"]

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {
                            "software": "foo",
                            "min_version": "1.0",
                            "max_version": "1.1"
                        }
                        ]
                    }))
        self.assert_created(response2)
        id = response2.json['id']

        response3 = self.client.get("/api/v1/jobtypes/TestJobType")
        self.assert_ok(response3)
        self.assertEqual(
            response3.json, {
                "batch_contiguous": True,
                "classname": None,
                "code": code,
                "description": "Jobtype for testing inserts and queries",
                "id": id,
                "max_batch": 1,
                "name": "TestJobType",
                "software_requirements": [
                    {
                        'max_version': '1.1',
                        'max_version_id': software_max_version_id,
                        'min_version': '1.0',
                        'min_version_id': software_min_version_id,
                        'software': 'foo',
                        'software_id': software_id
                    }
                    ],
                "version": 1
                })

    def test_jobtype_put_with_requirements_not_list(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": 42
                    }))
        self.assert_bad_request(response1)

    def test_jobtype_put_with_requirement_not_dict(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [42]
                    }))
        self.assert_bad_request(response1)

    def test_jobtype_put_with_requirement_unknown_software(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {
                            "software": "foo",
                            "min_version": "1.0",
                            "max_version": "1.1"
                        }
                        ]
                    }))
        self.assert_not_found(response1)

    def test_jobtype_put_with_requirements_unknown_sw_version(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo"
                       }))
        self.assert_created(response1)

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {
                            "software": "foo",
                            "min_version": "1.1"
                        }
                        ]
                    }))
        self.assert_not_found(response2)

        response3 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {
                            "software": "foo",
                            "max_version": "1.1"
                        }
                        ]
                    }))
        self.assert_not_found(response3)

    def test_jobtype_put_with_requirements_unknown_keys(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo"
                       }))
        self.assert_created(response1)

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {
                            "software": "foo",
                            "unknown_key": 42
                        }
                        ]
                    }))
        self.assert_bad_request(response2)

    def test_jobtype_put_with_requirements_missing_keys(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {}
                        ]
                    }))
        self.assert_bad_request(response1)

    def test_jobtype_put_retain_requirements(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {"version": "1.0"},
                                    {"version": "1.1"}
                            ]
                       }))
        self.assert_created(response1)
        software_id = response1.json['id']
        software_min_version_id = response1.json["versions"][0]["id"]
        software_max_version_id = response1.json["versions"][1]["id"]

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {
                            "software": "foo",
                            "min_version": "1.0",
                            "max_version": "1.1"
                        }
                        ]
                    }))
        self.assert_created(response2)
        id = response2.json['id']

        response3 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing (updated)",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response3)

        response4 = self.client.get("/api/v1/jobtypes/TestJobType")
        self.assert_ok(response4)
        self.assertEqual(
            response4.json, {
                "batch_contiguous": True,
                "classname": None,
                "code": code,
                "description": "Jobtype for testing (updated)",
                "id": id,
                "max_batch": 1,
                "name": "TestJobType",
                "software_requirements": [
                    {
                        'max_version': '1.1',
                        'max_version_id': software_max_version_id,
                        'min_version': '1.0',
                        'min_version_id': software_min_version_id,
                        'software': 'foo',
                        'software_id': software_id
                    }
                    ],
                "version": 2
                })

    def test_jobtype_delete(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {"version": "1.0"},
                                    {"version": "1.1"}
                            ]
                       }))
        self.assert_created(response1)

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {
                            "software": "foo",
                            "min_version": "1.0",
                            "max_version": "1.1"
                        }
                        ]
                    }))
        self.assert_created(response2)
        id = response2.json['id']

        response3 = self.client.delete("/api/v1/jobtypes/TestJobType")
        self.assert_no_content(response3)

        response4 = self.client.get("/api/v1/jobtypes/TestJobType")
        self.assert_not_found(response4)

        response5 = self.client.get("/api/v1/jobtypes/%s" % id)
        self.assert_not_found(response5)

    def test_jobtype_delete_by_id(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {"version": "1.0"},
                                    {"version": "1.1"}
                            ]
                       }))
        self.assert_created(response1)

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {
                            "software": "foo",
                            "min_version": "1.0",
                            "max_version": "1.1"
                        }
                        ]
                    }))
        self.assert_created(response2)
        id = response2.json['id']

        response3 = self.client.delete("/api/v1/jobtypes/%s" % id)
        self.assert_no_content(response3)

        response4 = self.client.get("/api/v1/jobtypes/TestJobType")
        self.assert_not_found(response4)

        response5 = self.client.get("/api/v1/jobtypes/%s" % id)
        self.assert_not_found(response5)

    def test_jobtype_get_versioned(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": []
                    }))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 2,
                    "code": code,
                    "software_requirements": []
                    }))
        self.assert_created(response2)
        id = response2.json['id']

        response3 = self.client.get("/api/v1/jobtypes/TestJobType/versions/1")
        self.assert_ok(response3)
        self.assertEqual(
            response3.json, {
                "batch_contiguous": True,
                "classname": None,
                "code": code,
                "description": "Jobtype for testing inserts and queries",
                "id": id,
                "max_batch": 1,
                "name": "TestJobType",
                "software_requirements": [],
                "version": 1
                })

        response4 = self.client.get("/api/v1/jobtypes/%s/versions/1" % id)
        self.assert_ok(response4)
        self.assertEqual(
            response4.json, {
                "batch_contiguous": True,
                "classname": None,
                "code": code,
                "description": "Jobtype for testing inserts and queries",
                "id": id,
                "max_batch": 1,
                "name": "TestJobType",
                "software_requirements": [],
                "version": 1
                })

        response5 = self.client.get("/api/v1/jobtypes/%s/versions/2" % id)
        self.assert_ok(response5)
        self.assertEqual(
            response5.json, {
                "batch_contiguous": True,
                "classname": None,
                "code": code,
                "description": "Jobtype for testing inserts and queries",
                "id": id,
                "max_batch": 2,
                "name": "TestJobType",
                "software_requirements": [],
                "version": 2
                })

    def test_jobtype_get_unknown_version(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": []
                    }))
        self.assert_created(response1)

        response2 = self.client.get("/api/v1/jobtypes/TestJobType/versions/42")
        self.assert_not_found(response2)

    def test_jobtype_delete_version(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": []
                    }))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 2,
                    "code": code,
                    "software_requirements": []
                    }))
        self.assert_created(response2)

        response3 = self.client.delete("/api/v1/jobtypes/TestJobType/versions/2")
        self.assert_no_content(response3)

        response4 = self.client.get("/api/v1/jobtypes/TestJobType/versions/2")
        self.assert_not_found(response4)

        response5 = self.client.get("/api/v1/jobtypes/TestJobType")
        self.assert_ok(response5)
        self.assertEqual(
            response5.json, {
                "batch_contiguous": True,
                "classname": None,
                "code": code,
                "description": "Jobtype for testing inserts and queries",
                "id": id,
                "max_batch": 1,
                "name": "TestJobType",
                "software_requirements": [],
                "version": 1
                })

    def test_jobtype_by_id_delete_version(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": []
                    }))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 2,
                    "code": code,
                    "software_requirements": []
                    }))
        self.assert_created(response2)

        response3 = self.client.delete("/api/v1/jobtypes/%s/versions/2" % id)
        self.assert_no_content(response3)

        response4 = self.client.get("/api/v1/jobtypes/TestJobType/versions/2")
        self.assert_not_found(response4)

        response5 = self.client.get("/api/v1/jobtypes/TestJobType")
        self.assert_ok(response5)
        self.assertEqual(
            response5.json, {
                "batch_contiguous": True,
                "classname": None,
                "code": code,
                "description": "Jobtype for testing inserts and queries",
                "id": id,
                "max_batch": 1,
                "name": "TestJobType",
                "software_requirements": [],
                "version": 1
                })

    def test_jobtype_get_code(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": []
                    }))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.get(
            "/api/v1/jobtypes/TestJobType/versions/1/code")
        self.assert_ok(response2)
        self.assertEqual(response2.data.decode(), code)

        response3 = self.client.get(
            "/api/v1/jobtypes/%s/versions/1/code" % id)
        self.assert_ok(response3)
        self.assertEqual(response3.data.decode(), code)

    def test_jobtype_get_code_not_found(self):
        response1 = self.client.get(
            "/api/v1/jobtypes/UnknownJobType/versions/1/code")
        self.assert_not_found(response1)

    def test_jobtype_list_requirements(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {"version": "1.0"},
                                    {"version": "1.1"}
                            ]
                       }))
        self.assert_created(response1)
        software_id = response1.json['id']
        software_min_version_id = response1.json["versions"][0]["id"]
        software_max_version_id = response1.json["versions"][1]["id"]

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {
                            "software": "foo",
                            "min_version": "1.0",
                            "max_version": "1.1"
                        }
                        ]
                    }))
        self.assert_created(response2)
        id = response2.json['id']

        response3 = self.client.get(
            "/api/v1/jobtypes/TestJobType/software_requirements/")
        self.assert_ok(response3)
        self.assertEqual(response3.json, [
                {
                    "software": {
                        "software": "foo",
                        "id": software_id
                        },
                    "max_version": {
                        "version": "1.1",
                        "id": software_max_version_id
                        },
                    "min_version": {
                        "version": "1.0",
                        "id": software_min_version_id
                        },
                    "jobtype_version": {
                        "version": 1,
                        "jobtype": "TestJobType",
                        }
                }
                ])

        response4 = self.client.get(
            "/api/v1/jobtypes/%s/versions/1/software_requirements/" % id)
        self.assert_ok(response4)
        self.assertEqual(response4.json, [
                {
                    "software": {
                        "software": "foo",
                        "id": software_id
                        },
                    "max_version": {
                        "version": "1.1",
                        "id": software_max_version_id
                        },
                    "min_version": {
                        "version": "1.0",
                        "id": software_min_version_id
                        },
                    "jobtype_version": {
                        "version": 1,
                        "jobtype": "TestJobType",
                        }
                }
                ])

    def test_jobtype_list_requirements_unknown_jobtype(self):
        response1 = self.client.get(
            "/api/v1/jobtypes/UnknownJobType/software_requirements/")
        self.assert_not_found(response1)

    def test_jobtype_list_requirements_unknown_version(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.get(
            "/api/v1/jobtypes/TestJobType/versions/100/software_requirements/")
        self.assert_not_found(response2)

    def test_jobtype_post_requirement(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {"version": "1.0"},
                                    {"version": "1.1"}
                            ]
                       }))
        self.assert_created(response2)
        software_id = response2.json['id']
        software_min_version_id = response2.json["versions"][0]["id"]
        software_max_version_id = response2.json["versions"][1]["id"]

        response3 = self.client.post(
            "/api/v1/jobtypes/TestJobType/software_requirements/",
            content_type="application/json",
            data=dumps({
                        "software" : "foo",
                        "min_version": "1.0",
                        "max_version": "1.1"}))
        self.assert_created(response3)

        response4 = self.client.get(
            "/api/v1/jobtypes/TestJobType/software_requirements/")
        self.assert_ok(response4)
        self.assertEqual(response4.json, [
                {
                    "software": {
                        "software": "foo",
                        "id": software_id
                        },
                    "max_version": {
                        "version": "1.1",
                        "id": software_max_version_id
                        },
                    "min_version": {
                        "version": "1.0",
                        "id": software_min_version_id
                        },
                    "jobtype_version": {
                        "version": 2,
                        "jobtype": "TestJobType",
                        }
                }
                ])

    def test_jobtype_by_id_post_requirement(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)
        id = response1.json['id']

        response2 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": []
                       }))
        self.assert_created(response2)

        response3 = self.client.post(
            "/api/v1/jobtypes/%s/software_requirements/" % id,
            content_type="application/json",
            data=dumps({"software" : "foo"}))
        self.assert_created(response3)

    def test_jobtype_versioned_post_requirement(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)

        response2 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {"version": "1.0"},
                                    {"version": "1.1"}
                            ]
                       }))
        self.assert_created(response2)

        response3 = self.client.post(
            "/api/v1/jobtypes/TestJobType/versions/1/software_requirements/",
            content_type="application/json",
            data=dumps({"software" : "foo"}))
        self.assert_method_not_allowed(response3)

    def test_jobtype_post_requirement_unknown_jobtype(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": []
                       }))
        self.assert_created(response1)

        response2 = self.client.post(
            "/api/v1/jobtypes/UnknownJobType/software_requirements/",
            content_type="application/json",
            data=dumps({"software" : "foo"}))
        self.assert_not_found(response2)

    def test_jobtype_post_requirement_no_versions(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)

        response2 = self.client.delete("/api/v1/jobtypes/TestJobType/versions/1")
        self.assert_no_content(response2)

        response3 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({"software": "foo"}))
        self.assert_created(response3)

        response4 = self.client.post(
            "/api/v1/jobtypes/TestJobType/software_requirements/",
            content_type="application/json",
            data=dumps({"software" : "foo"}))
        self.assert_not_found(response4)

    def test_jobtype_post_requirement_bad_software(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)

        response2 = self.client.post(
            "/api/v1/jobtypes/TestJobType/software_requirements/",
            content_type="application/json",
            data=dumps({}))
        self.assert_bad_request(response2)

        response3 = self.client.post(
            "/api/v1/jobtypes/TestJobType/software_requirements/",
            content_type="application/json",
            data=dumps({"software": 42}))
        self.assert_bad_request(response3)

    def test_jobtype_post_requirement_unknown_software(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)

        response2 = self.client.post(
            "/api/v1/jobtypes/TestJobType/software_requirements/",
            content_type="application/json",
            data=dumps({"software": "unknown software"}))
        self.assert_not_found(response2)

    def test_jobtype_post_requirement_with_existing(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({"software": "foo",
                        "versions": [
                                    {"version": "1.0"},
                                    {"version": "1.1"}
                            ]
                       }))
        self.assert_created(response1)

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [{
                        "software" : "foo",
                        "min_version": "1.0",
                        "max_version": "1.1"}]
                    }))
        self.assert_created(response2)

        response2 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({"software": "bar",
                        "versions": [
                                    {"version": "0.1"},
                                    {"version": "0.2"}
                            ]
                       }))
        self.assert_created(response2)

        response3 = self.client.post(
            "/api/v1/jobtypes/TestJobType/software_requirements/",
            content_type="application/json",
            data=dumps({"software" : "bar",
                        "min_version": "0.1",
                        "max_version": "0.2"}))
        self.assert_created(response3)

        response4 = self.client.get(
            "/api/v1/jobtypes/TestJobType/software_requirements/")
        self.assert_ok(response4)
        self.assertEqual(len(response4.json), 2)

    def test_jobtype_post_requirement_conflict(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({"software": "foo"}))
        self.assert_created(response1)

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [{"software" : "foo"}]
                    }))
        self.assert_created(response2)

        response3 = self.client.post(
            "/api/v1/jobtypes/TestJobType/software_requirements/",
            content_type="application/json",
            data=dumps({"software" : "foo"}))
        self.assert_conflict(response3)

    def test_jobtype_post_requirement_bad_min_version(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({"software": "foo"}))
        self.assert_created(response1)

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response2)

        response3 = self.client.post(
            "/api/v1/jobtypes/TestJobType/software_requirements/",
            content_type="application/json",
            data=dumps({"software": "foo",
                        "min_version": 42}))
        self.assert_bad_request(response3)
 
    def test_jobtype_post_requirement_unknown_min_version(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({"software": "foo"}))
        self.assert_created(response1)

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response2)

        response3 = self.client.post(
            "/api/v1/jobtypes/TestJobType/software_requirements/",
            content_type="application/json",
            data=dumps({"software": "foo",
                        "min_version": "1.0"}))
        self.assert_not_found(response3)

    def test_jobtype_post_requirement_bad_max_version(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({"software": "foo"}))
        self.assert_created(response1)

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response2)

        response3 = self.client.post(
            "/api/v1/jobtypes/TestJobType/software_requirements/",
            content_type="application/json",
            data=dumps({"software": "foo",
                        "max_version": 42}))
        self.assert_bad_request(response3)
 
    def test_jobtype_post_requirement_unknown_max_version(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({"software": "foo"}))
        self.assert_created(response1)

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response2)

        response3 = self.client.post(
            "/api/v1/jobtypes/TestJobType/software_requirements/",
            content_type="application/json",
            data=dumps({"software": "foo",
                        "max_version": "1.0"}))
        self.assert_not_found(response3)

    def test_jobtype_get_single_requirement(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {"version": "1.0"},
                                    {"version": "1.1"}
                            ]
                       }))
        self.assert_created(response1)
        software_id = response1.json['id']
        software_min_version_id = response1.json["versions"][0]["id"]
        software_max_version_id = response1.json["versions"][1]["id"]

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {
                            "software": "foo",
                            "min_version": "1.0",
                            "max_version": "1.1"
                        }
                        ]
                    }))
        self.assert_created(response2)
        id = response2.json['id']

        response3 = self.client.get(
            "/api/v1/jobtypes/TestJobType/software_requirements/foo")
        self.assert_ok(response3)
        self.assertEqual(
            response3.json, {
                    "software": {
                            "software": "foo",
                            "id": software_id
                        },
                    "max_version": {
                            "version": "1.1",
                            "id": software_max_version_id
                        },
                    "min_version": 
                        {
                            "version": "1.0",
                            "id": software_min_version_id
                        },
                    "jobtype_version": {
                            "version": 1,
                            "jobtype": "TestJobType",
                        }
                })

        response4 = self.client.get(
            "/api/v1/jobtypes/%s/software_requirements/foo" % id)
        self.assert_ok(response4)

    def test_jobtype_single_requirement_unknown_jobtype(self):
        response1 = self.client.get(
            "/api/v1/jobtypes/UnknownJobType/software_requirements/1")
        self.assert_not_found(response1)

    def test_jobtype_single_requirement_no_versions(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)

        response2 = self.client.delete("/api/v1/jobtypes/TestJobType/versions/1")
        self.assert_no_content(response2)

        response3 = self.client.get(
            "/api/v1/jobtypes/TestJobType/software_requirements/1")
        self.assert_not_found(response3)

    def test_jobtype_single_requirement_not_found(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)

        response2 = self.client.get(
            "/api/v1/jobtypes/TestJobType/software_requirements/1")
        self.assert_not_found(response2)

    def test_jobtype_delete_requirement(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "foo",
                        "versions": [
                                    {"version": "1.0"},
                                    {"version": "1.1"}
                            ]
                       }))
        self.assert_created(response1)

        response2 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({
                        "software": "bar",
                        "versions": [
                                    {"version": "0.1"},
                                    {"version": "0.2"}
                            ]
                       }))
        self.assert_created(response2)

        response3 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {
                            "software": "foo",
                            "min_version": "1.0",
                            "max_version": "1.1"
                        },
                        {
                            "software": "bar",
                            "min_version": "0.1",
                            "max_version": "0.2"
                        }
                        ]
                    }))
        self.assert_created(response3)
        id = response3.json['id']

        response4 = self.client.delete(
            "/api/v1/jobtypes/TestJobType/software_requirements/foo")
        self.assert_no_content(response4)

        response5 = self.client.delete(
            "/api/v1/jobtypes/TestJobType/software_requirements/foo")
        self.assert_no_content(response5)

        response6 = self.client.get(
            "/api/v1/jobtypes/TestJobType/software_requirements/foo")
        self.assert_not_found(response6)

        response7 = self.client.get(
            "/api/v1/jobtypes/TestJobType/software_requirements/bar")
        self.assert_ok(response7)

    def test_jobtype_by_id_delete_requirement(self):
        response1 = self.client.post(
            "/api/v1/software/",
            content_type="application/json",
            data=dumps({"software": "foo"}))
        self.assert_created(response1)

        response2 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code,
                    "software_requirements": [
                        {"software": "foo"}
                        ]
                    }))
        self.assert_created(response2)
        id = response2.json['id']

        response3 = self.client.delete(
            "/api/v1/jobtypes/%s/software_requirements/foo" % id)
        self.assert_no_content(response3)

        response4 = self.client.get(
            "/api/v1/jobtypes/TestJobType/software_requirements/")
        self.assertEqual(len(response4.json), 0)

    def test_jobtype_delete_requirement_unknown_jobtype(self):
        response1 = self.client.delete(
            "/api/v1/jobtypes/UnknownJobType/software_requirements/1")
        self.assert_not_found(response1)

    def test_jobtype_delete_requirement_no_versions(self):
        response1 = self.client.put(
            "/api/v1/jobtypes/TestJobType",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": code
                    }))
        self.assert_created(response1)

        response2 = self.client.delete("/api/v1/jobtypes/TestJobType/versions/1")
        self.assert_no_content(response2)

        response3 = self.client.delete(
            "/api/v1/jobtypes/TestJobType/software_requirements/1")
        self.assert_not_found(response3)

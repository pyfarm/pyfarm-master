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

from pyfarm.models.core.cfg import MAX_JOBTYPE_LENGTH
from pyfarm.master.application import get_api_blueprint
from pyfarm.master.entrypoints.main import load_api
from pyfarm.models.job import Job

jobtype_code = """from pyfarm.jobtypes.core.jobtype import JobType

class TestJobType(JobType):
    def get_command(self):
        return "/usr/bin/touch"
    def get_arguments(self):
        return [os.path.join(
            self.assignment_data["job"]["data"]["path"],
            "%04d" % self.assignment_data[\"tasks\"][0][\"frame\"])]
"""


class TestJobAPI(BaseTestCase):
    def setup_app(self):
        super(TestJobAPI, self).setup_app()
        self.api = get_api_blueprint()
        self.app.register_blueprint(self.api)
        load_api(self.app, self.api)

    def test_jobtype_schema(self):
        response = self.client.get("/api/v1/jobs/schema")
        self.assert_ok(response)
        schema = Job.to_schema()
        schema["start"] = "NUMERIC(10,4)"
        schema["end"] = "NUMERIC(10,4)"
        del schema["jobtype_version_id"]
        schema["jobtype"] = "VARCHAR(%s)" % MAX_JOBTYPE_LENGTH
        schema["jobtype_version"] = "INTEGER"
        self.assertEqual(response.json, schema)

    def test_jobtype_post(self):
        self.maxDiff = None
        response1 = self.client.post(
            "/api/v1/jobtypes/",
            content_type="application/json",
            data=dumps({
                    "name": "TestJobType",
                    "description": "Jobtype for testing inserts and queries",
                    "max_batch": 1,
                    "code": jobtype_code
                    }))
        self.assert_created(response1)
        jobtype_id = response1.json['id']

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
            "/api/v1/jobs/",
            content_type="application/json",
            data=dumps({
                    "start": 1.0,
                    "end": 2.0,
                    "title": "Test Job",
                    "jobtype": "TestJobType",
                    "data": {"foo": "bar"},
                    "software_requirements": [
                            {
                                "software": "foo",
                                "min_version": "1.0",
                                "max_version": "1.1"}
                        ]
                    }))
        self.assert_created(response3)
        self.assertIn("time_submitted", response3.json)
        time_submitted = response3.json["time_submitted"]
        id = response3.json["id"]
        self.assertEqual(response3.json,
                        {
                            "id": id,
                            "time_finished": None,
                            "time_started": None,
                            "end": 2.0,
                            "time_submitted": time_submitted,
                            "jobtype_version": 1,
                            "jobtype": "TestJobType",
                            "start": 1.0,
                            "priority": 0,
                            "state": "queued",
                            "parents": [],
                            "hidden": False,
                            "project_id": None,
                            "ram_warning": None,
                            "title": "Test Job",
                            "tags": [],
                            "user": None,
                            "by": 1.0,
                            "data": {"foo": "bar"},
                            "ram_max": None,
                            "notes": "",
                            "batch": 1,
                            "environ": None,
                            "requeue": 3,
                            "software_requirements": [
                                {
                                    "min_version": "1.0",
                                    "max_version": "1.1",
                                    "max_version_id": software_max_version_id,
                                    "software_id": 1,
                                    "min_version_id": software_min_version_id,
                                    "software": "foo"
                                }
                            ],
                            "ram": 32,
                            "cpus": 1,
                            "children": []
                         })
